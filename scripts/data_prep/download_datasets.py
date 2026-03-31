"""
StreetSense -- Dataset Downloader

Automatically downloads all 4 datasets from their sources:
  1. Smartathon (Roboflow) -> potholes + manholes
  2. Andrew Pothole (Kaggle) -> potholes
  3. RDD 2022 (Kaggle) -> road cracks
  4. TACO (Kaggle) -> garbage

Prerequisites:
    pip install roboflow kaggle

    # Roboflow: get API key from https://app.roboflow.com/settings/api
    # Kaggle:   place kaggle.json in ~/.kaggle/kaggle.json
    #           or set KAGGLE_USERNAME + KAGGLE_KEY env vars

Usage:
    python scripts/data_prep/download_datasets.py \\
        --roboflow-key YOUR_ROBOFLOW_API_KEY

    # Download only specific datasets:
    python scripts/data_prep/download_datasets.py \\
        --roboflow-key YOUR_KEY \\
        --only smartathon rdd2022
"""

import argparse
import os
import subprocess
import sys
import zipfile
from pathlib import Path

# Add parent to path for config import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    RAW_DIR,
    SMARTATHON_CONFIG,
    ANDREW_CONFIG,
    RDD2022_CONFIG,
    TACO_CONFIG,
)


def download_smartathon(api_key: str) -> bool:
    """Download Smartathon pothole/manhole dataset from Roboflow."""
    dest = SMARTATHON_CONFIG["raw_dir"]
    dest.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"[1/4] Smartathon -- Pothole + Manhole (Roboflow)")
    print(f"{'='*60}")

    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] Install roboflow: pip install roboflow")
        return False

    try:
        rf_cfg = SMARTATHON_CONFIG["roboflow"]
        rf = Roboflow(api_key=api_key)
        project = rf.workspace(rf_cfg["workspace"]).project(rf_cfg["project"])
        version = project.version(rf_cfg["version"])
        dataset = version.download("yolov8", location=str(dest))
        print(f"[OK] Smartathon downloaded to: {dest}")
        return True
    except Exception as e:
        print(f"[ERROR] Smartathon download failed: {e}")
        print(f"   Manual download: https://universe.roboflow.com/smartathon/new-pothole-detection")
        print(f"   Download as YOLOv8 format, extract to: {dest}")
        return False


def download_kaggle_dataset(dataset_slug: str, dest: Path, name: str) -> bool:
    """Download a dataset from Kaggle using the kaggle CLI."""
    dest.mkdir(parents=True, exist_ok=True)

    print(f"\n  Downloading {name} from Kaggle: {dataset_slug}")

    # Check kaggle credentials
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    has_env = os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")

    if not kaggle_json.exists() and not has_env:
        print(f"  [ERROR] Kaggle credentials not found!")
        print(f"     Option 1: Place kaggle.json in ~/.kaggle/kaggle.json")
        print(f"     Option 2: Set KAGGLE_USERNAME and KAGGLE_KEY env vars")
        print(f"     Get credentials from: https://www.kaggle.com/settings -> API -> Create New Token")
        return False

    try:
        # Use kaggle CLI
        cmd = [
            sys.executable, "-m", "kaggle", "datasets", "download",
            "-d", dataset_slug,
            "-p", str(dest),
            "--unzip",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            # Try without --unzip and manually extract
            cmd_no_unzip = [
                sys.executable, "-m", "kaggle", "datasets", "download",
                "-d", dataset_slug,
                "-p", str(dest),
            ]
            result = subprocess.run(cmd_no_unzip, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                print(f"  [ERROR] Kaggle download failed: {result.stderr}")
                return False

            # Find and extract zip files
            for zip_file in dest.glob("*.zip"):
                print(f"  [EXTRACT] Extracting: {zip_file.name}")
                with zipfile.ZipFile(zip_file, "r") as zf:
                    zf.extractall(dest)
                zip_file.unlink()  # Remove zip after extraction

        print(f"  [OK] {name} downloaded to: {dest}")
        return True

    except FileNotFoundError:
        print(f"  [ERROR] kaggle CLI not found. Install: pip install kaggle")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Download timed out (>10 min). Try manual download.")
        return False
    except Exception as e:
        print(f"  [ERROR] Download failed: {e}")
        return False


def download_andrew(api_key: str = None) -> bool:
    """Download Andrew pothole dataset from Kaggle."""
    print(f"\n{'='*60}")
    print(f"[2/4] Andrew Pothole (Kaggle)")
    print(f"{'='*60}")

    cfg = ANDREW_CONFIG
    return download_kaggle_dataset(
        cfg["kaggle"]["dataset"],
        cfg["raw_dir"],
        "Andrew Pothole",
    )


def download_rdd2022(api_key: str = None) -> bool:
    """Download RDD 2022 road damage dataset from Kaggle."""
    print(f"\n{'='*60}")
    print(f"[3/4] RDD 2022 -- Road Cracks (Kaggle)")
    print(f"{'='*60}")

    cfg = RDD2022_CONFIG
    return download_kaggle_dataset(
        cfg["kaggle"]["dataset"],
        cfg["raw_dir"],
        "RDD 2022",
    )


def download_taco(api_key: str = None) -> bool:
    """Download TACO trash dataset from Kaggle."""
    print(f"\n{'='*60}")
    print(f"[4/4] TACO -- Garbage Detection (Kaggle)")
    print(f"{'='*60}")

    cfg = TACO_CONFIG
    return download_kaggle_dataset(
        cfg["kaggle"]["dataset"],
        cfg["raw_dir"],
        "TACO Trash",
    )


def scan_downloaded():
    """Scan raw directory and report what's available."""
    print(f"\n{'='*60}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*60}")

    for cfg in [SMARTATHON_CONFIG, ANDREW_CONFIG, RDD2022_CONFIG, TACO_CONFIG]:
        raw_dir = cfg["raw_dir"]
        name = cfg["name"]

        if raw_dir.exists():
            files = list(raw_dir.rglob("*"))
            img_files = [f for f in files if f.suffix.lower() in {".jpg", ".jpeg", ".png"}]
            xml_files = [f for f in files if f.suffix.lower() == ".xml"]
            txt_files = [f for f in files if f.suffix.lower() == ".txt" and f.stem != "classes"]
            json_files = [f for f in files if f.suffix.lower() == ".json"]

            print(f"\n  [DIR] {name}/")
            print(f"     Total files:  {len(files)}")
            print(f"     Images:       {len(img_files)}")
            print(f"     XML labels:   {len(xml_files)}")
            print(f"     TXT labels:   {len(txt_files)}")
            print(f"     JSON files:   {len(json_files)}")

            # Show top-level structure
            top_items = sorted([f.name for f in raw_dir.iterdir()])[:10]
            print(f"     Contents:     {', '.join(top_items)}")
        else:
            print(f"\n  [ERROR] {name}/ -- NOT DOWNLOADED")


def main():
    parser = argparse.ArgumentParser(description="Download StreetSense datasets")
    parser.add_argument("--roboflow-key", required=True, help="Roboflow API key")
    parser.add_argument(
        "--only",
        nargs="+",
        choices=["smartathon", "andrew", "rdd2022", "taco"],
        default=None,
        help="Download only specific datasets",
    )
    args = parser.parse_args()

    targets = args.only or ["smartathon", "andrew", "rdd2022", "taco"]

    print("=" * 60)
    print("StreetSense -- Dataset Downloader")
    print("=" * 60)
    print(f"Output: {RAW_DIR}")
    print(f"Targets: {targets}")

    results = {}

    if "smartathon" in targets:
        results["smartathon"] = download_smartathon(args.roboflow_key)

    if "andrew" in targets:
        results["andrew"] = download_andrew()

    if "rdd2022" in targets:
        results["rdd2022"] = download_rdd2022()

    if "taco" in targets:
        results["taco"] = download_taco()

    # Report
    scan_downloaded()

    # Final status
    success = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  Downloaded: {success}/{total}")

    if success == total:
        print(f"\n  [OK] All datasets downloaded!")
        print(f"     Next: python scripts/data_prep/convert_and_clean.py")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"\n  [WARN]  Failed: {failed}")
        print(f"     Download manually and place in: {RAW_DIR}/<dataset_name>/")
        print(f"     Then run: python scripts/data_prep/convert_and_clean.py")


if __name__ == "__main__":
    main()
