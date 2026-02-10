"""
MediaPipe-based blink animation processor for MuseTalk post-processing.

Adds natural blinking to lip-synced videos using MediaPipe FaceMesh
for accurate eye region detection and smooth eyelid animations.

Performance: ~1-3 seconds additional processing for typical videos.
"""

import logging
import random
import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_blink_processor_instance: Optional["BlinkProcessor"] = None
_blink_processor_lock = threading.Lock()


def get_blink_processor() -> "BlinkProcessor":
    """Get or create the singleton BlinkProcessor instance."""
    global _blink_processor_instance
    if _blink_processor_instance is not None:
        return _blink_processor_instance
    with _blink_processor_lock:
        if _blink_processor_instance is None:
            _blink_processor_instance = BlinkProcessor()
    return _blink_processor_instance


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BlinkEvent:
    """Represents a single blink event."""
    start_frame: int
    end_frame: int
    peak_frame: int  # Frame with maximum closure


@dataclass
class EyeRegion:
    """Eye region bounding box and landmarks."""
    # Bounding box (x1, y1, x2, y2)
    bbox: Tuple[int, int, int, int]
    # Center point
    center: Tuple[int, int]
    # Original landmark points for the eye
    landmarks: np.ndarray


# ---------------------------------------------------------------------------
# MediaPipe FaceMesh landmark indices for eyes
# ---------------------------------------------------------------------------

# Left eye contour (looking at the person)
LEFT_EYE_INDICES = [
    33, 7, 163, 144, 145, 153, 154, 155, 133,
    173, 157, 158, 159, 160, 161, 246
]

# Right eye contour
RIGHT_EYE_INDICES = [
    362, 382, 381, 380, 374, 373, 390, 249,
    263, 466, 388, 387, 386, 385, 384, 398
]

# Upper/lower eyelid for measuring openness
LEFT_EYE_UPPER = [159, 158, 157, 173, 133]
LEFT_EYE_LOWER = [145, 144, 163, 7, 33]
RIGHT_EYE_UPPER = [386, 385, 384, 398, 263]
RIGHT_EYE_LOWER = [374, 380, 381, 382, 362]


# ---------------------------------------------------------------------------
# BlinkProcessor
# ---------------------------------------------------------------------------

class BlinkProcessor:
    """
    Adds natural blink animations to video frames using MediaPipe FaceMesh.

    The processor:
    1. Generates a random blink schedule (3-5 second intervals)
    2. Detects eye regions using MediaPipe
    3. Applies smooth eyelid closing/opening animations
    """

    def __init__(self):
        self._face_mesh = None
        self._mesh_lock = threading.Lock()
        self._mesh_unavailable = False

    # ------------------------------------------------------------------
    # Lazy-load MediaPipe FaceMesh
    # ------------------------------------------------------------------

    def _load_face_mesh(self):
        """Lazy-load MediaPipe FaceMesh (CPU-only, thread-safe)."""
        if self._face_mesh is not None or self._mesh_unavailable:
            return
        with self._mesh_lock:
            if self._face_mesh is None and not self._mesh_unavailable:
                try:
                    import mediapipe as mp

                    logger.info("BlinkProcessor: initializing MediaPipe FaceMesh...")
                    self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                        static_image_mode=False,  # Video mode for faster processing
                        max_num_faces=1,
                        refine_landmarks=True,  # Includes iris landmarks
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    logger.info("BlinkProcessor: MediaPipe FaceMesh initialized")
                except ImportError:
                    self._mesh_unavailable = True
                    logger.warning(
                        "BlinkProcessor: mediapipe not installed, "
                        "blink animation will be skipped"
                    )
                except Exception as e:
                    self._mesh_unavailable = True
                    logger.error(f"BlinkProcessor: Failed to initialize FaceMesh: {e}")

    # ------------------------------------------------------------------
    # Resource Management
    # ------------------------------------------------------------------

    def close(self) -> None:
        """
        Release MediaPipe FaceMesh resources.

        Call this method when the processor is no longer needed to free memory.
        The processor can be reused after calling close() - the model will be
        lazy-loaded again on next use.
        """
        with self._mesh_lock:
            if self._face_mesh is not None:
                try:
                    self._face_mesh.close()
                    logger.info("BlinkProcessor: MediaPipe FaceMesh closed")
                except Exception as e:
                    logger.warning(f"BlinkProcessor: Error closing FaceMesh: {e}")
                finally:
                    self._face_mesh = None

    def __del__(self):
        """Destructor to ensure resources are released."""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during garbage collection

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_blinks_to_frames(
        self,
        frames: List[np.ndarray],
        fps: int = 25,
        blink_interval_range: Tuple[float, float] = (3.0, 5.0),
        blink_duration_range: Tuple[float, float] = (0.15, 0.30),
    ) -> List[np.ndarray]:
        """
        Add natural blink animations to video frames.

        Args:
            frames: List of BGR numpy arrays (H, W, 3)
            fps: Video frame rate
            blink_interval_range: (min, max) seconds between blinks
            blink_duration_range: (min, max) seconds per blink

        Returns:
            List of frames with blink animations applied
        """
        if not frames:
            return frames

        self._load_face_mesh()
        if self._face_mesh is None:
            logger.warning("BlinkProcessor: FaceMesh unavailable, returning original frames")
            return frames

        # Generate blink schedule
        total_duration = len(frames) / fps
        blink_events = self._generate_blink_schedule(
            total_duration=total_duration,
            fps=fps,
            interval_range=blink_interval_range,
            duration_range=blink_duration_range
        )

        if not blink_events:
            logger.info("BlinkProcessor: No blinks scheduled for this video duration")
            return frames

        logger.info(f"BlinkProcessor: Scheduled {len(blink_events)} blinks for {len(frames)} frames")

        # Apply blinks to frames
        result_frames = []
        blink_frame_set = self._build_blink_frame_map(blink_events)

        for i, frame in enumerate(frames):
            if i in blink_frame_set:
                # This frame needs blink animation
                blink_progress = blink_frame_set[i]
                processed = self._apply_blink_to_frame(frame, blink_progress)
                result_frames.append(processed)
            else:
                result_frames.append(frame)

        return result_frames

    # ------------------------------------------------------------------
    # Blink schedule generation
    # ------------------------------------------------------------------

    def _generate_blink_schedule(
        self,
        total_duration: float,
        fps: int,
        interval_range: Tuple[float, float],
        duration_range: Tuple[float, float]
    ) -> List[BlinkEvent]:
        """Generate random blink events throughout the video."""
        events = []
        current_time = random.uniform(0.5, interval_range[0])  # Start after 0.5-interval_min sec

        while current_time < total_duration - duration_range[1]:
            # Random blink duration
            blink_duration = random.uniform(*duration_range)

            start_frame = int(current_time * fps)
            end_frame = int((current_time + blink_duration) * fps)
            # Peak is at 40% through the blink (close phase)
            peak_frame = start_frame + int((end_frame - start_frame) * 0.4)

            events.append(BlinkEvent(
                start_frame=start_frame,
                end_frame=end_frame,
                peak_frame=peak_frame
            ))

            # Next blink after random interval
            interval = random.uniform(*interval_range)
            current_time += blink_duration + interval

        return events

    def _build_blink_frame_map(self, events: List[BlinkEvent]) -> dict:
        """
        Build a mapping of frame_index -> blink_progress (0.0 to 1.0).

        Progress represents eye closure amount:
        - 0.0: Eyes fully open
        - 1.0: Eyes fully closed

        Blink phases:
        - Close phase (0-40%): Progress increases 0 -> 1
        - Hold phase (40-60%): Progress stays at 1
        - Open phase (60-100%): Progress decreases 1 -> 0
        """
        frame_map = {}

        for event in events:
            total_frames = event.end_frame - event.start_frame
            if total_frames <= 0:
                continue

            for i in range(event.start_frame, event.end_frame + 1):
                # Calculate normalized position within blink (0.0 to 1.0)
                pos = (i - event.start_frame) / total_frames

                # Convert position to closure amount using smooth curve
                if pos < 0.4:
                    # Closing phase: ease-in
                    t = pos / 0.4
                    progress = self._ease_in_out(t)
                elif pos < 0.6:
                    # Hold phase: fully closed
                    progress = 1.0
                else:
                    # Opening phase: ease-out
                    t = (pos - 0.6) / 0.4
                    progress = 1.0 - self._ease_in_out(t)

                frame_map[i] = progress

        return frame_map

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Smooth easing function (cubic)."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def _apply_blink_to_frame(
        self,
        frame: np.ndarray,
        blink_progress: float
    ) -> np.ndarray:
        """
        Apply blink animation to a single frame.

        Args:
            frame: BGR numpy array (H, W, 3)
            blink_progress: 0.0 (open) to 1.0 (closed)

        Returns:
            Modified frame with blinking eyes
        """
        if blink_progress < 0.01:
            # Negligible blink, return original
            return frame

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            # No face detected, return original
            return frame

        face_landmarks = results.multi_face_landmarks[0]
        h, w = frame.shape[:2]

        # Get eye regions
        left_eye = self._get_eye_region(face_landmarks, LEFT_EYE_INDICES, w, h)
        right_eye = self._get_eye_region(face_landmarks, RIGHT_EYE_INDICES, w, h)

        if left_eye is None or right_eye is None:
            return frame

        # Apply blink effect to each eye
        result = frame.copy()
        result = self._apply_eye_close(result, left_eye, blink_progress)
        result = self._apply_eye_close(result, right_eye, blink_progress)

        return result

    def _get_eye_region(
        self,
        face_landmarks,
        indices: List[int],
        img_width: int,
        img_height: int
    ) -> Optional[EyeRegion]:
        """Extract eye region from face landmarks."""
        try:
            points = []
            for idx in indices:
                lm = face_landmarks.landmark[idx]
                x = int(lm.x * img_width)
                y = int(lm.y * img_height)
                points.append([x, y])

            points = np.array(points, dtype=np.int32)

            x_min, y_min = points.min(axis=0)
            x_max, y_max = points.max(axis=0)

            # Add padding
            padding = max(5, int((x_max - x_min) * 0.2))
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(img_width, x_max + padding)
            y_max = min(img_height, y_max + padding)

            center_x = (x_min + x_max) // 2
            center_y = (y_min + y_max) // 2

            return EyeRegion(
                bbox=(x_min, y_min, x_max, y_max),
                center=(center_x, center_y),
                landmarks=points
            )
        except Exception as e:
            logger.warning(f"Failed to extract eye region: {e}")
            return None

    def _apply_eye_close(
        self,
        frame: np.ndarray,
        eye: EyeRegion,
        progress: float
    ) -> np.ndarray:
        """
        Apply eye closing effect by scaling the eye region vertically.

        Uses affine transformation to compress the eye region toward
        its center, simulating eyelid closure.
        """
        x1, y1, x2, y2 = eye.bbox
        cx, cy = eye.center

        # Region dimensions
        region_w = x2 - x1
        region_h = y2 - y1

        if region_w <= 0 or region_h <= 0:
            return frame

        # Scale factor: 1.0 (open) -> 0.2 (nearly closed)
        # We don't go to 0 to avoid artifacts
        scale_y = 1.0 - (progress * 0.8)

        # Extract eye region
        eye_region = frame[y1:y2, x1:x2].copy()

        # Create scaled version
        new_h = max(1, int(region_h * scale_y))
        scaled = cv2.resize(eye_region, (region_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Calculate vertical offset to center the scaled region
        y_offset = (region_h - new_h) // 2

        # Create output region with skin color fill
        # Sample skin color from just above the eye
        skin_sample_y = max(0, y1 - 5)
        skin_color = frame[skin_sample_y, cx].astype(np.float32)

        # Fill with skin color
        output_region = np.full_like(eye_region, skin_color, dtype=np.uint8)

        # Place scaled eye in center
        if new_h > 0:
            output_region[y_offset:y_offset + new_h, :] = scaled

        # Smooth blending at edges
        # Create a soft mask for blending
        mask = np.zeros((region_h, region_w), dtype=np.float32)

        # Horizontal gradient at left and right edges
        blend_width = min(10, region_w // 4)
        for i in range(blend_width):
            alpha = i / blend_width
            mask[:, i] = alpha
            mask[:, region_w - 1 - i] = alpha
        mask[:, blend_width:region_w - blend_width] = 1.0

        # Vertical gradient at top and bottom
        blend_height = min(5, region_h // 4)
        for i in range(blend_height):
            alpha = i / blend_height
            mask[i, :] *= alpha
            mask[region_h - 1 - i, :] *= alpha

        # Apply blended result
        mask_3d = np.stack([mask] * 3, axis=-1)
        blended = (
            output_region.astype(np.float32) * mask_3d +
            frame[y1:y2, x1:x2].astype(np.float32) * (1 - mask_3d)
        ).astype(np.uint8)

        frame[y1:y2, x1:x2] = blended

        return frame
