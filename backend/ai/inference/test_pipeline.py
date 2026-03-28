"""
StreetSense -- Pipeline Test CLI

Test the full YOLO + MiDaS + Severity pipeline on images or videos.

Usage:
    cd backend

    # Test on a single image
    python -m ai.inference.test_pipeline --image path/to/image.jpg

    # Test on a video
    python -m ai.inference.test_pipeline --video path/to/video.mp4

    # Without depth estimation (faster, YOLO only)
    python -m ai.inference.test_pipeline --image path/to/image.jpg --no-depth

    # Use smaller MiDaS model for speed
    python -m ai.inference.test_pipeline --image path/to/image.jpg --midas-model MiDaS_small

    # Custom confidence threshold
    python -m ai.inference.test_pipeline --image path/to/image.jpg --conf 0.3
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_image(args):
    """Test pipeline on a single image."""
    from ai.inference.pipeline import InferencePipeline

    print("=" * 60)
    print("StreetSense -- Pipeline Test (Image)")
    print("=" * 60)

    # Initialize pipeline
    pipeline = InferencePipeline(
        yolo_weights=args.weights,
        midas_model=args.midas_model,
        confidence=args.conf,
        enable_depth=not args.no_depth,
    )

    print(f"  YOLO weights:  {args.weights}")
    print(f"  MiDaS model:   {args.midas_model if not args.no_depth else 'DISABLED'}")
    print(f"  Confidence:    {args.conf}")
    print(f"  Image:         {args.image}")

    # Load models
    print("\nLoading models...")
    start = time.time()
    pipeline.load()
    print(f"  Models loaded in {time.time() - start:.1f}s")

    # Process image
    print("\nRunning inference...")
    result = pipeline.process_image_file(
        args.image,
        output_dir=args.output or str(BACKEND_DIR / "runs" / "pipeline_test"),
    )

    # Print results
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Image size:      {result.image_shape}")
    print(f"  Processing time: {result.processing_time_ms:.1f} ms")
    print(f"  Detections:      {result.detection_count}")

    if result.has_detections:
        print(f"  Severity:        {result.severity_summary}")

        for i, det in enumerate(result.detections):
            print(f"\n  Detection {i+1}:")
            print(f"    Class:       {det.class_name}")
            print(f"    Confidence:  {det.confidence:.3f}")
            print(f"    BBox:        ({det.x1:.0f}, {det.y1:.0f}) - ({det.x2:.0f}, {det.y2:.0f})")
            print(f"    Area:        {det.bbox_area:.0f} px")
            print(f"    Severity:    {det.severity} (score: {det.severity_score:.4f})")

            if det.depth_info:
                d = det.depth_info
                print(f"    Depth info:")
                print(f"      Avg depth:       {d['avg_depth']:.4f}")
                print(f"      Surrounding:     {d['surrounding_depth']:.4f}")
                print(f"      Contrast:        {d['depth_contrast']:.4f}")
                print(f"      Std deviation:   {d['std_depth']:.4f}")

    else:
        print("\n  No detections found.")
        print(f"  Try lowering confidence: --conf 0.25")

    # Save JSON results
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = BACKEND_DIR / "runs" / "pipeline_test"

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{Path(args.image).stem}_results.json"
    with open(json_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    print(f"\n  Results JSON: {json_path}")
    print(f"  Output dir:   {out_dir}")


def test_video(args):
    """Test pipeline on a video."""
    from ai.inference.pipeline import InferencePipeline

    print("=" * 60)
    print("StreetSense -- Pipeline Test (Video)")
    print("=" * 60)

    pipeline = InferencePipeline(
        yolo_weights=args.weights,
        midas_model=args.midas_model,
        confidence=args.conf,
        enable_depth=not args.no_depth,
    )

    print(f"  Video: {args.video}")
    print(f"  Frame skip: {args.frame_skip}")

    print("\nLoading models...")
    pipeline.load()

    out_dir = args.output or str(BACKEND_DIR / "runs" / "pipeline_test")
    output_video = str(Path(out_dir) / f"{Path(args.video).stem}_annotated.mp4")

    print(f"\nProcessing video...")
    total_detections = 0
    frame_count = 0

    def on_frame(frame_num, result):
        nonlocal total_detections, frame_count
        frame_count += 1
        total_detections += result.detection_count
        if frame_count % 10 == 0:
            print(f"  Frame {frame_num}: {result.detection_count} detections, "
                  f"{result.processing_time_ms:.0f}ms")

    for frame_num, result in pipeline.process_video(
        args.video,
        output_path=output_video,
        frame_skip=args.frame_skip,
        callback=on_frame,
    ):
        pass

    print(f"\n  Frames processed: {frame_count}")
    print(f"  Total detections: {total_detections}")
    print(f"  Output video:     {output_video}")


def main():
    parser = argparse.ArgumentParser(description="Test StreetSense inference pipeline")
    parser.add_argument("--image", type=str, help="Path to test image")
    parser.add_argument("--video", type=str, help="Path to test video")
    parser.add_argument("--weights", type=str, default=str(BACKEND_DIR / "ai" / "weights" / "best.pt"))
    parser.add_argument("--midas-model", type=str, default="DPT_Large",
                        choices=["DPT_Large", "DPT_Hybrid", "MiDaS_small"])
    parser.add_argument("--conf", type=float, default=0.5)
    parser.add_argument("--no-depth", action="store_true", help="Disable MiDaS depth estimation")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--frame-skip", type=int, default=3, help="Video: process every Nth frame")
    args = parser.parse_args()

    if not args.image and not args.video:
        parser.error("Provide --image or --video")

    if args.image:
        test_image(args)
    elif args.video:
        test_video(args)


if __name__ == "__main__":
    main()
