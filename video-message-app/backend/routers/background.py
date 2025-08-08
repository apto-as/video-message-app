"""
背景削除・画像処理ルーター
"""

from fastapi import APIRouter, HTTPException, File, Form, UploadFile
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
    image: UploadFile = File(..., description="処理する画像"),
    remove_background: bool = Form(default=True, description="背景削除を実行"),
    enhance_quality: bool = Form(default=True, description="画質向上を実行"),
    background: Optional[UploadFile] = File(None, description="背景画像（オプション）")
):
    """画像の背景処理を実行"""
    
    temp_files = []
    
    try:
        # 画像データ読み込み
        image_content = await image.read()
        
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
            
            # 背景画像の検証も統一的に実行
            bg_valid, bg_error = processor.validate_image(background_content)
            if not bg_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"背景画像検証エラー: {bg_error}"
                )
        
        # 実際の画像処理を実行
        processed_image_bytes = image_content  # デフォルトは元画像
        
        if remove_background or background_content or enhance_quality:
            # ImageProcessorを使用した実際の処理
            processed_image_bytes = await processor.process_for_did(
                image_bytes=image_content,
                background_bytes=background_content,
                enhance_quality=enhance_quality
            )
        
        processing_info = {
            "background_removed": remove_background,
            "background_composited": background_content is not None,
            "quality_enhanced": enhance_quality,
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"画像処理エラー: {str(e)}")
        return ImageProcessResponse(
            success=False,
            error=str(e),
            message="画像処理中にエラーが発生しました"
        )
        
    finally:
        # 一時ファイル削除
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"一時ファイル削除失敗: {temp_file} - {str(e)}")

@router.post("/background/remove-background")
async def remove_background_only(
    image: UploadFile = File(..., description="背景削除する画像")
):
    """背景削除のみを実行（シンプル版）"""
    
    try:
        # 画像データ読み込み
        image_content = await image.read()
        
        # ImageProcessorを使用した統一的な画像検証
        processor = ImageProcessor()
        is_valid, error_msg = processor.validate_image(image_content)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"画像検証エラー: {error_msg}"
            )
        
        # 実際の背景削除を実行
        processed_image_bytes = await processor.remove_background(image_content)
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"背景削除エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"背景削除中にエラーが発生しました: {str(e)}"
        )