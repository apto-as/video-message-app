"""
Audio mixer service for combining BGM with speech audio in videos.
Uses ffmpeg for mixing.
"""

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Storage paths
STORAGE_DIR = Path("/app/storage")
MUSIC_DIR = STORAGE_DIR / "presets" / "music"


def _find_bgm_file(track_id: str) -> Path:
    """Find the BGM file by track ID."""
    for ext in (".mp3", ".wav", ".ogg", ".m4a"):
        path = MUSIC_DIR / f"{track_id}{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(f"BGM track not found: {track_id}")


def _mix_bgm_sync(
    video_path: str,
    bgm_path: str,
    output_path: str,
    bgm_volume_db: float = -18.0,
    fade_out_seconds: float = 2.0,
) -> None:
    """
    Mix BGM into a video file using ffmpeg (synchronous).

    The BGM is:
    - Looped if shorter than the video
    - Trimmed to match video duration
    - Mixed at the specified volume (relative to original audio)
    - Faded out near the end

    Args:
        video_path: Path to input video (with speech audio)
        bgm_path: Path to BGM audio file
        output_path: Path for output video
        bgm_volume_db: BGM volume in dB (default -18dB, well below speech)
        fade_out_seconds: Duration of BGM fade-out at end
    """
    # Get video duration first
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    probe_result = subprocess.run(
        probe_cmd, capture_output=True, text=True, timeout=10
    )
    if probe_result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {probe_result.stderr}")

    video_duration = float(probe_result.stdout.strip())
    fade_start = max(0, video_duration - fade_out_seconds)

    # Build ffmpeg command:
    # - Input 0: original video (with speech)
    # - Input 1: BGM audio (looped)
    # - Filter: volume adjust BGM, fade out, mix with original audio
    bgm_filter = (
        f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{video_duration},"
        f"volume={bgm_volume_db}dB,"
        f"afade=t=out:st={fade_start}:d={fade_out_seconds}[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[mixed]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex", bgm_filter,
        "-map", "0:v",
        "-map", "[mixed]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mixing failed: {result.stderr[-500:]}")


async def mix_bgm_into_video(
    video_path: Path,
    track_id: str,
    bgm_volume_db: float = -18.0,
    fade_out_seconds: float = 2.0,
) -> None:
    """
    Mix a preset BGM track into a video file (in-place replacement).

    Args:
        video_path: Path to the video file (will be replaced with mixed version)
        track_id: ID of the BGM preset track
        bgm_volume_db: BGM volume relative to speech in dB
        fade_out_seconds: Fade-out duration at end of video
    """
    bgm_path = _find_bgm_file(track_id)
    logger.info(f"Mixing BGM '{track_id}' into {video_path} at {bgm_volume_db}dB")

    # Use temp file for output, then replace original
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            _mix_bgm_sync,
            str(video_path),
            str(bgm_path),
            tmp_path,
            bgm_volume_db,
            fade_out_seconds,
        )
        # Replace original with mixed version
        shutil.move(tmp_path, str(video_path))
        logger.info(f"BGM mixing complete: {video_path}")
    except Exception:
        # Cleanup temp file on failure
        Path(tmp_path).unlink(missing_ok=True)
        raise
