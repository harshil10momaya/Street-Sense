"""
StreetSense -- Inference Pipeline

Orchestrates the full detection pipeline:
  1. YOLO detection (bounding boxes + class + confidence)
  2. MiDaS depth estimation (depth map for entire image)
  3. Depth extraction per bounding box
  4. Severity estimation (area + depth -> low/medium/high)
  5. Annotated output generation

Supports:
  - Single image inference
  - Video inference (frame-by-frame)
  - Batch image inference

Usage:
    from ai.inference.pipeline import InferencePipeline

    pipeline = InferencePipeline(
        yolo_weights="ai/weights/best.pt",
        midas_model="DPT_Large",
    )
    pipeline.load()

    results = pipeline.process_image(image_bgr)
    # results.detections, results.depth_map, results.annotated_image
"""

import cv2
import numpy as np
import time
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger

from ai.inference.detector import YOLODetector, Detection
from ai.inference.depth_estimator import DepthEstimator
from ai.inference.severity import SeverityEstimator


@dataclass
class PipelineResult:
    """Result from processing a single image."""
    detections: List[Detection] = field(default_factory=list)
    depth_map: Optional[np.ndarray] = None
    annotated_image: Optional[np.ndarray] = None
    depth_visualization: Optional[np.ndarray] = None
    image_shape: Tuple[int, int] = (0, 0)
    processing_time_ms: float = 0.0

    @property
    def detection_count(self) -> int:
        return len(self.detections)

    @property
    def has_detections(self) -> bool:
        return len(self.detections) > 0

    @property
    def severity_summary(self) -> dict:
        """Count detections by severity level."""
        summary = {"low": 0, "medium": 0, "high": 0}
        for det in self.detections:
            if det.severity:
                summary[det.severity] += 1
        return summary

    def to_dict(self) -> dict:
        return {
            "detection_count": self.detection_count,
            "detections": [d.to_dict() for d in self.detections],
            "image_shape": list(self.image_shape),
            "processing_time_ms": round(self.processing_time_ms, 1),
            "severity_summary": self.severity_summary,
        }


class InferencePipeline:
    """Full YOLO + MiDaS + Severity pipeline."""

    def __init__(
        self,
        yolo_weights: str = "ai/weights/best.pt",
        midas_model: str = "DPT_Large",
        confidence: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = None,
        enable_depth: bool = True,
    ):
        """
        Args:
            yolo_weights: Path to trained YOLO weights
            midas_model: MiDaS model type (DPT_Large, DPT_Hybrid, MiDaS_small)
            confidence: Detection confidence threshold
            iou_threshold: NMS IoU threshold
            device: 'cuda', 'cpu', or None (auto)
            enable_depth: Whether to run MiDaS depth estimation
        """
        self.confidence = confidence
        self.iou_threshold = iou_threshold
        self.enable_depth = enable_depth

        # Initialize components
        self.detector = YOLODetector(yolo_weights, device=device)
        self.severity = SeverityEstimator()

        if enable_depth:
            self.depth_estimator = DepthEstimator(midas_model, device=device)
        else:
            self.depth_estimator = None

        self._loaded = False
        logger.info(
            f"Pipeline initialized: YOLO={yolo_weights}, "
            f"MiDaS={midas_model if enable_depth else 'disabled'}, "
            f"conf={confidence}"
        )

    def load(self):
        """Load all models into memory."""
        if self._loaded:
            return

        logger.info("Loading inference pipeline models...")
        start = time.time()

        self.detector.load()

        if self.enable_depth and self.depth_estimator:
            self.depth_estimator.load()

        elapsed = time.time() - start
        self._loaded = True
        logger.info(f"Pipeline loaded in {elapsed:.1f}s")

    def process_image(
        self,
        image: np.ndarray,
        generate_visuals: bool = True,
    ) -> PipelineResult:
        """
        Run full inference pipeline on a single image.

        Steps:
          1. YOLO detection
          2. MiDaS depth estimation (if enabled)
          3. Extract depth per bounding box
          4. Compute severity per detection
          5. Generate annotated output

        Args:
            image: BGR image (H, W, 3), uint8
            generate_visuals: Whether to create annotated images

        Returns:
            PipelineResult with detections, depth map, annotated image
        """
        if not self._loaded:
            self.load()

        start = time.time()
        h, w = image.shape[:2]

        result = PipelineResult(image_shape=(h, w))

        # Step 1: YOLO Detection
        detections = self.detector.detect(
            image,
            conf=self.confidence,
            iou=self.iou_threshold,
        )
        logger.debug(f"YOLO: {len(detections)} detections")

        # Step 2: MiDaS Depth Estimation
        depth_map = None
        if self.enable_depth and self.depth_estimator:
            depth_map = self.depth_estimator.estimate(image)
            result.depth_map = depth_map
            logger.debug(f"MiDaS: depth map shape={depth_map.shape}")

        # Step 3 & 4: Per-detection depth extraction + severity
        for det in detections:
            # Extract depth stats for this bounding box
            if depth_map is not None:
                det.depth_info = self.depth_estimator.get_bbox_depth(
                    depth_map,
                    int(det.x1), int(det.y1),
                    int(det.x2), int(det.y2),
                )

            # Compute severity
            self.severity.compute_for_detection(det, image.shape)

        result.detections = detections

        # Step 5: Generate visual outputs
        if generate_visuals:
            result.annotated_image = self.detector.get_annotated_image(
                image, detections, show_severity=True,
            )

            if depth_map is not None:
                result.depth_visualization = self.depth_estimator.generate_depth_visualization(
                    depth_map
                )

        elapsed = (time.time() - start) * 1000
        result.processing_time_ms = elapsed
        logger.debug(f"Pipeline: {elapsed:.1f}ms total, {len(detections)} detections")

        return result

    def process_image_file(
        self,
        image_path: str,
        output_dir: str = None,
    ) -> PipelineResult:
        """
        Process a single image file.

        Args:
            image_path: Path to image file
            output_dir: If provided, save annotated outputs here

        Returns:
            PipelineResult
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not read image: {path}")

        result = self.process_image(image, generate_visuals=True)

        # Save outputs if requested
        if output_dir and result.has_detections:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)

            stem = path.stem

            if result.annotated_image is not None:
                cv2.imwrite(
                    str(out / f"{stem}_annotated.jpg"),
                    result.annotated_image,
                )

            if result.depth_visualization is not None:
                cv2.imwrite(
                    str(out / f"{stem}_depth.jpg"),
                    result.depth_visualization,
                )

            logger.info(f"Saved outputs to {out}")

        return result

    def process_video(
        self,
        video_path: str,
        output_path: str = None,
        frame_skip: int = 1,
        callback=None,
    ):
        """
        Process a video file frame-by-frame.

        Args:
            video_path: Path to video file
            output_path: If provided, save annotated video here
            frame_skip: Process every Nth frame (1=all, 2=every other, etc.)
            callback: Optional function called with (frame_num, result) for each frame

        Yields:
            (frame_number, PipelineResult) for each processed frame
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Video: {width}x{height}, {fps:.1f} FPS, {total_frames} frames")

        # Output video writer
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_num = 0
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_num += 1

                if frame_num % frame_skip != 0:
                    if writer:
                        writer.write(frame)  # Write original frame
                    continue

                # Process frame
                result = self.process_image(frame, generate_visuals=True)

                if writer and result.annotated_image is not None:
                    writer.write(result.annotated_image)
                elif writer:
                    writer.write(frame)

                if callback:
                    callback(frame_num, result)

                yield frame_num, result

        finally:
            cap.release()
            if writer:
                writer.release()
                logger.info(f"Video saved to {output_path}")

    @property
    def is_loaded(self) -> bool:
        return self._loaded
