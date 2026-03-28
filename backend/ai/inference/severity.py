"""
StreetSense -- Severity Estimation Module

Combines two signals to estimate damage severity:

  1. BOUNDING BOX AREA (from YOLO)
     - Larger detected area = more severe damage
     - Normalized relative to image size

  2. DEPTH CONTRAST (from MiDaS)
     - Difference between surrounding road depth and damage interior depth
     - Higher contrast = deeper/more pronounced damage

  3. CLASS-SPECIFIC WEIGHTS
     - Potholes: depth matters most (deep potholes are dangerous)
     - Cracks: area matters most (wide cracks indicate structural damage)
     - Manholes: depth contrast matters (open/displaced covers are dangerous)
     - Garbage: area matters most (large piles are worse)

Final severity is classified as:
  - LOW:    score < 0.33
  - MEDIUM: score 0.33 - 0.66
  - HIGH:   score > 0.66

Usage:
    from ai.inference.severity import SeverityEstimator

    estimator = SeverityEstimator()
    severity, score = estimator.compute(detection, image_shape)
"""

import numpy as np
from typing import Tuple
from loguru import logger


class SeverityEstimator:
    """Depth-aware severity estimation for road damage."""

    # Class-specific weights for combining area and depth signals
    # Format: (area_weight, depth_weight)
    # Must sum to 1.0
    CLASS_WEIGHTS = {
        0: (0.35, 0.65),  # pothole: depth is more important
        1: (0.60, 0.40),  # crack: area is more important
        2: (0.30, 0.70),  # manhole: depth contrast is critical
        3: (0.75, 0.25),  # garbage: area is more important
    }

    # Severity thresholds
    LOW_MAX = 0.33
    MEDIUM_MAX = 0.66

    # Area normalization parameters
    # What fraction of image area counts as "maximum" severity from area alone
    # e.g., a pothole covering 10% of the image = max area severity
    MAX_AREA_FRACTION = {
        0: 0.10,  # pothole
        1: 0.15,  # crack (can be long/thin)
        2: 0.08,  # manhole
        3: 0.20,  # garbage (can cover large area)
    }

    # Depth contrast normalization
    # What depth contrast value counts as "maximum" severity from depth alone
    MAX_DEPTH_CONTRAST = {
        0: 0.15,  # pothole
        1: 0.08,  # crack (subtle depth changes)
        2: 0.20,  # manhole (can be very deep if open)
        3: 0.10,  # garbage (slight depth variation)
    }

    def __init__(
        self,
        low_threshold: float = None,
        medium_threshold: float = None,
    ):
        """
        Args:
            low_threshold: Max score for LOW severity (default 0.33)
            medium_threshold: Max score for MEDIUM severity (default 0.66)
        """
        if low_threshold is not None:
            self.LOW_MAX = low_threshold
        if medium_threshold is not None:
            self.MEDIUM_MAX = medium_threshold

    def compute_area_score(
        self,
        bbox_area: float,
        image_area: float,
        class_id: int,
    ) -> float:
        """
        Compute severity score from bounding box area.

        Args:
            bbox_area: Area of bounding box in pixels
            image_area: Total image area in pixels
            class_id: Detection class ID

        Returns:
            Normalized area score [0, 1]
        """
        if image_area <= 0:
            return 0.0

        area_fraction = bbox_area / image_area
        max_fraction = self.MAX_AREA_FRACTION.get(class_id, 0.10)

        # Normalize: 0 at 0%, 1 at max_fraction
        score = min(1.0, area_fraction / max_fraction)

        # Apply slight curve to avoid linearity
        score = score ** 0.8

        return float(score)

    def compute_depth_score(
        self,
        depth_info: dict,
        class_id: int,
    ) -> float:
        """
        Compute severity score from MiDaS depth analysis.

        Uses depth_contrast (difference between surrounding area and bbox interior)
        as the primary signal. Higher contrast = more severe.

        Also factors in depth standard deviation inside the bbox
        (high std = uneven surface = more damage).

        Args:
            depth_info: Dict from DepthEstimator.get_bbox_depth()
            class_id: Detection class ID

        Returns:
            Normalized depth score [0, 1]
        """
        if not depth_info:
            return 0.0

        contrast = depth_info.get("depth_contrast", 0.0)
        std = depth_info.get("std_depth", 0.0)

        max_contrast = self.MAX_DEPTH_CONTRAST.get(class_id, 0.10)

        # Primary signal: depth contrast
        contrast_score = min(1.0, contrast / max_contrast)

        # Secondary signal: depth variability inside bbox
        # High std = uneven surface = more damage
        std_score = min(1.0, std / 0.15)

        # Combine: 80% contrast, 20% variability
        score = 0.80 * contrast_score + 0.20 * std_score

        # Apply curve
        score = score ** 0.8

        return float(min(1.0, score))

    def compute(
        self,
        class_id: int,
        confidence: float,
        bbox_area: float,
        image_shape: Tuple[int, int],
        depth_info: dict = None,
    ) -> Tuple[str, float]:
        """
        Compute final severity for a detection.

        Args:
            class_id: Detection class ID (0-3)
            confidence: Detection confidence
            bbox_area: Bounding box area in pixels
            image_shape: (height, width) of the image
            depth_info: Depth statistics from MiDaS (optional)

        Returns:
            (severity_label, severity_score)
            severity_label: "low", "medium", or "high"
            severity_score: float [0, 1]
        """
        img_h, img_w = image_shape[:2]
        image_area = img_h * img_w

        # Get class-specific weights
        area_weight, depth_weight = self.CLASS_WEIGHTS.get(class_id, (0.5, 0.5))

        # Compute component scores
        area_score = self.compute_area_score(bbox_area, image_area, class_id)

        if depth_info:
            depth_score = self.compute_depth_score(depth_info, class_id)
        else:
            depth_score = 0.0
            # Without depth, fall back to area-only estimation
            area_weight = 1.0
            depth_weight = 0.0

        # Weighted combination
        raw_score = (area_weight * area_score) + (depth_weight * depth_score)

        # Confidence modulation: low-confidence detections get slightly reduced severity
        confidence_factor = 0.7 + (0.3 * confidence)
        final_score = raw_score * confidence_factor

        # Clamp to [0, 1]
        final_score = max(0.0, min(1.0, final_score))

        # Classify
        if final_score <= self.LOW_MAX:
            severity = "low"
        elif final_score <= self.MEDIUM_MAX:
            severity = "medium"
        else:
            severity = "high"

        return severity, round(final_score, 4)

    def compute_for_detection(self, detection, image_shape):
        """
        Convenience method: compute severity directly on a Detection object.
        Mutates the detection in-place (sets .severity and .severity_score).

        Args:
            detection: Detection object from YOLODetector
            image_shape: (height, width) of the image
        """
        severity, score = self.compute(
            class_id=detection.class_id,
            confidence=detection.confidence,
            bbox_area=detection.bbox_area,
            image_shape=image_shape,
            depth_info=detection.depth_info,
        )
        detection.severity = severity
        detection.severity_score = score
        return severity, score
