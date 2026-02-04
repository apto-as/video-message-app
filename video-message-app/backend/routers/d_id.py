"""
MuseTalk 動画生成 API ルーター
MuseTalkを使用したリップシンク動画生成
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import logging

from core.config import settings

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

# リクエスト/レスポンスモデル
class VideoGenerationRequest(BaseModel):
    """動画生成リクエスト（リップシンクのみ）"""
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

        logger.info(f"MuseTalk動画生成開始: audio_url={request.audio_url}")
        result = await musetalk.create_talk_video(
            audio_url=request.audio_url,
            source_url=request.source_url,
            wait_for_completion=True
        )

        return VideoGenerationResponse(
            id=result["id"],
            status=result["status"],
            result_url=result.get("result_url"),
            created_at=result["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"動画生成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"動画生成に失敗しました: {str(e)}")


@router.get("/talk-status/{talk_id}")
async def get_talk_status(talk_id: str):
    """
    動画生成ステータスを確認

    Args:
        talk_id: MuseTalkジョブID

    Returns:
        動画生成の現在の状態
    """
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
    ソース画像をMuseTalkにアップロード

    Args:
        file: アップロードする画像ファイル

    Returns:
        アップロードされた画像のURL
    """
    try:
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="画像ファイルをアップロードしてください")

        image_data = await file.read()

        musetalk = get_musetalk_client()
        if musetalk is None:
            raise HTTPException(status_code=503, detail="MuseTalkサービスが利用できません")

        if not await musetalk.check_service_health():
            raise HTTPException(status_code=503, detail="MuseTalkサービスが応答していません")

        image_url = await musetalk.upload_image(image_data, file.filename)
        logger.info(f"MuseTalk画像アップロード完了: {image_url}")
        return {"url": image_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"画像アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    音声ファイルをMuseTalkにアップロード

    Args:
        file: アップロードする音声ファイル

    Returns:
        アップロードされた音声のURL
    """
    try:
        allowed_types = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/mp4', 'audio/flac', 'audio/m4a']
        if not file.content_type or file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="音声ファイル（WAV, MP3, MP4, FLAC, M4A）をアップロードしてください")

        audio_data = await file.read()

        musetalk = get_musetalk_client()
        if musetalk is None:
            raise HTTPException(status_code=503, detail="MuseTalkサービスが利用できません")

        if not await musetalk.check_service_health():
            raise HTTPException(status_code=503, detail="MuseTalkサービスが応答していません")

        audio_url = await musetalk.upload_audio(audio_data, file.filename)
        logger.info(f"MuseTalk音声アップロード完了: {audio_url}")
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