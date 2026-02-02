"""
D-ID / MuseTalk 動画生成 API ルーター
USE_LOCAL_LIPSYNC=true の場合はMuseTalk、それ以外はD-ID APIを使用
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import os
import aiofiles
from pathlib import Path
import httpx
from services.d_id_client import d_id_client
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
    動画を生成（MuseTalkまたはD-ID APIを使用）

    USE_LOCAL_LIPSYNC=true の場合はMuseTalk、それ以外はD-ID APIを使用

    Args:
        request: 動画生成リクエスト

    Returns:
        生成された動画の情報
    """
    try:
        # Check if local lip-sync (MuseTalk) should be used
        if settings.should_use_local_lipsync:
            musetalk = get_musetalk_client()
            if musetalk is not None:
                try:
                    # Check MuseTalk service health
                    if await musetalk.check_service_health():
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
                    else:
                        logger.warning("MuseTalkサービスが利用不可、D-IDにフォールバック")
                except Exception as e:
                    logger.warning(f"MuseTalk処理エラー、D-IDにフォールバック: {e}")
                    if not settings.should_fallback_to_cloud:
                        raise HTTPException(status_code=503, detail=f"MuseTalkサービスエラー: {str(e)}")

        # Fallback to D-ID API
        logger.info(f"D-ID動画生成開始: audio_url={request.audio_url}")
        result = await d_id_client.create_talk_video(
            audio_url=request.audio_url,
            source_url=request.source_url
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
        talk_id: トークID（MuseTalkまたはD-ID）

    Returns:
        動画生成の現在の状態
    """
    try:
        # Check if local lip-sync (MuseTalk) should be used
        if settings.should_use_local_lipsync:
            musetalk = get_musetalk_client()
            if musetalk is not None:
                try:
                    status = await musetalk.get_talk_status(talk_id)
                    return status
                except Exception as e:
                    logger.warning(f"MuseTalkステータス取得エラー、D-IDを試行: {e}")
                    if not settings.should_fallback_to_cloud:
                        raise HTTPException(status_code=503, detail=f"MuseTalkサービスエラー: {str(e)}")

        # Fallback to D-ID API
        status = await d_id_client.get_talk_status(talk_id)
        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ステータス取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail="ステータスの取得に失敗しました")


@router.post("/upload-source-image")
async def upload_source_image(file: UploadFile = File(...)):
    """
    ソース画像をアップロード（MuseTalkまたはD-IDを使用）

    USE_LOCAL_LIPSYNC=true の場合はMuseTalk、それ以外はD-IDにアップロード

    Args:
        file: アップロードする画像ファイル

    Returns:
        アップロードされた画像のURL
    """
    try:
        # ファイル形式の検証
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="画像ファイルをアップロードしてください")

        # ファイルデータを読み取り
        image_data = await file.read()

        # Check if local lip-sync (MuseTalk) should be used
        if settings.should_use_local_lipsync:
            musetalk = get_musetalk_client()
            if musetalk is not None:
                try:
                    # Check MuseTalk service health
                    if await musetalk.check_service_health():
                        image_url = await musetalk.upload_image(image_data, file.filename)
                        logger.info(f"MuseTalk画像アップロード完了: {image_url}")
                        return {"url": image_url}
                    else:
                        logger.warning("MuseTalkサービスが利用不可、D-IDにフォールバック")
                except Exception as e:
                    logger.warning(f"MuseTalkアップロードエラー、D-IDにフォールバック: {e}")
                    if not settings.should_fallback_to_cloud:
                        raise HTTPException(status_code=503, detail=f"MuseTalkサービスエラー: {str(e)}")

        # Fallback to D-ID
        image_url = await d_id_client.upload_image(image_data, file.filename)
        logger.info(f"D-ID画像アップロード完了: {image_url}")

        return {"url": image_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"画像アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    音声ファイルをアップロード（MuseTalkまたはD-IDを使用）

    USE_LOCAL_LIPSYNC=true の場合はMuseTalk、それ以外はD-IDにアップロード

    Args:
        file: アップロードする音声ファイル

    Returns:
        アップロードされた音声のURL
    """
    try:
        # ファイル形式の検証
        allowed_types = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/mp4', 'audio/flac', 'audio/m4a']
        if not file.content_type or file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="音声ファイル（WAV, MP3, MP4, FLAC, M4A）をアップロードしてください")

        # ファイルデータを読み取り
        audio_data = await file.read()

        # Check if local lip-sync (MuseTalk) should be used
        if settings.should_use_local_lipsync:
            musetalk = get_musetalk_client()
            if musetalk is not None:
                try:
                    # Check MuseTalk service health
                    if await musetalk.check_service_health():
                        audio_url = await musetalk.upload_audio(audio_data, file.filename)
                        logger.info(f"MuseTalk音声アップロード完了: {audio_url}")
                        return {"url": audio_url}
                    else:
                        logger.warning("MuseTalkサービスが利用不可、D-IDにフォールバック")
                except Exception as e:
                    logger.warning(f"MuseTalkアップロードエラー、D-IDにフォールバック: {e}")
                    if not settings.should_fallback_to_cloud:
                        raise HTTPException(status_code=503, detail=f"MuseTalkサービスエラー: {str(e)}")

        # Fallback to D-ID
        audio_url = await d_id_client.upload_audio(audio_data, file.filename)
        logger.info(f"D-ID音声アップロード完了: {audio_url}")

        return {"url": audio_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音声アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="音声のアップロードに失敗しました")

@router.get("/health")
async def health_check():
    """
    リップシンクサービスのヘルスチェック

    USE_LOCAL_LIPSYNC=true の場合はMuseTalk、それ以外はD-IDのステータスを返す

    Returns:
        サービスの状態
    """
    result = {
        "status": "healthy",
        "use_local_lipsync": settings.should_use_local_lipsync,
        "fallback_enabled": settings.should_fallback_to_cloud
    }

    # Check MuseTalk service if local lip-sync is enabled
    if settings.should_use_local_lipsync:
        musetalk = get_musetalk_client()
        if musetalk is not None:
            try:
                musetalk_healthy = await musetalk.check_service_health()
                result["musetalk"] = {
                    "available": musetalk_healthy,
                    "service_url": musetalk.base_url
                }
                if musetalk_healthy:
                    result["primary_service"] = "musetalk"
                else:
                    result["primary_service"] = "d-id" if settings.should_fallback_to_cloud else "none"
            except Exception as e:
                result["musetalk"] = {
                    "available": False,
                    "error": str(e)
                }
                result["primary_service"] = "d-id" if settings.should_fallback_to_cloud else "none"
        else:
            result["musetalk"] = {"available": False, "error": "Client not initialized"}
            result["primary_service"] = "d-id" if settings.should_fallback_to_cloud else "none"
    else:
        result["primary_service"] = "d-id"

    # Always include D-ID status for fallback awareness
    result["d_id"] = {
        "api_key_configured": bool(d_id_client.api_key)
    }

    return result