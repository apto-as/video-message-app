"""
Video I/O utilities for frame-level video processing.

Provides functions to read video files into frames and write frames back
to video files with optional audio track.
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Storage directory for path validation
STORAGE_DIR = Path(os.environ.get("STORAGE_PATH", "/app/storage"))


def _validate_path(file_path: str, must_exist: bool = True) -> Path:
    """
    Validate a file path for security.

    All paths must be within STORAGE_DIR to prevent:
    - Path traversal attacks (CWE-22)
    - Symlink attacks (CWE-61)
    - Arbitrary file access

    Args:
        file_path: Path to validate
        must_exist: Whether the file must exist

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is invalid or outside allowed directory
    """
    path = Path(file_path)

    # Resolve to absolute path first (handles symlinks atomically)
    resolved = path.resolve()
    storage_resolved = STORAGE_DIR.resolve()

    # Ensure path is within STORAGE_DIR (prevents CWE-22 and CWE-61)
    # Use os.sep to ensure proper directory boundary check
    storage_prefix = str(storage_resolved) + os.sep
    if not (str(resolved) == str(storage_resolved) or
            str(resolved).startswith(storage_prefix)):
        raise ValueError(f"Path outside allowed directory: {file_path}")

    # Check existence if required
    if must_exist and not resolved.exists():
        raise ValueError(f"File not found: {file_path}")

    return resolved


def read_video_frames(video_path: str) -> Tuple[List[np.ndarray], int]:
    """
    Read all frames from a video file.

    Args:
        video_path: Path to the video file

    Returns:
        Tuple of (list of BGR frames, fps)

    Raises:
        ValueError: If video cannot be opened or has no frames
    """
    # Validate path for security
    validated_path = _validate_path(video_path, must_exist=True)
    video_path = str(validated_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    try:
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 25  # Default fallback

        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)

        if not frames:
            raise ValueError(f"No frames read from video: {video_path}")

        logger.info(f"Read {len(frames)} frames at {fps} fps from {video_path}")
        return frames, fps

    finally:
        cap.release()


def write_video_frames(
    frames: List[np.ndarray],
    output_path: str,
    fps: int,
    audio_path: Optional[str] = None,
) -> str:
    """
    Write frames to a video file, optionally with audio.

    Args:
        frames: List of BGR numpy arrays (H, W, 3)
        output_path: Output video file path (must be within STORAGE_DIR)
        fps: Frame rate
        audio_path: Optional path to audio file to mux (must be within STORAGE_DIR)

    Returns:
        Path to the output video file

    Raises:
        ValueError: If frames are empty, invalid, or paths are outside allowed directory
    """
    if not frames:
        raise ValueError("No frames to write")

    # Validate output path for security (must_exist=False for new files)
    validated_output = _validate_path(output_path, must_exist=False)
    output_path = str(validated_output)

    # Validate audio path if provided
    if audio_path:
        validated_audio = _validate_path(audio_path, must_exist=True)
        audio_path = str(validated_audio)

    h, w = frames[0].shape[:2]

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if audio_path:
        # Write with audio using FFmpeg
        return _write_with_ffmpeg(frames, output_path, fps, audio_path, w, h)
    else:
        # Write without audio using OpenCV
        return _write_with_opencv(frames, output_path, fps, w, h)


def _write_with_opencv(
    frames: List[np.ndarray],
    output_path: str,
    fps: int,
    width: int,
    height: int
) -> str:
    """Write video using OpenCV (no audio)."""
    # Use mp4v codec for compatibility
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        raise ValueError(f"Could not create video writer for: {output_path}")

    try:
        for frame in frames:
            writer.write(frame)
        logger.info(f"Wrote {len(frames)} frames to {output_path}")
        return output_path
    finally:
        writer.release()


def _write_with_ffmpeg(
    frames: List[np.ndarray],
    output_path: str,
    fps: int,
    audio_path: str,
    width: int,
    height: int
) -> str:
    """
    Write video with audio using FFmpeg.

    Strategy:
    1. Write frames to temporary video file
    2. Use FFmpeg to combine video + audio
    """
    # Create temp file for intermediate video
    temp_fd, temp_video = tempfile.mkstemp(suffix=".mp4")
    os.close(temp_fd)

    try:
        # Write frames to temp video
        _write_with_opencv(frames, temp_video, fps, width, height)

        # Mux video + audio with FFmpeg
        _mux_video_audio(temp_video, audio_path, output_path)

        logger.info(f"Wrote {len(frames)} frames with audio to {output_path}")
        return output_path

    finally:
        # Clean up temp file
        if os.path.exists(temp_video):
            try:
                os.unlink(temp_video)
            except OSError as e:
                logger.warning(f"Failed to delete temp file {temp_video}: {e}")


def _mux_video_audio(video_path: str, audio_path: str, output_path: str):
    """
    Combine video and audio using FFmpeg.

    Uses the video stream from video_path and audio stream from audio_path.
    """
    if not os.path.exists(audio_path):
        raise ValueError(f"Audio file not found: {audio_path}")

    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", video_path,  # Video input
        "-i", audio_path,  # Audio input
        "-c:v", "libx264",  # Re-encode video for compatibility
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",  # AAC audio codec
        "-b:a", "128k",
        "-map", "0:v:0",  # Video from first input
        "-map", "1:a:0",  # Audio from second input
        "-shortest",  # Match shortest stream length
        output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=120  # 2 minute timeout
        )
        logger.debug(f"FFmpeg mux completed: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg mux failed: {e.stderr}")
        raise ValueError(f"Failed to mux video and audio: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise ValueError("FFmpeg mux timed out (>120s)")


def extract_audio_from_video(video_path: str, output_audio_path: Optional[str] = None) -> str:
    """
    Extract audio track from a video file.

    Args:
        video_path: Path to the video file
        output_audio_path: Optional output path. If not provided,
            creates a .wav file alongside the video.

    Returns:
        Path to the extracted audio file
    """
    # Validate path for security
    validated_path = _validate_path(video_path, must_exist=True)
    video_path = str(validated_path)

    if output_audio_path is None:
        base = os.path.splitext(video_path)[0]
        output_audio_path = f"{base}_audio.wav"

    # Validate output path for security (defense in depth)
    validated_output = _validate_path(output_audio_path, must_exist=False)
    output_audio_path = str(validated_output)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # WAV format
        "-ar", "44100",  # Sample rate
        "-ac", "2",  # Stereo
        output_audio_path
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        logger.info(f"Extracted audio to {output_audio_path}")
        return output_audio_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio extraction failed: {e.stderr}")
        raise ValueError(f"Failed to extract audio: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise ValueError("FFmpeg audio extraction timed out (>60s)")


def get_video_info(video_path: str) -> dict:
    """
    Get basic video information.

    Returns:
        dict with keys: fps, width, height, frame_count, duration
    """
    # Validate path for security
    validated_path = _validate_path(video_path, must_exist=True)
    video_path = str(validated_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        return {
            "fps": fps,
            "width": width,
            "height": height,
            "frame_count": frame_count,
            "duration": duration
        }
    finally:
        cap.release()
