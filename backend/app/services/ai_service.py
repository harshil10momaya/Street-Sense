"""
StreetSense -- AI Service

Manages the inference pipeline lifecycle and provides
a clean interface for the API layer.

- Loads models on startup (or lazily on first request)
- Runs inference on uploaded images
- Returns structured detection results
"""

import cv2
import numpy as np
import uuid
from pathlib import Path
from typing import List, Optional
from loguru import logger

from app.core.config import settings
from app.utils.file_utils import save_image, get_relative_url


# Global pipeline instance (loaded once, reused)
_pipeline = None
_pipeline_loading = False


def get_pipeline():
    """Get or create the global inference pipeline."""
    global _pipeline, _pipeline_loading

    if _pipeline is not None:
        return _pipeline

    if _pipeline_loading:
        raise RuntimeError("Pipeline is currently loading. Please wait.")

    _pipeline_loading = True
    try:
        from ai.inference.pipeline import InferencePipeline

        weights_path = settings.weights_path
        if not weights_path.exists():
            logger.warning(f"YOLO weights not found at {weights_path}")
            logger.warning("AI inference will not be available until weights are placed.")
            _pipeline_loading = False
            return None

        pipeline = InferencePipeline(
            yolo_weights=str(weights_path),
            midas_model=settings.midas_model_type,
            confidence=settings.confidence_threshold,
            enable_depth=True,
        )
        pipeline.load()

        _pipeline = pipeline
        logger.info("AI pipeline loaded and ready")
        return _pipeline

    except Exception as e:
        logger.error(f"Failed to load AI pipeline: {e}")
        _pipeline_loading = False
        raise
    finally:
        _pipeline_loading = False


def is_pipeline_loaded() -> bool:
    """Check if the AI pipeline is loaded."""
    return _pipeline is not None and _pipeline.is_loaded


async def run_inference(
    image: np.ndarray,
    image_id: str = None,
) -> dict:
    """
    Run the full AI pipeline on an image.

    Args:
        image: BGR image (numpy array)
        image_id: Optional identifier for this image

    Returns:
        Dict with detections, saved file paths, processing time
    """
    pipeline = get_pipeline()
    if pipeline is None:
        raise RuntimeError(
            "AI pipeline not available. Place best.pt in backend/ai/weights/"
        )

    if image_id is None:
        image_id = uuid.uuid4().hex[:12]

    # Run pipeline
    result = pipeline.process_image(image, generate_visuals=True)

    # Save annotated image and depth map
    annotated_url = None
    depth_url = None

    if result.annotated_image is not None:
        path = save_image(
            result.annotated_image,
            subdirectory=f"results/{image_id}",
            name=f"{image_id}_annotated.jpg",
        )
        annotated_url = get_relative_url(path)

    if result.depth_visualization is not None:
        path = save_image(
            result.depth_visualization,
            subdirectory=f"results/{image_id}",
            name=f"{image_id}_depth.jpg",
        )
        depth_url = get_relative_url(path)

    # Structure results
    detections = []
    for det in result.detections:
        detections.append({
            "issue_type": det.class_name,
            "confidence": round(det.confidence, 4),
            "bbox": {
                "x": round(det.x1, 1),
                "y": round(det.y1, 1),
                "w": round(det.bbox_width, 1),
                "h": round(det.bbox_height, 1),
            },
            "depth_value": det.depth_info.get("avg_depth") if det.depth_info else None,
            "depth_contrast": det.depth_info.get("depth_contrast") if det.depth_info else None,
            "severity": det.severity or "low",
            "severity_score": det.severity_score,
        })

    return {
        "image_id": image_id,
        "detections": detections,
        "annotated_image_url": annotated_url,
        "depth_map_url": depth_url,
        "processing_time_ms": round(result.processing_time_ms, 1),
        "image_shape": list(result.image_shape),
    }
