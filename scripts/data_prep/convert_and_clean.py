"""
StreetSense -- Convert & Clean Pipeline (v4)

Processes all 4 raw datasets into a single unified YOLO dataset:
  1. Smartathon (YOLO) -> Clean labels, remap pothole/manhole
  2. Andrew (VOC XML) -> Convert XML->YOLO, all -> pothole
  3. RDD 2022 (YOLO TXT) -> Read labels, remap D10/D20/D40 -> crack, D00 -> REMOVE
  4. TACO (COCO JSON) -> Convert JSON->YOLO, all categories -> garbage

Usage:
    python scripts/data_prep/convert_and_clean.py
"""

import argparse
import random
import shutil
import sys
import os
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    RAW_DIR, OUTPUT_DIR, FINAL_CLASSES, CLASS_NAME_TO_ID,
    NUM_CLASSES, IMG_EXTENSIONS,
    SMARTATHON_CONFIG, ANDREW_CONFIG, RDD2022_CONFIG, TACO_CONFIG, MANHOLE_CONFIG,
)
from converters.voc_to_yolo import parse_voc_xml
from converters.coco_to_yolo import load_coco_json, convert_coco_to_yolo
from converters.smartathon_cleaner import (
    detect_smartathon_classes, build_smartathon_remap, clean_smartathon_label_file,
)


def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


class DatasetStats:
    def __init__(self):
        self.images_processed = 0
        self.images_skipped = 0
        self.annotations_kept = 0
        self.annotations_removed = 0
        self.class_counts = defaultdict(int)

    def summary(self):
        lines = [
            f"  Images processed: {self.images_processed}",
            f"  Images skipped:   {self.images_skipped}",
            f"  Annotations kept: {self.annotations_kept}",
            f"  Annotations removed: {self.annotations_removed}",
        ]
        if self.class_counts:
            lines.append("  Per-class counts:")
            for cls_id in sorted(self.class_counts):
                name = FINAL_CLASSES.get(cls_id, f"unknown_{cls_id}")
                lines.append(f"    {name}: {self.class_counts[cls_id]}")
        return "\n".join(lines)


def scan_directory(base_dir, label):
    safe_print(f"  [SCAN] Contents of {base_dir}:")
    if not base_dir.exists():
        safe_print(f"  [SCAN]   Directory does not exist!")
        return
    count = 0
    for item in sorted(base_dir.rglob("*")):
        rel = item.relative_to(base_dir)
        depth = len(rel.parts)
        if depth <= 3 and count < 60:
            prefix = "    " + "  " * depth
            suffix = "/" if item.is_dir() else ""
            safe_print(f"  [SCAN] {prefix}{item.name}{suffix}")
            count += 1
    xml_c = len(list(base_dir.rglob("*.xml")))
    json_c = len(list(base_dir.rglob("*.json")))
    txt_c = len(list(base_dir.rglob("*.txt")))
    img_c = sum(len(list(base_dir.rglob(f"*{e}"))) for e in [".jpg", ".jpeg", ".png"])
    safe_print(f"  [SCAN] Totals: {img_c} images, {xml_c} XMLs, {json_c} JSONs, {txt_c} TXTs")


# ===================================================================
# 1. SMARTATHON
# ===================================================================

def process_smartathon(collected_images, collected_labels, stats):
    raw_dir = SMARTATHON_CONFIG["raw_dir"]
    safe_print(f"\n{'='*60}")
    safe_print(f"[1/4] SMARTATHON -- Potholes + Manholes")
    safe_print(f"{'='*60}")

    if not raw_dir.exists():
        safe_print(f"  [ERROR] Not found: {raw_dir}")
        return

    original_classes = detect_smartathon_classes(raw_dir)
    if not original_classes:
        original_classes = {0: "pothole"}
    safe_print(f"  Original classes found: {original_classes}")
    remap = build_smartathon_remap(original_classes)
    safe_print(f"  Remap table: {remap}")

    pairs = []
    for split in ["train", "valid", "val", "test"]:
        img_dir = raw_dir / split / "images"
        lbl_dir = raw_dir / split / "labels"
        if img_dir.exists() and lbl_dir.exists():
            for img in img_dir.iterdir():
                if img.suffix.lower() in IMG_EXTENSIONS:
                    lbl = lbl_dir / f"{img.stem}.txt"
                    pairs.append((img, lbl if lbl.exists() else None))
    if not pairs:
        for d in [raw_dir / "images"]:
            if d.exists():
                lbl_dir = raw_dir / "labels"
                for img in d.iterdir():
                    if img.suffix.lower() in IMG_EXTENSIONS:
                        lbl = lbl_dir / f"{img.stem}.txt"
                        pairs.append((img, lbl if lbl.exists() else None))

    safe_print(f"  Found {len(pairs)} image-label pairs")
    for img_file, label_file in pairs:
        if not label_file or not label_file.exists():
            stats.images_skipped += 1
            continue
        cleaned, kept, removed = clean_smartathon_label_file(label_file, remap)
        stats.annotations_kept += kept
        stats.annotations_removed += removed
        if not cleaned:
            stats.images_skipped += 1
            continue
        for line in cleaned:
            stats.class_counts[int(line.split()[0])] += 1
        collected_images.append((img_file, f"smartathon_{img_file.name}"))
        collected_labels.append((cleaned, f"smartathon_{img_file.stem}.txt"))
        stats.images_processed += 1
    safe_print(stats.summary())


# ===================================================================
# 2. ANDREW POTHOLE (VOC XML)
# ===================================================================

def process_andrew(collected_images, collected_labels, stats):
    raw_dir = ANDREW_CONFIG["raw_dir"]
    safe_print(f"\n{'='*60}")
    safe_print(f"[2/4] ANDREW -- Potholes (VOC XML)")
    safe_print(f"{'='*60}")

    if not raw_dir.exists():
        safe_print(f"  [ERROR] Not found: {raw_dir}")
        return

    xml_files = list(raw_dir.rglob("*.xml"))
    safe_print(f"  Found {len(xml_files)} XML annotation files")
    if not xml_files:
        scan_directory(raw_dir, "andrew")
        return

    for xml_file in xml_files:
        parsed = parse_voc_xml(xml_file)
        if parsed is None:
            stats.images_skipped += 1
            continue
        img_name = parsed["filename"]
        img_file = None
        for sd in [xml_file.parent, xml_file.parent / "images",
                    xml_file.parent.parent / "images", xml_file.parent.parent,
                    raw_dir / "images", raw_dir]:
            if not sd.exists():
                continue
            for try_name in [img_name] + [f"{Path(img_name).stem}{e}" for e in [".jpg", ".jpeg", ".png"]]:
                c = sd / try_name
                if c.exists():
                    img_file = c
                    break
            if img_file:
                break
        if not img_file:
            stats.images_skipped += 1
            continue

        yolo_lines = []
        tid = CLASS_NAME_TO_ID["pothole"]
        for obj in parsed["objects"]:
            xmin, ymin, xmax, ymax = obj["bbox"]
            w, h = parsed["width"], parsed["height"]
            xc = max(0, min(1, ((xmin+xmax)/2)/w))
            yc = max(0, min(1, ((ymin+ymax)/2)/h))
            bw = max(0.001, min(1, (xmax-xmin)/w))
            bh = max(0.001, min(1, (ymax-ymin)/h))
            yolo_lines.append(f"{tid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
            stats.annotations_kept += 1
            stats.class_counts[tid] += 1
        if not yolo_lines:
            stats.images_skipped += 1
            continue
        collected_images.append((img_file, f"andrew_{img_file.name}"))
        collected_labels.append((yolo_lines, f"andrew_{img_file.stem}.txt"))
        stats.images_processed += 1
    safe_print(stats.summary())


# ===================================================================
# 3. RDD 2022 -- YOLO FORMAT (pre-split from Kaggle)
# ===================================================================

def process_rdd2022(collected_images, collected_labels, stats):
    """RDD2022 from Kaggle (sovitrath) comes pre-converted to YOLO format:
        rdd2022/RDD_SPLIT/train/images/*.jpg
        rdd2022/RDD_SPLIT/train/labels/*.txt

    The label files contain class IDs that correspond to:
        0: D00 (longitudinal construction joint) -> REMOVE
        1: D10 (longitudinal crack) -> crack
        2: D20 (transverse crack) -> crack
        3: D40 (alligator crack) -> crack

    We remap: 1,2,3 -> our crack class (1), and 0 -> REMOVE.
    """
    raw_dir = RDD2022_CONFIG["raw_dir"]

    safe_print(f"\n{'='*60}")
    safe_print(f"[3/4] RDD 2022 -- Road Cracks (YOLO pre-split)")
    safe_print(f"{'='*60}")

    if not raw_dir.exists():
        safe_print(f"  [ERROR] Not found: {raw_dir}")
        return

    # RDD2022 class ID mapping (source -> target)
    # Source classes: 0=D00, 1=D10, 2=D20, 3=D40
    # D00 -> None (REMOVE), D10/D20/D40 -> crack (class 1)
    rdd_remap = {
        0: None,   # D00 -> REMOVE
        1: CLASS_NAME_TO_ID["crack"],  # D10 -> crack
        2: CLASS_NAME_TO_ID["crack"],  # D20 -> crack
        3: CLASS_NAME_TO_ID["crack"],  # D40 -> crack
    }

    safe_print(f"  RDD class remap: {rdd_remap}")

    # Find image-label pairs in YOLO format
    # Structure: rdd2022/RDD_SPLIT/train/images/ + labels/
    # Or could be: rdd2022/train/images/ + labels/
    pairs_found = 0

    # Search recursively for any directory named "images" that has a sibling "labels"
    for img_dir in raw_dir.rglob("images"):
        if not img_dir.is_dir():
            continue
        lbl_dir = img_dir.parent / "labels"
        if not lbl_dir.exists():
            continue

        split_name = img_dir.parent.name  # e.g., "train", "val", "test"
        safe_print(f"  Found split: {img_dir.parent.relative_to(raw_dir)} "
                    f"({split_name})")

        img_files = [f for f in img_dir.iterdir() if f.suffix.lower() in IMG_EXTENSIONS]
        safe_print(f"    Images: {len(img_files)}")

        for img_file in img_files:
            label_file = lbl_dir / f"{img_file.stem}.txt"
            if not label_file.exists():
                stats.images_skipped += 1
                continue

            # Read and remap label file
            content = label_file.read_text().strip()
            if not content:
                stats.images_skipped += 1
                continue

            yolo_lines = []
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue

                try:
                    orig_class = int(parts[0])
                    x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                except ValueError:
                    continue

                # Remap class
                new_class = rdd_remap.get(orig_class)
                if new_class is None:
                    # D00 -> REMOVE, or unknown class
                    stats.annotations_removed += 1
                    continue

                # Validate bbox
                x = max(0, min(1, x))
                y = max(0, min(1, y))
                w = max(0.001, min(1, w))
                h = max(0.001, min(1, h))

                yolo_lines.append(f"{new_class} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
                stats.annotations_kept += 1
                stats.class_counts[new_class] += 1

            if not yolo_lines:
                stats.images_skipped += 1
                continue

            new_name = f"rdd_{split_name}_{img_file.name}"
            collected_images.append((img_file, new_name))
            collected_labels.append((yolo_lines, f"rdd_{split_name}_{img_file.stem}.txt"))
            stats.images_processed += 1
            pairs_found += 1

    if pairs_found == 0:
        safe_print(f"  [ERROR] No YOLO image-label pairs found!")
        safe_print(f"  Scanning directory for debugging...")
        scan_directory(raw_dir, "rdd2022")

    safe_print(stats.summary())


# ===================================================================
# 4. TACO (COCO JSON)
# ===================================================================

def process_taco(collected_images, collected_labels, stats):
    raw_dir = TACO_CONFIG["raw_dir"]
    target_class_id = CLASS_NAME_TO_ID["garbage"]

    safe_print(f"\n{'='*60}")
    safe_print(f"[4/4] TACO -- Garbage Detection (COCO JSON)")
    safe_print(f"{'='*60}")

    if not raw_dir.exists():
        safe_print(f"  [ERROR] Not found: {raw_dir}")
        return

    # Find annotation JSON
    annotation_json = None
    for name in ["annotations.json", "annotations_0.json", "instances_default.json"]:
        found = list(raw_dir.rglob(name))
        if found:
            annotation_json = found[0]
            break
    if not annotation_json:
        for jf in raw_dir.rglob("*.json"):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    h = f.read(1000)
                if '"annotations"' in h and '"images"' in h:
                    annotation_json = jf
                    break
            except Exception:
                continue
    if not annotation_json:
        safe_print(f"  [ERROR] No COCO JSON found in {raw_dir}")
        scan_directory(raw_dir, "taco")
        return

    safe_print(f"  Using: {annotation_json}")
    coco_data = load_coco_json(annotation_json)
    if not coco_data:
        return

    safe_print(f"  COCO: {len(coco_data.get('images',[]))} images, "
               f"{len(coco_data.get('annotations',[]))} annotations, "
               f"{len(coco_data.get('categories',[]))} categories")

    yolo_per_image = convert_coco_to_yolo(coco_data, target_class_id=target_class_id, category_filter=None)

    # Build image search paths
    img_bases = [annotation_json.parent, raw_dir, raw_dir / "data"]
    for base in [annotation_json.parent, raw_dir]:
        if base.exists():
            for d in base.iterdir():
                if d.is_dir():
                    img_bases.append(d)

    found = 0
    not_found = 0

    for img_filename, yolo_lines in yolo_per_image.items():
        img_file = None
        name_only = Path(img_filename).name

        for base in img_bases:
            if not base.exists():
                continue
            for try_name in [img_filename, name_only]:
                c = base / try_name
                if c.exists():
                    img_file = c
                    break
            if img_file:
                break
            for sub in base.iterdir():
                if sub.is_dir():
                    for try_name in [name_only, img_filename]:
                        c = sub / try_name
                        if c.exists():
                            img_file = c
                            break
                if img_file:
                    break
            if img_file:
                break

        if not img_file:
            not_found += 1
            stats.images_skipped += 1
            if not_found <= 3:
                safe_print(f"  [WARN] Not found: {img_filename}")
            continue

        found += 1
        for line in yolo_lines:
            stats.class_counts[target_class_id] += 1
        stats.annotations_kept += len(yolo_lines)
        stats.images_processed += 1

        cn = Path(img_filename).name
        collected_images.append((img_file, f"taco_{cn}"))
        collected_labels.append((yolo_lines, f"taco_{Path(cn).stem}.txt"))

    if not_found > 3:
        safe_print(f"  [WARN] ... and {not_found - 3} more not found")
    safe_print(f"  Images found: {found}, not found: {not_found}")
    safe_print(stats.summary())


# ===================================================================
# 5. MANHOLE (Roboflow YOLO -- optional extra dataset)
# ===================================================================

def process_manhole(collected_images, collected_labels, stats):
    """Process manhole dataset from Roboflow (YOLO format).
    All labels get remapped to manhole (class 2).
    If directory doesn't exist, gracefully skip.
    """
    raw_dir = MANHOLE_CONFIG["raw_dir"]
    target_id = CLASS_NAME_TO_ID["manhole"]

    safe_print(f"\n{'='*60}")
    safe_print(f"[5/5] MANHOLE -- Manhole Covers (YOLO)")
    safe_print(f"{'='*60}")

    if not raw_dir.exists():
        safe_print(f"  [SKIP] Not found: {raw_dir}")
        safe_print(f"  To add manhole data:")
        safe_print(f"    1. Go to: https://universe.roboflow.com/manhole-jyxfj/manhole-cover-jyxfj")
        safe_print(f"    2. Download as YOLOv8 format")
        safe_print(f"    3. Extract to: {raw_dir}")
        safe_print(f"    4. Re-run this script")
        return

    # Find YOLO image-label pairs
    pairs = []
    for split in ["train", "valid", "val", "test"]:
        img_dir = raw_dir / split / "images"
        lbl_dir = raw_dir / split / "labels"
        if img_dir.exists() and lbl_dir.exists():
            for img in img_dir.iterdir():
                if img.suffix.lower() in IMG_EXTENSIONS:
                    lbl = lbl_dir / f"{img.stem}.txt"
                    pairs.append((img, lbl if lbl.exists() else None))

    if not pairs:
        # Flat structure fallback
        img_dir = raw_dir / "images"
        lbl_dir = raw_dir / "labels"
        if img_dir.exists():
            for img in img_dir.iterdir():
                if img.suffix.lower() in IMG_EXTENSIONS:
                    lbl = lbl_dir / f"{img.stem}.txt"
                    pairs.append((img, lbl if lbl.exists() else None))

    if not pairs:
        safe_print(f"  [WARN] No image-label pairs found")
        scan_directory(raw_dir, "manhole")
        return

    safe_print(f"  Found {len(pairs)} image-label pairs")

    for img_file, label_file in pairs:
        if not label_file or not label_file.exists():
            stats.images_skipped += 1
            continue

        content = label_file.read_text().strip()
        if not content:
            stats.images_skipped += 1
            continue

        yolo_lines = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            except ValueError:
                continue

            x = max(0, min(1, x))
            y = max(0, min(1, y))
            w = max(0.001, min(1, w))
            h = max(0.001, min(1, h))

            # ALL classes -> manhole (class 2)
            yolo_lines.append(f"{target_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
            stats.annotations_kept += 1
            stats.class_counts[target_id] += 1

        if not yolo_lines:
            stats.images_skipped += 1
            continue

        collected_images.append((img_file, f"manhole_{img_file.name}"))
        collected_labels.append((yolo_lines, f"manhole_{img_file.stem}.txt"))
        stats.images_processed += 1

    safe_print(stats.summary())


# ===================================================================
# WRITE FINAL DATASET
# ===================================================================

def write_final_dataset(collected_images, collected_labels, val_ratio=0.15, seed=42):
    safe_print(f"\n{'='*60}")
    safe_print(f"WRITING FINAL DATASET")
    safe_print(f"{'='*60}")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    for s in ["train", "val"]:
        (OUTPUT_DIR / "images" / s).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "labels" / s).mkdir(parents=True, exist_ok=True)

    random.seed(seed)
    indices = list(range(len(collected_images)))
    random.shuffle(indices)
    val_count = max(1, int(len(indices) * val_ratio))
    val_indices = set(indices[:val_count])

    train_c = val_c = 0
    for i in indices:
        img_src, img_name = collected_images[i]
        yolo_lines, lbl_name = collected_labels[i]
        split = "val" if i in val_indices else "train"
        shutil.copy2(img_src, OUTPUT_DIR / "images" / split / img_name)
        (OUTPUT_DIR / "labels" / split / lbl_name).write_text("\n".join(yolo_lines) + "\n")
        if split == "train":
            train_c += 1
        else:
            val_c += 1

    safe_print(f"  Train: {train_c} images")
    safe_print(f"  Val:   {val_c} images")
    safe_print(f"  Total: {train_c + val_c} images")
    return train_c, val_c


def write_dataset_yaml():
    yaml_content = f"""# StreetSense -- YOLOv8 Dataset Configuration
# Auto-generated by convert_and_clean.py

path: {OUTPUT_DIR}
train: images/train
val: images/val

nc: {NUM_CLASSES}

names:
"""
    for cid in sorted(FINAL_CLASSES.keys()):
        yaml_content += f"  {cid}: {FINAL_CLASSES[cid]}\n"
    yaml_path = OUTPUT_DIR / "dataset.yaml"
    yaml_path.write_text(yaml_content)
    safe_print(f"\n  [OK] dataset.yaml written to: {yaml_path}")
    backend_yaml = Path(__file__).resolve().parent.parent.parent / "backend" / "ai" / "config" / "dataset.yaml"
    if backend_yaml.parent.exists():
        backend_yaml.write_text(yaml_content)
        safe_print(f"  [OK] Backend config updated: {backend_yaml}")
    return yaml_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    safe_print("=" * 60)
    safe_print("StreetSense -- Convert & Clean Pipeline")
    safe_print("=" * 60)
    safe_print(f"Target classes: {FINAL_CLASSES}")
    safe_print(f"Raw input:      {RAW_DIR}")
    safe_print(f"Output:         {OUTPUT_DIR}")
    safe_print(f"Val ratio:      {args.val_ratio}")

    collected_images = []
    collected_labels = []

    s1 = DatasetStats()
    process_smartathon(collected_images, collected_labels, s1)

    s2 = DatasetStats()
    process_andrew(collected_images, collected_labels, s2)

    s3 = DatasetStats()
    process_rdd2022(collected_images, collected_labels, s3)

    s4 = DatasetStats()
    process_taco(collected_images, collected_labels, s4)

    s5 = DatasetStats()
    process_manhole(collected_images, collected_labels, s5)

    if not collected_images:
        safe_print(f"\n[ERROR] No images collected!")
        sys.exit(1)

    tc, vc = write_final_dataset(collected_images, collected_labels,
                                  val_ratio=args.val_ratio, seed=args.seed)
    yaml_path = write_dataset_yaml()

    # Summary
    safe_print(f"\n{'='*60}")
    safe_print(f"FINAL SUMMARY")
    safe_print(f"{'='*60}")

    total_cc = defaultdict(int)
    total_img = total_ann = 0
    for name, st in [("Smartathon", s1), ("Andrew", s2), ("RDD 2022", s3), ("TACO", s4), ("Manhole", s5)]:
        safe_print(f"\n  {name}:")
        safe_print(f"    Images: {st.images_processed}, Skipped: {st.images_skipped}")
        safe_print(f"    Annotations: kept={st.annotations_kept}, removed={st.annotations_removed}")
        total_img += st.images_processed
        total_ann += st.annotations_kept
        for cid, cnt in st.class_counts.items():
            total_cc[cid] += cnt

    safe_print(f"\n  --- Combined ---")
    safe_print(f"  Total images:      {total_img}")
    safe_print(f"  Total annotations: {total_ann}")
    safe_print(f"  Train / Val:       {tc} / {vc}")
    safe_print(f"\n  Class distribution:")
    for cid in sorted(FINAL_CLASSES.keys()):
        nm = FINAL_CLASSES[cid]
        cnt = total_cc.get(cid, 0)
        pct = cnt / total_ann * 100 if total_ann > 0 else 0
        bar = "#" * int(pct / 2)
        safe_print(f"    {cid}: {nm:10s} {cnt:6d} ({pct:5.1f}%) {bar}")

    missing = [FINAL_CLASSES[i] for i in range(NUM_CLASSES) if total_cc.get(i, 0) == 0]
    if missing:
        safe_print(f"\n  [WARNING] Missing classes (0 annotations): {missing}")
        if "manhole" in missing:
            safe_print(f"\n  [INFO] MANHOLE DATA NEEDED!")
            safe_print(f"  Download from Roboflow (free, no API key needed):")
            safe_print(f"    https://universe.roboflow.com/manhole-jyxfj/manhole-cover-jyxfj")
            safe_print(f"  Steps:")
            safe_print(f"    1. Click 'Download Dataset' -> YOLOv8 format")
            safe_print(f"    2. Extract to: data/datasets/raw/manhole/")
            safe_print(f"    3. Re-run this script")

    safe_print(f"\n  Dataset YAML: {yaml_path}")
    if not missing:
        safe_print(f"\n  [OK] Dataset ready for training!")
        safe_print(f"  Run: cd backend && python -m ai.models.train")
    else:
        safe_print(f"\n  [WARN] Fix missing classes before training for best results.")
        safe_print(f"  You CAN still train with available classes (pothole + crack + garbage).")


if __name__ == "__main__":
    main()
