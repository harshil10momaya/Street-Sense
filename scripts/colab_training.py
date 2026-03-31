# ============================================================
# StreetSense -- YOLOv8 Training on Google Colab
# ============================================================
#
# Instructions:
#   1. Open https://colab.research.google.com
#   2. File -> New Notebook
#   3. Runtime -> Change runtime type -> T4 GPU
#   4. Copy each CELL section below into separate Colab cells
#   5. Run them in order
#
# Prerequisites:
#   - streetsense_dataset.zip uploaded to Google Drive root
#   - Contains: images/train, images/val, labels/train, labels/val, dataset.yaml
# ============================================================


# %%
# ====================
# CELL 1: Check GPU
# ====================
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
else:
    print("WARNING: No GPU detected! Go to Runtime -> Change runtime type -> T4 GPU")


# %%
# ====================
# CELL 2: Install dependencies
# ====================
!pip install ultralytics --quiet
print("Ultralytics installed!")


# %%
# ====================
# CELL 3: Mount Google Drive
# ====================
from google.colab import drive
drive.mount('/content/drive')

# Check if dataset zip exists
import os
zip_path = '/content/drive/MyDrive/streetsense_dataset.zip'
if os.path.exists(zip_path):
    size_gb = os.path.getsize(zip_path) / 1e9
    print(f"Dataset found: {zip_path} ({size_gb:.2f} GB)")
else:
    print(f"ERROR: {zip_path} not found!")
    print("Upload streetsense_dataset.zip to your Google Drive root folder.")
    print("If it's in a subfolder, update zip_path above.")


# %%
# ====================
# CELL 4: Extract dataset
# ====================
import zipfile
import time

zip_path = '/content/drive/MyDrive/streetsense_dataset.zip'
extract_dir = '/content/streetsense_dataset'

# Clean if exists
if os.path.exists(extract_dir):
    !rm -rf {extract_dir}

os.makedirs(extract_dir, exist_ok=True)

print("Extracting dataset (this may take a few minutes)...")
start = time.time()

with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(extract_dir)

elapsed = time.time() - start
print(f"Extracted in {elapsed:.1f} seconds")

# Show structure
!find {extract_dir} -maxdepth 3 -type d | head -20
print()
!find {extract_dir} -name "*.jpg" | wc -l
print("images found ^")


# %%
# ====================
# CELL 5: Create dataset.yaml with correct paths
# ====================
import yaml

# Detect the actual structure (might have extra nesting)
dataset_root = extract_dir

# Check if images/train exists directly or in a subfolder
if os.path.exists(os.path.join(dataset_root, 'images', 'train')):
    pass  # Already correct
elif os.path.exists(os.path.join(dataset_root, 'streetsense', 'images', 'train')):
    dataset_root = os.path.join(extract_dir, 'streetsense')
else:
    # Search for the images/train directory
    for root, dirs, files in os.walk(extract_dir):
        if 'images' in dirs:
            img_dir = os.path.join(root, 'images')
            if os.path.exists(os.path.join(img_dir, 'train')):
                dataset_root = root
                break

print(f"Dataset root: {dataset_root}")

# Count images
train_imgs = len([f for f in os.listdir(os.path.join(dataset_root, 'images', 'train'))
                   if f.endswith(('.jpg', '.jpeg', '.png'))])
val_imgs = len([f for f in os.listdir(os.path.join(dataset_root, 'images', 'val'))
                 if f.endswith(('.jpg', '.jpeg', '.png'))])

print(f"Train images: {train_imgs}")
print(f"Val images:   {val_imgs}")

# Write dataset.yaml with absolute Colab paths
dataset_yaml = {
    'path': dataset_root,
    'train': 'images/train',
    'val': 'images/val',
    'nc': 4,
    'names': {
        0: 'pothole',
        1: 'crack',
        2: 'manhole',
        3: 'garbage',
    }
}

yaml_path = os.path.join(dataset_root, 'dataset.yaml')
with open(yaml_path, 'w') as f:
    yaml.dump(dataset_yaml, f, default_flow_style=False)

print(f"\nDataset YAML written to: {yaml_path}")
print(f"\nContents:")
!cat {yaml_path}


# %%
# ====================
# CELL 6: Train YOLOv8
# ====================
from ultralytics import YOLO

# Load pretrained YOLOv8 small model (good balance of speed + accuracy)
model = YOLO('yolov8s.pt')

# Train
results = model.train(
    data=yaml_path,
    epochs=100,
    batch=16,            # Reduce to 8 if OOM on T4
    imgsz=640,
    patience=20,         # Early stopping
    device=0,            # GPU

    # Optimizer
    optimizer='auto',
    lr0=0.01,
    lrf=0.01,
    weight_decay=0.0005,
    warmup_epochs=3,

    # Augmentation (important for class imbalance)
    mosaic=1.0,
    mixup=0.15,
    copy_paste=0.1,
    flipud=0.5,
    fliplr=0.5,
    degrees=10.0,
    translate=0.1,
    scale=0.5,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,

    # Loss
    box=7.5,
    cls=0.5,
    dfl=1.5,

    # Output
    project='/content/runs',
    name='streetsense_v1',
    exist_ok=True,
    save=True,
    save_period=10,
    plots=True,
    verbose=True,
)

print("\nTraining complete!")


# %%
# ====================
# CELL 7: Validate model
# ====================
model = YOLO('/content/runs/streetsense_v1/weights/best.pt')
results = model.val(data=yaml_path, imgsz=640, conf=0.25)

metrics = results.results_dict
print(f"\n{'='*60}")
print(f"VALIDATION RESULTS")
print(f"{'='*60}")
print(f"  mAP@50:      {metrics.get('metrics/mAP50(B)', 0):.4f}")
print(f"  mAP@50:95:   {metrics.get('metrics/mAP50-95(B)', 0):.4f}")
print(f"  Precision:   {metrics.get('metrics/precision(B)', 0):.4f}")
print(f"  Recall:      {metrics.get('metrics/recall(B)', 0):.4f}")

# Per-class
class_names = ['pothole', 'crack', 'manhole', 'garbage']
if hasattr(results, 'box') and hasattr(results.box, 'maps'):
    print(f"\n  Per-Class mAP@50:")
    for i, name in enumerate(class_names):
        if i < len(results.box.maps):
            print(f"    {name:10s}: {results.box.maps[i]:.4f}")


# %%
# ====================
# CELL 8: Show training results
# ====================
from IPython.display import Image, display

results_dir = '/content/runs/streetsense_v1'

# Training curves
if os.path.exists(f'{results_dir}/results.png'):
    print("Training curves:")
    display(Image(filename=f'{results_dir}/results.png', width=900))

# Confusion matrix
if os.path.exists(f'{results_dir}/confusion_matrix.png'):
    print("\nConfusion matrix:")
    display(Image(filename=f'{results_dir}/confusion_matrix.png', width=600))

# Sample predictions
for img_name in ['val_batch0_pred.jpg', 'val_batch1_pred.jpg']:
    path = f'{results_dir}/{img_name}'
    if os.path.exists(path):
        print(f"\n{img_name}:")
        display(Image(filename=path, width=900))


# %%
# ====================
# CELL 9: Test on sample images
# ====================
import glob

model = YOLO('/content/runs/streetsense_v1/weights/best.pt')

# Pick 5 random validation images
val_images = glob.glob(os.path.join(dataset_root, 'images', 'val', '*.jpg'))[:5]

for img_path in val_images:
    results = model.predict(img_path, conf=0.25, save=True,
                            project='/content/runs', name='test_predictions', exist_ok=True)
    print(f"\n{os.path.basename(img_path)}:")
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = class_names[cls_id] if cls_id < len(class_names) else f"class_{cls_id}"
            print(f"  {name}: {conf:.3f}")

# Show annotated images
test_dir = '/content/runs/test_predictions'
if os.path.exists(test_dir):
    for img in sorted(glob.glob(f'{test_dir}/*.jpg'))[:5]:
        display(Image(filename=img, width=600))


# %%
# ====================
# CELL 10: Download best weights
# ====================
from google.colab import files
import shutil

# Copy best weights to Drive for safekeeping
weights_src = '/content/runs/streetsense_v1/weights/best.pt'
weights_drive = '/content/drive/MyDrive/streetsense_best.pt'

if os.path.exists(weights_src):
    shutil.copy2(weights_src, weights_drive)
    print(f"Best weights saved to Google Drive: {weights_drive}")
    
    # Also copy last weights
    last_src = '/content/runs/streetsense_v1/weights/last.pt'
    if os.path.exists(last_src):
        shutil.copy2(last_src, '/content/drive/MyDrive/streetsense_last.pt')
    
    # Download to local machine
    print("\nDownloading best.pt to your computer...")
    files.download(weights_src)
    print("\nSave this file as: backend/ai/weights/best.pt")
else:
    print("ERROR: best.pt not found. Training may have failed.")


# %%
# ====================
# CELL 11: Export to ONNX (optional, for faster inference)
# ====================
# model = YOLO('/content/runs/streetsense_v1/weights/best.pt')
# model.export(format='onnx', imgsz=640, simplify=True)
# print("ONNX model exported!")
# files.download('/content/runs/streetsense_v1/weights/best.onnx')
