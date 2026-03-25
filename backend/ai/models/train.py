"""
StreetSense — YOLOv8 Training Script

Trains a YOLOv8 model on the merged StreetSense dataset.
Handles:
- Model selection (nano → xlarge)
- Custom hyperparameters from config
- Training with early stopping
- Automatic best weight saving
- Training metrics logging

Usage:
    cd backend
    python -m ai.models.train
    python -m ai.models.train --model yolov8s.pt --epochs 150 --batch 8
"""

import argparse
import shutil
import sys
from pathlib import Path

# Resolve paths
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

DATASET_YAML = BACKEND_DIR / "ai" / "config" / "dataset.yaml"
WEIGHTS_DIR = BACKEND_DIR / "ai" / "weights"
RUNS_DIR = BACKEND_DIR / "runs"


def check_dataset():
    """Verify dataset exists before training."""
    dataset_dir = ROOT_DIR / "data" / "datasets" / "streetsense"
    train_dir = dataset_dir / "images" / "train"

    if not train_dir.exists():
        print("❌ Training images not found!")
        print(f"   Expected: {train_dir}")
        print(f"\n   Steps to fix:")
        print(f"   1. Download datasets (see data/DATASET_GUIDE.md)")
        print(f"   2. Run: python scripts/data_prep/merge_datasets.py")
        print(f"   3. Run: python scripts/data_prep/validate_dataset.py")
        return False

    image_count = len(list(train_dir.glob("*")))
    if image_count < 10:
        print(f"⚠️  Only {image_count} training images found. Need at least 50+")
        return False

    print(f"✅ Dataset found: {image_count} training images")
    return True


def check_dataset_yaml():
    """Verify and fix dataset.yaml paths."""
    if not DATASET_YAML.exists():
        print(f"❌ Dataset config not found: {DATASET_YAML}")
        return False

    # Read and update path to absolute
    content = DATASET_YAML.read_text()
    abs_dataset_path = str(ROOT_DIR / "data" / "datasets" / "streetsense")

    # Replace relative path with absolute path for training
    updated = []
    for line in content.split("\n"):
        if line.startswith("path:"):
            updated.append(f"path: {abs_dataset_path}")
        else:
            updated.append(line)

    DATASET_YAML.write_text("\n".join(updated))
    print(f"✅ Dataset YAML updated with absolute path")
    return True


def train(
    model_name: str = "yolov8n.pt",
    epochs: int = 100,
    batch: int = 16,
    imgsz: int = 640,
    patience: int = 20,
    device: str = "",
    resume: bool = False,
    workers: int = 8,
):
    """Run YOLOv8 training."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ Ultralytics not installed!")
        print("   Run: pip install ultralytics")
        sys.exit(1)

    print("=" * 60)
    print("StreetSense — YOLOv8 Training")
    print("=" * 60)

    # Checks
    if not check_dataset():
        sys.exit(1)
    if not check_dataset_yaml():
        sys.exit(1)

    # Auto-detect device
    if not device:
        import torch
        if torch.cuda.is_available():
            device = "0"
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1e9
            print(f"🖥️  GPU detected: {gpu_name} ({gpu_mem:.1f} GB)")
        else:
            device = "cpu"
            print("⚠️  No GPU found — training on CPU (will be very slow!)")
            print("   Consider using Google Colab with free GPU")

    # Adjust batch size for CPU
    if device == "cpu" and batch > 8:
        batch = 4
        print(f"   Reduced batch size to {batch} for CPU training")

    print(f"\n  Model:     {model_name}")
    print(f"  Epochs:    {epochs}")
    print(f"  Batch:     {batch}")
    print(f"  Image size: {imgsz}")
    print(f"  Patience:  {patience}")
    print(f"  Device:    {device}")
    print(f"  Dataset:   {DATASET_YAML}")
    print()

    # Load model
    model = YOLO(model_name)

    # Train
    results = model.train(
        data=str(DATASET_YAML),
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        patience=patience,
        device=device,
        workers=workers,
        project=str(RUNS_DIR / "detect"),
        name="streetsense_v1",
        exist_ok=True,
        resume=resume,
        # Augmentation
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        flipud=0.5,
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.1,
        # Loss
        box=7.5,
        cls=0.5,
        dfl=1.5,
        # Output
        save=True,
        save_period=10,
        plots=True,
        verbose=True,
    )

    # Copy best weights to our weights directory
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    best_weight_src = RUNS_DIR / "detect" / "streetsense_v1" / "weights" / "best.pt"
    last_weight_src = RUNS_DIR / "detect" / "streetsense_v1" / "weights" / "last.pt"

    if best_weight_src.exists():
        dest = WEIGHTS_DIR / "best.pt"
        shutil.copy2(best_weight_src, dest)
        print(f"\n✅ Best weights saved to: {dest}")

    if last_weight_src.exists():
        dest = WEIGHTS_DIR / "last.pt"
        shutil.copy2(last_weight_src, dest)
        print(f"✅ Last weights saved to: {dest}")

    # Print results
    print(f"\n{'='*60}")
    print("TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"  Results dir: {RUNS_DIR / 'detect' / 'streetsense_v1'}")
    print(f"  Best weights: {WEIGHTS_DIR / 'best.pt'}")
    print(f"\n  Check these files:")
    print(f"  - results.png    (training curves)")
    print(f"  - confusion_matrix.png")
    print(f"  - val_batch0_pred.jpg (sample predictions)")
    print(f"\n  Next: python -m ai.models.validate")

    return results


def main():
    parser = argparse.ArgumentParser(description="Train StreetSense YOLOv8 model")
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        choices=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
        help="Base model (n=nano, s=small, m=medium, l=large, x=xlarge)",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--device", type=str, default="", help="cuda device or cpu")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    train(
        model_name=args.model,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        patience=args.patience,
        device=args.device,
        resume=args.resume,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
