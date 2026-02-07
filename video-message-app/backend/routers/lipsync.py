"""
リップシンク動画生成 API ルーター
MuseTalk/EchoMimicを使用したリップシンク動画生成
"""

import os
import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Tuple
import logging

from core.config import settings

STORAGE_DIR = Path(os.environ.get("STORAGE_PATH", "/app/storage"))

# File size limits for shared volume reads (prevent DoS via oversized files)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB

logger = logging.getLogger(__name__)


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

def _get_musetalk_client():
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


# EchoMimic client (lazy loaded)
_echomimic_client = None

def _get_echomimic_client():
    """Get or initialize EchoMimic client singleton"""
    global _echomimic_client
    if _echomimic_client is None:
        try:
            from services.echomimic_client import EchoMimicClient
            _echomimic_client = EchoMimicClient()
            logger.info("EchoMimicClient initialized")
        except ImportError as e:
            logger.warning(f"EchoMimicClient not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize EchoMimicClient: {e}")
            return None
    return _echomimic_client


async def _select_lipsync_engine() -> Tuple[str, object]:
    """
    Select the appropriate lip-sync engine based on configuration and availability.

    Returns:
        Tuple of (engine_name, client_instance)
        engine_name: 'musetalk', 'echomimic', or 'liveportrait'
        client_instance: The corresponding client object

    Raises:
        HTTPException: If no engine is available
    """
    configured_engine = settings.get_lipsync_engine

    if configured_engine == 'musetalk':
        client = _get_musetalk_client()
        if client and await client.check_service_health():
            return ('musetalk', client)
        raise HTTPException(status_code=503, detail="MuseTalkサービスが利用できません")

    elif configured_engine == 'echomimic':
        client = _get_echomimic_client()
        if client and await client.check_service_health():
            return ('echomimic', client)
        raise HTTPException(status_code=503, detail="EchoMimicサービスが利用できません")

    elif configured_engine == 'liveportrait':
        # LivePortrait is not yet implemented in this router
        raise HTTPException(status_code=501, detail="LivePortraitエンジンは未実装です")

    elif configured_engine == 'auto':
        # Try engines in order of preference: MuseTalk -> EchoMimic
        # MuseTalk first (faster, lower VRAM)
        musetalk = _get_musetalk_client()
        if musetalk:
            try:
                if await musetalk.check_service_health():
                    logger.info("Auto-selected engine: MuseTalk")
                    return ('musetalk', musetalk)
            except Exception as e:
                logger.warning(f"MuseTalk health check failed: {e}")

        # EchoMimic fallback (higher quality, more VRAM)
        echomimic = _get_echomimic_client()
        if echomimic:
            try:
                if await echomimic.check_service_health():
                    logger.info("Auto-selected engine: EchoMimic")
                    return ('echomimic', echomimic)
            except Exception as e:
                logger.warning(f"EchoMimic health check failed: {e}")

        raise HTTPException(
            status_code=503,
            detail="利用可能なリップシンクエンジンがありません"
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown lip-sync engine: {configured_engine}"
        )


# Keep the old function name for backward compatibility
def get_musetalk_client():
    """Backward compatibility wrapper for _get_musetalk_client"""
    return _get_musetalk_client()

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
    リップシンク動画を生成（MuseTalk/EchoMimic自動選択）

    Args:
        request: 動画生成リクエスト

    Returns:
        生成された動画の情報
    """
    try:
        # Select the appropriate lip-sync engine
        engine_name, client = await _select_lipsync_engine()
        logger.info(f"Using lip-sync engine: {engine_name}")

        # Read uploaded files from shared Docker volume (with size limits)
        try:
            audio_path = _resolve_storage_path(request.audio_url, max_size_bytes=MAX_AUDIO_SIZE_BYTES)
            image_path = _resolve_storage_path(request.source_url, max_size_bytes=MAX_IMAGE_SIZE_BYTES)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))

        audio_data = audio_path.read_bytes()
        image_data = image_path.read_bytes()

        # Smart upper-body crop for optimal MuseTalk/EchoMimic/LivePortrait input
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
            f"{engine_name}動画生成開始: audio={audio_path.name} ({len(audio_data)} bytes), "
            f"image={image_path.name} ({len(image_data)} bytes)"
        )

        # Generate video using the selected engine
        if engine_name == 'musetalk':
            result = await client.create_talk_video(
                audio_data=audio_data,
                image_data=image_data,
                audio_filename=audio_path.name,
                image_filename=image_path.name,
                wait_for_completion=True
            )
        elif engine_name == 'echomimic':
            result = await client.create_video(
                audio_data=audio_data,
                image_data=image_data,
                audio_filename=audio_path.name,
                image_filename=image_path.name,
                wait_for_completion=True
            )
        else:
            raise HTTPException(status_code=501, detail=f"Engine {engine_name} not implemented")

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
    リップシンクサービス（MuseTalk/EchoMimic）のヘルスチェック

    Returns:
        サービスの状態
    """
    configured_engine = settings.get_lipsync_engine
    result = {
        "status": "healthy",
        "configured_engine": configured_engine,
        "available_engines": []
    }

    # Check MuseTalk
    musetalk = _get_musetalk_client()
    if musetalk is not None:
        try:
            musetalk_healthy = await musetalk.check_service_health()
            result["musetalk"] = {
                "available": musetalk_healthy,
                "service_url": musetalk.base_url
            }
            if musetalk_healthy:
                result["available_engines"].append("musetalk")
        except Exception as e:
            result["musetalk"] = {
                "available": False,
                "error": str(e)
            }
    else:
        result["musetalk"] = {"available": False, "error": "Client not initialized"}

    # Check EchoMimic
    echomimic = _get_echomimic_client()
    if echomimic is not None:
        try:
            echomimic_healthy = await echomimic.check_service_health()
            result["echomimic"] = {
                "available": echomimic_healthy,
                "service_url": echomimic.base_url
            }
            if echomimic_healthy:
                result["available_engines"].append("echomimic")
        except Exception as e:
            result["echomimic"] = {
                "available": False,
                "error": str(e)
            }
    else:
        result["echomimic"] = {"available": False, "error": "Client not initialized"}

    # Determine overall status
    if not result["available_engines"]:
        result["status"] = "unhealthy"
    elif configured_engine != 'auto':
        # Check if the configured engine is available
        if configured_engine not in result["available_engines"]:
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