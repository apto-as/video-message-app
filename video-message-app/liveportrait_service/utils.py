"""
Utility functions for LivePortrait + JoyVASA Service
"""
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def load_image(image_path: str) -> np.ndarray:
    """
    Load image from path and convert to RGB

    Args:
        image_path: Path to image file

    Returns:
        Image as numpy array in RGB format
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def resize_image(image: np.ndarray, target_size: int = 512) -> np.ndarray:
    """
    Resize image to target size while maintaining aspect ratio

    Args:
        image: Input image (HxWxC)
        target_size: Target size for the longer side

    Returns:
        Resized image
    """
    h, w = image.shape[:2]
    if h > w:
        new_h = target_size
        new_w = int(w * target_size / h)
    else:
        new_w = target_size
        new_h = int(h * target_size / w)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    return resized


def pad_to_square(image: np.ndarray, target_size: int = 512) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """
    Pad image to square with black borders

    Args:
        image: Input image (HxWxC)
        target_size: Target square size

    Returns:
        Tuple of (padded_image, padding_info) where padding_info is (top, bottom, left, right)
    """
    h, w = image.shape[:2]

    # First resize to fit within target_size
    scale = min(target_size / h, target_size / w)
    new_h, new_w = int(h * scale), int(w * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # Pad to square
    pad_top = (target_size - new_h) // 2
    pad_bottom = target_size - new_h - pad_top
    pad_left = (target_size - new_w) // 2
    pad_right = target_size - new_w - pad_left

    padded = cv2.copyMakeBorder(
        resized,
        pad_top, pad_bottom, pad_left, pad_right,
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0)
    )

    return padded, (pad_top, pad_bottom, pad_left, pad_right)


def remove_padding(image: np.ndarray, padding: Tuple[int, int, int, int], original_size: Tuple[int, int]) -> np.ndarray:
    """
    Remove padding and resize back to original size

    Args:
        image: Padded image
        padding: (top, bottom, left, right) padding values
        original_size: Original (height, width)

    Returns:
        Unpadded and resized image
    """
    pad_top, pad_bottom, pad_left, pad_right = padding
    h, w = image.shape[:2]

    # Remove padding
    cropped = image[pad_top:h-pad_bottom if pad_bottom > 0 else h,
                    pad_left:w-pad_right if pad_right > 0 else w]

    # Resize to original
    resized = cv2.resize(cropped, (original_size[1], original_size[0]), interpolation=cv2.INTER_LANCZOS4)
    return resized


def normalize_image(image: np.ndarray) -> np.ndarray:
    """
    Normalize image to [-1, 1] range for neural network input

    Args:
        image: Input image in [0, 255] range

    Returns:
        Normalized image in [-1, 1] range
    """
    return (image.astype(np.float32) / 255.0) * 2.0 - 1.0


def denormalize_image(image: np.ndarray) -> np.ndarray:
    """
    Denormalize image from [-1, 1] to [0, 255] range

    Args:
        image: Normalized image in [-1, 1] range

    Returns:
        Image in [0, 255] range as uint8
    """
    return np.clip((image + 1.0) * 127.5, 0, 255).astype(np.uint8)


def get_audio_duration(audio_path: str) -> float:
    """
    Get duration of audio file in seconds using ffprobe

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds
    """
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")
        return 0.0


def convert_audio_to_wav(input_path: str, output_path: str, sample_rate: int = 16000) -> str:
    """
    Convert audio to WAV format with specified sample rate

    Args:
        input_path: Input audio file path
        output_path: Output WAV file path
        sample_rate: Target sample rate (default 16kHz for HuBERT)

    Returns:
        Path to converted file
    """
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-ar', str(sample_rate),
        '-ac', '1',  # Mono
        '-f', 'wav',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def merge_audio_video(video_path: str, audio_path: str, output_path: str, video_codec: str = "libx264", audio_codec: str = "aac") -> str:
    """
    Merge video and audio using ffmpeg

    Args:
        video_path: Path to video file (without audio)
        audio_path: Path to audio file
        output_path: Path for output video
        video_codec: Video codec to use
        audio_codec: Audio codec to use

    Returns:
        Path to output file
    """
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', video_codec,
        '-c:a', audio_codec,
        '-shortest',
        '-preset', 'fast',
        '-crf', '23',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def write_video_frames(frames: List[np.ndarray], output_path: str, fps: int = 25) -> str:
    """
    Write list of frames to video file

    Args:
        frames: List of frames (HxWxC in BGR format)
        output_path: Output video path
        fps: Frames per second

    Returns:
        Path to output file
    """
    if not frames:
        raise ValueError("No frames to write")

    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        # Ensure BGR format
        if frame.shape[2] == 3:
            writer.write(frame)
    writer.release()

    return output_path


def create_smooth_motion_sequence(
    motion_sequence: np.ndarray,
    window_size: int = 5,
    sigma: float = 1.0
) -> np.ndarray:
    """
    Apply temporal smoothing to motion sequence

    Args:
        motion_sequence: Motion data (T, D) where T is frames and D is motion dimensions
        window_size: Smoothing window size
        sigma: Gaussian sigma for smoothing

    Returns:
        Smoothed motion sequence
    """
    from scipy.ndimage import gaussian_filter1d

    smoothed = np.zeros_like(motion_sequence)
    for i in range(motion_sequence.shape[1]):
        smoothed[:, i] = gaussian_filter1d(motion_sequence[:, i], sigma=sigma)

    return smoothed


def crop_face_region(
    image: np.ndarray,
    bbox: Tuple[int, int, int, int],
    expand_ratio: float = 1.5
) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """
    Crop face region from image with expansion

    Args:
        image: Input image
        bbox: Face bounding box (x1, y1, x2, y2)
        expand_ratio: Ratio to expand the bounding box

    Returns:
        Tuple of (cropped_image, expanded_bbox)
    """
    x1, y1, x2, y2 = bbox
    h, w = image.shape[:2]

    # Calculate center and size
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    box_w, box_h = x2 - x1, y2 - y1

    # Expand
    new_w = int(box_w * expand_ratio)
    new_h = int(box_h * expand_ratio)

    # Calculate new coordinates
    new_x1 = max(0, cx - new_w // 2)
    new_y1 = max(0, cy - new_h // 2)
    new_x2 = min(w, cx + new_w // 2)
    new_y2 = min(h, cy + new_h // 2)

    cropped = image[new_y1:new_y2, new_x1:new_x2]
    return cropped, (new_x1, new_y1, new_x2, new_y2)


def blend_face_to_background(
    background: np.ndarray,
    face: np.ndarray,
    bbox: Tuple[int, int, int, int],
    feather_amount: int = 10
) -> np.ndarray:
    """
    Blend generated face back into background image

    Args:
        background: Original background image
        face: Generated face image
        bbox: Bounding box (x1, y1, x2, y2) where to place face
        feather_amount: Amount of feathering for smooth blending

    Returns:
        Blended image
    """
    x1, y1, x2, y2 = bbox
    result = background.copy()

    # Resize face to match bbox
    target_h = y2 - y1
    target_w = x2 - x1
    face_resized = cv2.resize(face, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    if feather_amount > 0:
        # Create feathered mask
        mask = np.ones((target_h, target_w), dtype=np.float32)
        for i in range(feather_amount):
            alpha = (i + 1) / feather_amount
            mask[i, :] *= alpha
            mask[-(i+1), :] *= alpha
            mask[:, i] *= alpha
            mask[:, -(i+1)] *= alpha

        mask = np.expand_dims(mask, axis=2)
        mask = np.repeat(mask, 3, axis=2)

        # Blend with feathering
        bg_region = result[y1:y2, x1:x2].astype(np.float32)
        face_float = face_resized.astype(np.float32)
        blended = bg_region * (1 - mask) + face_float * mask
        result[y1:y2, x1:x2] = blended.astype(np.uint8)
    else:
        # Simple paste
        result[y1:y2, x1:x2] = face_resized

    return result
