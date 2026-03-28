# ============================================
# StreetSense AI - Full Training Script
# YOLOv8 Road Damage Detection
# ============================================

# ====================
# 1. Install Dependencies
# ====================
print("Installing dependencies...")

#!pip install ultralytics --quiet

# ====================
# 2. Imports
# ====================
from ultralytics import YOLO
import os
import shutil
from google.colab import drive
from PIL import Image
import matplotlib.pyplot as plt

# ====================
# 3. Mount Google Drive
# ====================
print("Mounting Google Drive...")
drive.mount('/content/drive')

# ====================
# 4. Dataset Path
# ====================

dataset_path = "/content/streetsense_dataset"
yaml_path = "/content/streetsense_dataset/data.yaml"

print("Dataset Path:", dataset_path)

# ====================
# 5. Load Model
# ====================

print("Loading YOLOv8 model...")
model = YOLO("yolov8n.pt")

# ====================
# 6. Train Model
# ====================

print("Starting training...")

model.train(
    data=yaml_path,
    epochs=30,
    imgsz=640,
    batch=8,
    name="streetsense_v1",
    project="/content/runs"
)

print("Training Complete")

# ====================
# 7. Save Model Immediately
# ====================

best_model_path = "/content/runs/streetsense_v1/weights/best.pt"

drive_save_path = "/content/drive/MyDrive/StreetSense/best.pt"

os.makedirs("/content/drive/MyDrive/StreetSense", exist_ok=True)

shutil.copy(best_model_path, drive_save_path)

print("Model saved to Google Drive")
print(drive_save_path)

# ====================
# 8. Validation
# ====================

print("Running validation...")

model = YOLO(best_model_path)

results = model.val(
    data=yaml_path,
    imgsz=640,
    conf=0.25
)

print("Validation Complete")
print("mAP50:", results.box.map50)
print("mAP50-95:", results.box.map)

# ====================
# 9. Test Predictions
# ====================

print("Running test predictions...")

test_folder = "/content/streetsense_dataset/images/val"

test_images = os.listdir(test_folder)[:5]

for img in test_images:

    img_path = os.path.join(test_folder, img)

    model.predict(
        source=img_path,
        conf=0.25,
        save=True
    )

print("Predictions Complete")

# ====================
# 10. Show Predictions
# ====================

print("Displaying predictions...")

pred_folder = "/content/runs/detect/predict"

for img in os.listdir(pred_folder)[:5]:

    img_path = os.path.join(pred_folder, img)

    display(Image.open(img_path))

# ====================
# 11. Download Model
# ====================

print("Final model location:")
print(best_model_path)

print("\nTraining Pipeline Complete 🚀")