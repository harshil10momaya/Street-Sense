"""
StreetSense — Dataset Analyzer

Generates detailed statistics about the merged dataset:
- Per-class annotation counts
- Per-split distributions
- Bounding box size distributions
- Class balance ratios
- Recommended actions if imbalanced

Usage:
    python scripts/data_prep/analyze_dataset.py
"""

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = ROOT / "data" / "datasets" / "streetsense"

CLASS_NAMES = {0: "pothole", 1: "crack", 2: "garbage", 3: "manhole"}
IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def analyze():
    print("=" * 60)
    print("StreetSense — Dataset Analysis")
    print("=" * 60)

    if not DATASET_DIR.exists():
        print(f"\n❌ Dataset not found: {DATASET_DIR}")
        sys.exit(1)

    # Collect stats
    split_stats = {}

    for split in ["train", "val", "test"]:
        img_dir = DATASET_DIR / "images" / split
        lbl_dir = DATASET_DIR / "labels" / split

        if not img_dir.exists():
            continue

        images = [f for f in img_dir.iterdir() if f.suffix.lower() in IMG_EXTENSIONS]

        class_counts = defaultdict(int)
        bbox_areas = defaultdict(list)
        total_annotations = 0
        empty_labels = 0

        for img_file in images:
            label_file = lbl_dir / f"{img_file.stem}.txt"
            if not label_file.exists():
                empty_labels += 1
                continue

            content = label_file.read_text().strip()
            if not content:
                empty_labels += 1
                continue

            for line in content.split("\n"):
                parts = line.strip().split()
                if len(parts) >= 5:
                    cid = int(parts[0])
                    w, h = float(parts[3]), float(parts[4])
                    class_counts[cid] += 1
                    bbox_areas[cid].append(w * h)
                    total_annotations += 1

        split_stats[split] = {
            "images": len(images),
            "annotations": total_annotations,
            "empty_labels": empty_labels,
            "class_counts": dict(class_counts),
            "bbox_areas": dict(bbox_areas),
        }

    # Print results
    for split, stats in split_stats.items():
        print(f"\n📂 {split.upper()}")
        print(f"   Images: {stats['images']}")
        print(f"   Annotations: {stats['annotations']}")
        print(f"   Empty labels (background): {stats['empty_labels']}")
        print(f"   Class breakdown:")
        for cid in sorted(CLASS_NAMES.keys()):
            count = stats["class_counts"].get(cid, 0)
            pct = count / stats["annotations"] * 100 if stats["annotations"] > 0 else 0
            areas = stats["bbox_areas"].get(cid, [])
            avg_area = sum(areas) / len(areas) if areas else 0
            bar = "█" * int(pct / 2)
            print(f"     {CLASS_NAMES[cid]:10s}: {count:5d} ({pct:5.1f}%) {bar}")
            if areas:
                print(f"                    avg bbox area: {avg_area:.4f} (normalized)")

    # Overall balance check
    print(f"\n{'='*60}")
    print("BALANCE ANALYSIS")
    print(f"{'='*60}")

    total_per_class = defaultdict(int)
    for stats in split_stats.values():
        for cid, count in stats["class_counts"].items():
            total_per_class[cid] += count

    if total_per_class:
        max_count = max(total_per_class.values())
        min_count = min(total_per_class.values()) if total_per_class else 0
        ratio = min_count / max_count if max_count > 0 else 0

        print(f"\n  Overall class totals:")
        for cid in sorted(CLASS_NAMES.keys()):
            count = total_per_class.get(cid, 0)
            print(f"    {CLASS_NAMES[cid]:10s}: {count}")

        print(f"\n  Balance ratio (min/max): {ratio:.2f}")

        if ratio < 0.3:
            print(f"\n  ⚠️  SEVERE CLASS IMBALANCE (ratio < 0.3)")
            print(f"     Recommendations:")
            print(f"     1. Add more data for underrepresented classes")
            print(f"     2. Use augmentation (mosaic, mixup) — already enabled in train_config.yaml")
            print(f"     3. Consider class weights in loss function")
            print(f"     4. Use oversampling for minority classes")
        elif ratio < 0.5:
            print(f"\n  ⚠️  Moderate imbalance. Augmentation should handle this.")
        else:
            print(f"\n  ✅ Good class balance!")
    else:
        print(f"\n  ❌ No annotations found. Download and merge datasets first!")

    # Training readiness
    total_train = split_stats.get("train", {}).get("images", 0)
    total_val = split_stats.get("val", {}).get("images", 0)

    print(f"\n{'='*60}")
    print("TRAINING READINESS")
    print(f"{'='*60}")

    checks = [
        ("Train images > 100", total_train > 100),
        ("Val images > 20", total_val > 20),
        ("All 4 classes present", len(total_per_class) == 4),
        ("Balance ratio > 0.3", (min(total_per_class.values()) / max(total_per_class.values()) > 0.3) if total_per_class else False),
    ]

    all_pass = True
    for check_name, passed in checks:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {check_name}")
        if not passed:
            all_pass = False

    if all_pass:
        print(f"\n  🚀 Dataset ready for training!")
        print(f"     Run: cd backend && python -m ai.models.train")
    else:
        print(f"\n  ⚠️  Fix issues above before training.")


if __name__ == "__main__":
    analyze()
