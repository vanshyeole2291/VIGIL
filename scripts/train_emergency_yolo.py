"""
scripts/train_emergency_yolo.py — VIGIL Emergency Vehicle YOLOv8 Retraining Pipeline
=====================================================================================
Fine-tunes YOLOv8 / YOLOv11 for high-precision visual detection of emergency vehicles
(Ambulance, Fire Truck) alongside standard urban traffic classes (Car, Motorcycle, Bus, Truck).

Features:
- Configurable dataset, weights, epochs, batch size, image resolution, seed, and device.
- Pre-flight checks: validates image counts, label files, bounding box coordinate normalization [0, 1].
- GPU memory inspection with automatic batch-size reduction fallback on CUDA Out-Of-Memory.
- Safe model candidate isolation: preserves models/best.pt until explicit promotion.
- Automated evaluation metrics, confusion matrix, and reports generation.
"""

import os
import sys
import shutil
import argparse
import time
import json
from pathlib import Path
import yaml
import torch

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Unpickle compatibility for custom heads
import ultralytics.nn.modules.head as head
if not hasattr(head, 'RefineDetect'):
    head.RefineDetect = head.Detect
from ultralytics import YOLO


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
                        help="Batch size (automatically halved on CUDA OOM)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Image resolution (square pixels)")
    parser.add_argument("--lr0", type=float, default=0.01,
                        help="Initial learning rate")
    parser.add_argument("--patience", type=int, default=15,
                        help="Early stopping patience (epochs without validation improvement)")
    parser.add_argument("--workers", type=int, default=2 if sys.platform == "win32" else 4,
                        help="Number of worker threads for data loading")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for deterministic reproducibility")
    parser.add_argument("--resume", action="store_true", default=False,
                        help="Resume training from previous checkpoint in run directory")
    
    # Hardware & Experiment Tracking
    default_device = "0" if torch.cuda.is_available() else "cpu"
    parser.add_argument("--device", type=str, default=default_device,
                        help="Compute device ('0', '1', 'cpu', 'cuda')")
    parser.add_argument("--name", type=str, default="emergency_yolo_run",
                        help="Experiment run name")
    parser.add_argument("--project", type=str, default=str(PROJECT_ROOT / "runs" / "train"),
                        help="Output directory for training runs")
    parser.add_argument("--promote", action="store_true", default=False,
                        help="Promote candidate weights to primary models/best.pt with timestamped backup")
    parser.add_argument("--export", type=str, default=None, choices=["onnx", "torchscript", None],
                        help="Export format for the final fine-tuned model")
    
    return parser.parse_args()


def inspect_hardware_and_vram(device_str: str) -> None:
    """Check GPU availability, VRAM capacity, and device status."""
    print("\n" + "=" * 65)
    print("   VIGIL Compute & Hardware Diagnostics")
    print("=" * 65)
    cuda_avail = torch.cuda.is_available()
    print(f"CUDA Available     : {cuda_avail}")
    if cuda_avail:
        device_count = torch.cuda.device_count()
        current_dev = torch.cuda.current_device()
        dev_name = torch.cuda.get_device_name(current_dev)
        vram_total = torch.cuda.get_device_properties(current_dev).total_memory / (1024 ** 3)
        vram_alloc = torch.cuda.memory_allocated(current_dev) / (1024 ** 3)
        vram_free = vram_total - vram_alloc
        print(f"GPU Devices        : {device_count} (Current: [{current_dev}] {dev_name})")
        print(f"Total VRAM         : {vram_total:.2f} GB")
        print(f"Free VRAM          : {vram_free:.2f} GB")
    else:
        print("Compute Device     : CPU (CPU inference/training fallback enabled)")
        print("Note               : For fast GPU fine-tuning, run on a CUDA-enabled machine or Google Colab T4.")
    print("=" * 65)


def verify_dataset_prerequisites(data_yaml_path: str) -> bool:
    """Validate dataset YAML, image directories, label files, and bounding box normalization."""
    yaml_file = Path(data_yaml_path).resolve()
    if not yaml_file.exists():
        print(f"\n[ERROR] Dataset config not found: {yaml_file}")
        return False
        
    try:
        with open(yaml_file, "r") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"\n[ERROR] Failed to parse YAML file: {e}")
        return False

    dataset_root = cfg.get("path")
    if dataset_root:
        resolved_root = (yaml_file.parent / dataset_root).resolve()
    else:
        resolved_root = yaml_file.parent

    train_rel = cfg.get("train", "images/train")
    val_rel = cfg.get("val", "images/val")
    train_path = resolved_root / train_rel
    val_path = resolved_root / val_rel

    print("\n" + "=" * 65)
    print("   VIGIL YOLOv8 Emergency Vehicle Retraining Pre-Flight Check")
    print("=" * 65)
    print(f"Dataset Config : {yaml_file}")
    print(f"Dataset Root   : {resolved_root}")
    print(f"Train Images   : {train_path}")
    print(f"Val Images     : {val_path}")
    print(f"Target Classes : {cfg.get('names', {})}")
    print("=" * 65)

    if not train_path.exists():
        print("\n[WARNING] Training image directory does not exist yet!")
        print(f"Expected path: {train_path}")
        print("\nTo prepare your dataset:")
        print("  1. Download an Emergency Vehicles dataset from Roboflow in YOLOv8 format.")
        print(f"  2. Extract it into: {resolved_root}")
        print("  3. Verify images exist in: images/train/ and images/val/")
        print("  4. See docs/RETRAINING_GUIDE.md for step-by-step instructions.")
        print("=" * 65)
        return False

    # Check for image files
    train_images = [p for p in train_path.glob("*.*") if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]]
    if not train_images:
        print(f"\n[WARNING] No valid image files found in {train_path}")
        return False

    # Check for corresponding labels directory
    labels_train = resolved_root / "labels" / Path(train_rel).name
    if not labels_train.exists():
        # Check adjacent labels folder
        labels_train = train_path.parent.parent / "labels" / train_path.name

    if labels_train.exists():
        label_files = list(labels_train.glob("*.txt"))
        print(f"Pre-flight Check: Found {len(train_images)} training images and {len(label_files)} label files.")
        
        # Validate sample label format (first 20 files)
        valid_boxes = 0
        invalid_boxes = 0
        for lf in label_files[:20]:
            try:
                with open(lf, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            cls_id = int(parts[0])
                            xc, yc, w, h = map(float, parts[1:5])
                            if 0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 <= w <= 1.0 and 0.0 <= h <= 1.0:
                                valid_boxes += 1
                            else:
                                invalid_boxes += 1
            except Exception:
                pass
        if invalid_boxes > 0:
            print(f"[WARNING] Detected {invalid_boxes} out-of-bounds normalized boxes in sample labels!")
        else:
            print(f"Annotation Integrity: Validated {valid_boxes} bounding boxes in sample labels [0.0 - 1.0].")
    else:
        print(f"[INFO] Separate labels/ folder not found at {labels_train}; Ultralytics will check auto-relative labels.")

    return True


def execute_training_with_oom_guard(model, training_args: dict):
    """Run training with automatic batch-size reduction if CUDA OOM occurs."""
    current_batch = training_args.get("batch", 16)
    while current_batch >= 2:
        try:
            print(f"\n[VIGIL AI] Launching training with batch size = {current_batch}...")
            training_args["batch"] = current_batch
            results = model.train(**training_args)
            return results
        except RuntimeError as e:
            err_msg = str(e).lower()
            if "out of memory" in err_msg or "cuda" in err_msg and "memory" in err_msg:
                print(f"\n[WARNING] CUDA Out-of-Memory encountered at batch size = {current_batch}!")
                torch.cuda.empty_cache()
                current_batch = current_batch // 2
                if current_batch < 2:
                    print("[ERROR] Insufficient GPU VRAM even at batch size = 2. Falling back to CPU or smaller imgsz.")
                    raise e
                print(f"[RECOVERY] Retrying training with halved batch size = {current_batch}...")
            else:
                raise e


def train_emergency_detector(args):
    """Execute fine-tuning on the custom emergency dataset and report metrics."""
    start_time = time.time()
    inspect_hardware_and_vram(args.device)
    
    print(f"\n[VIGIL AI] Loading model weights: {args.weights}")
    model = YOLO(args.weights)
    
    print(f"[VIGIL AI] Base model classes ({len(model.names)}): {list(model.names.values())[:8]}...")
    
    training_args = {
        "data": args.data,
        "epochs": args.epochs,
        "batch": args.batch,
        "imgsz": args.imgsz,
        "device": args.device,
        "workers": args.workers,
        "lr0": args.lr0,
        "patience": args.patience,
        "seed": args.seed,
        "project": args.project,
        "name": args.name,
        "exist_ok": True,
        "resume": args.resume,
        "pretrained": True,
        "verbose": True,
        # CCTV-tuned augmentations
        "hsv_h": 0.015,   # Hue jitter for emergency strobes
        "hsv_s": 0.7,     # Saturation
        "hsv_v": 0.4,     # Brightness shift for day/night
        "degrees": 4.0,   # Slight tilt
        "scale": 0.35,    # Distance scale variations
        "fliplr": 0.5,    # Horizontal flip
        "mosaic": 0.8,    # Multi-vehicle context
    }
    
    results = execute_training_with_oom_guard(model, training_args)
    elapsed = time.time() - start_time
    print(f"\n[VIGIL AI] Training completed in {elapsed / 60:.1f} minutes.")
    
    # ── Post-Training Validation ──────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("   VIGIL Candidate Model Evaluation & Class-by-Class Metrics")
    print("=" * 65)
    val_results = model.val()
    
    metrics = getattr(val_results, 'results_dict', {})
    map50 = float(metrics.get('metrics/mAP50(B)', 0.0))
    map50_95 = float(metrics.get('metrics/mAP50-95(B)', 0.0))
    precision = float(metrics.get('metrics/precision(B)', 0.0))
    recall = float(metrics.get('metrics/recall(B)', 0.0))
    
    print(f"Overall Precision : {precision * 100:.2f}%")
    print(f"Overall Recall    : {recall * 100:.2f}%")
    print(f"Overall mAP@0.50  : {map50 * 100:.2f}%")
    print(f"Overall mAP@0.5-95: {map50_95 * 100:.2f}%")
    print("=" * 65)
    
    # ── Save Candidate Model (Safe Isolation) ─────────────────────────────────
    best_pt_path = Path(args.project) / args.name / "weights" / "best.pt"
    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(exist_ok=True)
    
    candidate_path = models_dir / "candidate_emergency.pt"
    if best_pt_path.exists():
        shutil.copy2(best_pt_path, candidate_path)
        print(f"[VIGIL AI] Saved candidate checkpoint to: {candidate_path}")
        
        # Save evaluation report
        eval_record = {
            "timestamp": time.time(),
            "candidate_checkpoint": str(candidate_path.relative_to(PROJECT_ROOT)),
            "base_checkpoint": args.weights,
            "dataset_config": args.data,
            "epochs": args.epochs,
            "imgsz": args.imgsz,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "map50": round(map50, 4),
            "map50_95": round(map50_95, 4),
            "training_time_minutes": round(elapsed / 60.0, 2),
        }
        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        report_file = reports_dir / "candidate_evaluation.json"
        with open(report_file, "w") as f:
            json.dump(eval_record, f, indent=2)
        print(f"[VIGIL AI] Candidate evaluation report saved to: {report_file}")
        
        # Explicit promotion only if requested
        if args.promote:
            primary_dest = models_dir / "best.pt"
            backup_dest = models_dir / f"best_backup_{int(time.time())}.pt"
            if primary_dest.exists():
                shutil.copy2(primary_dest, backup_dest)
                print(f"[VIGIL AI] Backed up previous production weights to: {backup_dest}")
            shutil.copy2(best_pt_path, primary_dest)
            print(f"[VIGIL AI] Promoted candidate to production: {primary_dest}")
        else:
            print("[VIGIL AI] Production weights models/best.pt untouched. Pass --promote to promote candidate after verification.")

    if args.export:
        print(f"\n[VIGIL AI] Exporting model to {args.export.upper()}...")
        model.export(format=args.export)
        
    return results


def main():
    args = parse_arguments()
    dataset_ready = verify_dataset_prerequisites(args.data)
    
    if not dataset_ready:
        print("\n[INFO] Dataset not found or empty. Stopping before training.")
        print("Please follow docs/RETRAINING_GUIDE.md to obtain your dataset, then re-run.")
        sys.exit(1)
        
    train_emergency_detector(args)


if __name__ == "__main__":
    main()
