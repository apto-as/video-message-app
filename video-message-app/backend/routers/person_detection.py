"""Person detection API endpoints"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import logging
from typing import Optional

from services.person_detector import PersonDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/person-detection", tags=["person-detection"])

# Initialize detector (lazy loading on first request)
_detector: Optional[PersonDetector] = None


def get_detector() -> PersonDetector:
    """Get or initialize person detector singleton"""
    global _detector
    if _detector is None:
        try:
            _detector = PersonDetector(device=None)  # Auto-detects GPU/CPU
            logger.info("PersonDetector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PersonDetector: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize person detection model"
            )
    return _detector


@router.get("/health")
async def health_check():
    """Health check endpoint for person detection service"""
    try:
        detector = get_detector()
        model_info = detector.get_model_info()
        return {
            "status": "healthy",
            "service": "Person Detection API",
            "model": model_info
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@router.post("/detect")
async def detect_persons(
    image: UploadFile = File(...),
    conf_threshold: float = Query(0.5, ge=0.0, le=1.0, description="Confidence threshold"),
    iou_threshold: float = Query(0.45, ge=0.0, le=1.0, description="IoU threshold for NMS")
):
    """
    Detect persons in uploaded image

    Args:
        image: Image file (JPEG, PNG, etc.)
        conf_threshold: Confidence threshold (0.0 - 1.0), default 0.5
        iou_threshold: IoU threshold for Non-Maximum Suppression (0.0 - 1.0), default 0.45

    Returns:
        JSON response with detected persons and their bounding boxes
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {image.content_type}. Expected image file."
        )

    # Generate unique ID for this detection request
    file_id = str(uuid.uuid4())
    temp_dir = Path("/tmp/person_detection")
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = temp_dir / f"{file_id}_{image.filename}"

    try:
        # Save uploaded file to temp location
        content = await image.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Verify file was saved
        if not temp_path.exists():
            raise FileNotFoundError(f"Failed to save image to {temp_path}")

        logger.info(f"Processing image: {image.filename} (ID: {file_id}), saved to: {temp_path}, size: {temp_path.stat().st_size} bytes")

        # Detect persons
        detector = get_detector()
        persons = detector.detect_persons(
            str(temp_path),
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold
        )

        response = {
            "image_id": file_id,
            "filename": image.filename,
            "person_count": len(persons),
            "persons": persons,
            "parameters": {
                "conf_threshold": conf_threshold,
                "iou_threshold": iou_threshold
            }
        }

        logger.info(f"Detection complete: {len(persons)} person(s) found")
        return response

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Detection failed for {image.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Person detection failed: {str(e)}"
        )

    finally:
        # Cleanup temp file
        if temp_path.exists():
            try:
                temp_path.unlink()
                logger.debug(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")


@router.get("/model-info")
async def get_model_info():
    """Get information about the person detection model"""
    try:
        detector = get_detector()
        return detector.get_model_info()
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve model information"
        )
