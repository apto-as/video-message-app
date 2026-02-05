"""
Smart upper-body cropper for LivePortrait/MuseTalk input preparation.

Detects face landmarks using face_alignment (68-point iBUG) to compute an
optimal upper-body crop region, then resizes to a square output (default 512x512).

Fallback chain:
  1. Face landmarks detected -> landmark-based crop
  2. No face but YOLO person detected -> center crop of person bbox
  3. No person detected -> center crop of full image
"""

import asyncio
import io
import logging
import threading
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_cropper_instance: Optional["UpperBodyCropper"] = None
_cropper_lock = threading.Lock()


def get_upper_body_cropper(target_size: int = 512, face_ratio: float = 0.5) -> "UpperBodyCropper":
    """Get or create the singleton UpperBodyCropper instance.

    Args:
        target_size: Output square size in pixels (used only on first call).
        face_ratio: Target face-height ratio (0.0-1.0). The cropper uses
            ``face_ratio - 0.10`` as min and ``face_ratio + 0.10`` as max.
    """
    global _cropper_instance
    if _cropper_instance is not None:
        return _cropper_instance
    with _cropper_lock:
        if _cropper_instance is None:
            ratio_min = max(0.1, face_ratio - 0.10)
            ratio_max = min(1.0, face_ratio + 0.10)
            _cropper_instance = UpperBodyCropper(
                target_size=target_size,
                face_ratio_min=ratio_min,
                face_ratio_max=ratio_max,
            )
    return _cropper_instance


# ---------------------------------------------------------------------------
# UpperBodyCropper
# ---------------------------------------------------------------------------

class UpperBodyCropper:
    """Smart upper-body cropper for LivePortrait/MuseTalk input preparation."""

    # Maximum input image size (defense-in-depth, upstream also enforces 10MB)
    _MAX_INPUT_BYTES = 10 * 1024 * 1024  # 10MB

    def __init__(
        self,
        target_size: int = 512,
        face_ratio_min: float = 0.40,
        face_ratio_max: float = 0.60,
    ):
        self._face_alignment = None
        self._fa_lock = threading.Lock()
        self._fa_unavailable = False  # Set True if face_alignment import fails
        self._target_size = target_size
        self._face_ratio_min = face_ratio_min
        self._face_ratio_max = face_ratio_max
        self._person_detector = None  # Cached PersonDetector instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def crop_upper_body(self, image_bytes: bytes) -> Tuple[bytes, Dict]:
        """
        Main entry point.  Runs CPU-bound work in a thread-pool executor.

        Returns:
            (cropped_jpeg_bytes, metadata_dict)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._crop_sync, image_bytes)

    # ------------------------------------------------------------------
    # Internal (synchronous, runs inside executor)
    # ------------------------------------------------------------------

    def _crop_sync(self, image_bytes: bytes) -> Tuple[bytes, Dict]:
        """Synchronous crop pipeline."""
        # FINDING-001: Input validation (defense-in-depth)
        if not image_bytes or len(image_bytes) > self._MAX_INPUT_BYTES:
            raise ValueError(
                f"Invalid image: size={len(image_bytes) if image_bytes else 0} bytes "
                f"(max {self._MAX_INPUT_BYTES})"
            )

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)  # H x W x 3, uint8, RGB

        metadata: Dict = {
            "original_size": list(image_np.shape[:2]),
            "target_size": self._target_size,
            "method": "unknown",
        }

        # 1. Try face-landmark crop
        landmarks = self._detect_face_landmarks(image_np)
        if landmarks is not None:
            crop_region = self._compute_crop_region(landmarks, image_np.shape)
            face_height = float(np.max(landmarks[:, 1]) - np.min(landmarks[:, 1]))
            crop_h = crop_region[3] - crop_region[1]

            # If face already occupies >max ratio of image, skip crop and just resize
            if face_height / image_np.shape[0] > self._face_ratio_max:
                result_np = self._fallback_center_crop(image_np)
                metadata["method"] = "face_too_large_resize"
            else:
                result_np = self._crop_and_resize(image_np, crop_region)
                metadata["method"] = "face_landmark"
                metadata["face_height_ratio"] = round(face_height / crop_h, 3)

            metadata["crop_region"] = list(crop_region)
            return self._encode_jpeg(result_np), metadata

        # 2. Fallback: YOLO person detection
        person_bbox = self._detect_person_yolo(image_bytes)
        if person_bbox is not None:
            x1, y1, x2, y2 = person_bbox
            person_crop = image_np[y1:y2, x1:x2]
            result_np = self._fallback_center_crop(person_crop)
            metadata["method"] = "yolo_person_center"
            metadata["person_bbox"] = list(person_bbox)
            return self._encode_jpeg(result_np), metadata

        # 3. Fallback: center crop of full image
        result_np = self._fallback_center_crop(image_np)
        metadata["method"] = "full_image_center"
        return self._encode_jpeg(result_np), metadata

    # ------------------------------------------------------------------
    # Face alignment (lazy-loaded, CPU-only)
    # ------------------------------------------------------------------

    def _load_face_alignment(self):
        """Lazy-load face_alignment model (CPU-only, thread-safe)."""
        if self._face_alignment is not None or self._fa_unavailable:
            return
        with self._fa_lock:
            if self._face_alignment is None and not self._fa_unavailable:
                try:
                    import face_alignment

                    logger.info("UpperBodyCropper: initializing face_alignment (CPU)...")
                    self._face_alignment = face_alignment.FaceAlignment(
                        face_alignment.LandmarksType.TWO_D,
                        flip_input=False,
                        device="cpu",
                    )
                    logger.info("UpperBodyCropper: face_alignment initialized")
                except ImportError:
                    self._fa_unavailable = True
                    logger.warning(
                        "UpperBodyCropper: face_alignment not installed, "
                        "falling back to YOLO-only mode"
                    )

    def _detect_face_landmarks(self, image_np: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect 68-point iBUG face landmarks.  If multiple faces are found,
        return landmarks for the largest (most prominent) face.

        Args:
            image_np: RGB uint8 array (H, W, 3)

        Returns:
            (68, 2) ndarray of landmark coordinates, or None
        """
        self._load_face_alignment()
        if self._face_alignment is None:
            return None
        try:
            preds = self._face_alignment.get_landmarks(image_np)
        except Exception as e:
            logger.warning(f"face_alignment inference failed: {e}")
            return None

        if preds is None or len(preds) == 0:
            return None

        if len(preds) == 1:
            return preds[0].astype(np.float64)

        # Multiple faces -- pick the one with the largest bounding area
        best_idx = 0
        best_area = 0.0
        for i, lm in enumerate(preds):
            w = np.max(lm[:, 0]) - np.min(lm[:, 0])
            h = np.max(lm[:, 1]) - np.min(lm[:, 1])
            area = w * h
            if area > best_area:
                best_area = area
                best_idx = i
        return preds[best_idx].astype(np.float64)

    # ------------------------------------------------------------------
    # Crop region computation
    # ------------------------------------------------------------------

    def _compute_crop_region(
        self, landmarks: np.ndarray, image_shape: tuple
    ) -> Tuple[int, int, int, int]:
        """
        Compute upper-body crop region from face landmarks.

        Strategy:
          - Face center: landmark[29] (nose bridge)
          - Face height: max(y) - min(y) of all landmarks
          - Face width:  max(x) - min(x) of all landmarks
          - Top:    min(y) - 1.5 * face_height   (hair / hat space)
          - Bottom: max(y) + 1.5 * face_height   (neck / upper chest)
          - Left:   face_center_x - 1.5 * face_width
          - Right:  face_center_x + 1.5 * face_width
          - Clamp all to image boundaries
          - Ensure square aspect (expand shorter axis symmetrically)
        """
        img_h, img_w = image_shape[:2]

        face_center_x = float(landmarks[29, 0])
        min_x = float(np.min(landmarks[:, 0]))
        max_x = float(np.max(landmarks[:, 0]))
        min_y = float(np.min(landmarks[:, 1]))
        max_y = float(np.max(landmarks[:, 1]))

        face_width = max_x - min_x
        face_height = max_y - min_y

        # Raw region
        top = min_y - 1.5 * face_height
        bottom = max_y + 1.5 * face_height
        left = face_center_x - 1.5 * face_width
        right = face_center_x + 1.5 * face_width

        # Make square (use the larger dimension)
        region_w = right - left
        region_h = bottom - top
        if region_w > region_h:
            diff = region_w - region_h
            top -= diff / 2
            bottom += diff / 2
        elif region_h > region_w:
            diff = region_h - region_w
            left -= diff / 2
            right += diff / 2

        # Adjust face ratio: target 40-60% of crop height
        crop_h = bottom - top
        ratio = face_height / crop_h if crop_h > 0 else 0
        if ratio < self._face_ratio_min and crop_h > 0:
            # Face too small relative to crop -- shrink crop
            desired_h = face_height / self._face_ratio_min
            delta = (crop_h - desired_h) / 2
            top += delta
            bottom -= delta
            # Keep square
            left += delta
            right -= delta
        elif ratio > self._face_ratio_max and crop_h > 0:
            # Face too large relative to crop -- expand crop
            desired_h = face_height / self._face_ratio_max
            delta = (desired_h - crop_h) / 2
            top -= delta
            bottom += delta
            left -= delta
            right += delta

        # Clamp to image boundaries
        top = max(0.0, top)
        left = max(0.0, left)
        bottom = min(float(img_h), bottom)
        right = min(float(img_w), right)

        return int(round(left)), int(round(top)), int(round(right)), int(round(bottom))

    # ------------------------------------------------------------------
    # Crop & resize helpers
    # ------------------------------------------------------------------

    def _crop_and_resize(
        self, image_np: np.ndarray, crop_region: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Crop to region, pad to square if needed (reflected border), resize to
        target_size x target_size.

        Args:
            image_np: RGB uint8 (H, W, 3)
            crop_region: (x1, y1, x2, y2)

        Returns:
            RGB uint8 (target_size, target_size, 3)
        """
        x1, y1, x2, y2 = crop_region
        cropped = image_np[y1:y2, x1:x2]

        if cropped.size == 0:
            return self._fallback_center_crop(image_np)

        # Pad to square
        h, w = cropped.shape[:2]
        if h != w:
            size = max(h, w)
            padded = np.zeros((size, size, 3), dtype=np.uint8)
            y_off = (size - h) // 2
            x_off = (size - w) // 2
            padded[y_off : y_off + h, x_off : x_off + w] = cropped

            # Fill padding with reflected border pixels for natural look
            if y_off > 0:
                # top padding -- reflect top rows
                for i in range(y_off):
                    src_row = min(y_off + (y_off - i), y_off + h - 1)
                    padded[i, x_off : x_off + w] = padded[src_row, x_off : x_off + w]
            if y_off + h < size:
                # bottom padding
                for i in range(y_off + h, size):
                    src_row = max(y_off + h - 1 - (i - y_off - h), y_off)
                    padded[i, x_off : x_off + w] = padded[src_row, x_off : x_off + w]
            if x_off > 0:
                # left padding
                for j in range(x_off):
                    src_col = min(x_off + (x_off - j), x_off + w - 1)
                    padded[:, j] = padded[:, src_col]
            if x_off + w < size:
                # right padding
                for j in range(x_off + w, size):
                    src_col = max(x_off + w - 1 - (j - x_off - w), x_off)
                    padded[:, j] = padded[:, src_col]

            cropped = padded

        # Resize to target
        pil_img = Image.fromarray(cropped)
        pil_img = pil_img.resize(
            (self._target_size, self._target_size), Image.LANCZOS
        )
        return np.array(pil_img)

    def _fallback_center_crop(self, image_np: np.ndarray) -> np.ndarray:
        """
        Fallback: center crop to square then resize to target_size.

        Args:
            image_np: RGB uint8 (H, W, 3)

        Returns:
            RGB uint8 (target_size, target_size, 3)
        """
        h, w = image_np.shape[:2]
        size = min(h, w)
        y_off = (h - size) // 2
        x_off = (w - size) // 2
        cropped = image_np[y_off : y_off + size, x_off : x_off + size]

        pil_img = Image.fromarray(cropped)
        pil_img = pil_img.resize(
            (self._target_size, self._target_size), Image.LANCZOS
        )
        return np.array(pil_img)

    # ------------------------------------------------------------------
    # YOLO person detection fallback
    # ------------------------------------------------------------------

    def _detect_person_yolo(self, image_bytes: bytes) -> Optional[Tuple[int, int, int, int]]:
        """
        Fallback person detection using existing PersonDetector singleton.
        Saves bytes to a temp file because PersonDetector.detect_persons()
        expects a file path.

        Returns:
            (x1, y1, x2, y2) of the largest person bbox, or None
        """
        import tempfile
        import os

        tmp_path = None
        try:
            from services.person_detector import PersonDetector

            # FINDING-002: Write directly via fd to eliminate TOCTOU window
            fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
            try:
                os.write(fd, image_bytes)
            finally:
                os.close(fd)

            # FINDING-004: Cache PersonDetector to avoid GPU memory re-allocation
            if self._person_detector is None:
                self._person_detector = PersonDetector()
            persons = self._person_detector.detect_persons(tmp_path, conf_threshold=0.3)
            if not persons:
                return None

            # Pick largest by area
            largest = max(persons, key=lambda p: p["area"])
            bbox = largest["bbox"]
            return (bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"])

        except Exception as e:
            logger.warning(f"YOLO person detection fallback failed: {e}")
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_jpeg(image_np: np.ndarray, quality: int = 95) -> bytes:
        """Encode RGB numpy array to JPEG bytes."""
        pil_img = Image.fromarray(image_np)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
