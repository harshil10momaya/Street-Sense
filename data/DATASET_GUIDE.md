# StreetSense — Dataset Preparation Guide

## Overview

We need labeled images for 4 classes: **pothole**, **crack**, **garbage**, **manhole**.
All annotations must be in YOLO format:

```
<class_id> <x_center> <y_center> <width> <height>
```

Values are normalized (0.0 — 1.0) relative to image dimensions.

---

## Recommended Datasets

### 1. Potholes (Class 0)
- **Roboflow**: https://universe.roboflow.com/atharva-deshmukh/road-pothole/dataset/1
  - Download in "YOLOv8" format
  - ~1500 images with bounding boxes
- **Alternative (Kaggle)**: https://www.kaggle.com/datasets/sachinpatel21/pothole-image-dataset

### 2. Cracks (Class 1)  
- **Roboflow**: https://universe.roboflow.com/university-bswxt/road-crack-detection-ss5go/dataset/1
  - Download in "YOLOv8" format
  - ~1200 images
- **Alternative**: https://universe.roboflow.com/crack-bphdr/crack-detection-uo7a9

### 3. Garbage / Litter (Class 2)
- **Roboflow**: https://universe.roboflow.com/divya-lzcld/garbage-detection-q3vcn/dataset/1
  - Download in "YOLOv8" format
  - ~800 images
- **Alternative (TACO)**: http://tacodataset.org/ (larger, needs COCO→YOLO conversion)

### 4. Manholes (Class 3)
- **Roboflow**: https://universe.roboflow.com/manhole-detector/manhole-detection-4hwfb/dataset/1
  - Download in "YOLOv8" format
  - ~600 images
- **Alternative**: https://universe.roboflow.com/new-workspace-u15bo/manhole-cover-jyxfj

---

## Download Steps (Roboflow — Recommended)

### Option A: Roboflow Web UI
1. Go to the dataset URL above
2. Click "Download Dataset"
3. Select format: **YOLOv8**
4. Choose "download zip"
5. Extract into: `data/datasets/raw/<classname>/`

### Option B: Roboflow Python API (automated)
```bash
pip install roboflow
```
```python
from roboflow import Roboflow

# Get your API key from https://app.roboflow.com/settings/api
rf = Roboflow(api_key="YOUR_API_KEY")

# Example: Download pothole dataset
project = rf.workspace("atharva-deshmukh").project("road-pothole")
dataset = project.version(1).download("yolov8", location="data/datasets/raw/pothole")
```

### Option C: Quick Start with the merge script
After downloading all 4 datasets into `data/datasets/raw/`, run:
```bash
cd streetsense
python scripts/data_prep/merge_datasets.py
```

---

## Expected Raw Structure After Download

```
data/datasets/raw/
├── pothole/
│   ├── train/
│   │   ├── images/
│   │   └── labels/
│   ├── valid/
│   │   ├── images/
│   │   └── labels/
│   └── test/    (optional)
├── crack/
│   ├── train/images/  labels/
│   ├── valid/images/  labels/
├── garbage/
│   ├── train/images/  labels/
│   ├── valid/images/  labels/
└── manhole/
    ├── train/images/  labels/
    └── valid/images/  labels/
```

---

## After Download

Run these scripts in order:

1. `python scripts/data_prep/merge_datasets.py` — Merges all datasets, remaps class IDs
2. `python scripts/data_prep/validate_dataset.py` — Checks for errors
3. `python scripts/data_prep/analyze_dataset.py` — Prints class distribution stats

Then proceed to training:
```bash
cd backend
python -m ai.models.train
```
