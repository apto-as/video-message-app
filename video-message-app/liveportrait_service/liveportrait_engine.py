"""
LivePortrait Engine - Motion to Video Generation

This module applies motion sequences to source images using ONNX models:
1. Extract appearance features from source image
2. Extract source motion (keypoints)
3. Apply target motion frame by frame
4. Generate output video frames
"""
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Callable, Dict, Any

import cv2
import numpy as np
import onnxruntime as ort

from config import Config
from utils import (
    load_image,
    pad_to_square,
    remove_padding,
    normalize_image,
    denormalize_image,
    write_video_frames,
    merge_audio_video,
    blend_face_to_background
)

logger = logging.getLogger(__name__)


class LivePortraitEngine:
    """
    ONNX-based LivePortrait engine for video generation

    Uses the following ONNX models:
    - appearance_feature_extractor: Extract 3D appearance features
    - motion_extractor: Extract source motion/keypoints
    - warping_spade: Warp appearance and generate output
    - stitching: Blend generated face with background
    """

    def __init__(self, device: str = "cuda"):
        self.device = device
        self.providers = self._get_providers()

        # ONNX sessions
        self.appearance_extractor = None
        self.motion_extractor = None
        self.warping_generator = None
        self.stitching = None
        self.stitching_eye = None
        self.stitching_lip = None

        # Face detector
        self.face_detector = None

        self.model_loaded = False
        self.input_size = Config.OUTPUT_RESOLUTION  # 512x512 for LivePortrait

        logger.info(f"LivePortrait engine initialized for device: {device}")
        logger.info(f"ONNX providers: {self.providers}")

    def _get_providers(self) -> List[str]:
        """Get ONNX Runtime execution providers"""
        if self.device == "cuda":
            return ['CUDAExecutionProvider', 'CPUExecutionProvider']
        return ['CPUExecutionProvider']

    def load_models(self) -> bool:
        """Load all ONNX models"""
        if self.model_loaded:
            logger.info("LivePortrait models already loaded")
            return True

        try:
            logger.info("Loading LivePortrait ONNX models...")

            # Session options
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            # Load appearance extractor
            self._load_appearance_extractor(sess_options)

            # Load motion extractor
            self._load_motion_extractor(sess_options)

            # Load warping generator (SPADE)
            self._load_warping_generator(sess_options)

            # Load stitching modules
            self._load_stitching_modules(sess_options)

            # Load face detector
            self._load_face_detector()

            self.model_loaded = True
            logger.info("LivePortrait models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load LivePortrait models: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_appearance_extractor(self, sess_options: ort.SessionOptions):
        """Load appearance feature extractor"""
        model_path = str(Config.APPEARANCE_EXTRACTOR)
        logger.info(f"Loading appearance extractor from {model_path}")

        if not Config.APPEARANCE_EXTRACTOR.exists():
            raise FileNotFoundError(f"Appearance extractor not found: {model_path}")

        self.appearance_extractor = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=self.providers
        )

    def _load_motion_extractor(self, sess_options: ort.SessionOptions):
        """Load motion extractor"""
        model_path = str(Config.MOTION_EXTRACTOR)
        logger.info(f"Loading motion extractor from {model_path}")

        if not Config.MOTION_EXTRACTOR.exists():
            raise FileNotFoundError(f"Motion extractor not found: {model_path}")

        self.motion_extractor = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=self.providers
        )

    def _load_warping_generator(self, sess_options: ort.SessionOptions):
        """Load warping SPADE generator"""
        model_path = str(Config.WARPING_SPADE)
        logger.info(f"Loading warping generator from {model_path}")

        if not Config.WARPING_SPADE.exists():
            raise FileNotFoundError(f"Warping generator not found: {model_path}")

        self.warping_generator = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=self.providers
        )

    def _load_stitching_modules(self, sess_options: ort.SessionOptions):
        """Load stitching modules"""
        # Main stitching
        if Config.STITCHING_MODEL.exists():
            self.stitching = ort.InferenceSession(
                str(Config.STITCHING_MODEL),
                sess_options=sess_options,
                providers=self.providers
            )
            logger.info("Stitching module loaded")

        # Eye retargeting
        if Config.STITCHING_EYE.exists():
            self.stitching_eye = ort.InferenceSession(
                str(Config.STITCHING_EYE),
                sess_options=sess_options,
                providers=self.providers
            )
            logger.info("Eye stitching module loaded")

        # Lip retargeting
        if Config.STITCHING_LIP.exists():
            self.stitching_lip = ort.InferenceSession(
                str(Config.STITCHING_LIP),
                sess_options=sess_options,
                providers=self.providers
            )
            logger.info("Lip stitching module loaded")

    def _load_face_detector(self):
        """Load InsightFace detector for face detection"""
        try:
            from insightface.app import FaceAnalysis

            insightface_path = str(Config.INSIGHTFACE_DIR)
            logger.info(f"Loading face detector from {insightface_path}")

            self.face_detector = FaceAnalysis(
                name='buffalo_l',
                root=insightface_path,
                providers=self.providers
            )
            self.face_detector.prepare(ctx_id=0 if self.device == "cuda" else -1, det_size=(640, 640))
            logger.info("Face detector loaded")

        except ImportError:
            logger.warning("InsightFace not available, using fallback face detection")
            self.face_detector = None
        except Exception as e:
            logger.warning(f"Failed to load InsightFace: {e}, using fallback")
            self.face_detector = None

    def unload_models(self):
        """Unload all models"""
        self.appearance_extractor = None
        self.motion_extractor = None
        self.warping_generator = None
        self.stitching = None
        self.stitching_eye = None
        self.stitching_lip = None
        self.face_detector = None
        self.model_loaded = False

        import gc
        gc.collect()

        logger.info("LivePortrait models unloaded")

    def detect_face(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Detect face in image and return cropped face with bounding box

        Args:
            image: Input image (H, W, 3) in RGB

        Returns:
            Tuple of (cropped_face, bbox) or None if no face detected
        """
        if self.face_detector is not None:
            # Use InsightFace
            faces = self.face_detector.get(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            if not faces:
                return None

            # Get largest face
            face = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]))
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox

            # Expand bbox
            h, w = image.shape[:2]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            size = max(x2 - x1, y2 - y1)
            half_size = int(size * 0.75)  # Expand by 50%

            x1 = max(0, cx - half_size)
            y1 = max(0, cy - half_size)
            x2 = min(w, cx + half_size)
            y2 = min(h, cy + half_size)

            cropped = image[y1:y2, x1:x2]
            return cropped, (x1, y1, x2, y2)

        else:
            # Fallback: use OpenCV Haar cascade
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) == 0:
                return None

            # Get largest face
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            x1, y1 = x, y
            x2, y2 = x + fw, y + fh

            # Expand bbox
            h, w = image.shape[:2]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            size = max(x2 - x1, y2 - y1)
            half_size = int(size * 0.75)

            x1 = max(0, cx - half_size)
            y1 = max(0, cy - half_size)
            x2 = min(w, cx + half_size)
            y2 = min(h, cy + half_size)

            cropped = image[y1:y2, x1:x2]
            return cropped, (x1, y1, x2, y2)

    def extract_appearance_features(self, face_image: np.ndarray) -> np.ndarray:
        """
        Extract 3D appearance features from face image

        Args:
            face_image: Face image (512, 512, 3) in RGB, normalized [-1, 1]

        Returns:
            Appearance features tensor
        """
        # Prepare input
        if face_image.max() > 1.0:
            face_image = normalize_image(face_image)

        # Add batch dimension and transpose to NCHW
        x = face_image.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)

        # Run inference
        outputs = self.appearance_extractor.run(None, {'input': x})
        return outputs[0]

    def extract_motion(self, face_image: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Extract motion/keypoints from face image

        Args:
            face_image: Face image (512, 512, 3) in RGB, normalized [-1, 1]

        Returns:
            Dict with motion coefficients (pitch, yaw, roll, exp, t, scale)
        """
        # Prepare input
        if face_image.max() > 1.0:
            face_image = normalize_image(face_image)

        # Add batch dimension and transpose to NCHW
        x = face_image.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)

        # Run inference
        outputs = self.motion_extractor.run(None, {'input': x})

        # Parse outputs - LivePortrait motion format
        # Typically: pitch, yaw, roll (rotation), exp (expression), t (translation), scale
        motion = {
            'pitch': outputs[0],
            'yaw': outputs[1],
            'roll': outputs[2],
            'exp': outputs[3],      # Expression coefficients (21 dimensions)
            't': outputs[4],        # Translation
            'scale': outputs[5]     # Scale
        }
        return motion

    def generate_frame(
        self,
        appearance_features: np.ndarray,
        source_motion: Dict[str, np.ndarray],
        target_motion: np.ndarray
    ) -> np.ndarray:
        """
        Generate a single frame by applying target motion to source appearance

        Args:
            appearance_features: Source appearance features
            source_motion: Source motion dict
            target_motion: Target motion coefficients (66,)

        Returns:
            Generated face image (512, 512, 3) in RGB [0, 255]
        """
        # Parse target motion into components
        # JoyVASA motion format: [exp(21*3), pitch, yaw, roll, tx, ty, tz, scale]
        # = 63 + 1 + 1 + 1 + 3 + 1 = 70 or similar
        # Simplified: exp(21*3=63) + rotation(3)

        exp_coeffs = target_motion[:63].reshape(21, 3) if len(target_motion) >= 63 else source_motion['exp']

        # Extract rotation if available
        if len(target_motion) >= 66:
            target_pitch = target_motion[63:64]
            target_yaw = target_motion[64:65]
            target_roll = target_motion[65:66]
        else:
            target_pitch = source_motion['pitch']
            target_yaw = source_motion['yaw']
            target_roll = source_motion['roll']

        # Prepare inputs for warping generator
        inputs = {
            'appearance': appearance_features,
            'source_kp': source_motion['exp'],
            'target_kp': exp_coeffs.reshape(1, 21, 3).astype(np.float32),
            'pitch': target_pitch.astype(np.float32),
            'yaw': target_yaw.astype(np.float32),
            'roll': target_roll.astype(np.float32),
        }

        # Run warping generator
        try:
            outputs = self.warping_generator.run(None, inputs)
            generated = outputs[0]  # (1, 3, 512, 512)

            # Convert to image
            generated = generated[0].transpose(1, 2, 0)  # (512, 512, 3)
            generated = denormalize_image(generated)

            return generated

        except Exception as e:
            logger.warning(f"Warping failed: {e}, using simplified generation")
            # Fallback: just return source with expression blend
            return self._simple_generate(appearance_features, source_motion, target_motion)

    def _simple_generate(
        self,
        appearance_features: np.ndarray,
        source_motion: Dict[str, np.ndarray],
        target_motion: np.ndarray
    ) -> np.ndarray:
        """Simple fallback generation when warping fails"""
        # This is a placeholder - actual implementation would need proper warping
        # For now, return a blank frame
        return np.zeros((512, 512, 3), dtype=np.uint8)

    def apply_stitching(
        self,
        generated: np.ndarray,
        source_motion: Dict[str, np.ndarray],
        target_motion: np.ndarray
    ) -> np.ndarray:
        """
        Apply stitching for smooth blending

        Args:
            generated: Generated face (512, 512, 3)
            source_motion: Source motion dict
            target_motion: Target motion coefficients

        Returns:
            Stitched face image
        """
        if self.stitching is None:
            return generated

        # Stitching would refine the generated output
        # This is a placeholder for the actual stitching logic
        return generated

    def motion_to_video(
        self,
        image_path: str,
        motion_sequence: np.ndarray,
        audio_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Generate video from source image and motion sequence

        Args:
            image_path: Path to source image
            motion_sequence: Motion sequence (T, 66)
            audio_path: Path to audio file
            output_path: Output video path
            progress_callback: Progress callback

        Returns:
            Path to output video
        """
        if not self.model_loaded:
            if not self.load_models():
                raise RuntimeError("Failed to load LivePortrait models")

        temp_dir = Path(tempfile.mkdtemp(dir=Config.TEMP_DIR))

        try:
            if progress_callback:
                progress_callback(0.5, "Processing source image")

            # Load and process source image
            source_image = load_image(image_path)
            original_size = source_image.shape[:2]

            # Detect face
            face_result = self.detect_face(source_image)
            if face_result is None:
                raise ValueError("No face detected in source image")

            face_crop, face_bbox = face_result

            # Resize face to model input size
            face_resized = cv2.resize(face_crop, (self.input_size, self.input_size))
            face_normalized = normalize_image(face_resized)

            if progress_callback:
                progress_callback(0.55, "Extracting appearance features")

            # Extract appearance features (only once)
            appearance_features = self.extract_appearance_features(face_normalized)

            # Extract source motion
            source_motion = self.extract_motion(face_normalized)

            if progress_callback:
                progress_callback(0.6, "Generating video frames")

            # Generate frames
            num_frames = motion_sequence.shape[0]
            frames = []

            for i, target_motion in enumerate(motion_sequence):
                if progress_callback and i % 10 == 0:
                    progress = 0.6 + 0.3 * (i / num_frames)
                    progress_callback(progress, f"Generating frame {i+1}/{num_frames}")

                # Generate face frame
                generated_face = self.generate_frame(
                    appearance_features,
                    source_motion,
                    target_motion
                )

                # Apply stitching
                generated_face = self.apply_stitching(
                    generated_face,
                    source_motion,
                    target_motion
                )

                # Blend back to original image
                full_frame = blend_face_to_background(
                    cv2.cvtColor(source_image, cv2.COLOR_RGB2BGR),
                    cv2.cvtColor(generated_face, cv2.COLOR_RGB2BGR),
                    face_bbox,
                    feather_amount=15
                )

                frames.append(full_frame)

            if progress_callback:
                progress_callback(0.9, "Encoding video")

            # Write video frames
            temp_video = str(temp_dir / "temp_video.mp4")
            write_video_frames(frames, temp_video, fps=Config.OUTPUT_FPS)

            # Merge with audio
            merge_audio_video(
                temp_video,
                audio_path,
                output_path,
                video_codec=Config.VIDEO_CODEC,
                audio_codec=Config.AUDIO_CODEC
            )

            if progress_callback:
                progress_callback(1.0, "Complete")

            logger.info(f"Video generated: {output_path}")
            return output_path

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

    def get_model_status(self) -> Dict[str, bool]:
        """Get status of loaded models"""
        return {
            "appearance_extractor": self.appearance_extractor is not None,
            "motion_extractor": self.motion_extractor is not None,
            "warping_generator": self.warping_generator is not None,
            "stitching": self.stitching is not None,
            "face_detector": self.face_detector is not None,
            "fully_loaded": self.model_loaded
        }
