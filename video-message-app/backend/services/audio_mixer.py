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


def _get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())


def _mix_bgm_sync(
    video_path: str,
    bgm_path: str,
    output_path: str,
    bgm_volume_db: float = -18.0,
    fade_out_seconds: float = 2.0,
    pad_seconds: float = 1.0,
) -> None:
    """
    Mix BGM into a video file using ffmpeg (synchronous).

    The BGM is:
    - Looped if shorter than the video
    - Trimmed to match video duration
    - Mixed at the specified volume (without normalizing speech)
    - Faded out near the end

    When pad_seconds > 0, the video is extended by cloning the first/last
    frame so that BGM-only audio plays before and after speech.

    Args:
        video_path: Path to input video (with speech audio)
        bgm_path: Path to BGM audio file
        output_path: Path for output video
        bgm_volume_db: BGM volume in dB (default -18dB, well below speech)
        fade_out_seconds: Duration of BGM fade-out at end
        pad_seconds: Seconds of BGM-only padding before and after speech
    """
    video_duration = _get_video_duration(video_path)
    total_duration = video_duration + pad_seconds * 2
    fade_start = max(0, total_duration - fade_out_seconds)

    pad_ms = int(pad_seconds * 1000)

    if pad_seconds > 0:
        # With padding: extend video with cloned first/last frame,
        # delay speech audio, pad end with silence
        bgm_filter = (
            # Pad video with cloned frames
            f"[0:v]tpad=start_duration={pad_seconds}:stop_duration={pad_seconds}"
            f":start_mode=clone:stop_mode=clone[padv];"
            # Delay speech audio by pad_seconds, pad end with silence
            f"[0:a]adelay={pad_ms}|{pad_ms},apad=pad_dur={pad_seconds}[pada];"
            # Loop BGM, trim to total duration, apply volume + fade
            f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{total_duration},"
            f"volume={bgm_volume_db}dB,"
            f"afade=t=out:st={fade_start}:d={fade_out_seconds}[bgm];"
            # Mix speech + BGM without normalizing (preserve speech volume)
            f"[pada][bgm]amix=inputs=2:duration=first"
            f":dropout_transition=0:normalize=0[mixed]"
        )
        video_map = "[padv]"
        # Must re-encode video since tpad changes frames
        video_codec = ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
    else:
        # No padding: simple BGM overlay (video stream copied as-is)
        bgm_filter = (
            f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{video_duration},"
            f"volume={bgm_volume_db}dB,"
            f"afade=t=out:st={fade_start}:d={fade_out_seconds}[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first"
            f":dropout_transition=0:normalize=0[mixed]"
        )
        video_map = "0:v"
        video_codec = ["-c:v", "copy"]

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex", bgm_filter,
        "-map", video_map,
        "-map", "[mixed]",
        *video_codec,
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mixing failed: {result.stderr[-500:]}")


async def mix_bgm_into_video(
    video_path: Path,
    track_id: str,
    bgm_volume_db: float = -18.0,
    fade_out_seconds: float = 2.0,
    pad_seconds: float = 1.0,
) -> None:
    """
    Mix a preset BGM track into a video file (in-place replacement).

    Args:
        video_path: Path to the video file (will be replaced with mixed version)
        track_id: ID of the BGM preset track
        bgm_volume_db: BGM volume relative to speech in dB
        fade_out_seconds: Fade-out duration at end of video
        pad_seconds: Seconds of BGM-only padding before and after speech
    """
    bgm_path = _find_bgm_file(track_id)
    logger.info(
        f"Mixing BGM '{track_id}' into {video_path} "
        f"at {bgm_volume_db}dB, pad={pad_seconds}s"
    )

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
            pad_seconds,
        )
        # Replace original with mixed version
        shutil.move(tmp_path, str(video_path))
        logger.info(f"BGM mixing complete: {video_path}")
    except Exception:
        # Cleanup temp file on failure
        Path(tmp_path).unlink(missing_ok=True)
        raise
