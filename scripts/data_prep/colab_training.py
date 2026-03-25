"""
StreetSense — Google Colab Training Notebook

If you don't have a local GPU, use this notebook on Google Colab
for free GPU-accelerated training.

Steps:
1. Open Google Colab: https://colab.research.google.com
2. Upload this file or copy-paste into cells
3. Runtime → Change runtime type → T4 GPU
4. Run all cells

Each section below represents one Colab cell.
Separate cells with: # --- CELL --- comments
"""

# ============================================================
# CELL 1: Setup Environment
# ============================================================
# !pip install ultralytics roboflow
# import torch
# print(f"PyTorch: {torch.__version__}")
# print(f"CUDA available: {torch.cuda.is_available()}")
# if torch.cuda.is_available():
#     print(f"GPU: {torch.cuda.get_device_name(0)}")

# ============================================================
# CELL 2: Download Datasets
# ============================================================
# from roboflow import Roboflow
#
# API_KEY = "YOUR_ROBOFLOW_API_KEY"  # ← Replace this
# rf = Roboflow(api_key=API_KEY)
#
# # Download all 4 datasets
# datasets = {
#     "pothole": ("atharva-deshmukh", "road-pothole", 1),
#     "crack": ("university-bswxt", "road-crack-detection-ss5go", 1),
#     "garbage": ("divya-lzcld", "garbage-detection-q3vcn", 1),
#     "manhole": ("manhole-detector", "manhole-detection-4hwfb", 1),
# }
#
# for name, (ws, proj, ver) in datasets.items():
#     print(f"Downloading {name}...")
#     project = rf.workspace(ws).project(proj)
#     dataset = project.version(ver).download("yolov8", location=f"/content/raw/{name}")

# ============================================================
# CELL 3: Upload merge script and run it
# ============================================================
# Upload merge_datasets.py from scripts/data_prep/ or run inline:
#
# !mkdir -p /content/streetsense/images/train /content/streetsense/images/val
# !mkdir -p /content/streetsense/labels/train /content/streetsense/labels/val
#
# # (Run the merge logic from merge_datasets.py here)
# # Or upload the script:
# # from google.colab import files
# # uploaded = files.upload()  # Upload merge_datasets.py

# ============================================================
# CELL 4: Create dataset.yaml
# ============================================================
# dataset_yaml = """
# path: /content/streetsense
# train: images/train
# val: images/val
#
# nc: 4
# names:
#   0: pothole
#   1: crack
#   2: garbage
#   3: manhole
# """
#
# with open("/content/dataset.yaml", "w") as f:
#     f.write(dataset_yaml)

# ============================================================
# CELL 5: Train YOLOv8
# ============================================================
# from ultralytics import YOLO
#
# model = YOLO("yolov8s.pt")  # Use 'small' model on Colab
#
# results = model.train(
#     data="/content/dataset.yaml",
#     epochs=100,
#     batch=16,
#     imgsz=640,
#     patience=20,
#     device=0,
#     project="/content/runs",
#     name="streetsense_v1",
#     # Augmentation
#     mosaic=1.0,
#     mixup=0.1,
#     flipud=0.5,
#     fliplr=0.5,
#     degrees=10.0,
#     scale=0.5,
# )

# ============================================================
# CELL 6: Validate
# ============================================================
# model = YOLO("/content/runs/streetsense_v1/weights/best.pt")
# results = model.val(data="/content/dataset.yaml")
# print(f"mAP@50: {results.results_dict['metrics/mAP50(B)']:.4f}")

# ============================================================
# CELL 7: Download Weights
# ============================================================
# from google.colab import files
# files.download("/content/runs/streetsense_v1/weights/best.pt")
# # Save this as: backend/ai/weights/best.pt
