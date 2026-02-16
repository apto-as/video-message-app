"""Person detection API endpoints"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import logging
import json
import base64
from typing import Optional, List
import numpy as np
import cv2

from services.person_detector import PersonDetector
from services.image_processor import ImageProcessor
from core.config import settings

logger = logging.getLogger(__name__)

# LaMa Inpainting service (lazy loaded)
_inpainting_service = None

def get_inpainting_service():
    """Get or initialize inpainting service singleton"""
    global _inpainting_service
    if _inpainting_service is None:
        try:
            from services.inpainting_service import InpaintingService
            _inpainting_service = InpaintingService(device=settings.inpainting_device)
            logger.info("InpaintingService initialized successfully")
        except ImportError as e:
            logger.warning(f"InpaintingService not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize InpaintingService: {e}")
            return None
    return _inpainting_service

def release_inpainting_service():
    """Release inpainting service and free VRAM"""
    global _inpainting_service
    if _inpainting_service is not None:
        try:
            _inpainting_service.unload_model()
            _inpainting_service = None
            logger.info("InpaintingService released")
        except Exception as e:
            logger.warning(f"Failed to release InpaintingService: {e}")

router = APIRouter(prefix="/api/person-detection", tags=["person-detection"])

# Initialize detector (lazy loading on first request)
_detector: Optional[PersonDetector] = None
_image_processor: Optional[ImageProcessor] = None


def get_image_processor() -> ImageProcessor:
    """Get or initialize image processor singleton for background removal"""
    global _image_processor
    if _image_processor is None:
        _image_processor = ImageProcessor()
        logger.info("ImageProcessor initialized for person extraction")
    return _image_processor


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


@router.post("/extract-person")
async def extract_selected_person(
    image: UploadFile = File(...),
    selected_person_ids: str = Form(..., description="JSON array of person IDs to keep, e.g., [0, 2]"),
    conf_threshold: float = Form(0.5, ge=0.0, le=1.0),
    padding: int = Form(20, ge=0, le=100, description="Padding around person bbox in pixels"),
    add_transparent_padding: bool = Form(True, description="Add 300px transparent padding around extracted person"),
    transparent_padding_size: int = Form(300, ge=0, le=500, description="Size of transparent padding in pixels")
):
    """
    Extract only selected persons from image, removing background and other people.

    Args:
        image: Image file (JPEG, PNG, etc.)
        selected_person_ids: JSON array of person IDs to keep (from detect endpoint)
        conf_threshold: Confidence threshold for detection
        padding: Extra padding around person bounding box
        add_transparent_padding: If True, add transparent padding around extracted person (default True)
        transparent_padding_size: Size of transparent padding in pixels (default 300)

    Returns:
        PNG image with only selected persons (transparent background), optionally with extra padding
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {image.content_type}. Expected image file."
        )

    # Parse selected person IDs
    try:
        person_ids = json.loads(selected_person_ids)
        if not isinstance(person_ids, list):
            raise ValueError("selected_person_ids must be a JSON array")
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON for selected_person_ids: {e}"
        )

    file_id = str(uuid.uuid4())
    temp_dir = Path("/tmp/person_detection")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{file_id}_{image.filename}"

    try:
        # Save uploaded file
        content = await image.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        logger.info(f"Processing extraction for persons {person_ids} from {image.filename}")

        # Detect all persons first
        detector = get_detector()
        all_persons = detector.detect_persons(
            str(temp_path),
            conf_threshold=conf_threshold
        )

        if not all_persons:
            raise HTTPException(
                status_code=404,
                detail="No persons detected in the image"
            )

        # Filter to selected persons
        selected_persons = [p for p in all_persons if p["person_id"] in person_ids]

        if not selected_persons:
            raise HTTPException(
                status_code=404,
                detail=f"Selected person IDs {person_ids} not found. Available: {[p['person_id'] for p in all_persons]}"
            )

        # Load image with OpenCV
        img = cv2.imread(str(temp_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise HTTPException(status_code=500, detail="Failed to load image")

        h, w = img.shape[:2]

        # Create mask for selected persons using ImageProcessor service
        try:
            processor = get_image_processor()

            # Create combined mask
            combined_mask = np.zeros((h, w), dtype=np.uint8)

            for person in selected_persons:
                bbox = person["bbox"]
                # Add padding
                x1 = max(0, bbox["x1"] - padding)
                y1 = max(0, bbox["y1"] - padding)
                x2 = min(w, bbox["x2"] + padding)
                y2 = min(h, bbox["y2"] + padding)

                # Extract person region
                person_region = img[y1:y2, x1:x2]

                # Remove background via ImageProcessor service layer
                # Alpha matting有効化: 白い服が透過する問題を軽減
                person_rgba = processor.remove_background_region(
                    person_region,
                    alpha_matting_foreground_threshold=270,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=10,
                )

                # --- LaMa Inpainting Integration ---
                # Repair clothing damaged by background removal
                if settings.is_inpainting_enabled:
                    try:
                        inpainting_svc = get_inpainting_service()
                        if inpainting_svc is not None:
                            from PIL import Image
                            from io import BytesIO

                            # Convert numpy arrays to bytes for inpainting service
                            pil_rembg = Image.fromarray(person_rgba)
                            rembg_buffer = BytesIO()
                            pil_rembg.save(rembg_buffer, format='PNG')
                            rembg_bytes = rembg_buffer.getvalue()

                            # Original region for reference
                            pil_original = Image.fromarray(cv2.cvtColor(person_region, cv2.COLOR_BGR2RGB))
                            original_buffer = BytesIO()
                            pil_original.save(original_buffer, format='PNG')
                            original_bytes = original_buffer.getvalue()

                            # Person bbox within the cropped region
                            region_bbox = {
                                'x1': 0,
                                'y1': 0,
                                'x2': person_rgba.shape[1],
                                'y2': person_rgba.shape[0]
                            }

                            # Run auto repair
                            repaired_bytes, repair_stats = inpainting_svc.auto_repair(
                                original_image=original_bytes,
                                rembg_output=rembg_bytes,
                                bbox=region_bbox,
                                threshold=settings.get_inpainting_threshold,
                                dilate_mask=settings.inpainting_dilate_mask
                            )

                            if repair_stats.get('repaired', False):
                                # Load repaired image back to numpy
                                repaired_img = Image.open(BytesIO(repaired_bytes))
                                person_rgba = np.array(repaired_img)
                                logger.info(f"LaMa inpainting applied: {repair_stats.get('damage_ratio', 0):.2%} damage repaired")
                            else:
                                logger.debug(f"No inpainting needed - damage {repair_stats.get('damage_ratio', 0):.2%} below threshold")

                    except Exception as e:
                        logger.warning(f"LaMa inpainting failed, using original rembg output: {e}")
                # --- End LaMa Inpainting Integration ---

                # Extract alpha channel as mask
                if person_rgba.shape[2] == 4:
                    region_mask = person_rgba[:, :, 3]
                else:
                    # Fallback: create simple rectangular mask
                    region_mask = np.ones((y2-y1, x2-x1), dtype=np.uint8) * 255

                # Place mask in combined mask
                combined_mask[y1:y2, x1:x2] = np.maximum(
                    combined_mask[y1:y2, x1:x2],
                    region_mask
                )

            # Apply mask to original image
            if img.shape[2] == 3:
                # Convert BGR to BGRA
                result = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            else:
                result = img.copy()

            # Apply combined mask as alpha
            result[:, :, 3] = combined_mask

            # Crop to the content bounding box (non-transparent area)
            non_zero = cv2.findNonZero(combined_mask)
            if non_zero is not None:
                content_x, content_y, content_w, content_h = cv2.boundingRect(non_zero)
                result = result[content_y:content_y+content_h, content_x:content_x+content_w]
                final_h, final_w = result.shape[:2]
            else:
                final_h, final_w = result.shape[:2]

            # Add transparent padding if requested
            if add_transparent_padding and transparent_padding_size > 0:
                pad = transparent_padding_size
                padded_h = final_h + 2 * pad
                padded_w = final_w + 2 * pad

                # Create transparent canvas
                padded_result = np.zeros((padded_h, padded_w, 4), dtype=np.uint8)

                # Place the extracted person in the center
                padded_result[pad:pad+final_h, pad:pad+final_w] = result
                result = padded_result
                final_h, final_w = padded_h, padded_w

            # Smart upper-body crop for optimal MuseTalk/LivePortrait input
            upper_body_cropped = False
            crop_metadata = None
            if settings.upper_body_crop_enabled:
                try:
                    from services.upper_body_cropper import get_upper_body_cropper
                    import io
                    from PIL import Image as PILImage

                    cropper = get_upper_body_cropper(
                        target_size=settings.upper_body_crop_target_size,
                        face_ratio=settings.upper_body_crop_face_ratio,
                    )

                    # Compose BGRA onto white background for face detection
                    rgba_pil = PILImage.fromarray(cv2.cvtColor(result, cv2.COLOR_BGRA2RGBA))
                    white_bg = PILImage.new("RGB", rgba_pil.size, (255, 255, 255))
                    white_bg.paste(rgba_pil, mask=rgba_pil.split()[3])
                    buf = io.BytesIO()
                    white_bg.save(buf, format="JPEG", quality=95)
                    rgb_bytes = buf.getvalue()

                    cropped_bytes, crop_metadata = await cropper.crop_upper_body(rgb_bytes)
                    upper_body_cropped = True
                    logger.info(f"Upper-body crop: {crop_metadata}")

                    # Use cropped image for response
                    cropped_base64 = base64.b64encode(cropped_bytes).decode('utf-8')
                    return {
                        "success": True,
                        "image_id": file_id,
                        "extracted_persons": [p["person_id"] for p in selected_persons],
                        "total_persons_detected": len(all_persons),
                        "processed_image": f"data:image/jpeg;base64,{cropped_base64}",
                        "image_dimensions": {"width": settings.upper_body_crop_target_size, "height": settings.upper_body_crop_target_size},
                        "padding_added": add_transparent_padding,
                        "padding_size": transparent_padding_size if add_transparent_padding else 0,
                        "upper_body_cropped": True,
                        "crop_metadata": crop_metadata
                    }
                except Exception as e:
                    logger.warning(f"Upper-body crop failed, using uncropped extraction: {e}")

            # Encode as PNG (fallback if crop disabled or failed)
            _, png_bytes = cv2.imencode('.png', result)
            png_base64 = base64.b64encode(png_bytes.tobytes()).decode('utf-8')

            return {
                "success": True,
                "image_id": file_id,
                "extracted_persons": [p["person_id"] for p in selected_persons],
                "total_persons_detected": len(all_persons),
                "processed_image": f"data:image/png;base64,{png_base64}",
                "image_dimensions": {"width": final_w, "height": final_h},
                "padding_added": add_transparent_padding,
                "padding_size": transparent_padding_size if add_transparent_padding else 0,
                "upper_body_cropped": False
            }

        except ImportError:
            logger.error("rembg/ImageProcessor not available, falling back to bbox-only extraction")
            # Fallback: simple bbox extraction without background removal
            combined_mask = np.zeros((h, w), dtype=np.uint8)

            for person in selected_persons:
                bbox = person["bbox"]
                x1 = max(0, bbox["x1"] - padding)
                y1 = max(0, bbox["y1"] - padding)
                x2 = min(w, bbox["x2"] + padding)
                y2 = min(h, bbox["y2"] + padding)
                combined_mask[y1:y2, x1:x2] = 255

            if img.shape[2] == 3:
                result = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            else:
                result = img.copy()

            result[:, :, 3] = combined_mask

            # Crop to the content bounding box (non-transparent area)
            non_zero = cv2.findNonZero(combined_mask)
            if non_zero is not None:
                content_x, content_y, content_w, content_h = cv2.boundingRect(non_zero)
                result = result[content_y:content_y+content_h, content_x:content_x+content_w]
                final_h, final_w = result.shape[:2]
            else:
                final_h, final_w = result.shape[:2]

            # Add transparent padding if requested
            if add_transparent_padding and transparent_padding_size > 0:
                pad = transparent_padding_size
                padded_h = final_h + 2 * pad
                padded_w = final_w + 2 * pad

                # Create transparent canvas
                padded_result = np.zeros((padded_h, padded_w, 4), dtype=np.uint8)

                # Place the extracted person in the center
                padded_result[pad:pad+final_h, pad:pad+final_w] = result
                result = padded_result
                final_h, final_w = padded_h, padded_w

            # Smart upper-body crop (fallback path)
            if settings.upper_body_crop_enabled:
                try:
                    from services.upper_body_cropper import get_upper_body_cropper
                    import io
                    from PIL import Image as PILImage

                    cropper = get_upper_body_cropper(
                        target_size=settings.upper_body_crop_target_size,
                        face_ratio=settings.upper_body_crop_face_ratio,
                    )

                    rgba_pil = PILImage.fromarray(cv2.cvtColor(result, cv2.COLOR_BGRA2RGBA))
                    white_bg = PILImage.new("RGB", rgba_pil.size, (255, 255, 255))
                    white_bg.paste(rgba_pil, mask=rgba_pil.split()[3])
                    buf = io.BytesIO()
                    white_bg.save(buf, format="JPEG", quality=95)
                    rgb_bytes = buf.getvalue()

                    cropped_bytes, crop_metadata = await cropper.crop_upper_body(rgb_bytes)
                    logger.info(f"Upper-body crop (fallback): {crop_metadata}")

                    cropped_base64 = base64.b64encode(cropped_bytes).decode('utf-8')
                    return {
                        "success": True,
                        "image_id": file_id,
                        "extracted_persons": [p["person_id"] for p in selected_persons],
                        "total_persons_detected": len(all_persons),
                        "processed_image": f"data:image/jpeg;base64,{cropped_base64}",
                        "image_dimensions": {"width": settings.upper_body_crop_target_size, "height": settings.upper_body_crop_target_size},
                        "padding_added": add_transparent_padding,
                        "padding_size": transparent_padding_size if add_transparent_padding else 0,
                        "upper_body_cropped": True,
                        "crop_metadata": crop_metadata,
                        "note": "Background removal not available, using bbox extraction only"
                    }
                except Exception as e:
                    logger.warning(f"Upper-body crop failed (fallback path): {e}")

            _, png_bytes = cv2.imencode('.png', result)
            png_base64 = base64.b64encode(png_bytes.tobytes()).decode('utf-8')

            return {
                "success": True,
                "image_id": file_id,
                "extracted_persons": [p["person_id"] for p in selected_persons],
                "total_persons_detected": len(all_persons),
                "processed_image": f"data:image/png;base64,{png_base64}",
                "image_dimensions": {"width": final_w, "height": final_h},
                "padding_added": add_transparent_padding,
                "padding_size": transparent_padding_size if add_transparent_padding else 0,
                "upper_body_cropped": False,
                "note": "Background removal not available, using bbox extraction only"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Person extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Person extraction failed: {str(e)}"
        )

    finally:
        # Cleanup
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")
