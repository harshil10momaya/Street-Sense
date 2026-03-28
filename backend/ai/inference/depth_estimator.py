"""
StreetSense -- MiDaS Depth Estimation Module

Loads a pretrained MiDaS model (via PyTorch Hub or timm) and runs
monocular depth estimation on images.

MiDaS outputs a relative depth map where:
  - Higher values = closer to camera
  - Lower values = further from camera

For road damage assessment:
  - A pothole/crack that is "deeper" relative to the road surface
    will have a LOWER depth value (further from camera) inside the
    bounding box compared to the surrounding road surface.
  - We use the depth CONTRAST (difference between bbox interior
    and surrounding area) to estimate physical severity.

Supported models (from fastest to most accurate):
  - MiDaS_small   : Fastest, lower accuracy (good for real-time)
  - DPT_Hybrid    : Good balance
  - DPT_Large     : Most accurate (default)

Usage:
    from ai.inference.depth_estimator import DepthEstimator

    estimator = DepthEstimator(model_type="DPT_Large")
    depth_map = estimator.estimate(image_bgr)
    avg_depth = estimator.get_bbox_depth(depth_map, x1, y1, x2, y2)
"""

import cv2
import numpy as np
import torch
from pathlib import Path
from loguru import logger


class DepthEstimator:
    """Monocular depth estimation using MiDaS."""

    SUPPORTED_MODELS = ["DPT_Large", "DPT_Hybrid", "MiDaS_small"]

    def __init__(self, model_type: str = "DPT_Large", device: str = None):
        """
        Initialize MiDaS depth estimator.

        Args:
            model_type: One of DPT_Large, DPT_Hybrid, MiDaS_small
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        if model_type not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model_type}. "
                f"Choose from: {self.SUPPORTED_MODELS}"
            )

        self.model_type = model_type
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.transform = None
        self._loaded = False

        logger.info(f"DepthEstimator initialized: model={model_type}, device={self.device}")

    def load(self):
        """Load MiDaS model and transforms from PyTorch Hub."""
        if self._loaded:
            return

        logger.info(f"Loading MiDaS model: {self.model_type}...")

        try:
            # Load model from PyTorch Hub
            self.model = torch.hub.load(
                "intel-isl/MiDaS",
                self.model_type,
                trust_repo=True,
            )
            self.model.to(self.device)
            self.model.eval()

            # Load transforms
            midas_transforms = torch.hub.load(
                "intel-isl/MiDaS",
                "transforms",
                trust_repo=True,
            )

            if self.model_type == "DPT_Large" or self.model_type == "DPT_Hybrid":
                self.transform = midas_transforms.dpt_transform
            else:
                self.transform = midas_transforms.small_transform

            self._loaded = True
            logger.info(f"MiDaS model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load MiDaS model: {e}")
            raise

    def estimate(self, image_bgr: np.ndarray) -> np.ndarray:
        """
        Run depth estimation on a BGR image.

        Args:
            image_bgr: OpenCV BGR image (H, W, 3), uint8

        Returns:
            depth_map: Normalized depth map (H, W), float32, range [0, 1]
                       Higher values = closer to camera
        """
        if not self._loaded:
            self.load()

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        # Apply MiDaS transform
        input_batch = self.transform(image_rgb).to(self.device)

        # Run inference
        with torch.no_grad():
            prediction = self.model(input_batch)

            # Resize to original image size
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=image_bgr.shape[:2],  # (H, W)
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        # Convert to numpy
        depth_map = prediction.cpu().numpy()

        # Normalize to [0, 1]
        depth_map = self._normalize(depth_map)

        return depth_map

    def _normalize(self, depth_map: np.ndarray) -> np.ndarray:
        """Normalize depth map to [0, 1] range."""
        d_min = depth_map.min()
        d_max = depth_map.max()

        if d_max - d_min < 1e-6:
            return np.zeros_like(depth_map, dtype=np.float32)

        normalized = (depth_map - d_min) / (d_max - d_min)
        return normalized.astype(np.float32)

    def get_bbox_depth(
        self,
        depth_map: np.ndarray,
        x1: int, y1: int, x2: int, y2: int,
        margin: int = 20,
    ) -> dict:
        """
        Extract depth statistics for a bounding box region.

        Computes:
          - avg_depth: Mean depth inside the bounding box
          - min_depth: Minimum depth (deepest point relative to camera)
          - max_depth: Maximum depth (shallowest point)
          - surrounding_depth: Mean depth of the area around the bbox
          - depth_contrast: Difference between surrounding and bbox depth
                           Higher contrast = more severe damage

        Args:
            depth_map: Normalized depth map (H, W), float32
            x1, y1, x2, y2: Bounding box coordinates (absolute pixels)
            margin: Pixels to expand for surrounding area calculation

        Returns:
            Dict with depth statistics
        """
        h, w = depth_map.shape[:2]

        # Clamp bbox to image bounds
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(w, int(x2))
        y2 = min(h, int(y2))

        if x2 <= x1 or y2 <= y1:
            return {
                "avg_depth": 0.0,
                "min_depth": 0.0,
                "max_depth": 0.0,
                "surrounding_depth": 0.0,
                "depth_contrast": 0.0,
                "std_depth": 0.0,
            }

        # Depth inside bounding box
        bbox_region = depth_map[y1:y2, x1:x2]
        avg_depth = float(np.mean(bbox_region))
        min_depth = float(np.min(bbox_region))
        max_depth = float(np.max(bbox_region))
        std_depth = float(np.std(bbox_region))

        # Surrounding area depth (for contrast calculation)
        sx1 = max(0, x1 - margin)
        sy1 = max(0, y1 - margin)
        sx2 = min(w, x2 + margin)
        sy2 = min(h, y2 + margin)

        # Create mask: surrounding area minus bbox
        surround_mask = np.zeros((h, w), dtype=bool)
        surround_mask[sy1:sy2, sx1:sx2] = True
        surround_mask[y1:y2, x1:x2] = False

        if np.any(surround_mask):
            surrounding_depth = float(np.mean(depth_map[surround_mask]))
        else:
            surrounding_depth = avg_depth

        # Depth contrast: how much deeper is the damage compared to surroundings
        # Positive contrast = damage is deeper (lower depth = further from camera)
        depth_contrast = abs(surrounding_depth - avg_depth)

        return {
            "avg_depth": round(avg_depth, 4),
            "min_depth": round(min_depth, 4),
            "max_depth": round(max_depth, 4),
            "surrounding_depth": round(surrounding_depth, 4),
            "depth_contrast": round(depth_contrast, 4),
            "std_depth": round(std_depth, 4),
        }

    def generate_depth_visualization(
        self,
        depth_map: np.ndarray,
        colormap: int = cv2.COLORMAP_MAGMA,
    ) -> np.ndarray:
        """
        Create a colored visualization of the depth map.

        Args:
            depth_map: Normalized depth map (H, W), float32, [0, 1]
            colormap: OpenCV colormap constant

        Returns:
            Colored depth visualization (H, W, 3), uint8 BGR
        """
        # Convert to uint8 for colormap
        depth_uint8 = (depth_map * 255).astype(np.uint8)
        colored = cv2.applyColorMap(depth_uint8, colormap)
        return colored

    @property
    def is_loaded(self) -> bool:
        return self._loaded
