"""
リップシンク動画生成 API ルーター
MuseTalkを使用したリップシンク動画生成
"""

import os
import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import logging

from core.config import settings

STORAGE_DIR = Path(os.environ.get("STORAGE_PATH", "/app/storage"))

# File size limits for shared volume reads (prevent DoS via oversized files)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB


def _resolve_storage_path(storage_url: str, max_size_bytes: int = None) -> Path:
    """Resolve a MuseTalk storage URL to a local filesystem path.

    Both backend and MuseTalk share the Docker volume at /app/storage.
    URLs like '/storage/uploads/hash.jpg' map to '/app/storage/uploads/hash.jpg'.
    """
    # Strip /storage/ prefix
    relative = storage_url.removeprefix("/storage/")
    if relative == storage_url:
        # URL didn't start with /storage/, might be a full path
        relative = storage_url.lstrip("/")

    full_path = (STORAGE_DIR / relative).resolve()

    # Prevent directory traversal
    if not str(full_path).startswith(str(STORAGE_DIR.resolve())):
        raise ValueError("Invalid storage path")

    if not full_path.exists():
        raise FileNotFoundError("File not found in storage")

    # Check file size if limit specified
    if max_size_bytes is not None:
        file_size = full_path.stat().st_size
        if file_size > max_size_bytes:
            raise ValueError(f"File exceeds size limit ({file_size} > {max_size_bytes})")

    return full_path

# MuseTalk client (lazy loaded)
_musetalk_client = None

def get_musetalk_client():
    """Get or initialize MuseTalk client singleton"""
    global _musetalk_client
    if _musetalk_client is None:
        try:
            from services.musetalk_client import MuseTalkClient
            _musetalk_client = MuseTalkClient()
            logger.info("MuseTalkClient initialized")
        except ImportError as e:
            logger.warning(f"MuseTalkClient not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize MuseTalkClient: {e}")
            return None
    return _musetalk_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def _save_to_storage(data: bytes, filename: str, subdir: str = "uploads") -> str:
    """Save file directly to shared storage volume and return storage URL."""
    ext = Path(filename).suffix.lower() or '.bin'
    content_hash = hashlib.sha256(data).hexdigest()[:16]
    storage_filename = f"{content_hash}{ext}"

    upload_dir = STORAGE_DIR / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / storage_filename
    file_path.write_bytes(data)

    return f"/storage/{subdir}/{storage_filename}"

# リクエスト/レスポンスモデル
class VideoGenerationRequest(BaseModel):
    """リップシンク動画生成リクエスト（MuseTalk）"""
    audio_url: str
    source_url: str  # リップシンクには必須

class VideoGenerationResponse(BaseModel):
    """動画生成レスポンス"""
    id: str
    status: str
    result_url: Optional[str] = None
    created_at: str
    

@router.post("/generate-video", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """
    MuseTalkを使用して動画を生成

    Args:
        request: 動画生成リクエスト

    Returns:
        生成された動画の情報
    """
    try:
        musetalk = get_musetalk_client()
        if musetalk is None:
            raise HTTPException(status_code=503, detail="MuseTalkサービスが利用できません")

        if not await musetalk.check_service_health():
            raise HTTPException(status_code=503, detail="MuseTalkサービスが応答していません")

        # Read uploaded files from shared Docker volume (with size limits)
        try:
            audio_path = _resolve_storage_path(request.audio_url, max_size_bytes=MAX_AUDIO_SIZE_BYTES)
            image_path = _resolve_storage_path(request.source_url, max_size_bytes=MAX_IMAGE_SIZE_BYTES)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))

        audio_data = audio_path.read_bytes()
        image_data = image_path.read_bytes()

        # Smart upper-body crop for optimal MuseTalk/LivePortrait input
        if settings.upper_body_crop_enabled:
            from services.upper_body_cropper import get_upper_body_cropper
            cropper = get_upper_body_cropper(
                target_size=settings.upper_body_crop_target_size,
                face_ratio=settings.upper_body_crop_face_ratio,
            )
            try:
                image_data, crop_metadata = await cropper.crop_upper_body(image_data)
                logger.info(f"Upper-body crop: {crop_metadata}")
            except Exception as e:
                logger.warning(f"Upper-body crop failed, using original image: {e}")

        logger.info(
            f"MuseTalk動画生成開始: audio={audio_path.name} ({len(audio_data)} bytes), "
            f"image={image_path.name} ({len(image_data)} bytes)"
        )

        result = await musetalk.create_talk_video(
            audio_data=audio_data,
            image_data=image_data,
            audio_filename=audio_path.name,
            image_filename=image_path.name,
            wait_for_completion=True
        )

        # Transform result_url to backend-served path
        result_url = None
        if result.get("result_url"):
            result_url = f"/api/lipsync/videos/{result['id']}"

        return VideoGenerationResponse(
            id=result["id"],
            status=result["status"],
            result_url=result_url,
            created_at=result["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"動画生成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail="動画生成に失敗しました")


@router.get("/talk-status/{talk_id}")
async def get_talk_status(talk_id: str):
    """
    動画生成ステータスを確認

    Args:
        talk_id: MuseTalkジョブID

    Returns:
        動画生成の現在の状態
    """
    # Sanitize talk_id to prevent injection
    if not talk_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid talk ID")

    try:
        musetalk = get_musetalk_client()
        if musetalk is None:
            raise HTTPException(status_code=503, detail="MuseTalkサービスが利用できません")

        status = await musetalk.get_talk_status(talk_id)
        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ステータス取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail="ステータスの取得に失敗しました")


@router.post("/upload-source-image")
async def upload_source_image(file: UploadFile = File(...)):
    """
    ソース画像を共有ストレージに保存

    Args:
        file: アップロードする画像ファイル

    Returns:
        保存された画像のストレージURL
    """
    try:
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="画像ファイルをアップロードしてください")

        image_data = await file.read()

        if len(image_data) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"画像ファイルが大きすぎます（最大{MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB）")

        image_url = await _save_to_storage(image_data, file.filename or "image.png", subdir="uploads")
        logger.info(f"画像保存完了: {image_url}")
        return {"url": image_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"画像アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    音声ファイルを共有ストレージに保存

    Args:
        file: アップロードする音声ファイル

    Returns:
        保存された音声のストレージURL
    """
    try:
        allowed_types = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/mp4', 'audio/flac', 'audio/m4a']
        if not file.content_type or file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="音声ファイル（WAV, MP3, MP4, FLAC, M4A）をアップロードしてください")

        audio_data = await file.read()

        if len(audio_data) > MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"音声ファイルが大きすぎます（最大{MAX_AUDIO_SIZE_BYTES // (1024*1024)}MB）")

        audio_url = await _save_to_storage(audio_data, file.filename or "audio.wav", subdir="uploads")
        logger.info(f"音声保存完了: {audio_url}")
        return {"url": audio_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音声アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="音声のアップロードに失敗しました")

@router.get("/health")
async def health_check():
    """
    MuseTalkリップシンクサービスのヘルスチェック

    Returns:
        サービスの状態
    """
    result = {
        "status": "healthy",
        "primary_service": "musetalk"
    }

    musetalk = get_musetalk_client()
    if musetalk is not None:
        try:
            musetalk_healthy = await musetalk.check_service_health()
            result["musetalk"] = {
                "available": musetalk_healthy,
                "service_url": musetalk.base_url
            }
            if not musetalk_healthy:
                result["status"] = "degraded"
        except Exception as e:
            result["musetalk"] = {
                "available": False,
                "error": str(e)
            }
            result["status"] = "degraded"
    else:
        result["musetalk"] = {"available": False, "error": "Client not initialized"}
        result["status"] = "degraded"

    return result


@router.get("/videos/{job_id}")
async def get_video(job_id: str):
    """Serve generated video from shared storage volume."""
    # Sanitize job_id to prevent path traversal
    if not job_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID")

    video_path = STORAGE_DIR / "videos" / f"{job_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{job_id}.mp4"
    )