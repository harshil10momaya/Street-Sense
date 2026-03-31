"""
StreetSense -- Dataset Configuration

Single source of truth for all dataset info, class mappings, and cleaning rules.
"""

from pathlib import Path

# -- Project Paths --
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "datasets" / "raw"
OUTPUT_DIR = DATA_DIR / "datasets" / "streetsense"

# -- Final Target Classes (EXACTLY 4) --
FINAL_CLASSES = {
    0: "pothole",
    1: "crack",
    2: "manhole",
    3: "garbage",
}

CLASS_NAME_TO_ID = {v: k for k, v in FINAL_CLASSES.items()}
NUM_CLASSES = len(FINAL_CLASSES)

IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


# ============================================================
# DATASET 1: Smartathon (Roboflow) -- Potholes + Manholes
# ============================================================
# Source: https://universe.roboflow.com/smartathon/new-pothole-detection
# Format: YOLO (from Roboflow export)

SMARTATHON_CONFIG = {
    "name": "smartathon",
    "raw_dir": RAW_DIR / "smartathon",
    "format": "yolo",
    "roboflow": {
        "workspace": "smartathon",
        "project": "new-pothole-detection",
        "version": 1,
    },
    "label_map": {
        "pothole": "pothole",
        "Pothole": "pothole",
        "potholes": "pothole",
        "POTHOLE": "pothole",
        "manhole": "manhole",
        "Manhole": "manhole",
        "object": None,
        "Object": None,
        "unknown": None,
        "Unknown": None,
    },
    "fuzzy_rules": [
        (["pothole", "pot", "hole"], "pothole"),
        (["manhole", "man", "cover"], "manhole"),
    ],
}


# ============================================================
# DATASET 2: Andrew Pothole (Kaggle) -- Potholes
# ============================================================
# Source: https://www.kaggle.com/datasets/andrewmvd/pothole-detection
# Format: Pascal VOC (XML)

ANDREW_CONFIG = {
    "name": "andrew_pothole",
    "raw_dir": RAW_DIR / "andrew_pothole",
    "format": "voc",
    "kaggle": {"dataset": "andrewmvd/pothole-detection"},
    "label_map": {
        "pothole": "pothole",
        "Pothole": "pothole",
    },
}


# ============================================================
# DATASET 3: RDD 2022 (Kaggle) -- Road Cracks
# ============================================================
# Source: https://www.kaggle.com/datasets/sovitrath/rdd2022-road-damage-detection-dataset
# Format: YOLO (pre-split by sovitrath)
#
# The Kaggle version has YOLO .txt labels with class IDs:
#   0: D00 (construction joint) -> REMOVE
#   1: D10 (longitudinal crack) -> crack
#   2: D20 (transverse crack) -> crack
#   3: D40 (alligator crack) -> crack

RDD2022_CONFIG = {
    "name": "rdd2022",
    "raw_dir": RAW_DIR / "rdd2022",
    "format": "yolo",  # Pre-converted YOLO format from Kaggle
    "kaggle": {"dataset": "sovitrath/rdd2022-road-damage-detection-dataset"},
    "label_map": {
        "D10": "crack",
        "D20": "crack",
        "D40": "crack",
        "D00": None,  # REMOVE
    },
    # YOLO class ID remapping (source_id -> our_class_name)
    "yolo_remap": {
        0: None,      # D00 -> REMOVE
        1: "crack",   # D10 -> crack
        2: "crack",   # D20 -> crack
        3: "crack",   # D40 -> crack
    },
}


# ============================================================
# DATASET 4: TACO (Kaggle) -- Garbage
# ============================================================
# Source: https://www.kaggle.com/datasets/kneroma/tacotrashdataset
# Format: COCO JSON

TACO_CONFIG = {
    "name": "taco",
    "raw_dir": RAW_DIR / "taco",
    "format": "coco",
    "kaggle": {"dataset": "kneroma/tacotrashdataset"},
    "target_class": "garbage",
}


# ============================================================
# DATASET 5: Manhole (Roboflow) -- Manholes
# ============================================================
# Source: https://universe.roboflow.com/workspace-an3qw/manhole-cover-byh6y
# Format: YOLO (from Roboflow export as YOLOv8)
# Download: YOLOv8 format -> extract to raw/manhole/
#
# Known class names from this dataset:
#   "manhole cover", "Manhole Cover", "manhole", "Manhole"
# ALL -> manhole (class 2)

MANHOLE_CONFIG = {
    "name": "manhole",
    "raw_dir": RAW_DIR / "manhole",
    "format": "yolo",
    "target_class": "manhole",
    "roboflow_url": "https://universe.roboflow.com/workspace-an3qw/manhole-cover-byh6y",
    # Label normalization: all variants -> manhole
    "label_variants": [
        "manhole cover", "Manhole Cover", "manhole_cover",
        "manhole", "Manhole", "MANHOLE",
        "cover", "Cover", "drain", "Drain",
    ],
}


# ============================================================
# All datasets in processing order
# ============================================================
ALL_DATASETS = [
    SMARTATHON_CONFIG,
    ANDREW_CONFIG,
    RDD2022_CONFIG,
    TACO_CONFIG,
    MANHOLE_CONFIG,
]
