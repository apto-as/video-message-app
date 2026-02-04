"""
LaMa-based clothing repair service for fixing rembg artifacts.

This service detects and repairs clothing that was incorrectly made transparent
by background removal, particularly white or light-colored garments.
"""

import logging
from typing import Tuple, Optional, Dict, Any
from io import BytesIO

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class InpaintingService:
    """
    LaMa-based clothing repair service.

    Uses simple-lama-inpainting to repair areas where rembg incorrectly
    removed parts of clothing (especially white garments).

    Usage:
        service = InpaintingService()
        repaired = service.auto_repair(original_bytes, rembg_output_bytes)
        service.unload_model()  # Release VRAM when done
    """

    def __init__(self, device: Optional[str] = None):
        """
        Initialize the inpainting service.

        Args:
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.model = None
        self._device = device
        self._model_loaded = False

        # Auto-detect device if not specified
        if self._device is None:
            try:
                import torch
                if torch.cuda.is_available():
                    self._device = "cuda"
                    logger.info("InpaintingService: CUDA detected, using GPU")
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self._device = "cpu"  # LaMa doesn't fully support MPS yet
                    logger.info("InpaintingService: MPS detected, but using CPU for LaMa compatibility")
                else:
                    self._device = "cpu"
                    logger.info("InpaintingService: Using CPU")
            except ImportError:
                self._device = "cpu"
                logger.warning("InpaintingService: PyTorch not available, defaulting to CPU")

    @property
    def device(self) -> str:
        """Get the device being used."""
        return self._device

    def _load_model(self) -> None:
        """
        Lazy-load the LaMa inpainting model.

        The model is only loaded when needed to conserve VRAM.
        """
        if self._model_loaded:
            return

        try:
            from simple_lama_inpainting import SimpleLama

            logger.info(f"Loading LaMa inpainting model on {self._device}...")
            self.model = SimpleLama(device=self._device)
            self._model_loaded = True
            logger.info("LaMa inpainting model loaded successfully")

        except ImportError as e:
            logger.error(f"simple-lama-inpainting not installed: {e}")
            raise ImportError(
                "simple-lama-inpainting is required for clothing repair. "
                "Install with: pip install simple-lama-inpainting"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load LaMa model: {e}")
            raise

    def detect_clothing_damage(
        self,
        original_image: bytes,
        rembg_output: bytes,
        bbox: Optional[Dict[str, int]] = None,
        threshold: float = 0.01
    ) -> Tuple[bool, Optional[bytes], Dict[str, Any]]:
        """
        Detect if rembg incorrectly removed clothing.

        Compares the alpha channel of rembg output with expected person region
        to identify areas that should be opaque but are transparent.

        Args:
            original_image: Original image bytes (before background removal)
            rembg_output: Image bytes with alpha channel from rembg
            bbox: Optional bounding box dict with x1, y1, x2, y2 keys
            threshold: Minimum damage ratio to trigger repair (0.0-1.0)

        Returns:
            Tuple of (is_damaged, damage_mask_bytes, stats_dict)
            - is_damaged: True if damage exceeds threshold
            - damage_mask_bytes: PNG bytes of the damage mask (white = damaged)
            - stats_dict: Statistics about the damage detection
        """
        try:
            # Load images
            original = Image.open(BytesIO(original_image)).convert('RGB')
            rembg_img = Image.open(BytesIO(rembg_output)).convert('RGBA')

            # Extract alpha channel
            alpha = np.array(rembg_img.split()[-1])
            original_np = np.array(original)

            h, w = alpha.shape

            # Define analysis region (bbox or full image)
            if bbox:
                x1 = max(0, bbox.get('x1', 0))
                y1 = max(0, bbox.get('y1', 0))
                x2 = min(w, bbox.get('x2', w))
                y2 = min(h, bbox.get('y2', h))
            else:
                x1, y1, x2, y2 = 0, 0, w, h

            # Extract region of interest
            alpha_roi = alpha[y1:y2, x1:x2]
            original_roi = original_np[y1:y2, x1:x2]

            # Find transparent pixels that might be clothing damage
            # Strategy: Look for transparent pixels in bright areas (likely white clothing)

            # Convert to grayscale for brightness analysis
            brightness = np.mean(original_roi, axis=2)

            # Transparent pixels (alpha < 128) in bright areas (brightness > 200)
            # are likely damaged white clothing
            transparent_mask = alpha_roi < 128
            bright_mask = brightness > 200

            # Also consider semi-transparent pixels (128 <= alpha < 200) as potential damage
            semi_transparent_mask = (alpha_roi >= 128) & (alpha_roi < 200)

            # Damage candidates: transparent bright pixels or semi-transparent bright pixels
            damage_candidates = (transparent_mask & bright_mask) | (semi_transparent_mask & bright_mask)

            # Additional heuristic: check color variance
            # Solid white clothing has low color variance
            color_variance = np.var(original_roi, axis=2)
            low_variance_mask = color_variance < 500  # Low variance = solid color

            # Final damage mask: transparent/semi-transparent, bright, low variance areas
            damage_in_roi = damage_candidates & low_variance_mask

            # Create full-size damage mask
            damage_mask = np.zeros((h, w), dtype=np.uint8)
            damage_mask[y1:y2, x1:x2] = damage_in_roi.astype(np.uint8) * 255

            # Apply morphological operations to clean up the mask
            from PIL import ImageFilter
            damage_pil = Image.fromarray(damage_mask)

            # Dilate to connect nearby damaged areas
            damage_pil = damage_pil.filter(ImageFilter.MaxFilter(5))
            # Erode to remove noise
            damage_pil = damage_pil.filter(ImageFilter.MinFilter(3))

            damage_mask = np.array(damage_pil)

            # Calculate statistics
            total_person_pixels = np.sum(alpha_roi >= 128)  # Visible person pixels
            if total_person_pixels == 0:
                # No person detected in region
                logger.warning("No visible person pixels found in the analysis region")
                total_person_pixels = (y2 - y1) * (x2 - x1)  # Use full bbox

            damaged_pixels = np.sum(damage_mask > 0)
            damage_ratio = damaged_pixels / total_person_pixels if total_person_pixels > 0 else 0.0

            is_damaged = damage_ratio >= threshold

            stats = {
                'total_pixels': int(total_person_pixels),
                'damaged_pixels': int(damaged_pixels),
                'damage_ratio': float(damage_ratio),
                'threshold': threshold,
                'is_damaged': is_damaged,
                'bbox_used': bbox is not None,
                'analysis_region': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
            }

            logger.info(
                f"Damage detection: {damage_ratio:.2%} damaged "
                f"({damaged_pixels}/{total_person_pixels} pixels), "
                f"threshold={threshold:.2%}, is_damaged={is_damaged}"
            )

            # Convert mask to bytes
            mask_img = Image.fromarray(damage_mask)
            mask_buffer = BytesIO()
            mask_img.save(mask_buffer, format='PNG')
            mask_bytes = mask_buffer.getvalue()

            return is_damaged, mask_bytes, stats

        except Exception as e:
            logger.error(f"Damage detection failed: {e}")
            raise

    def repair_image(
        self,
        image: bytes,
        mask: bytes,
        dilate_mask: int = 5
    ) -> bytes:
        """
        Repair damaged areas using LaMa inpainting.

        Args:
            image: Image bytes (RGB or RGBA)
            mask: Mask bytes (white pixels = areas to repair)
            dilate_mask: Pixels to dilate the mask for better blending

        Returns:
            Repaired image bytes (PNG format with alpha if input had alpha)
        """
        try:
            # Load model if not already loaded
            self._load_model()

            # Load images
            img = Image.open(BytesIO(image))
            mask_img = Image.open(BytesIO(mask)).convert('L')

            # Store original alpha if present
            original_alpha = None
            if img.mode == 'RGBA':
                original_alpha = img.split()[-1]
                img_rgb = img.convert('RGB')
            else:
                img_rgb = img.convert('RGB')

            # Dilate mask for better blending at edges
            if dilate_mask > 0:
                from PIL import ImageFilter
                for _ in range(dilate_mask):
                    mask_img = mask_img.filter(ImageFilter.MaxFilter(3))

            # Ensure mask and image have same size
            if mask_img.size != img_rgb.size:
                mask_img = mask_img.resize(img_rgb.size, Image.NEAREST)

            logger.info(f"Running LaMa inpainting on {img_rgb.size} image...")

            # Run inpainting
            result = self.model(img_rgb, mask_img)

            # Restore alpha channel if original had one
            if original_alpha is not None:
                # For repaired areas, set alpha to fully opaque
                mask_np = np.array(mask_img)
                alpha_np = np.array(original_alpha)

                # Make repaired areas opaque
                alpha_np[mask_np > 128] = 255

                new_alpha = Image.fromarray(alpha_np)
                result = result.convert('RGB')
                result.putalpha(new_alpha)

            # Save to bytes
            output_buffer = BytesIO()
            result.save(output_buffer, format='PNG')

            logger.info("LaMa inpainting completed successfully")
            return output_buffer.getvalue()

        except Exception as e:
            logger.error(f"Image repair failed: {e}")
            raise

    def auto_repair(
        self,
        original_image: bytes,
        rembg_output: bytes,
        bbox: Optional[Dict[str, int]] = None,
        threshold: float = 0.01,
        dilate_mask: int = 5
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Automatically detect and repair clothing damage.

        This is the main entry point for the inpainting service.
        It detects damage, and if threshold is exceeded, repairs the image.

        Args:
            original_image: Original image bytes (before background removal)
            rembg_output: Image bytes with alpha channel from rembg
            bbox: Optional bounding box for the person
            threshold: Minimum damage ratio to trigger repair (0.0-1.0)
            dilate_mask: Pixels to dilate repair mask for better blending

        Returns:
            Tuple of (result_image_bytes, stats_dict)
            - If damage detected: repaired image
            - If no damage: original rembg_output unchanged
        """
        try:
            # Detect damage
            is_damaged, mask_bytes, stats = self.detect_clothing_damage(
                original_image=original_image,
                rembg_output=rembg_output,
                bbox=bbox,
                threshold=threshold
            )

            if not is_damaged:
                logger.info("No significant clothing damage detected, returning original")
                stats['repaired'] = False
                return rembg_output, stats

            logger.info(f"Clothing damage detected ({stats['damage_ratio']:.2%}), initiating repair...")

            # Repair the image
            repaired_bytes = self.repair_image(
                image=rembg_output,
                mask=mask_bytes,
                dilate_mask=dilate_mask
            )

            stats['repaired'] = True
            logger.info("Image repair completed")

            return repaired_bytes, stats

        except Exception as e:
            logger.error(f"Auto repair failed: {e}")
            # Return original on failure
            return rembg_output, {
                'error': str(e),
                'repaired': False,
                'fallback': True
            }

    def unload_model(self) -> None:
        """
        Release VRAM by unloading the model.

        Call this when done with inpainting to free GPU memory.
        """
        if self._model_loaded and self.model is not None:
            try:
                import torch
                del self.model
                self.model = None
                self._model_loaded = False

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("LaMa model unloaded and CUDA cache cleared")
                else:
                    logger.info("LaMa model unloaded")

            except Exception as e:
                logger.warning(f"Error during model unload: {e}")
                self.model = None
                self._model_loaded = False

    def get_status(self) -> Dict[str, Any]:
        """
        Get service status information.

        Returns:
            Dict with status information
        """
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                gpu_memory = {
                    'allocated': torch.cuda.memory_allocated() / 1024**2,
                    'reserved': torch.cuda.memory_reserved() / 1024**2,
                }
            else:
                gpu_memory = None
        except ImportError:
            cuda_available = False
            gpu_memory = None

        return {
            'service': 'InpaintingService',
            'model_loaded': self._model_loaded,
            'device': self._device,
            'cuda_available': cuda_available,
            'gpu_memory_mb': gpu_memory,
        }

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.unload_model()
        except Exception:
            pass


# Singleton instance for reuse
_inpainting_service: Optional[InpaintingService] = None


def get_inpainting_service(device: Optional[str] = None) -> InpaintingService:
    """
    Get or create a singleton InpaintingService instance.

    Args:
        device: Device to use ('cuda', 'cpu', or None for auto-detect)

    Returns:
        InpaintingService instance
    """
    global _inpainting_service

    if _inpainting_service is None:
        _inpainting_service = InpaintingService(device=device)

    return _inpainting_service


def release_inpainting_service() -> None:
    """
    Release the singleton InpaintingService and free VRAM.
    """
    global _inpainting_service

    if _inpainting_service is not None:
        _inpainting_service.unload_model()
        _inpainting_service = None
        logger.info("InpaintingService singleton released")
