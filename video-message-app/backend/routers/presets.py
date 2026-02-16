"""
Preset backgrounds and BGM router.
Serves pre-configured birthday celebration assets.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(tags=["Presets"])
logger = logging.getLogger(__name__)

# Storage path for preset assets (Docker volume)
STORAGE_DIR = Path("/app/storage")
BACKGROUNDS_DIR = STORAGE_DIR / "presets" / "backgrounds"
MUSIC_DIR = STORAGE_DIR / "presets" / "music"

# Bundled metadata path (in repo, copied to Docker image)
BUNDLED_DATA_DIR = Path(__file__).parent.parent / "data" / "presets"

# Metadata loaded once at import time
_backgrounds_meta = None
_music_meta = None


def _load_metadata(storage_meta: Path, bundled_meta: Path) -> dict:
    """Load metadata from storage volume, falling back to bundled data."""
    for meta_path in (storage_meta, bundled_meta):
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load metadata {meta_path}: {e}")
    logger.warning(f"No metadata found at {storage_meta} or {bundled_meta}")
    return {"version": "1.0", "items": []}


def _get_backgrounds_metadata() -> dict:
    global _backgrounds_meta
    if _backgrounds_meta is None:
        _backgrounds_meta = _load_metadata(
            BACKGROUNDS_DIR / "metadata.json",
            BUNDLED_DATA_DIR / "backgrounds_metadata.json",
        )
    return _backgrounds_meta


def _get_music_metadata() -> dict:
    global _music_meta
    if _music_meta is None:
        _music_meta = _load_metadata(
            MUSIC_DIR / "metadata.json",
            BUNDLED_DATA_DIR / "music_metadata.json",
        )
    return _music_meta


def _validate_asset_id(asset_id: str) -> None:
    """Validate asset ID to prevent path traversal."""
    if not asset_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid asset ID")


# =========================================================================
# Background Preset Endpoints
# =========================================================================


@router.get("/presets/backgrounds")
async def list_background_presets(category: Optional[str] = Query(None)):
    """List available background image presets."""
    meta = _get_backgrounds_metadata()
    items = meta.get("items", [])

    if category:
        items = [bg for bg in items if bg.get("category") == category]

    # Add image URLs
    result = []
    for bg in items:
        entry = {**bg}
        entry["image_url"] = f"/api/presets/backgrounds/{bg['id']}/image"
        entry["thumbnail_url"] = f"/api/presets/backgrounds/{bg['id']}/thumbnail"
        result.append(entry)

    return {
        "backgrounds": result,
        "total": len(result),
        "categories": list({bg.get("category", "") for bg in meta.get("items", [])})
    }


@router.get("/presets/backgrounds/{bg_id}/image")
async def get_background_image(bg_id: str):
    """Serve a background preset image."""
    _validate_asset_id(bg_id)

    # Try common image extensions
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        image_path = BACKGROUNDS_DIR / f"{bg_id}{ext}"
        if image_path.exists():
            media_types = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp"
            }
            return FileResponse(
                image_path,
                media_type=media_types.get(ext, "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"}
            )

    raise HTTPException(status_code=404, detail="Background image not found")


@router.get("/presets/backgrounds/{bg_id}/thumbnail")
async def get_background_thumbnail(bg_id: str):
    """Serve a background preset thumbnail (falls back to full image)."""
    _validate_asset_id(bg_id)

    # Check for thumbnail first
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        thumb_path = BACKGROUNDS_DIR / "thumbnails" / f"{bg_id}{ext}"
        if thumb_path.exists():
            media_types = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp"
            }
            return FileResponse(
                thumb_path,
                media_type=media_types.get(ext, "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"}
            )

    # Fallback to full image
    return await get_background_image(bg_id)


# =========================================================================
# Music/BGM Preset Endpoints
# =========================================================================


@router.get("/presets/music")
async def list_music_presets(mood: Optional[str] = Query(None)):
    """List available BGM presets."""
    meta = _get_music_metadata()
    items = meta.get("items", [])

    if mood:
        items = [t for t in items if t.get("mood") == mood]

    result = []
    for track in items:
        entry = {**track}
        entry["audio_url"] = f"/api/presets/music/{track['id']}/audio"
        entry["preview_url"] = f"/api/presets/music/{track['id']}/preview"
        result.append(entry)

    return {
        "tracks": result,
        "total": len(result),
        "moods": list({t.get("mood", "") for t in meta.get("items", [])})
    }


@router.get("/presets/music/{track_id}/audio")
async def get_music_audio(track_id: str):
    """Serve a BGM preset audio file."""
    _validate_asset_id(track_id)

    for ext in (".mp3", ".wav", ".ogg", ".m4a"):
        audio_path = MUSIC_DIR / f"{track_id}{ext}"
        if audio_path.exists():
            media_types = {
                ".mp3": "audio/mpeg", ".wav": "audio/wav",
                ".ogg": "audio/ogg", ".m4a": "audio/mp4"
            }
            return FileResponse(
                audio_path,
                media_type=media_types.get(ext, "audio/mpeg"),
                headers={"Cache-Control": "public, max-age=86400"}
            )

    raise HTTPException(status_code=404, detail="BGM audio not found")


@router.get("/presets/music/{track_id}/preview")
async def get_music_preview(track_id: str):
    """Serve a BGM preview clip (falls back to full audio)."""
    _validate_asset_id(track_id)

    for ext in (".mp3", ".wav", ".ogg", ".m4a"):
        preview_path = MUSIC_DIR / "previews" / f"{track_id}{ext}"
        if preview_path.exists():
            media_types = {
                ".mp3": "audio/mpeg", ".wav": "audio/wav",
                ".ogg": "audio/ogg", ".m4a": "audio/mp4"
            }
            return FileResponse(
                preview_path,
                media_type=media_types.get(ext, "audio/mpeg"),
                headers={"Cache-Control": "public, max-age=86400"}
            )

    # Fallback to full audio
    return await get_music_audio(track_id)


@router.get("/presets/backgrounds/{bg_id}/download-url")
async def get_background_for_processing(bg_id: str):
    """Get the storage path for a preset background (used by process-image)."""
    _validate_asset_id(bg_id)

    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        image_path = BACKGROUNDS_DIR / f"{bg_id}{ext}"
        if image_path.exists():
            return {"path": str(image_path), "id": bg_id}

    raise HTTPException(status_code=404, detail="Background image not found")
