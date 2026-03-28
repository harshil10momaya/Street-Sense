"""
StreetSense -- YOLO Detector Module

Wraps Ultralytics YOLOv8 for object detection.
Handles model loading, inference, and result parsing.

Usage:
    from ai.inference.detector import YOLODetector

    detector = YOLODetector("ai/weights/best.pt")
    detections = detector.detect(image_bgr, conf=0.5)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional
from loguru import logger


class Detection:
    """Single detection result from YOLO."""

    CLASS_NAMES = {0: "pothole", 1: "crack", 2: "manhole", 3: "garbage"}

    def __init__(
        self,
        class_id: int,
        confidence: float,
        x1: float, y1: float, x2: float, y2: float,
    ):
        self.class_id = class_id
        self.confidence = confidence
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

        # Depth and severity (filled later by pipeline)
        self.depth_info = None
        self.severity = None
        self.severity_score = 0.0

    @property
    def class_name(self) -> str:
        return self.CLASS_NAMES.get(self.class_id, f"class_{self.class_id}")

    @property
    def bbox_width(self) -> float:
        return self.x2 - self.x1

    @property
    def bbox_height(self) -> float:
        return self.y2 - self.y1

    @property
    def bbox_area(self) -> float:
        return self.bbox_width * self.bbox_height

    @property
    def bbox_center(self) -> tuple:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def bbox_xyxy(self) -> tuple:
        return (int(self.x1), int(self.y1), int(self.x2), int(self.y2))

    @property
    def bbox_xywh_normalized(self) -> tuple:
        """Normalized center-x, center-y, width, height."""
        cx, cy = self.bbox_center
        return (cx, cy, self.bbox_width, self.bbox_height)

    def to_dict(self) -> dict:
        result = {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": {
                "x1": round(self.x1, 1),
                "y1": round(self.y1, 1),
                "x2": round(self.x2, 1),
                "y2": round(self.y2, 1),
                "width": round(self.bbox_width, 1),
                "height": round(self.bbox_height, 1),
                "area": round(self.bbox_area, 1),
            },
        }
        if self.depth_info:
            result["depth"] = self.depth_info
        if self.severity:
            result["severity"] = self.severity
            result["severity_score"] = round(self.severity_score, 4)
        return result

    def __repr__(self):
        return (
            f"Detection({self.class_name}, conf={self.confidence:.2f}, "
            f"bbox=[{self.x1:.0f},{self.y1:.0f},{self.x2:.0f},{self.y2:.0f}]"
            f"{f', severity={self.severity}' if self.severity else ''})"
        )


class YOLODetector:
    """YOLOv8 object detector for road damage."""

    def __init__(self, weights_path: str, device: str = None):
        """
        Args:
            weights_path: Path to trained YOLO weights (best.pt)
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        self.weights_path = Path(weights_path)
        self.device = device
        self.model = None
        self._loaded = False

    def load(self):
        """Load YOLO model."""
        if self._loaded:
            return

        if not self.weights_path.exists():
            raise FileNotFoundError(
                f"YOLO weights not found: {self.weights_path}\n"
                f"Train the model first or download best.pt from Colab."
            )

        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError("Install ultralytics: pip install ultralytics")

        logger.info(f"Loading YOLO model from: {self.weights_path}")
        self.model = YOLO(str(self.weights_path))

        if self.device:
            self.model.to(self.device)

        self._loaded = True
        logger.info(f"YOLO model loaded ({self.weights_path.name})")

    def detect(
        self,
        image: np.ndarray,
        conf: float = 0.5,
        iou: float = 0.45,
        max_det: int = 50,
    ) -> List[Detection]:
        """
        Run object detection on a BGR image.

        Args:
            image: OpenCV BGR image (H, W, 3)
            conf: Minimum confidence threshold
            iou: IoU threshold for NMS
            max_det: Maximum detections per image

        Returns:
            List of Detection objects
        """
        if not self._loaded:
            self.load()

        results = self.model.predict(
            source=image,
            conf=conf,
            iou=iou,
            max_det=max_det,
            verbose=False,
        )

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                det = Detection(
                    class_id=int(box.cls[0]),
                    confidence=float(box.conf[0]),
                    x1=float(box.xyxy[0][0]),
                    y1=float(box.xyxy[0][1]),
                    x2=float(box.xyxy[0][2]),
                    y2=float(box.xyxy[0][3]),
                )
                detections.append(det)

        return detections

    def get_annotated_image(
        self,
        image: np.ndarray,
        detections: List[Detection],
        show_severity: bool = True,
    ) -> np.ndarray:
        """
        Draw detection boxes and labels on the image.

        Args:
            image: Original BGR image
            detections: List of Detection objects
            show_severity: Include severity in labels

        Returns:
            Annotated BGR image
        """
        annotated = image.copy()

        # Colors per class (BGR)
        colors = {
            0: (0, 0, 255),     # pothole - red
            1: (0, 165, 255),   # crack - orange
            2: (255, 255, 0),   # manhole - cyan
            3: (0, 255, 0),     # garbage - green
        }

        severity_colors = {
            "low": (0, 255, 0),       # green
            "medium": (0, 165, 255),  # orange
            "high": (0, 0, 255),      # red
        }

        for det in detections:
            x1, y1, x2, y2 = det.bbox_xyxy
            color = colors.get(det.class_id, (255, 255, 255))

            # Use severity color if available
            if show_severity and det.severity:
                color = severity_colors.get(det.severity, color)

            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Build label
            label = f"{det.class_name} {det.confidence:.2f}"
            if show_severity and det.severity:
                label += f" [{det.severity.upper()}]"

            # Draw label background
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw, y1), color, -1)
            cv2.putText(
                annotated, label, (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
            )

        return annotated

    @property
    def is_loaded(self) -> bool:
        return self._loaded
