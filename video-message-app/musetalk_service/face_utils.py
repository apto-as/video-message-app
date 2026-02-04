"""
Face detection and landmark extraction utilities.

Uses face_alignment (dlib-based) instead of mmpose to avoid CUDA extension
segfault caused by broken mmcv._ext in the container. The face_alignment
library provides equivalent 68-point face landmarks and face detection.

This module replaces musetalk.utils.preprocessing for our use case.
"""
import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Singleton face alignment instance (lazy-initialized)
_fa_instance = None

# Placeholder for no-face-detected case (matches MuseTalk convention)
coord_placeholder = (0.0, 0.0, 0.0, 0.0)


def _get_face_alignment():
    """Get or create the singleton FaceAlignment instance (CPU)."""
    global _fa_instance
    if _fa_instance is None:
        import face_alignment
        logger.info("Initializing face_alignment (CPU)...")
        _fa_instance = face_alignment.FaceAlignment(
            face_alignment.LandmarksType.TWO_D,
            flip_input=False,
            device='cpu'
        )
        logger.info("face_alignment initialized")
    return _fa_instance


def read_imgs(img_list):
    """Read images from file paths or pass through numpy arrays."""
    frames = []
    for img in img_list:
        if isinstance(img, str):
            frame = cv2.imread(img)
            if frame is None:
                raise ValueError(f"Could not read image: {img}")
            frames.append(frame)
        elif isinstance(img, np.ndarray):
            frames.append(img)
        else:
            raise TypeError(f"Expected str or ndarray, got {type(img)}")
    return frames


def get_landmark_and_bbox(
    img_list,
    upperbondrange: int = 0
) -> Tuple[List, List]:
    """
    Detect face landmarks and compute crop bounding boxes.

    Drop-in replacement for musetalk.utils.preprocessing.get_landmark_and_bbox
    using face_alignment instead of mmpose (which segfaults due to broken mmcv).

    The 68 face landmarks from face_alignment follow the iBUG convention,
    which is compatible with MuseTalk's face region keypoints (mmpose indices
    23-91 also follow iBUG ordering).

    Args:
        img_list: List of image paths (str) or numpy arrays (BGR)
        upperbondrange: Vertical shift for upper boundary (0 = default)

    Returns:
        coords_list: List of (x1, y1, x2, y2) bounding box tuples
        frames: List of numpy arrays (BGR images)
    """
    fa = _get_face_alignment()
    frames = read_imgs(img_list)

    coords_list = []
    for frame in frames:
        # face_alignment expects RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        preds = fa.get_landmarks(rgb_frame)

        if preds is None or len(preds) == 0:
            coords_list.append(coord_placeholder)
            continue

        landmarks = preds[0].astype(np.int32)  # (68, 2)

        # Compute crop region using the same logic as MuseTalk's preprocessing:
        # - half_face_coord = landmark[29] (nose bridge, iBUG convention)
        # - upper boundary extends above the face center by half_face_dist
        # - x range from min/max of all face landmark x-coordinates
        # - y range from upper_bond to max face landmark y-coordinate
        half_face_coord = landmarks[29].copy()

        if upperbondrange != 0:
            half_face_coord[1] += upperbondrange

        half_face_dist = np.max(landmarks[:, 1]) - half_face_coord[1]
        upper_bond = max(0, half_face_coord[1] - half_face_dist)

        x1 = int(np.min(landmarks[:, 0]))
        y1 = int(upper_bond)
        x2 = int(np.max(landmarks[:, 0]))
        y2 = int(np.max(landmarks[:, 1]))

        if y2 - y1 <= 0 or x2 - x1 <= 0 or x1 < 0:
            # Invalid landmark bbox - use face detection bbox as fallback
            try:
                det = fa.face_detector.detect_from_image(rgb_frame)
                if det is not None and len(det) > 0:
                    d = det[0]
                    coords_list.append((int(d[0]), int(d[1]), int(d[2]), int(d[3])))
                else:
                    coords_list.append(coord_placeholder)
            except Exception:
                coords_list.append(coord_placeholder)
        else:
            coords_list.append((x1, y1, x2, y2))

    return coords_list, frames
