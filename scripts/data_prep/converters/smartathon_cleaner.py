"""
StreetSense -- Smartathon Label Cleaner

Cleans the Smartathon dataset's messy YOLO labels:
- Multiple variants: pothole, Pothole, potholes, etc. -> pothole (class 0)
- Manhole variations -> manhole (class 2)
- Removes: object, unknown, irrelevant classes

The Smartathon dataset exports from Roboflow with a classes.txt or data.yaml
that lists its own class indices. We need to:
1. Read the original class names from the dataset
2. Map them to our unified class IDs
3. Rewrite all label files
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def detect_smartathon_classes(dataset_dir: Path) -> Dict[int, str]:
    """
    Detect the original class mapping from the Smartathon dataset.
    Roboflow exports include either data.yaml or classes.txt.
    """
    original_classes = {}

    # Try data.yaml first
    yaml_files = list(dataset_dir.rglob("data.yaml")) + list(dataset_dir.rglob("*.yaml"))
    for yaml_file in yaml_files:
        content = yaml_file.read_text()
        # Parse names section
        in_names = False
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("names:"):
                in_names = True
                # Check inline list format: names: ['pothole', 'manhole']
                match = re.search(r"names:\s*\[(.+)\]", line)
                if match:
                    names = [n.strip().strip("'\"") for n in match.group(1).split(",")]
                    for i, name in enumerate(names):
                        original_classes[i] = name
                    return original_classes
                continue
            if in_names:
                # Parse dict format: 0: pothole
                match = re.match(r"(\d+):\s*(.+)", line)
                if match:
                    idx = int(match.group(1))
                    name = match.group(2).strip().strip("'\"")
                    original_classes[idx] = name
                elif line and not line.startswith("#"):
                    break  # End of names section

        if original_classes:
            return original_classes

    # Try classes.txt
    classes_files = list(dataset_dir.rglob("classes.txt"))
    for classes_file in classes_files:
        for i, line in enumerate(classes_file.read_text().strip().split("\n")):
            name = line.strip()
            if name:
                original_classes[i] = name

        if original_classes:
            return original_classes

    return original_classes


def normalize_label(raw_label: str) -> Optional[str]:
    """
    Normalize a messy Smartathon label to one of our target classes.

    Returns:
        'pothole', 'manhole', or None (to remove)
    """
    label = raw_label.strip().lower()

    # Remove extra whitespace
    label = re.sub(r"\s+", " ", label)

    # Pothole patterns
    pothole_patterns = [
        "pothole", "pot hole", "potholes", "pot-hole",
        "road hole", "road_hole", "hole",
    ]
    for pattern in pothole_patterns:
        if pattern in label:
            return "pothole"

    # Manhole patterns
    manhole_patterns = [
        "manhole", "man hole", "manholes", "man-hole",
        "manhole cover", "sewer", "drain cover",
    ]
    for pattern in manhole_patterns:
        if pattern in label:
            return "manhole"

    # Everything else -> REMOVE
    return None


def build_smartathon_remap(original_classes: Dict[int, str]) -> Dict[int, Optional[int]]:
    """
    Build a mapping from original Smartathon class IDs to our final class IDs.

    Returns:
        {original_id: new_id or None}
        None means the class should be removed.
    """
    from config import CLASS_NAME_TO_ID

    remap = {}
    for orig_id, orig_name in original_classes.items():
        target_name = normalize_label(orig_name)
        if target_name is not None:
            remap[orig_id] = CLASS_NAME_TO_ID[target_name]
        else:
            remap[orig_id] = None  # Remove this class
            print(f"    REMOVING class {orig_id}: '{orig_name}'")

    return remap


def clean_smartathon_label_file(
    label_path: Path,
    remap: Dict[int, Optional[int]],
) -> Tuple[List[str], int, int]:
    """
    Clean a single Smartathon YOLO label file.

    Returns:
        (cleaned_lines, kept_count, removed_count)
    """
    content = label_path.read_text().strip()
    if not content:
        return [], 0, 0

    cleaned = []
    kept = 0
    removed = 0

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 5:
            removed += 1
            continue

        try:
            orig_class = int(parts[0])
        except ValueError:
            removed += 1
            continue

        new_class = remap.get(orig_class)
        if new_class is None:
            removed += 1
            continue

        # Validate bbox values
        try:
            x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
        except ValueError:
            removed += 1
            continue

        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            # Try to salvage by clamping
            x = max(0, min(1, x))
            y = max(0, min(1, y))
            w = max(0.001, min(1, w))
            h = max(0.001, min(1, h))

        parts[0] = str(new_class)
        parts[1] = f"{x:.6f}"
        parts[2] = f"{y:.6f}"
        parts[3] = f"{w:.6f}"
        parts[4] = f"{h:.6f}"

        cleaned.append(" ".join(parts[:5]))
        kept += 1

    return cleaned, kept, removed
