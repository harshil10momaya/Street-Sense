"""
StreetSense -- COCO JSON to YOLO Format Converter

Converts COCO-format annotations (annotations.json) to YOLO format.
Specifically designed for TACO dataset where ALL categories -> garbage.

COCO format:
    {
        "images": [{"id": 1, "file_name": "img.jpg", "width": 640, "height": 480}],
        "annotations": [{"image_id": 1, "category_id": 5, "bbox": [x,y,w,h]}],
        "categories": [{"id": 5, "name": "Plastic bag"}]
    }

YOLO format (per image):
    class_id x_center y_center width height (normalized 0-1)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


def load_coco_json(json_path: Path) -> Optional[dict]:
    """Load and validate a COCO annotation JSON file."""
    try:
        with open(json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"    [ERROR] Cannot load {json_path}: {e}")
        return None

    # Validate required fields
    for key in ["images", "annotations"]:
        if key not in data:
            print(f"    [ERROR] Missing '{key}' in COCO JSON")
            return None

    return data


def convert_coco_to_yolo(
    coco_data: dict,
    target_class_id: int,
    category_filter: Optional[Dict[str, str]] = None,
) -> Dict[str, List[str]]:
    """
    Convert COCO annotations to YOLO format.

    Args:
        coco_data: Parsed COCO JSON dict
        target_class_id: YOLO class ID to assign (e.g., 3 for garbage)
        category_filter: Optional {coco_category_name: target_class_name}
                        If None, ALL categories map to target_class_id

    Returns:
        Dict mapping image_filename -> list of YOLO format lines
    """
    # Build lookups
    img_lookup = {}
    for img in coco_data["images"]:
        img_lookup[img["id"]] = {
            "file_name": img["file_name"],
            "width": img.get("width", 0),
            "height": img.get("height", 0),
        }

    cat_lookup = {}
    if "categories" in coco_data:
        for cat in coco_data["categories"]:
            cat_lookup[cat["id"]] = cat.get("name", f"cat_{cat['id']}")

    # Group annotations by image
    img_annotations = defaultdict(list)
    for ann in coco_data["annotations"]:
        img_id = ann["image_id"]
        img_annotations[img_id].append(ann)

    # Convert
    result = {}
    skipped_no_size = 0
    skipped_bad_bbox = 0
    converted = 0

    for img_id, img_info in img_lookup.items():
        filename = img_info["file_name"]
        w = img_info["width"]
        h = img_info["height"]

        if w <= 0 or h <= 0:
            skipped_no_size += 1
            continue

        anns = img_annotations.get(img_id, [])
        yolo_lines = []

        for ann in anns:
            cat_id = ann.get("category_id")
            cat_name = cat_lookup.get(cat_id, "")

            # Apply category filter if provided
            if category_filter is not None:
                mapped = None
                for key, target in category_filter.items():
                    if key.lower() in cat_name.lower():
                        mapped = target
                        break
                if mapped is None:
                    continue  # Skip unmapped categories

            # COCO bbox: [x_min, y_min, bbox_width, bbox_height] (absolute pixels)
            bbox = ann.get("bbox", [])
            if len(bbox) < 4:
                skipped_bad_bbox += 1
                continue

            bx, by, bw, bh = bbox[0], bbox[1], bbox[2], bbox[3]

            if bw <= 0 or bh <= 0:
                skipped_bad_bbox += 1
                continue

            # Convert to YOLO normalized format
            x_center = (bx + bw / 2) / w
            y_center = (by + bh / 2) / h
            norm_w = bw / w
            norm_h = bh / h

            # Clamp
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            norm_w = max(0.001, min(1.0, norm_w))
            norm_h = max(0.001, min(1.0, norm_h))

            yolo_lines.append(
                f"{target_class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}"
            )
            converted += 1

        if yolo_lines:
            # Use just the filename (strip any subdirectory paths)
            clean_name = Path(filename).name
            result[clean_name] = yolo_lines

    print(f"    Converted: {converted} annotations across {len(result)} images")
    if skipped_no_size:
        print(f"    Skipped (no image size): {skipped_no_size}")
    if skipped_bad_bbox:
        print(f"    Skipped (bad bbox): {skipped_bad_bbox}")

    return result
