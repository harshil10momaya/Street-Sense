"""
StreetSense -- Pascal VOC (XML) to YOLO Format Converter

Converts Pascal VOC XML annotation files to YOLO format:
    VOC:  <object><name>D20</name><bndbox><xmin>10</xmin>...</bndbox></object>
    YOLO: class_id x_center y_center width height (normalized 0-1)

Handles:
- Parsing XML annotation files
- Applying class label remapping
- Normalizing bounding box coordinates
- Skipping removed/ignored classes
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_voc_xml(xml_path: Path) -> Optional[dict]:
    """
    Parse a Pascal VOC XML annotation file.

    Returns:
        {
            "filename": "image.jpg",
            "width": 640,
            "height": 480,
            "objects": [
                {"name": "D20", "bbox": (xmin, ymin, xmax, ymax)},
                ...
            ]
        }
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"    [WARN]  Cannot parse {xml_path.name}: {e}")
        return None

    # Get image filename
    filename_elem = root.find("filename")
    filename = filename_elem.text.strip() if filename_elem is not None else None

    # Get image size
    size = root.find("size")
    if size is None:
        return None

    width_elem = size.find("width")
    height_elem = size.find("height")

    if width_elem is None or height_elem is None:
        return None

    try:
        width = int(width_elem.text)
        height = int(height_elem.text)
    except (ValueError, TypeError):
        return None

    if width <= 0 or height <= 0:
        return None

    # Parse objects
    objects = []
    for obj in root.findall("object"):
        name_elem = obj.find("name")
        if name_elem is None:
            continue

        name = name_elem.text.strip()

        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue

        try:
            xmin = float(bndbox.find("xmin").text)
            ymin = float(bndbox.find("ymin").text)
            xmax = float(bndbox.find("xmax").text)
            ymax = float(bndbox.find("ymax").text)
        except (ValueError, TypeError, AttributeError):
            continue

        # Sanity check
        if xmax <= xmin or ymax <= ymin:
            continue

        objects.append({
            "name": name,
            "bbox": (xmin, ymin, xmax, ymax),
        })

    return {
        "filename": filename,
        "width": width,
        "height": height,
        "objects": objects,
    }


def voc_to_yolo_line(
    obj_name: str,
    bbox: Tuple[float, float, float, float],
    img_width: int,
    img_height: int,
    label_map: Dict[str, Optional[str]],
    class_name_to_id: Dict[str, int],
) -> Optional[str]:
    """
    Convert a single VOC object to a YOLO format line.

    Returns:
        "class_id x_center y_center width height" or None if class should be removed.
    """
    # Apply label mapping
    mapped_name = label_map.get(obj_name)

    if mapped_name is None:
        # None means REMOVE this class
        if obj_name in label_map:
            return None  # Explicitly mapped to None -> skip
        else:
            # Unknown label not in map -> skip with warning
            return None

    # Get class ID
    class_id = class_name_to_id.get(mapped_name)
    if class_id is None:
        return None

    # Convert bbox: VOC (xmin,ymin,xmax,ymax) -> YOLO (x_center,y_center,w,h) normalized
    xmin, ymin, xmax, ymax = bbox

    # Clamp to image bounds
    xmin = max(0, min(xmin, img_width))
    ymin = max(0, min(ymin, img_height))
    xmax = max(0, min(xmax, img_width))
    ymax = max(0, min(ymax, img_height))

    # Calculate normalized values
    x_center = ((xmin + xmax) / 2) / img_width
    y_center = ((ymin + ymax) / 2) / img_height
    w = (xmax - xmin) / img_width
    h = (ymax - ymin) / img_height

    # Final clamp to [0, 1]
    x_center = max(0.0, min(1.0, x_center))
    y_center = max(0.0, min(1.0, y_center))
    w = max(0.001, min(1.0, w))  # Minimum size
    h = max(0.001, min(1.0, h))

    return f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}"


def convert_voc_to_yolo(
    xml_path: Path,
    label_map: Dict[str, Optional[str]],
    class_name_to_id: Dict[str, int],
) -> Optional[List[str]]:
    """
    Convert a VOC XML file to YOLO format lines.

    Returns:
        List of YOLO format strings, or None if parsing failed.
    """
    parsed = parse_voc_xml(xml_path)
    if parsed is None:
        return None

    yolo_lines = []
    for obj in parsed["objects"]:
        line = voc_to_yolo_line(
            obj["name"],
            obj["bbox"],
            parsed["width"],
            parsed["height"],
            label_map,
            class_name_to_id,
        )
        if line is not None:
            yolo_lines.append(line)

    return yolo_lines
