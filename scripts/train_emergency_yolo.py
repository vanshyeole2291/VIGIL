"""
scripts/train_emergency_yolo.py — VIGIL Emergency Vehicle YOLOv8 Retraining Pipeline
=====================================================================================
Fine-tunes YOLOv8 / YOLOv11 for high-precision visual detection of emergency vehicles
(Ambulance, Fire Truck) alongside standard urban traffic classes (Car, Motorcycle, Bus, Truck).

Usage:
  # Local GPU Training (Recommended)
  python scripts/train_emergency_yolo.py --epochs 50 --batch 16 --imgsz 640 --device 0

  # CPU Fallback / Quick Smoke Test
  python scripts/train_emergency_yolo.py --epochs 1 --batch 2 --imgsz 320 --device cpu

  # Custom Dataset Path
  python scripts/train_emergency_yolo.py --data path/to/data.yaml --weights models/yolov8n.pt
"""

import os
import sys
import shutil
import argparse
import time
from pathlib import Path
import yaml
import torch
from ultralytics import YOLO

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="VIGIL — Fine-Tune YOLOv8 for Emergency Vehicle Detection (Ambulance & Fire Truck)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Model & Data Configuration
    default_weights = PROJECT_ROOT / "models" / "best.pt"
    if not default_weights.exists():
        default_weights = PROJECT_ROOT / "models" / "yolov8n.pt"
        if not default_weights.exists():
            default_weights = "yolov8n.pt"
            
    parser.add_argument("--weights", type=str, default=str(default_weights),
                        help="Initial model checkpoint (e.g., models/best.pt, yolov8n.pt, yolo11n.pt)")
    parser.add_argument("--data", type=str, default=str(PROJECT_ROOT / "scripts" / "emergency_data.yaml"),
                        help="Path to dataset YAML configuration file")
    
    # Training Hyperparameters
    parser.add_argument("--epochs", type=int, default=50,
                        help="Number of fine-tuning epochs")
    parser.add_argument("--batch", type=int, default=16,
                        help="Batch size (reduce to 8 or 4 if encountering CUDA out of memory)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Image resolution (square pixels)")
    parser.add_argument("--lr0", type=float, default=0.01,
                        help="Initial learning rate")
    parser.add_argument("--patience", type=int, default=15,
                        help="Early stopping patience (epochs without validation improvement)")
    parser.add_argument("--workers", type=int, default=2 if sys.platform == "win32" else 4,
                        help="Number of worker threads for data loading")
    
    # Hardware & Experiment Tracking
    default_device = "0" if torch.cuda.is_available() else "cpu"
    parser.add_argument("--device", type=str, default=default_device,
                        help="Compute device ('0', '1', 'cpu', 'cuda')")
    parser.add_argument("--name", type=str, default="emergency_yolo_run",
                        help="Experiment run name")
    parser.add_argument("--project", type=str, default=str(PROJECT_ROOT / "runs" / "train"),
                        help="Output directory for training runs")
    parser.add_argument("--deploy", action="store_true", default=True,
                        help="Automatically deploy trained best.pt to models/ directory")
    parser.add_argument("--export", type=str, default=None, choices=["onnx", "torchscript", None],
                        help="Export format for the final fine-tuned model")
    
    return parser.parse_args()


def verify_dataset_prerequisites(data_yaml_path: str) -> bool:
    """Validate that the dataset YAML and image directories exist before launching training."""
    yaml_file = Path(data_yaml_path).resolve()
    if not yaml_file.exists():
        print(f"\n[ERROR] Dataset config not found: {yaml_file}")
        print("Please check the path or create the config file.")
        return False
        
    try:
        with open(yaml_file, "r") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"\n[ERROR] Failed to parse YAML file: {e}")
        return False

    dataset_root = cfg.get("path")
    if dataset_root:
        # Resolve relative to YAML location
        resolved_root = (yaml_file.parent / dataset_root).resolve()
    else:
        resolved_root = yaml_file.parent

    train_path = resolved_root / cfg.get("train", "images/train")
    val_path = resolved_root / cfg.get("val", "images/val")

    print("\n" + "=" * 65)
    print("   VIGIL YOLOv8 Emergency Vehicle Retraining Pre-Flight Check")
    print("=" * 65)
    print(f"Dataset Config : {yaml_file}")
    print(f"Dataset Root   : {resolved_root}")
    print(f"Train Images   : {train_path}")
    print(f"Val Images     : {val_path}")
    print(f"Target Classes : {cfg.get('names', {})}")
    print("=" * 65)

    if not train_path.exists() or not any(train_path.iterdir()):
        print("\n[WARNING] Training image directory is missing or empty!")
        print(f"Expected image path: {train_path}")
        print("\nTo prepare your dataset:")
        print("  1. Download an Emergency Vehicles dataset from Roboflow in YOLOv8 format.")
        print(f"  2. Extract it into: {resolved_root}")
        print("  3. Verify images exist in: images/train/ and images/val/")
        print("  4. See docs/RETRAINING_GUIDE.md for step-by-step instructions.")
        print("=" * 65)
        return False

    return True


def train_emergency_detector(args):
    """Execute YOLOv8 fine-tuning on the custom emergency dataset."""
    start_time = time.time()
    
    print(f"\n[VIGIL AI] Initializing YOLOv8 from base weights: {args.weights}")
    model = YOLO(args.weights)
    
    # Display baseline architecture and class summary
    print(f"[VIGIL AI] Base model classes ({len(model.names)}): {list(model.names.values())[:8]}...")
    print(f"[VIGIL AI] Training device: {args.device} (CUDA Available: {torch.cuda.is_available()})")
    
    # Hyperparameters tuned for emergency vehicle visual discrimination:
    # - Augmentation for emergency beacons (hsv_h, hsv_s, hsv_v)
    # - Flip and scale variations for diverse camera angles
    training_args = {
        "data": args.data,
        "epochs": args.epochs,
        "batch": args.batch,
        "imgsz": args.imgsz,
        "device": args.device,
        "workers": args.workers,
        "lr0": args.lr0,
        "patience": args.patience,
        "project": args.project,
        "name": args.name,
        "exist_ok": True,
        "pretrained": True,
        "verbose": True,
        # Augmentations for emergency strobes and beacon lights
        "hsv_h": 0.025,   # Hue shift to capture red/blue strobe variations
        "hsv_s": 0.7,     # Saturation adjustment
        "hsv_v": 0.4,     # Brightness shifts (day vs night flashing beacons)
        "degrees": 5.0,   # Slight tilt rotation
        "scale": 0.4,     # Scale range (near vs distant vehicles)
        "fliplr": 0.5,    # Horizontal flip
        "mosaic": 1.0,    # Multi-vehicle context mosaic
    }
    
    print("\n[VIGIL AI] Starting training epochs...")
    results = model.train(**training_args)
    
    elapsed = time.time() - start_time
    print(f"\n[VIGIL AI] Training completed in {elapsed / 60:.1f} minutes.")
    
    # ── Post-Training Validation ──────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("   VIGIL Model Validation & Class-by-Class Evaluation")
    print("=" * 65)
    val_results = model.val()
    
    metrics = getattr(val_results, 'results_dict', {})
    map50 = metrics.get('metrics/mAP50(B)', 0.0)
    map50_95 = metrics.get('metrics/mAP50-95(B)', 0.0)
    precision = metrics.get('metrics/precision(B)', 0.0)
    recall = metrics.get('metrics/recall(B)', 0.0)
    
    print(f"Overall Precision : {precision * 100:.2f}%")
    print(f"Overall Recall    : {recall * 100:.2f}%")
    print(f"Overall mAP@0.50  : {map50 * 100:.2f}%")
    print(f"Overall mAP@0.5-95: {map50_95 * 100:.2f}%")
    print("=" * 65)
    
    # ── Automatic Weight Deployment ───────────────────────────────────────────
    best_pt_path = Path(args.project) / args.name / "weights" / "best.pt"
    if args.deploy and best_pt_path.exists():
        models_dir = PROJECT_ROOT / "models"
        models_dir.mkdir(exist_ok=True)
        
        # 1. Save dedicated emergency model
        emergency_dest = models_dir / "best_emergency.pt"
        shutil.copy2(best_pt_path, emergency_dest)
        print(f"[VIGIL AI] Deployed emergency model: {emergency_dest}")
        
        # 2. Update primary best.pt with automatic safety backup
        primary_dest = models_dir / "best.pt"
        if primary_dest.exists():
            backup_dest = models_dir / f"best_backup_{int(time.time())}.pt"
            shutil.copy2(primary_dest, backup_dest)
            print(f"[VIGIL AI] Backed up previous weights to: {backup_dest}")
            
        shutil.copy2(best_pt_path, primary_dest)
        print(f"[VIGIL AI] Updated primary weights: {primary_dest}")
        
    # Optional Export
    if args.export:
        print(f"\n[VIGIL AI] Exporting model to {args.export.upper()}...")
        model.export(format=args.export)
        
    print("\n[VIGIL AI] Pipeline finished successfully! The VIGIL server can now visually detect Ambulances & Fire Trucks.")
    return results


def main():
    args = parse_arguments()
    dataset_ready = verify_dataset_prerequisites(args.data)
    
    if not dataset_ready:
        print("\n[INFO] Pre-flight check stopped: Dataset images not yet detected.")
        print("Please follow docs/RETRAINING_GUIDE.md to download your dataset, then re-run this command.")
        sys.exit(1)
        
    train_emergency_detector(args)


if __name__ == "__main__":
    main()
