# ============================================================
# StreetSense — YOLOv8 Training on Google Colab
# ============================================================
#
# INSTRUCTIONS:
# 1. Open Google Colab: https://colab.research.google.com
# 2. Runtime → Change runtime type → T4 GPU
# 3. Upload your processed dataset (streetsense.zip)
# 4. Run each cell in order
#
# Your dataset should be the ALREADY PROCESSED one from:
#   D:\streetsense\data\datasets\streetsense\
#
# Zip it on your PC:
#   Right-click "streetsense" folder → Send to → Compressed (zipped) folder
#   Or in terminal: cd D:\streetsense\data\datasets && tar -czf streetsense_dataset.tar.gz streetsense/
#
# ============================================================

# %% [markdown]
# ## Cell 1: Check GPU & Install Dependencies

# %%
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
else:
    print("WARNING: No GPU detected! Go to Runtime → Change runtime type → T4 GPU")

# Install ultralytics
# !pip install -q ultralytics

# %% [markdown]
# ## Cell 2: Upload Dataset
# 
# **Option A: Upload ZIP directly (small datasets < 1GB)**
# 
# **Option B: Upload to Google Drive first (recommended for large datasets)**

# %%
# === OPTION A: Direct upload ===
# from google.colab import files
# uploaded = files.upload()  # Select your streetsense_dataset.tar.gz or streetsense.zip

# === OPTION B: Google Drive (RECOMMENDED for 29K images) ===
from google.colab import drive
drive.mount('/content/drive')

# After mounting, upload streetsense_dataset.tar.gz to your Google Drive root
# Then it will be at: /content/drive/MyDrive/streetsense_dataset.tar.gz

# %% [markdown]
# ## Cell 3: Extract Dataset

# %%
import os
import shutil

# Clean any previous extraction
if os.path.exists('/content/streetsense'):
    shutil.rmtree('/content/streetsense')

# Extract from Google Drive (Option B)
# Change the path if you put it in a subfolder
DATASET_SOURCE = '/content/drive/MyDrive/streetsense_dataset.tar.gz'

if DATASET_SOURCE.endswith('.tar.gz'):
    os.system(f'tar -xzf "{DATASET_SOURCE}" -C /content/')
elif DATASET_SOURCE.endswith('.zip'):
    os.system(f'unzip -q "{DATASET_SOURCE}" -d /content/')

# Verify extraction
dataset_dir = '/content/streetsense'
if not os.path.exists(dataset_dir):
    # Maybe extracted into a subdirectory
    for d in os.listdir('/content/'):
        check = f'/content/{d}'
        if os.path.isdir(check) and os.path.exists(f'{check}/images/train'):
            dataset_dir = check
            break

print(f"Dataset directory: {dataset_dir}")
print(f"Contents: {os.listdir(dataset_dir)}")

# Count images
train_imgs = len(os.listdir(f'{dataset_dir}/images/train'))
val_imgs = len(os.listdir(f'{dataset_dir}/images/val'))
print(f"\nTrain images: {train_imgs}")
print(f"Val images:   {val_imgs}")
print(f"Total:        {train_imgs + val_imgs}")

# %% [markdown]
# ## Cell 4: Create dataset.yaml

# %%
dataset_yaml = f"""# StreetSense Dataset Configuration
path: {dataset_dir}
train: images/train
val: images/val

nc: 4

names:
  0: pothole
  1: crack
  2: manhole
  3: garbage
"""

yaml_path = f'{dataset_dir}/dataset.yaml'
with open(yaml_path, 'w') as f:
    f.write(dataset_yaml)

print(f"Dataset YAML written to: {yaml_path}")
print(dataset_yaml)

# %% [markdown]
# ## Cell 5: Verify Label Distribution

# %%
from collections import Counter
import os

class_names = {0: 'pothole', 1: 'crack', 2: 'manhole', 3: 'garbage'}
class_counts = Counter()

label_dir = f'{dataset_dir}/labels/train'
for label_file in os.listdir(label_dir):
    if not label_file.endswith('.txt'):
        continue
    with open(f'{label_dir}/{label_file}') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                cls_id = int(parts[0])
                class_counts[cls_id] += 1

print("Training set class distribution:")
print("=" * 40)
total = sum(class_counts.values())
for cls_id in sorted(class_names.keys()):
    count = class_counts.get(cls_id, 0)
    pct = count / total * 100 if total > 0 else 0
    bar = '#' * int(pct / 2)
    print(f"  {cls_id}: {class_names[cls_id]:10s} {count:6d} ({pct:5.1f}%) {bar}")
print(f"\nTotal annotations: {total}")

# %% [markdown]
# ## Cell 6: Train YOLOv8
# 
# **Model choices:**
# - `yolov8n.pt` — Nano (fastest, least accurate)
# - `yolov8s.pt` — Small (good balance) ← **RECOMMENDED**
# - `yolov8m.pt` — Medium (better accuracy, slower)
# - `yolov8l.pt` — Large (high accuracy, needs more VRAM)

# %%
from ultralytics import YOLO

# Load pretrained model
model = YOLO('yolov8s.pt')  # Change to yolov8m.pt for better accuracy

# Train
results = model.train(
    data=yaml_path,
    epochs=100,
    batch=16,             # Reduce to 8 if OOM error
    imgsz=640,
    patience=20,          # Early stopping
    device=0,             # GPU
    workers=2,            # Colab has limited CPU
    project='/content/runs',
    name='streetsense_v1',
    exist_ok=True,
    # Augmentation (important for class imbalance)
    mosaic=1.0,
    mixup=0.15,           # Slightly higher for imbalanced classes
    copy_paste=0.1,
    flipud=0.5,
    fliplr=0.5,
    degrees=10.0,
    translate=0.1,
    scale=0.5,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    # Loss weights
    box=7.5,
    cls=0.5,
    dfl=1.5,
    # Save
    save=True,
    save_period=10,
    plots=True,
    verbose=True,
)

# %% [markdown]
# ## Cell 7: Validate Model

# %%
# Load best weights
best_model = YOLO('/content/runs/streetsense_v1/weights/best.pt')

# Validate
val_results = best_model.val(
    data=yaml_path,
    imgsz=640,
    conf=0.25,
    iou=0.45,
    device=0,
    plots=True,
    verbose=True,
)

# Print results
print("\n" + "=" * 60)
print("VALIDATION RESULTS")
print("=" * 60)
metrics = val_results.results_dict
print(f"  mAP@50:      {metrics.get('metrics/mAP50(B)', 0):.4f}")
print(f"  mAP@50:95:   {metrics.get('metrics/mAP50-95(B)', 0):.4f}")
print(f"  Precision:   {metrics.get('metrics/precision(B)', 0):.4f}")
print(f"  Recall:      {metrics.get('metrics/recall(B)', 0):.4f}")

# %% [markdown]
# ## Cell 8: View Training Results

# %%
from IPython.display import Image, display
import os

results_dir = '/content/runs/streetsense_v1'

# Show training curves
if os.path.exists(f'{results_dir}/results.png'):
    display(Image(filename=f'{results_dir}/results.png', width=900))

# Show confusion matrix
if os.path.exists(f'{results_dir}/confusion_matrix.png'):
    display(Image(filename=f'{results_dir}/confusion_matrix.png', width=600))

# Show sample predictions
for img_name in ['val_batch0_pred.jpg', 'val_batch1_pred.jpg']:
    path = f'{results_dir}/{img_name}'
    if os.path.exists(path):
        print(f"\n{img_name}:")
        display(Image(filename=path, width=800))

# %% [markdown]
# ## Cell 9: Test on Sample Images

# %%
import glob
import random

# Pick random validation images
val_images = glob.glob(f'{dataset_dir}/images/val/*.jpg')
if not val_images:
    val_images = glob.glob(f'{dataset_dir}/images/val/*.png')

if val_images:
    test_images = random.sample(val_images, min(5, len(val_images)))

    best_model = YOLO('/content/runs/streetsense_v1/weights/best.pt')
    results = best_model.predict(
        source=test_images,
        conf=0.4,
        save=True,
        project='/content/runs',
        name='test_predictions',
        exist_ok=True,
    )

    # Show results
    for img_path in glob.glob('/content/runs/test_predictions/*.jpg')[:5]:
        display(Image(filename=img_path, width=600))
else:
    print("No validation images found")

# %% [markdown]
# ## Cell 10: Download Trained Weights
# 
# **IMPORTANT: Download best.pt to your PC!**
# Save it to: `D:\streetsense\backend\ai\weights\best.pt`

# %%
from google.colab import files

weights_path = '/content/runs/streetsense_v1/weights/best.pt'
if os.path.exists(weights_path):
    size_mb = os.path.getsize(weights_path) / 1024 / 1024
    print(f"Best weights: {weights_path}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"\nDownloading...")
    files.download(weights_path)
    print(f"\nSave this file to: D:\\streetsense\\backend\\ai\\weights\\best.pt")
else:
    print("Weights not found! Check training output.")

# Also download last.pt as backup
last_path = '/content/runs/streetsense_v1/weights/last.pt'
if os.path.exists(last_path):
    files.download(last_path)
