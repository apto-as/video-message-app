"""
画像処理サービス
背景削除、背景合成、品質向上などの機能を提供
"""
import asyncio
import io
from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import rembg


class ImageProcessor:
    """画像処理サービスクラス"""
    
    def __init__(self):
        """初期化"""
        self.session = rembg.new_session('u2net')
    
    def validate_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        画像の妥当性を検証（セキュリティを考慮した堅牢な実装）
        
        Args:
            image_bytes: 検証する画像のバイナリデータ
            
        Returns:
            (is_valid: bool, error_message: str)
        """
        try:
            # 基本的なデータチェック
            if not image_bytes or len(image_bytes) == 0:
                return False, "画像データが空です"
            
            # ファイルサイズ制限（DoS攻撃防止 - 10MB制限）
            if len(image_bytes) > 10 * 1024 * 1024:
                return False, "ファイルサイズは10MB以下にしてください"
            
            # マジックバイト検証（基本的なファイル偽装検知）
            magic_bytes = image_bytes[:20]  # 最初の20バイトをチェック
            
            # 一般的な画像フォーマットのマジックバイト
            valid_formats = {
                b'\xff\xd8\xff': 'JPEG',
                b'\x89PNG\r\n\x1a\n': 'PNG', 
                b'RIFF': 'WEBP',  # WEBPはRIFFコンテナ
                b'BM': 'BMP',
                b'GIF87a': 'GIF',
                b'GIF89a': 'GIF'
            }
            
            is_valid_format = False
            for magic, fmt in valid_formats.items():
                if magic_bytes.startswith(magic):
                    is_valid_format = True
                    break
            
            if not is_valid_format:
                return False, "サポートされていない画像形式です"
            
            # PIL安全読み込み（メモリ枯渇攻撃防止）
            try:
                with Image.open(io.BytesIO(image_bytes)) as image:
                    # サポートする形式チェック
                    if image.format not in ['JPEG', 'PNG', 'WEBP', 'BMP', 'GIF']:
                        return False, f"サポートされていない画像形式: {image.format}"
                    
                    # 画像サイズ制限（50MP制限 - メモリ枯渇攻撃防止）
                    if image.width * image.height > 50_000_000:
                        return False, "画像サイズが大きすぎます（50MP以下にしてください）"
                    
                    # 最大解像度制限（8K解像度まで）
                    if image.width > 7680 or image.height > 4320:
                        return False, "画像解像度は8K以下にしてください"
                    
                    # 最小サイズチェック
                    if image.width < 64 or image.height < 64:
                        return False, "画像サイズは64x64ピクセル以上にしてください"
                    
                    # 危険な形式除外（セキュリティリスクのある形式）
                    if image.format in ['ICNS', 'ICO', 'CUR']:
                        return False, "この画像形式はサポートされていません"
                    
            except (OSError, IOError, ValueError) as e:
                return False, "破損した画像ファイルまたは無効な形式です"
            
            return True, ""
            
        except Exception:
            # セキュリティのため、詳細エラー情報は隠蔽
            return False, "画像検証中にエラーが発生しました"
        
    async def remove_background(self, image_bytes: bytes) -> bytes:
        """
        画像から背景を削除する
        
        Args:
            image_bytes: 入力画像のバイナリデータ
            
        Returns:
            背景削除後の画像バイナリデータ
        """
        # CPUバウンドなタスクを別スレッドで実行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self._remove_background_sync, 
            image_bytes
        )
        return result
    
    def _remove_background_sync(self, image_bytes: bytes) -> bytes:
        """背景削除の同期実行部分"""
        # rembgで背景削除
        output = rembg.remove(image_bytes, session=self.session)
        return output
    
    async def composite_background(self, subject_bytes: bytes, background_bytes: bytes) -> bytes:
        """
        被写体と背景を合成する
        
        Args:
            subject_bytes: 背景削除済みの被写体画像
            background_bytes: 背景画像
            
        Returns:
            合成後の画像バイナリデータ
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._composite_background_sync,
            subject_bytes, background_bytes
        )
        return result
    
    def _composite_background_sync(self, subject_bytes: bytes, background_bytes: bytes) -> bytes:
        """背景合成の同期実行部分"""
        # 被写体画像を読み込み
        subject = Image.open(io.BytesIO(subject_bytes)).convert("RGBA")
        
        # 背景画像を読み込み
        background = Image.open(io.BytesIO(background_bytes)).convert("RGB")
        
        # 被写体のサイズに背景をリサイズ
        background = background.resize(subject.size, Image.Resampling.LANCZOS)
        background = background.convert("RGBA")
        
        # アルファ合成
        composite = Image.alpha_composite(background, subject)
        
        # RGBに変換して出力
        final_image = composite.convert("RGB")
        
        # バイナリとして保存
        output_buffer = io.BytesIO()
        final_image.save(output_buffer, format="JPEG", quality=95)
        return output_buffer.getvalue()
    
    async def _enhance_edges(self, image_bytes: bytes) -> bytes:
        """
        エッジを強化して品質を向上させる
        
        Args:
            image_bytes: 入力画像のバイナリデータ
            
        Returns:
            品質向上後の画像バイナリデータ
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._enhance_edges_sync,
            image_bytes
        )
        return result
    
    def _enhance_edges_sync(self, image_bytes: bytes) -> bytes:
        """エッジ強化の同期実行部分"""
        image = Image.open(io.BytesIO(image_bytes))
        
        # シャープネス強化
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # 軽微なノイズ除去
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # バイナリとして保存
        output_buffer = io.BytesIO()
        if image.mode == "RGBA":
            image.save(output_buffer, format="PNG")
        else:
            image.save(output_buffer, format="JPEG", quality=95)
        
        return output_buffer.getvalue()
    
    async def process_for_did(self, image_bytes: bytes, background_bytes: Optional[bytes] = None, enhance_quality: bool = True) -> bytes:
        """
        D-ID APIに送信するための画像処理パイプライン
        
        Args:
            image_bytes: 入力画像のバイナリデータ
            background_bytes: 背景画像のバイナリデータ（オプション）
            enhance_quality: 品質向上を行うかどうか
            
        Returns:
            処理済み画像のバイナリデータ
        """
        # Step 1: 背景削除
        subject_bytes = await self.remove_background(image_bytes)
        
        # Step 2: 品質向上（オプション）
        if enhance_quality:
            subject_bytes = await self._enhance_edges(subject_bytes)
        
        # Step 3: 背景合成（背景が提供された場合）
        if background_bytes:
            final_bytes = await self.composite_background(subject_bytes, background_bytes)
            return final_bytes
        else:
            # 背景削除のみの場合、透明部分を白で塗りつぶし
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._add_white_background,
                subject_bytes
            )
            return result
    
    def _add_white_background(self, image_bytes: bytes) -> bytes:
        """透明背景を白背景に変換"""
        image = Image.open(io.BytesIO(image_bytes))
        
        if image.mode == "RGBA":
            # 白背景を作成
            background = Image.new("RGB", image.size, (255, 255, 255))
            # アルファチャンネルを使用して合成
            background.paste(image, mask=image.split()[-1])  # アルファチャンネルをマスクとして使用
            image = background
        
        # JPEG形式で保存
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="JPEG", quality=95)
        return output_buffer.getvalue()