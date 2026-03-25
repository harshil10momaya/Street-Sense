"""
StreetSense — Quick Inference Test

Run YOLO detection on a single image to verify the trained model works.

Usage:
    cd backend
    python -m ai.models.test_inference --image path/to/test_image.jpg
    python -m ai.models.test_inference --image path/to/image.jpg --conf 0.3 --show
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_WEIGHTS = BACKEND_DIR / "ai" / "weights" / "best.pt"

CLASS_NAMES = {0: "pothole", 1: "crack", 2: "garbage", 3: "manhole"}
SEVERITY_COLORS = {"low": "green", "medium": "orange", "high": "red"}


def run_test(image_path: str, weights: str = None, conf: float = 0.5, show: bool = False):
    """Run detection on a single image."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ Install: pip install ultralytics")
        sys.exit(1)

    weights_path = Path(weights) if weights else DEFAULT_WEIGHTS
    img_path = Path(image_path)

    if not weights_path.exists():
        print(f"❌ Weights not found: {weights_path}")
        print(f"   Train first: python -m ai.models.train")
        sys.exit(1)

    if not img_path.exists():
        print(f"❌ Image not found: {img_path}")
        sys.exit(1)

    print(f"Loading model from: {weights_path}")
    model = YOLO(str(weights_path))

    print(f"Running inference on: {img_path}")
    results = model.predict(
        source=str(img_path),
        conf=conf,
        save=True,
        save_txt=True,
        project=str(BACKEND_DIR / "runs" / "detect"),
        name="test_inference",
        exist_ok=True,
    )

    # Parse results
    result = results[0]
    boxes = result.boxes

    print(f"\n{'='*60}")
    print(f"DETECTION RESULTS")
    print(f"{'='*60}")
    print(f"  Image: {img_path.name}")
    print(f"  Size:  {result.orig_shape}")
    print(f"  Detections: {len(boxes)}")

    if len(boxes) == 0:
        print(f"\n  No objects detected at conf={conf}")
        print(f"  Try lowering confidence: --conf 0.25")
        return

    for i, box in enumerate(boxes):
        cls_id = int(box.cls[0])
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        w = x2 - x1
        h = y2 - y1
        area = w * h

        cls_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")

        print(f"\n  Detection {i+1}:")
        print(f"    Class:      {cls_name}")
        print(f"    Confidence: {confidence:.3f}")
        print(f"    BBox:       ({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f})")
        print(f"    Size:       {w:.0f} x {h:.0f} px (area: {area:.0f})")

    output_dir = BACKEND_DIR / "runs" / "detect" / "test_inference"
    print(f"\n  Annotated image saved to: {output_dir}")

    if show:
        try:
            import cv2
            annotated = result.plot()
            cv2.imshow("StreetSense Detection", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"  Could not display image: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test StreetSense model on an image")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--weights", default=None, help="Path to weights file")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--show", action="store_true", help="Display annotated image")
    args = parser.parse_args()

    run_test(args.image, args.weights, args.conf, args.show)


if __name__ == "__main__":
    main()
