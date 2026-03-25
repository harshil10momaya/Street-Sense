"""
StreetSense — YOLOv8 Validation Script

Evaluates the trained model on the validation set and prints detailed metrics.

Outputs:
- mAP@50, mAP@50:95 (overall and per-class)
- Precision, Recall, F1
- Confusion matrix
- Sample predictions

Usage:
    cd backend
    python -m ai.models.validate
    python -m ai.models.validate --weights ai/weights/best.pt --conf 0.25
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

DATASET_YAML = BACKEND_DIR / "ai" / "config" / "dataset.yaml"
DEFAULT_WEIGHTS = BACKEND_DIR / "ai" / "weights" / "best.pt"
RUNS_DIR = BACKEND_DIR / "runs"


def validate(
    weights: str = None,
    conf: float = 0.25,
    iou: float = 0.45,
    imgsz: int = 640,
    device: str = "",
):
    """Run validation on the test/val set."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ Install ultralytics: pip install ultralytics")
        sys.exit(1)

    weights_path = Path(weights) if weights else DEFAULT_WEIGHTS

    if not weights_path.exists():
        print(f"❌ Weights not found: {weights_path}")
        print(f"   Train first: python -m ai.models.train")
        sys.exit(1)

    print("=" * 60)
    print("StreetSense — YOLOv8 Validation")
    print("=" * 60)
    print(f"  Weights: {weights_path}")
    print(f"  Dataset: {DATASET_YAML}")
    print(f"  Conf threshold: {conf}")
    print(f"  IoU threshold:  {iou}")
    print()

    model = YOLO(str(weights_path))

    results = model.val(
        data=str(DATASET_YAML),
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        device=device or None,
        project=str(RUNS_DIR / "detect"),
        name="streetsense_val",
        exist_ok=True,
        plots=True,
        verbose=True,
    )

    # Extract metrics
    print(f"\n{'='*60}")
    print("VALIDATION RESULTS")
    print(f"{'='*60}")

    metrics = results.results_dict
    print(f"\n  Overall Metrics:")
    print(f"    mAP@50:      {metrics.get('metrics/mAP50(B)', 0):.4f}")
    print(f"    mAP@50:95:   {metrics.get('metrics/mAP50-95(B)', 0):.4f}")
    print(f"    Precision:   {metrics.get('metrics/precision(B)', 0):.4f}")
    print(f"    Recall:      {metrics.get('metrics/recall(B)', 0):.4f}")

    # Per-class results
    class_names = ["pothole", "crack", "garbage", "manhole"]
    if hasattr(results, 'box'):
        box = results.box
        if hasattr(box, 'maps'):
            print(f"\n  Per-Class mAP@50:")
            for i, name in enumerate(class_names):
                if i < len(box.maps):
                    print(f"    {name:10s}: {box.maps[i]:.4f}")

    print(f"\n  Results saved to: {RUNS_DIR / 'detect' / 'streetsense_val'}")

    # Quality assessment
    mAP50 = metrics.get("metrics/mAP50(B)", 0)
    if mAP50 >= 0.7:
        print(f"\n  ✅ Good model performance (mAP@50 = {mAP50:.2f})")
        print(f"     Ready for deployment!")
    elif mAP50 >= 0.5:
        print(f"\n  ⚠️  Moderate performance (mAP@50 = {mAP50:.2f})")
        print(f"     Consider:")
        print(f"     - More training data")
        print(f"     - Longer training (more epochs)")
        print(f"     - Larger model (yolov8s or yolov8m)")
    else:
        print(f"\n  ❌ Low performance (mAP@50 = {mAP50:.2f})")
        print(f"     Check:")
        print(f"     - Dataset quality and annotations")
        print(f"     - Class ID mapping in merge step")
        print(f"     - Try more epochs or different base model")

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate StreetSense model")
    parser.add_argument("--weights", type=str, default=None)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="")
    args = parser.parse_args()

    validate(
        weights=args.weights,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=args.device,
    )


if __name__ == "__main__":
    main()
