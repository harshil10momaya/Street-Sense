"""
StreetSense -- AI Service

Manages the inference pipeline lifecycle and provides
a clean interface for the API layer.

Key fix: runs heavy CPU inference in a thread pool executor
so it doesn't block the async event loop / cause timeouts.
"""

import asyncio
import cv2
import numpy as np
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from loguru import logger

from app.core.config import settings
from app.utils.file_utils import save_image, get_relative_url


# Global pipeline instance
_pipeline = None
_pipeline_loading = False

# Thread pool for CPU-heavy inference (1 worker = sequential processing)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai-inference")


def get_pipeline():
    """Get or create the global inference pipeline."""
    global _pipeline, _pipeline_loading

    if _pipeline is not None:
        return _pipeline

    if _pipeline_loading:
        raise RuntimeError("Pipeline is currently loading. Please try again in a moment.")

    _pipeline_loading = True
    try:
        from ai.inference.pipeline import InferencePipeline

        weights_path = settings.weights_path
        if not weights_path.exists():
            logger.warning(f"YOLO weights not found at {weights_path}")
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
        raise
    finally:
        _pipeline_loading = False


def is_pipeline_loaded() -> bool:
    """Check if the AI pipeline is loaded."""
    return _pipeline is not None and _pipeline.is_loaded


def _run_inference_sync(image: np.ndarray, image_id: str) -> dict:
    """
    Synchronous inference -- runs in thread pool.
    This is the heavy CPU work (YOLO + MiDaS).
    """
    pipeline = get_pipeline()
    if pipeline is None:
        raise RuntimeError(
            "AI pipeline not available. Place best.pt in backend/ai/weights/"
        )

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


async def run_inference(
    image: np.ndarray,
    image_id: str = None,
) -> dict:
    """
    Run the full AI pipeline on an image.
    Offloads heavy CPU work to a thread pool so it doesn't block the event loop.
    """
    if image_id is None:
        image_id = uuid.uuid4().hex[:12]

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        _run_inference_sync,
        image,
        image_id,
    )
    return result
