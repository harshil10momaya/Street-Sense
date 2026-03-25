"""
StreetSense — Dataset Validator

Validates the final merged dataset before training:
- Checks every image is readable
- Validates every label file format
- Verifies class IDs are in range [0, 3]
- Detects bbox anomalies
- Reports class balance
- Checks train/val split health

Usage:
    python scripts/data_prep/validate_dataset.py
"""

import sys
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_DIR, FINAL_CLASSES, NUM_CLASSES, IMG_EXTENSIONS


def validate_label_line(line: str, line_num: int) -> list:
    """Validate a single YOLO label line."""
    errors = []
    parts = line.strip().split()

    if len(parts) < 5:
        errors.append(f"L{line_num}: Need 5 values, got {len(parts)}")
        return errors

    try:
        cls_id = int(parts[0])
        x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
    except ValueError:
        errors.append(f"L{line_num}: Non-numeric values")
        return errors

    if cls_id < 0 or cls_id >= NUM_CLASSES:
        errors.append(f"L{line_num}: Class {cls_id} out of range [0,{NUM_CLASSES-1}]")

    for name, val in [("x", x), ("y", y), ("w", w), ("h", h)]:
        if val < 0 or val > 1:
            errors.append(f"L{line_num}: {name}={val:.4f} outside [0,1]")

    if w <= 0 or h <= 0:
        errors.append(f"L{line_num}: Zero/negative size (w={w:.4f}, h={h:.4f})")

    # Tiny bbox warning (might be noise)
    if w * h < 0.0001:
        errors.append(f"L{line_num}: [WARN] Very tiny bbox (area={w*h:.6f})")

    return errors


def main():
    print("=" * 60)
    print("StreetSense — Dataset Validator")
    print("=" * 60)

    if not OUTPUT_DIR.exists():
        print(f"\n❌ Dataset not found: {OUTPUT_DIR}")
        print(f"   Run convert_and_clean.py first!")
        sys.exit(1)

    total_images = 0
    total_labels = 0
    total_errors = 0
    total_warnings = 0
    class_counts = defaultdict(int)
    split_counts = {}

    for split in ["train", "val", "test"]:
        img_dir = OUTPUT_DIR / "images" / split
        lbl_dir = OUTPUT_DIR / "labels" / split

        if not img_dir.exists():
            continue

        images = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in IMG_EXTENSIONS])
        split_errors = 0
        split_count = len(images)
        split_counts[split] = split_count

        print(f"\n  📂 {split}/ ({split_count} images)")

        for img_file in images:
            total_images += 1

            # Validate image
            try:
                img = Image.open(img_file)
                img.verify()
            except Exception as e:
                print(f"     ❌ {img_file.name}: Corrupt ({e})")
                split_errors += 1
                continue

            # Check label
            label_file = lbl_dir / f"{img_file.stem}.txt"
            if not label_file.exists():
                total_warnings += 1
                continue

            total_labels += 1
            content = label_file.read_text().strip()
            if not content:
                continue  # Empty label = background

            for i, line in enumerate(content.split("\n"), 1):
                line = line.strip()
                if not line:
                    continue

                errors = validate_label_line(line, i)
                for err in errors:
                    if "[WARN]" in err:
                        total_warnings += 1
                    else:
                        split_errors += 1
                        if split_errors <= 10:  # Only show first 10
                            print(f"     ❌ {label_file.name}: {err}")

                # Count class
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        cls_id = int(parts[0])
                        if 0 <= cls_id < NUM_CLASSES:
                            class_counts[cls_id] += 1
                    except ValueError:
                        pass

        total_errors += split_errors
        if split_errors > 10:
            print(f"     ... and {split_errors - 10} more errors")
        print(f"     Errors: {split_errors}")

    # Summary
    print(f"\n{'='*60}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Images:     {total_images}")
    print(f"  Labels:     {total_labels}")
    print(f"  Errors:     {total_errors}")
    print(f"  Warnings:   {total_warnings}")

    total_annotations = sum(class_counts.values())
    print(f"\n  Annotations: {total_annotations}")
    print(f"  Class distribution:")
    for cls_id in sorted(FINAL_CLASSES.keys()):
        name = FINAL_CLASSES[cls_id]
        count = class_counts.get(cls_id, 0)
        pct = count / total_annotations * 100 if total_annotations > 0 else 0
        bar = "█" * max(1, int(pct / 2))
        print(f"    {cls_id}: {name:10s} {count:6d} ({pct:5.1f}%) {bar}")

    # Balance check
    if class_counts:
        max_c = max(class_counts.values())
        min_c = min(class_counts.values()) if len(class_counts) == NUM_CLASSES else 0
        ratio = min_c / max_c if max_c > 0 else 0
        print(f"\n  Balance ratio: {ratio:.2f} (min/max)")
        if ratio < 0.1:
            print(f"  ⚠️  SEVERE imbalance — consider oversampling minority class")
        elif ratio < 0.3:
            print(f"  ⚠️  Moderate imbalance — augmentation should help")
        else:
            print(f"  ✅ Acceptable balance")

    # Missing classes
    missing = [FINAL_CLASSES[i] for i in range(NUM_CLASSES) if class_counts.get(i, 0) == 0]
    if missing:
        print(f"\n  ❌ MISSING CLASSES: {missing}")
        print(f"     These classes have zero annotations!")

    # Final verdict
    if total_errors == 0 and total_images > 50 and len(class_counts) == NUM_CLASSES:
        print(f"\n  ✅ Dataset VALID — ready for training!")
        print(f"     cd backend && python -m ai.models.train")
    elif total_images == 0:
        print(f"\n  ❌ No images! Run convert_and_clean.py first.")
    else:
        print(f"\n  ⚠️  {total_errors} errors found. Review and re-run pipeline.")

    return total_errors


if __name__ == "__main__":
    errors = main()
    sys.exit(1 if errors > 0 else 0)
