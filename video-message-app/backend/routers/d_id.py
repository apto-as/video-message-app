"""
D-ID 動画生成 API ルーター
音声クローニング機能は削除し、動画生成機能のみ提供
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
    D-IDを使用して動画を生成
    
    Args:
        request: 動画生成リクエスト
        
    Returns:
        生成された動画の情報
    """
    try:
        logger.info(f"D-ID動画生成開始: audio_url={request.audio_url}")
        
        # D-ID APIを呼び出し（リップシンクのみ）
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
        
    except Exception as e:
        logger.error(f"動画生成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"動画生成に失敗しました: {str(e)}")


@router.get("/talk-status/{talk_id}")
async def get_talk_status(talk_id: str):
    """
    動画生成ステータスを確認
    
    Args:
        talk_id: D-ID トークID
        
    Returns:
        動画生成の現在の状態
    """
    try:
        status = await d_id_client.get_talk_status(talk_id)
        return status
        
    except Exception as e:
        logger.error(f"ステータス取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail="ステータスの取得に失敗しました")


@router.post("/upload-source-image")
async def upload_source_image(file: UploadFile = File(...)):
    """
    ソース画像をD-IDに直接アップロード
    
    Args:
        file: アップロードする画像ファイル
        
    Returns:
        D-IDでアップロードされた画像のURL
    """
    try:
        # ファイル形式の検証
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="画像ファイルをアップロードしてください")
        
        # ファイルデータを読み取り
        image_data = await file.read()
        
        # D-IDに直接アップロード
        image_url = await d_id_client.upload_image(image_data, file.filename)
        
        logger.info(f"D-ID画像アップロード完了: {image_url}")
        
        return {"url": image_url}
        
    except Exception as e:
        logger.error(f"画像アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    音声ファイルをD-IDに直接アップロード
    
    Args:
        file: アップロードする音声ファイル
        
    Returns:
        D-IDでアップロードされた音声のURL
    """
    try:
        # ファイル形式の検証
        allowed_types = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/mp4', 'audio/flac', 'audio/m4a']
        if not file.content_type or file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="音声ファイル（WAV, MP3, MP4, FLAC, M4A）をアップロードしてください")
        
        # ファイルデータを読み取り
        audio_data = await file.read()
        
        # D-IDに直接アップロード
        audio_url = await d_id_client.upload_audio(audio_data, file.filename)
        
        logger.info(f"D-ID音声アップロード完了: {audio_url}")
        
        return {"url": audio_url}
        
    except Exception as e:
        logger.error(f"音声アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="音声のアップロードに失敗しました")

@router.get("/health")
async def health_check():
    """
    D-ID サービスのヘルスチェック
    
    Returns:
        サービスの状態
    """
    return {
        "status": "healthy",
        "service": "d-id",
        "api_key_configured": bool(d_id_client.api_key)
    }