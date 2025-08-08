"""
画像処理サービス: 背景削除・背景合成機能
"""
import asyncio
import io
import os
from PIL import Image, ImageOps
from rembg import new_session, remove
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """画像処理サービス"""
    
    def __init__(self):
        """初期化: rembgセッションを作成"""
        try:
            # u2net モデルを使用（汎用性が高い）
            self.session = new_session('u2net')
            logger.info("rembg session initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize rembg session: {e}")
            self.session = None
    
    async def remove_background(self, image_bytes: bytes) -> bytes:
        """
        背景削除処理
        
        Args:
            image_bytes: 元画像のバイト列
            
        Returns:
            bytes: 背景削除済み画像のバイト列（PNG形式）
        """
        if not self.session:
            raise RuntimeError("rembg session not initialized")
        
        try:
            # 非同期で背景削除を実行
            output_bytes = await asyncio.get_event_loop().run_in_executor(
                None, 
                self._remove_background_sync, 
                image_bytes
            )
            return output_bytes
            
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            raise RuntimeError(f"Background removal failed: {e}")
    
    def _remove_background_sync(self, image_bytes: bytes) -> bytes:
        """同期的な背景削除処理"""
        # rembgで背景削除
        output_bytes = remove(image_bytes, session=self.session)
        return output_bytes
    
    async def composite_background(
        self, 
        subject_bytes: bytes, 
        background_bytes: bytes,
        subject_position: Tuple[int, int] = (0, 0),
        subject_scale: float = 1.0
    ) -> bytes:
        """
        背景合成処理
        
        Args:
            subject_bytes: 被写体画像（背景削除済み）のバイト列
            background_bytes: 背景画像のバイト列
            subject_position: 被写体の配置位置 (x, y)
            subject_scale: 被写体のスケール（1.0 = 等倍）
            
        Returns:
            bytes: 合成済み画像のバイト列（JPEG形式）
        """
        try:
            # 非同期で合成処理を実行
            output_bytes = await asyncio.get_event_loop().run_in_executor(
                None,
                self._composite_background_sync,
                subject_bytes,
                background_bytes,
                subject_position,
                subject_scale
            )
            return output_bytes
            
        except Exception as e:
            logger.error(f"Background composition failed: {e}")
            raise RuntimeError(f"Background composition failed: {e}")
    
    def _composite_background_sync(
        self,
        subject_bytes: bytes,
        background_bytes: bytes,
        subject_position: Tuple[int, int],
        subject_scale: float
    ) -> bytes:
        """同期的な背景合成処理"""
        # 画像を読み込み
        subject_img = Image.open(io.BytesIO(subject_bytes)).convert("RGBA")
        background_img = Image.open(io.BytesIO(background_bytes)).convert("RGB")
        
        # 被写体のリサイズ
        if subject_scale != 1.0:
            new_size = (
                int(subject_img.width * subject_scale),
                int(subject_img.height * subject_scale)
            )
            subject_img = subject_img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 背景画像のサイズに合わせて被写体を配置
        composite = background_img.copy()
        
        # 被写体を背景に合成
        # アルファチャンネルを使用して透明度を考慮
        composite.paste(subject_img, subject_position, subject_img)
        
        # JPEG形式で出力
        output_buffer = io.BytesIO()
        composite.save(output_buffer, format="JPEG", quality=95)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    
    async def process_for_did(
        self, 
        image_bytes: bytes,
        background_bytes: Optional[bytes] = None,
        enhance_quality: bool = True
    ) -> bytes:
        """
        D-ID API向けの画像処理パイプライン
        
        Args:
            image_bytes: 元画像のバイト列
            background_bytes: 背景画像のバイト列（Noneの場合は背景削除のみ）
            enhance_quality: 品質向上処理を行うか
            
        Returns:
            bytes: 処理済み画像のバイト列
        """
        try:
            # ステップ1: 背景削除
            logger.info("Starting background removal...")
            subject_bytes = await self.remove_background(image_bytes)
            
            # ステップ2: 品質向上（オプション）
            if enhance_quality:
                subject_bytes = await self._enhance_edges(subject_bytes)
            
            # ステップ3: 背景合成（背景画像が指定された場合）
            if background_bytes:
                logger.info("Starting background composition...")
                final_bytes = await self.composite_background(
                    subject_bytes, 
                    background_bytes
                )
            else:
                # 背景削除のみの場合、PNGからJPEGに変換（D-ID API要件）
                final_bytes = await self._convert_to_jpeg(subject_bytes)
            
            logger.info("Image processing completed successfully")
            return final_bytes
            
        except Exception as e:
            logger.error(f"Image processing pipeline failed: {e}")
            raise
    
    async def _enhance_edges(self, image_bytes: bytes) -> bytes:
        """エッジ品質向上処理"""
        try:
            output_bytes = await asyncio.get_event_loop().run_in_executor(
                None,
                self._enhance_edges_sync,
                image_bytes
            )
            return output_bytes
        except Exception as e:
            logger.warning(f"Edge enhancement failed, skipping: {e}")
            return image_bytes
    
    def _enhance_edges_sync(self, image_bytes: bytes) -> bytes:
        """同期的なエッジ品質向上処理"""
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        
        # 軽微なシャープニング
        enhanced = ImageOps.unsharp_mask(image, radius=1, percent=50, threshold=3)
        
        # PNG形式で出力
        output_buffer = io.BytesIO()
        enhanced.save(output_buffer, format="PNG", optimize=True)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    
    async def _convert_to_jpeg(self, png_bytes: bytes) -> bytes:
        """PNG画像をJPEGに変換"""
        try:
            output_bytes = await asyncio.get_event_loop().run_in_executor(
                None,
                self._convert_to_jpeg_sync,
                png_bytes
            )
            return output_bytes
        except Exception as e:
            logger.error(f"PNG to JPEG conversion failed: {e}")
            raise
    
    def _convert_to_jpeg_sync(self, png_bytes: bytes) -> bytes:
        """同期的なPNG→JPEG変換"""
        # PNGを読み込み
        image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        
        # 白い背景を作成
        background = Image.new("RGB", image.size, (255, 255, 255))
        
        # アルファチャンネルを使用して合成
        background.paste(image, mask=image.split()[3])  # アルファチャンネルをマスクとして使用
        
        # JPEG形式で出力
        output_buffer = io.BytesIO()
        background.save(output_buffer, format="JPEG", quality=95)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    
    def validate_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        画像の妥当性チェック
        
        Returns:
            Tuple[bool, str]: (有効かどうか, エラーメッセージ)
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # 基本的なチェック
            if image.width < 100 or image.height < 100:
                return False, "画像が小さすぎます（最小100x100px）"
            
            if image.width > 4096 or image.height > 4096:
                return False, "画像が大きすぎます（最大4096x4096px）"
            
            # ファイルサイズチェック
            if len(image_bytes) > 10 * 1024 * 1024:  # 10MB
                return False, "ファイルサイズが大きすぎます（最大10MB）"
            
            return True, ""
            
        except Exception as e:
            return False, f"画像形式が不正です: {e}"