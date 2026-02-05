"""
背景削除・画像処理ルーター

セキュリティ対策:
- Image bomb detection
- Metadata validation
- Processing timeout enforcement
- Per-user resource limiting
"""

from fastapi import APIRouter, HTTPException, File, Form, UploadFile, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import tempfile
import asyncio
from pathlib import Path
import aiofiles
import json
import base64
from datetime import datetime
import logging

from services.image_processor import ImageProcessor
from core.config import settings
from security.image_validator import (
    ImageSecurityValidator,
    ProcessingTimeoutManager,
    ProcessingTimeoutError,
    resource_limiter
)

router = APIRouter(tags=["Background Processing"])
logger = logging.getLogger(__name__)

class ImageProcessResponse(BaseModel):
    success: bool
    processed_image: Optional[str] = None
    processing_info: Optional[dict] = None
    message: str
    error: Optional[str] = None

@router.get("/background/health")
async def health_check():
    """背景処理サービスのヘルスチェック"""
    return {
        "status": "healthy", 
        "service": "background_processing",
        "message": "背景削除・画像処理サービスが利用可能です"
    }

@router.post("/process-image", response_model=ImageProcessResponse)
async def process_image(
    request: Request,
    image: UploadFile = File(..., description="処理する画像"),
    remove_background: bool = Form(default=True, description="背景削除を実行"),
    enhance_quality: bool = Form(default=True, description="画質向上を実行"),
    background: Optional[UploadFile] = File(None, description="背景画像（オプション）")
):
    """
    画像の背景処理を実行

    セキュリティ対策:
    - 並列リクエスト制限（ユーザーごと）
    - Image bomb検出
    - メタデータ検証
    - 処理タイムアウト
    """

    # Per-user resource limiting
    client_id = request.client.host
    if not resource_limiter.acquire(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent requests. Max {resource_limiter.max_concurrent} per user."
        )

    temp_files = []

    try:
        # 画像データ読み込み
        image_content = await image.read()

        # SECURITY: Image bomb detection & metadata validation
        is_safe, error_msg = ImageSecurityValidator.comprehensive_validation(image_content)
        if not is_safe:
            logger.warning(f"Security validation failed from {client_id}: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"セキュリティ検証エラー: {error_msg}"
            )
        
        # ImageProcessorを使用した統一的な画像検証
        processor = ImageProcessor()
        is_valid, error_msg = processor.validate_image(image_content)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"画像検証エラー: {error_msg}"
            )
        
        logger.info(f"画像処理開始: remove_background={remove_background}, enhance_quality={enhance_quality}")
        
        # 処理が不要な場合
        if not remove_background and not background and not enhance_quality:
            return ImageProcessResponse(
                success=False,
                message="処理対象が選択されていません"
            )
        
        # 一時ファイルに保存
        input_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix)
        temp_files.append(input_file.name)
        
        async with aiofiles.open(input_file.name, 'wb') as f:
            await f.write(image_content)
        
        # 背景画像の処理
        background_content = None
        if background:
            background_content = await background.read()

            # SECURITY: Background image validation
            bg_safe, bg_error = ImageSecurityValidator.comprehensive_validation(background_content)
            if not bg_safe:
                logger.warning(f"Background validation failed from {client_id}: {bg_error}")
                raise HTTPException(
                    status_code=400,
                    detail=f"背景画像セキュリティエラー: {bg_error}"
                )

            # 背景画像の検証も統一的に実行
            bg_valid, bg_error = processor.validate_image(background_content)
            if not bg_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"背景画像検証エラー: {bg_error}"
                )

        # 実際の画像処理を実行（タイムアウト付き）
        processed_image_bytes = image_content  # デフォルトは元画像

        if remove_background or background_content or enhance_quality:
            # SECURITY: Timeout enforcement
            with ProcessingTimeoutManager(timeout_seconds=30) as timeout:
                # ImageProcessorを使用した実際の処理
                processed_image_bytes = await processor.process_for_lipsync(
                    image_bytes=image_content,
                    background_bytes=background_content,
                    enhance_quality=enhance_quality
                )

                # Smart upper-body crop for optimal MuseTalk/LivePortrait input
                if settings.upper_body_crop_enabled:
                    from services.upper_body_cropper import get_upper_body_cropper
                    cropper = get_upper_body_cropper(
                        target_size=settings.upper_body_crop_target_size,
                        face_ratio=settings.upper_body_crop_face_ratio,
                    )
                    try:
                        processed_image_bytes, crop_metadata = await cropper.crop_upper_body(processed_image_bytes)
                        logger.info(f"Upper-body crop: {crop_metadata}")
                    except Exception as e:
                        logger.warning(f"Upper-body crop failed, using uncropped image: {e}")

                # Check timeout after processing
                timeout.check_timeout()
        
        processing_info = {
            "background_removed": remove_background,
            "background_composited": background_content is not None,
            "quality_enhanced": enhance_quality,
            "upper_body_cropped": settings.upper_body_crop_enabled,
            "original_size": len(image_content),
            "processed_size": len(processed_image_bytes),
            "processed_at": datetime.now().isoformat()
        }
        
        # 処理済み画像をBase64として返す
        processed_image_data = base64.b64encode(processed_image_bytes).decode('utf-8')
        processed_image_url = f"data:image/jpeg;base64,{processed_image_data}"
        
        logger.info(f"画像処理完了: {processing_info}")

        return ImageProcessResponse(
            success=True,
            processed_image=processed_image_url,
            processing_info=processing_info,
            message="画像処理が完了しました"
        )

    except ProcessingTimeoutError as e:
        logger.error(f"処理タイムアウト from {client_id}: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail=f"処理タイムアウト: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"画像処理エラー from {client_id}: {str(e)}")
        return ImageProcessResponse(
            success=False,
            error=str(e),
            message="画像処理中にエラーが発生しました"
        )

    finally:
        # SECURITY: Release resource slot
        resource_limiter.release(client_id)

        # 一時ファイル削除
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"一時ファイル削除失敗: {temp_file} - {str(e)}")

@router.post("/background/remove-background")
async def remove_background_only(
    request: Request,
    image: UploadFile = File(..., description="背景削除する画像")
):
    """
    背景削除のみを実行（シンプル版）

    セキュリティ対策:
    - 並列リクエスト制限
    - Image bomb検出
    - 処理タイムアウト
    """

    # Per-user resource limiting
    client_id = request.client.host
    if not resource_limiter.acquire(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent requests. Max {resource_limiter.max_concurrent} per user."
        )

    try:
        # 画像データ読み込み
        image_content = await image.read()

        # SECURITY: Image bomb detection & metadata validation
        is_safe, error_msg = ImageSecurityValidator.comprehensive_validation(image_content)
        if not is_safe:
            logger.warning(f"Security validation failed from {client_id}: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"セキュリティ検証エラー: {error_msg}"
            )

        # ImageProcessorを使用した統一的な画像検証
        processor = ImageProcessor()
        is_valid, error_msg = processor.validate_image(image_content)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"画像検証エラー: {error_msg}"
            )

        # SECURITY: Timeout enforcement
        with ProcessingTimeoutManager(timeout_seconds=30) as timeout:
            # 実際の背景削除を実行
            processed_image_bytes = await processor.remove_background(image_content)

            # Check timeout
            timeout.check_timeout()
        
        # 処理済み画像をBase64として返す
        processed_image_data = base64.b64encode(processed_image_bytes).decode('utf-8')
        processed_image_url = f"data:image/png;base64,{processed_image_data}"
        
        return JSONResponse(content={
            "success": True,
            "processed_image": processed_image_url,
            "message": "背景削除が完了しました",
            "processing_info": {
                "original_size": len(image_content),
                "processed_size": len(processed_image_bytes),
                "background_removed": True
            }
        })

    except ProcessingTimeoutError as e:
        logger.error(f"処理タイムアウト from {client_id}: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail=f"処理タイムアウト: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"背景削除エラー from {client_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"背景削除中にエラーが発生しました: {str(e)}"
        )

    finally:
        # SECURITY: Release resource slot
        resource_limiter.release(client_id)