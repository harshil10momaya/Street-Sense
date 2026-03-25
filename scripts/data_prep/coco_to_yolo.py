"""
StreetSense — COCO to YOLO Format Converter

Converts COCO JSON annotations to YOLO format text files.
Useful for datasets from Kaggle or TACO that use COCO format.

COCO format:
    annotations.json → {"images": [...], "annotations": [...], "categories": [...]}

YOLO format (per image):
    image_name.txt → "class_id x_center y_center width height" (normalized)

Usage:
    python scripts/data_prep/coco_to_yolo.py \\
        --coco-json path/to/annotations.json \\
        --image-dir path/to/images \\
        --output-dir path/to/output \\
        --class-map '{"original_cat_name": target_class_id}'

Example:
    python scripts/data_prep/coco_to_yolo.py \\
        --coco-json data/raw/taco/annotations.json \\
        --image-dir data/raw/taco/images \\
        --output-dir data/datasets/raw/garbage/train \\
        --class-map '{"Litter": 2, "Trash": 2, "Garbage": 2}'
"""

import argparse
import json
import shutil
from pathlib import Path


def convert_coco_to_yolo(coco_json: Path, image_dir: Path, output_dir: Path, class_map: dict):
    """Convert COCO annotations to YOLO format."""

    out_img_dir = output_dir / "images"
    out_lbl_dir = output_dir / "labels"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    with open(coco_json) as f:
        coco = json.load(f)

    # Build lookups
    cat_id_to_name = {c["id"]: c["name"] for c in coco["categories"]}
    img_id_to_info = {img["id"]: img for img in coco["images"]}

    # Group annotations by image
    img_annotations = {}
    for ann in coco["annotations"]:
        img_id = ann["image_id"]
        if img_id not in img_annotations:
            img_annotations[img_id] = []
        img_annotations[img_id].append(ann)

    converted = 0
    skipped = 0

    for img_id, img_info in img_id_to_info.items():
        filename = img_info["file_name"]
        img_w = img_info["width"]
        img_h = img_info["height"]

        # Source image
        src_img = image_dir / filename
        if not src_img.exists():
            # Try without subdirectory
            src_img = image_dir / Path(filename).name
            if not src_img.exists():
                skipped += 1
                continue

        # Get annotations for this image
        anns = img_annotations.get(img_id, [])
        yolo_lines = []

        for ann in anns:
            cat_name = cat_id_to_name.get(ann["category_id"], "")

            # Map to our class ID
            target_id = None
            for key, tid in class_map.items():
                if key.lower() in cat_name.lower():
                    target_id = tid
                    break

            if target_id is None:
                continue

            # COCO bbox: [x_min, y_min, width, height] (absolute pixels)
            bx, by, bw, bh = ann["bbox"]

            # Convert to YOLO: [x_center, y_center, width, height] (normalized)
            x_center = (bx + bw / 2) / img_w
            y_center = (by + bh / 2) / img_h
            norm_w = bw / img_w
            norm_h = bh / img_h

            # Clamp to [0, 1]
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            norm_w = max(0, min(1, norm_w))
            norm_h = max(0, min(1, norm_h))

            yolo_lines.append(f"{target_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}")

        if yolo_lines:
            # Copy image
            dest_img = out_img_dir / Path(filename).name
            shutil.copy2(src_img, dest_img)

            # Write YOLO label
            stem = Path(filename).stem
            label_file = out_lbl_dir / f"{stem}.txt"
            label_file.write_text("\n".join(yolo_lines) + "\n")

            converted += 1

    print(f"Converted: {converted} images")
    print(f"Skipped (missing image): {skipped}")
    print(f"Output: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Convert COCO to YOLO format")
    parser.add_argument("--coco-json", type=Path, required=True, help="Path to COCO annotations JSON")
    parser.add_argument("--image-dir", type=Path, required=True, help="Directory containing images")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")
    parser.add_argument(
        "--class-map",
        type=str,
        required=True,
        help='JSON string mapping category names to class IDs, e.g., \'{"Pothole": 0}\'',
    )
    args = parser.parse_args()

    class_map = json.loads(args.class_map)
    print(f"Class mapping: {class_map}")

    convert_coco_to_yolo(args.coco_json, args.image_dir, args.output_dir, class_map)


if __name__ == "__main__":
    main()
