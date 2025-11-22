"""Background removal service using BiRefNet with TensorRT optimization"""
import torch
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import time
import logging
from safetensors.torch import load_file

logger = logging.getLogger(__name__)

class BackgroundRemover:
    """BiRefNet-based background removal with TensorRT optimization"""

    def __init__(
        self,
        model_dir: str,
        device: str = "cuda",
        use_tensorrt: bool = True,
        use_fp16: bool = True,
        input_size: Tuple[int, int] = (1024, 1024)
    ):
        """Initialize BiRefNet background remover

        Args:
            model_dir: Path to BiRefNet model directory (contains model.safetensors)
            device: 'cuda' or 'cpu'
            use_tensorrt: Whether to use TensorRT optimization (CUDA only)
            use_fp16: Whether to use FP16 precision
            input_size: Input image size (width, height)
        """
        self.device = device if torch.cuda.is_available() else "cpu"
        self.input_size = input_size
        self.use_tensorrt = use_tensorrt and self.device == "cuda"
        self.use_fp16 = use_fp16 and self.device == "cuda"

        logger.info(f"Initializing BiRefNet: device={self.device}, TensorRT={self.use_tensorrt}, FP16={self.use_fp16}")

        # Load BiRefNet model
        self.model = self._load_model(model_dir)

        # Convert to TensorRT if requested
        if self.use_tensorrt:
            self._convert_to_tensorrt()
        elif self.use_fp16:
            # Fallback to PyTorch FP16
            self.model.half()
            logger.info("Using PyTorch FP16")

        logger.info("BiRefNet loaded successfully")

    def _load_model(self, model_dir: str):
        """Load BiRefNet model from safetensors using transformers AutoModel"""
        from transformers import AutoModelForImageSegmentation

        model_path = Path(model_dir)
        safetensors_path = model_path / "model.safetensors"

        if not safetensors_path.exists():
            raise FileNotFoundError(f"model.safetensors not found in {model_dir}")

        try:
            # Load model using transformers
            # This handles the config and model architecture automatically
            model = AutoModelForImageSegmentation.from_pretrained(
                model_dir,
                trust_remote_code=True,
                local_files_only=True
            )

            model.to(self.device)
            model.eval()

            logger.info(f"Model loaded from {model_dir}")
            return model

        except Exception as e:
            logger.error(f"Failed to load BiRefNet model: {e}")
            raise

    def _convert_to_tensorrt(self):
        """Convert PyTorch model to TensorRT FP16"""
        try:
            import torch_tensorrt

            logger.info("Converting model to TensorRT FP16...")

            # Dummy input for tracing
            dummy_input = torch.randn(1, 3, *self.input_size).to(self.device)
            if self.use_fp16:
                dummy_input = dummy_input.half()

            # TensorRT compilation
            self.model = torch_tensorrt.compile(
                self.model,
                inputs=[dummy_input],
                enabled_precisions={torch.float16} if self.use_fp16 else {torch.float32},
                workspace_size=1 << 30,  # 1GB
                min_block_size=1,
                max_batch_size=1
            )

            logger.info("TensorRT conversion successful")

        except ImportError:
            logger.warning("torch_tensorrt not available, falling back to PyTorch FP16")
            self.use_tensorrt = False
            if self.use_fp16:
                self.model.half()
        except Exception as e:
            logger.warning(f"TensorRT conversion failed: {e}, using PyTorch FP16")
            self.use_tensorrt = False
            if self.use_fp16:
                self.model.half()

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess image for BiRefNet

        Args:
            image: Input image (BGR, uint8)

        Returns:
            Preprocessed tensor (1, 3, H, W)
        """
        # Resize
        image = cv2.resize(image, self.input_size, interpolation=cv2.INTER_LINEAR)

        # BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Normalize (ImageNet stats)
        image = image.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        image = (image - mean) / std

        # HWC -> CHW
        image = np.transpose(image, (2, 0, 1))

        # Add batch dimension
        image = np.expand_dims(image, axis=0)

        tensor = torch.from_numpy(image).to(self.device)

        # Convert to FP16 if needed
        if self.use_fp16:
            tensor = tensor.half()

        return tensor

    def postprocess(
        self,
        mask: torch.Tensor,
        original_image: np.ndarray,
        apply_smoothing: bool = True
    ) -> np.ndarray:
        """Postprocess alpha matte and composite with original image

        Args:
            mask: Predicted mask (1, 1, H, W) or (1, H, W)
            original_image: Original input image (BGR, uint8)
            apply_smoothing: Whether to apply Gaussian smoothing

        Returns:
            RGBA image (H, W, 4) uint8
        """
        # Convert to numpy
        if mask.dim() == 4:
            mask = mask.squeeze(0).squeeze(0)  # (1, 1, H, W) -> (H, W)
        elif mask.dim() == 3:
            mask = mask.squeeze(0)  # (1, H, W) -> (H, W)

        mask = mask.cpu().float().numpy()

        # Resize to original size
        h, w = original_image.shape[:2]
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)

        # Threshold and normalize
        mask = np.clip(mask, 0, 1)

        # Smoothing (optional)
        if apply_smoothing:
            mask = cv2.GaussianBlur(mask, (5, 5), 0)

        # Convert to uint8
        alpha = (mask * 255).astype(np.uint8)

        # Create RGBA
        rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        rgba = np.dstack((rgb, alpha))

        return rgba

    @torch.no_grad()
    def remove_background(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        return_bytes: bool = True,
        smoothing: bool = True
    ) -> Optional[bytes]:
        """Remove background from image

        Args:
            image_path: Path to input image
            output_path: Optional path to save output
            return_bytes: Whether to return PNG bytes
            smoothing: Whether to apply edge smoothing

        Returns:
            PNG bytes (if return_bytes=True), otherwise None
        """
        start_time = time.perf_counter()

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        original_image = image.copy()

        # Preprocess
        input_tensor = self.preprocess(image)

        # Inference
        inference_start = time.perf_counter()
        mask = self.model(input_tensor)

        # Handle different output formats
        if isinstance(mask, (list, tuple)):
            mask = mask[0]  # Take first output if multiple

        inference_time = (time.perf_counter() - inference_start) * 1000  # ms

        # Postprocess
        rgba = self.postprocess(mask, original_image, apply_smoothing=smoothing)

        total_time = (time.perf_counter() - start_time) * 1000  # ms

        logger.info(f"Background removal: inference={inference_time:.1f}ms, total={total_time:.1f}ms")

        # Save to file
        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))

        # Return bytes
        if return_bytes:
            _, png_bytes = cv2.imencode('.png', cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
            return png_bytes.tobytes()

        return None
