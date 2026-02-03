"""
D-ID API クライアント（動画生成機能のみ）
音声クローニング機能は削除し、OpenVoice V2を使用

DEPRECATED: This module is deprecated as of 2026-02-03.
Use services.musetalk_client.MuseTalkClient for lip-sync video generation.

This module is kept for backwards compatibility and fallback scenarios.
Set USE_LOCAL_LIPSYNC=false to use D-ID API instead of MuseTalk.
"""
import warnings
warnings.warn(
    "d_id_client is deprecated, use musetalk_client instead",
    DeprecationWarning,
    stacklevel=2
)

import os
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
import base64
from core.config import settings

logger = logging.getLogger(__name__)

class DIdClient:
    """D-ID API クライアント（動画生成専用）"""
    
    def __init__(self):
        # 設定ファイルから優先的に取得、フォールバックで環境変数
        self.api_key = (
            getattr(settings, 'did_api_key', '') or 
            os.getenv("DID_API_KEY", os.getenv("D_ID_API_KEY", ""))
        )
        self.base_url = "https://api.d-id.com"
        self.timeout = 300  # 5分のタイムアウト
        
        if not self.api_key:
            logger.warning("DID_API_KEY が設定されていません。.envファイルまたは環境変数を確認してください。")
    
    @property
    def headers(self) -> Dict[str, str]:
        """API リクエストヘッダー"""
        return {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def upload_image(self, image_data: bytes, filename: str = None) -> str:
        """
        D-IDに画像をアップロード
        
        Args:
            image_data: 画像のバイナリデータ
            filename: ファイル名（オプション）
        
        Returns:
            アップロードされた画像のURL
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # multipart/form-dataでアップロード
            files = {"image": (filename or "image.jpg", image_data, "image/jpeg")}
            
            response = await client.post(
                f"{self.base_url}/images",
                headers={"Authorization": f"Basic {self.api_key}"},
                files=files
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"D-ID画像アップロード完了: {result.get('url')}")
            return result.get("url")
    
    async def upload_audio(self, audio_data: bytes, filename: str = None) -> str:
        """
        D-IDに音声をアップロード
        
        Args:
            audio_data: 音声のバイナリデータ
            filename: ファイル名（オプション）
        
        Returns:
            アップロードされた音声のURL
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # multipart/form-dataでアップロード
            files = {"audio": (filename or "audio.wav", audio_data, "audio/wav")}
            
            response = await client.post(
                f"{self.base_url}/audios",
                headers={"Authorization": f"Basic {self.api_key}"},
                files=files
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"D-ID音声アップロード完了: {result.get('url')}")
            return result.get("url")

    async def create_talk_video(
        self,
        audio_url: str,
        source_url: str
    ) -> Dict[str, Any]:
        """
        音声ファイルからリップシンク動画を生成（プレゼンター機能は削除）
        
        Args:
            audio_url: 音声ファイルのURL
            source_url: ソース画像/動画のURL（必須）
        
        Returns:
            生成された動画の情報
        """
        
        # リクエストボディの構築（プレゼンター機能は使用しない）
        body = {
            "script": {
                "type": "audio",
                "audio_url": audio_url
            },
            "source_url": source_url  # 直接画像URLを指定
        }
        
        # 設定オプション（リップシンク基本設定）
        body["config"] = {
            "stitch": True,
            "pad_audio": 0.0
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/talks",
                    headers=self.headers,
                    json=body
                )
                response.raise_for_status()
                
                talk_data = response.json()
                talk_id = talk_data.get("id")
                
                if not talk_id:
                    raise ValueError("動画IDが取得できませんでした")
                
                logger.info(f"動画生成開始: {talk_id}")
                
                # 動画生成の完了を待つ
                result = await self._wait_for_video(talk_id)
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(f"D-ID API エラー: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"動画生成エラー: {str(e)}")
                raise
    
    async def _wait_for_video(self, talk_id: str, max_attempts: int = 60) -> Dict[str, Any]:
        """
        動画生成の完了を待つ
        
        Args:
            talk_id: トークID
            max_attempts: 最大試行回数（5秒間隔）
        
        Returns:
            完成した動画の情報
        """
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(
                        f"{self.base_url}/talks/{talk_id}",
                        headers=self.headers
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    status = data.get("status")
                    
                    if status == "done":
                        logger.info(f"動画生成完了: {talk_id}")
                        return data
                    elif status == "error" or status == "rejected":
                        error_msg = data.get("error", {}).get("description", "不明なエラー")
                        raise ValueError(f"動画生成失敗: {error_msg}")
                    
                    # 生成中の場合は待機
                    logger.info(f"動画生成中... ({attempt + 1}/{max_attempts})")
                    await asyncio.sleep(5)
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"ステータス確認エラー: {e.response.status_code}")
                    raise
            
            raise TimeoutError("動画生成がタイムアウトしました")
    
    async def get_talk_status(self, talk_id: str) -> Dict[str, Any]:
        """
        動画生成ステータスを取得
        
        Args:
            talk_id: トークID
        
        Returns:
            ステータス情報
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/talks/{talk_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"ステータス取得エラー: {e.response.status_code}")
                return {"error": "ステータス取得に失敗しました"}
    

# シングルトンインスタンス
d_id_client = DIdClient()