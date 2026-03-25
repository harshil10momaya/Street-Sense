"""
StreetSense — Dataset Merger

Merges individual class datasets (pothole, crack, garbage, manhole) into a single
unified YOLO-format dataset with consistent class IDs:
    0: pothole
    1: crack
    2: garbage
    3: manhole

Handles:
- Remapping class IDs from source datasets (each source uses class 0 for its own class)
- Deduplicating filenames across sources
- Train/val/test split
- Copying images + rewriting label files

Usage:
    python scripts/data_prep/merge_datasets.py
    python scripts/data_prep/merge_datasets.py --raw-dir path/to/raw --output-dir path/to/output
"""

import argparse
import random
import shutil
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent.parent

# Unified class mapping
CLASS_MAP = {
    "pothole": 0,
    "crack": 1,
    "garbage": 2,
    "manhole": 3,
}

# Valid image extensions
IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def find_split_dirs(dataset_dir: Path) -> dict:
    """
    Detect the train/val/test structure of a downloaded dataset.
    Roboflow datasets can have different naming conventions.
    """
    splits = {}

    for split_name in ["train", "valid", "val", "test"]:
        # Check for images/labels subdirectory pattern
        img_dir = dataset_dir / split_name / "images"
        lbl_dir = dataset_dir / split_name / "labels"

        if img_dir.exists() and lbl_dir.exists():
            canonical = "val" if split_name == "valid" else split_name
            splits[canonical] = {"images": img_dir, "labels": lbl_dir}

    # Fallback: flat structure (images/ and labels/ at root)
    if not splits:
        img_dir = dataset_dir / "images"
        lbl_dir = dataset_dir / "labels"
        if img_dir.exists() and lbl_dir.exists():
            splits["train"] = {"images": img_dir, "labels": lbl_dir}

    return splits


def remap_label_file(src_label: Path, dest_label: Path, target_class_id: int, source_classes: list = None):
    """
    Read a YOLO label file, remap class IDs, and write to destination.

    If the source dataset has only 1 class (typical for Roboflow single-class exports),
    all detections are remapped to target_class_id.

    If source has multiple classes, source_classes defines the mapping.
    """
    lines = src_label.read_text().strip().split("\n")
    remapped_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 5:
            continue  # Malformed line

        original_class = int(parts[0])

        if source_classes:
            # Multi-class source: map by index
            if original_class < len(source_classes):
                new_class = CLASS_MAP.get(source_classes[original_class], target_class_id)
            else:
                new_class = target_class_id
        else:
            # Single-class source: remap everything to target
            new_class = target_class_id

        parts[0] = str(new_class)
        remapped_lines.append(" ".join(parts))

    dest_label.write_text("\n".join(remapped_lines) + "\n" if remapped_lines else "")


def merge_class_dataset(
    class_name: str,
    raw_dir: Path,
    output_dir: Path,
    stats: dict,
):
    """Merge a single class dataset into the unified output."""
    class_id = CLASS_MAP[class_name]
    dataset_dir = raw_dir / class_name

    if not dataset_dir.exists():
        print(f"  ⚠️  {class_name}/ not found in {raw_dir} — skipping")
        return

    splits = find_split_dirs(dataset_dir)
    if not splits:
        print(f"  ⚠️  No valid train/val structure found in {dataset_dir} — skipping")
        return

    print(f"\n  📂 {class_name} (class_id={class_id})")
    print(f"     Splits found: {list(splits.keys())}")

    for split_name, dirs in splits.items():
        img_dir = dirs["images"]
        lbl_dir = dirs["labels"]

        dest_img_dir = output_dir / "images" / split_name
        dest_lbl_dir = output_dir / "labels" / split_name
        dest_img_dir.mkdir(parents=True, exist_ok=True)
        dest_lbl_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for img_file in img_dir.iterdir():
            if img_file.suffix.lower() not in IMG_EXTENSIONS:
                continue

            # Prefix filename to avoid collisions between datasets
            new_name = f"{class_name}_{img_file.name}"
            label_file = lbl_dir / f"{img_file.stem}.txt"

            # Copy image
            dest_img = dest_img_dir / new_name
            shutil.copy2(img_file, dest_img)

            # Remap and copy label
            dest_lbl = dest_lbl_dir / f"{class_name}_{img_file.stem}.txt"
            if label_file.exists():
                remap_label_file(label_file, dest_lbl, class_id)
            else:
                # No label = no detections (background image)
                dest_lbl.write_text("")

            count += 1

        stats_key = f"{class_name}_{split_name}"
        stats[stats_key] = count
        print(f"     {split_name}: {count} images")


def create_val_from_train(output_dir: Path, val_ratio: float = 0.15):
    """
    If no validation split exists, create one by moving images from train.
    """
    train_img = output_dir / "images" / "train"
    val_img = output_dir / "images" / "val"
    train_lbl = output_dir / "labels" / "train"
    val_lbl = output_dir / "labels" / "val"

    if val_img.exists() and any(val_img.iterdir()):
        return  # Already has validation data

    val_img.mkdir(parents=True, exist_ok=True)
    val_lbl.mkdir(parents=True, exist_ok=True)

    images = list(train_img.glob("*"))
    images = [f for f in images if f.suffix.lower() in IMG_EXTENSIONS]

    if not images:
        return

    random.shuffle(images)
    val_count = max(1, int(len(images) * val_ratio))
    val_images = images[:val_count]

    print(f"\n  🔀 Creating validation split: {val_count} images ({val_ratio*100:.0f}% of train)")

    for img in val_images:
        lbl = train_lbl / f"{img.stem}.txt"

        shutil.move(str(img), val_img / img.name)
        if lbl.exists():
            shutil.move(str(lbl), val_lbl / lbl.name)


def main():
    parser = argparse.ArgumentParser(description="Merge StreetSense datasets")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "datasets" / "raw",
        help="Directory containing raw class datasets",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "datasets" / "streetsense",
        help="Output directory for merged YOLO dataset",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    print("=" * 60)
    print("StreetSense — Dataset Merger")
    print("=" * 60)
    print(f"Raw input:  {args.raw_dir}")
    print(f"Output:     {args.output_dir}")
    print(f"Classes:    {CLASS_MAP}")

    # Clean output
    if args.output_dir.exists():
        print(f"\n⚠️  Cleaning existing output directory...")
        shutil.rmtree(args.output_dir)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    stats = {}

    for class_name in CLASS_MAP:
        merge_class_dataset(class_name, args.raw_dir, args.output_dir, stats)

    # Ensure validation split exists
    create_val_from_train(args.output_dir)

    # Print summary
    print(f"\n{'='*60}")
    print("MERGE COMPLETE")
    print(f"{'='*60}")

    for key, count in sorted(stats.items()):
        print(f"  {key}: {count}")

    total = sum(stats.values())
    print(f"\n  TOTAL: {total} images")

    # Count per split
    for split in ["train", "val", "test"]:
        split_dir = args.output_dir / "images" / split
        if split_dir.exists():
            count = len([f for f in split_dir.iterdir() if f.suffix.lower() in IMG_EXTENSIONS])
            print(f"  {split}: {count} images")

    print(f"\n✅ Dataset ready at: {args.output_dir}")
    print(f"   Next: python scripts/data_prep/validate_dataset.py")


if __name__ == "__main__":
    main()
