"""Person detection service using YOLOv8"""
from ultralytics import YOLO
import numpy as np
from typing import List, Dict, Optional
import torch
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PersonDetector:
    """YOLOv8-based person detector with GPU acceleration support"""

    def __init__(self, model_path: str = "yolov8n.pt", device: Optional[str] = None):
        """
        Initialize person detector

        Args:
            model_path: Path to YOLOv8 model weights
            device: Device to run model on ('cuda', 'cpu', or None for auto-detect)
        """
        # Auto-detect best available device
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
                logger.info(f"CUDA available: using {torch.cuda.get_device_name(0)}")
            else:
                device = "cpu"
                logger.info("CUDA not available: using CPU")

        self.device = device

        try:
            self.model = YOLO(model_path)
            self.model.to(self.device)
            logger.info(f"YOLOv8 model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise

    def detect_persons(
        self,
        image_path: str,
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45
    ) -> List[Dict]:
        """
        Detect persons in image and return bounding boxes

        Args:
            image_path: Path to image file
            conf_threshold: Confidence threshold for detection (0.0 - 1.0)
            iou_threshold: IoU threshold for NMS

        Returns:
            List of detected persons with bounding boxes and confidence scores

        Example:
            [
                {
                    "person_id": 0,
                    "bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 400},
                    "confidence": 0.95,
                    "center": {"x": 200, "y": 225},
                    "area": 70000
                }
            ]
        """
        if not Path(image_path).exists():
            logger.error(f"Image not found: {image_path}")
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            # YOLO inference with class filtering (class 0 = person)
            results = self.model(
                image_path,
                conf=conf_threshold,
                iou=iou_threshold,
                classes=[0],  # Filter for person class only
                verbose=False
            )

            persons = []
            for result in results:
                boxes = result.boxes

                if boxes is None or len(boxes) == 0:
                    logger.info(f"No persons detected in {image_path}")
                    continue

                for i, box in enumerate(boxes):
                    # Extract bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])

                    # Calculate center point and area
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    area = int((x2 - x1) * (y2 - y1))

                    persons.append({
                        "person_id": i,
                        "bbox": {
                            "x1": int(x1),
                            "y1": int(y1),
                            "x2": int(x2),
                            "y2": int(y2)
                        },
                        "confidence": round(conf, 3),
                        "center": {
                            "x": center_x,
                            "y": center_y
                        },
                        "area": area
                    })

            logger.info(f"Detected {len(persons)} person(s) in {image_path}")
            return persons

        except Exception as e:
            logger.error(f"Person detection failed: {e}")
            raise

    def get_model_info(self) -> Dict:
        """Get information about loaded model"""
        return {
            "model_name": "YOLOv8n",
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "input_size": 640  # YOLOv8n default input size
        }
