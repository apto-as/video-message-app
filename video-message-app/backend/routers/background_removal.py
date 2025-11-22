"""Background removal API endpoints"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from pathlib import Path
import uuid
import logging
import os

router = APIRouter(prefix="/api/background-removal", tags=["background-removal"])
logger = logging.getLogger(__name__)

# Lazy-load the background remover (heavy model)
_remover = None


def get_remover():
    """Get or initialize background remover singleton"""
    global _remover
    if _remover is None:
        from services.background_remover import BackgroundRemover

        # Determine model path based on environment
        if os.path.exists("/app/data/models/birefnet-portrait"):
            # Docker environment
            model_dir = "/app/data/models/birefnet-portrait"
        else:
            # Local environment
            model_dir = Path(__file__).parent.parent.parent / "data" / "models" / "birefnet-portrait"

        if not Path(model_dir).exists():
            raise RuntimeError(f"BiRefNet model not found at {model_dir}")

        _remover = BackgroundRemover(
            model_dir=str(model_dir),
            device="cuda",
            use_tensorrt=True,
            use_fp16=True
        )
        logger.info("Background remover initialized")

    return _remover


@router.get("/health")
async def health_check():
    """Check BiRefNet service health"""
    try:
        remover = get_remover()
        return {
            "status": "healthy",
            "model": "BiRefNet-portrait",
            "device": remover.device,
            "tensorrt_enabled": remover.use_tensorrt,
            "fp16_enabled": remover.use_fp16
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@router.post("/remove")
async def remove_background(
    image: UploadFile = File(..., description="Input image (JPG/PNG)"),
    smoothing: bool = Query(True, description="Apply edge smoothing")
):
    """Remove background from uploaded image

    Returns PNG image with transparent background
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    # Create temp directory if needed
    temp_dir = Path("/tmp/bg_removal")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    file_id = str(uuid.uuid4())
    temp_input = temp_dir / f"{file_id}_input{Path(image.filename).suffix}"

    try:
        # Write uploaded file
        content = await image.read()
        with open(temp_input, "wb") as f:
            f.write(content)

        # Remove background
        remover = get_remover()
        png_bytes = remover.remove_background(
            str(temp_input),
            return_bytes=True,
            smoothing=smoothing
        )

        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={file_id}_nobg.png"
            }
        )

    except Exception as e:
        logger.error(f"Background removal failed: {e}", exc_info=True)
        raise HTTPException(500, f"Background removal failed: {str(e)}")

    finally:
        # Cleanup
        if temp_input.exists():
            try:
                temp_input.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")
