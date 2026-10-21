"""
scripts/train_accident_model.py
================================
Accident Perception & Multi-Class Retraining Pipeline
- Extracts keyframe pairs for vehicle accidents from south.mp4 and ai_south_accident.mp4
- Labels genuine vehicle collisions as Class 6: 'accident'
- Provides explicit negative samples from dense queuing traffic (Class 0: car, Class 4: auto)
  so heavy traffic queues are NEVER classified as accidents or ambulances
- Retrains YOLO weights and exports to:
    models/best_indian_traffic.pt
    models/best (12).pt
    models/accident_best.pt
"""

import os
import sys
import cv2
import numpy as np
import shutil
import yaml
from pathlib import Path
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config

DATASET_DIR = PROJECT_ROOT / "datasets" / "indian_traffic"
IMAGES_TRAIN = DATASET_DIR / "images" / "train"
IMAGES_VAL = DATASET_DIR / "images" / "val"
LABELS_TRAIN = DATASET_DIR / "labels" / "train"
LABELS_VAL = DATASET_DIR / "labels" / "val"

CLASSES = {
    0: "car",
    1: "motorcycle",
    2: "bus",
    3: "truck",
    4: "auto",
    5: "ambulance",
    6: "accident"
}

def setup_dirs():
    for d in [IMAGES_TRAIN, IMAGES_VAL, LABELS_TRAIN, LABELS_VAL]:
        d.mkdir(parents=True, exist_ok=True)
    # Clear old training cache if present
    for cache in DATASET_DIR.glob("**/*.cache"):
        try:
            cache.unlink()
        except Exception:
            pass

def to_yolo(x1, y1, x2, y2, fw, fh):
    cx = ((x1 + x2) / 2.0) / float(fw)
    cy = ((y1 + y2) / 2.0) / float(fh)
    w = float(max(2, x2 - x1)) / float(fw)
    h = float(max(2, y2 - y1)) / float(fh)
    return f"{cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"

def harvest_dataset():
    print("=" * 65)
    print("HARVESTING MULTI-CLASS ACCIDENT, EMERGENCY & TRAFFIC SAMPLES")
    print("=" * 65)
    
    samples_created = 0

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Harvest Accidents & Queues from assets/videos/south.mp4
    # ──────────────────────────────────────────────────────────────────────────
    south_path = PROJECT_ROOT / "assets" / "videos" / "south.mp4"
    if south_path.exists():
        cap = cv2.VideoCapture(str(south_path))
        print("Processing south.mp4...")
        
        # A. Collision impact sequence (frames 255 - 280)
        # Vehicles colliding in lower right quadrant [340..640, 130..355]
        for f in [255, 258, 260, 263, 265, 268, 270, 275]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]
            
            # Box 1: Accident Collision Impact Zone (Class 6)
            acc_box = to_yolo(340, 130, 638, 355, fw, fh)
            # Box 2: Background ambient traffic car (Class 0)
            car_bg = to_yolo(170, 36, 218, 60, fw, fh)
            lines = [f"6 {acc_box}", f"0 {car_bg}"]
            
            split = "val" if (f in [265, 275]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_acc_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_acc_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # B. Highway crash aftermath with crowd (frames 995 - 1030)
        for f in [995, 1000, 1005, 1010, 1015, 1020, 1025]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]
            
            # Accident Zone with crashed car/truck (Class 6)
            acc_box = to_yolo(160, 80, 639, 358, fw, fh)
            lines = [f"6 {acc_box}"]
            
            split = "val" if (f in [1005, 1025]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_crash_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_crash_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # C. Explicit Heavy Queue Traffic (NEGATIVE SAMPLES: Class 0 car, NEVER accident/ambulance)
        for f in [50, 100, 150, 200, 350, 450, 550, 750]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]
            
            lines = [
                f"0 {to_yolo(320, 196, 496, 353, fw, fh)}",
                f"0 {to_yolo(119, 57, 248, 107, fw, fh)}",
                f"0 {to_yolo(271, 61, 337, 118, fw, fh)}",
                f"0 {to_yolo(478, 109, 553, 158, fw, fh)}"
            ]
            split = "val" if (f == 200) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_queue_neg_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_queue_neg_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        cap.release()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Harvest Synthetic Collision from assets/videos/ai_south_accident.mp4
    # ──────────────────────────────────────────────────────────────────────────
    ai_acc_path = PROJECT_ROOT / "assets" / "videos" / "ai_south_accident.mp4"
    if ai_acc_path.exists():
        cap = cv2.VideoCapture(str(ai_acc_path))
        print("Processing ai_south_accident.mp4...")
        for f in [125, 140, 160, 180, 210, 250, 300, 360]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]
            
            # Collision Box (Class 6: accident)
            acc_box = to_yolo(320, 110, 470, 246, fw, fh)
            lines = [f"6 {acc_box}"]
            
            split = "val" if (f in [160, 300]) else "train"
            img_file = DATASET_DIR / "images" / split / f"ai_acc_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"ai_acc_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1
        cap.release()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Harvest Genuine Ambulance Samples (Class 5: ambulance)
    # ──────────────────────────────────────────────────────────────────────────
    amb_path = PROJECT_ROOT / "assets" / "videos" / "Ambulance-stuck-in-SnapYT.App.mp4"
    if amb_path.exists():
        cap = cv2.VideoCapture(str(amb_path))
        print("Processing Ambulance-stuck-in-SnapYT.App.mp4...")
        for f in [200, 300, 400, 500, 700, 900]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]
            
            # Ambulance (Class 5) + surrounding cars (Class 0)
            lines = [
                f"5 {to_yolo(130, 50, 425, 330, fw, fh)}",
                f"0 {to_yolo(418, 179, 536, 279, fw, fh)}"
            ]
            split = "val" if (f == 400) else "train"
            img_file = DATASET_DIR / "images" / split / f"amb_real_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"amb_real_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1
        cap.release()

    west_path = PROJECT_ROOT / "assets" / "videos" / "west.mp4"
    if west_path.exists():
        cap = cv2.VideoCapture(str(west_path))
        print("Processing west.mp4 ambulance...")
        for f in [120, 180, 250, 350, 450]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]
            lines = [
                f"5 {to_yolo(680, 170, 1140, 480, fw, fh)}",
                f"0 {to_yolo(120, 105, 535, 490, fw, fh)}"
            ]
            split = "val" if (f == 250) else "train"
            img_file = DATASET_DIR / "images" / split / f"west_amb_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"west_amb_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1
        cap.release()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Harvest Indian Auto-Rickshaws (Class 4: auto)
    # ──────────────────────────────────────────────────────────────────────────
    auto_path = PROJECT_ROOT / "assets" / "videos" / "13020032_3840_2160_30fps.mp4"
    if auto_path.exists():
        cap = cv2.VideoCapture(str(auto_path))
        print("Processing auto-rickshaw video...")
        for f in [60, 120, 180, 240, 300]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]
            lines = [
                f"4 {to_yolo(100, 300, 900, 1200, fw, fh)}",
                f"0 {to_yolo(1200, 400, 2000, 1300, fw, fh)}"
            ]
            split = "val" if (f == 180) else "train"
            img_file = DATASET_DIR / "images" / split / f"auto_indian_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"auto_indian_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1
        cap.release()

    print(f"\n[Dataset] Total curated keyframe samples: {samples_created}")

    data_yaml = {
        "path": str(DATASET_DIR).replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "names": CLASSES
    }
    yaml_path = DATASET_DIR / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, default_flow_style=False)
    print(f"[Dataset] Written data.yaml to {yaml_path}")
    return str(yaml_path)

def train_accident_model(yaml_path: str):
    print("\n" + "=" * 65)
    print("TRAINING NEURAL MODEL WITH SPECIALIZED ACCIDENT CLASS 6")
    print("=" * 65)

    base_model_path = PROJECT_ROOT / "models" / "best_indian_traffic.pt"
    if not base_model_path.exists():
        base_model_path = PROJECT_ROOT / "models" / "yolov8n.pt"

    print(f"[Training] Base neural network: {base_model_path}")
    model = YOLO(str(base_model_path))

    epochs = 4
    imgsz = 416
    batch = 4

    print(f"[Training] Hyperparameters: epochs={epochs}, imgsz={imgsz}, batch={batch}, device=cpu")
    run_dir = PROJECT_ROOT / "runs" / "train"
    results = model.train(
        data=yaml_path,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device="cpu",
        workers=0,
        project=str(run_dir),
        name="accident_traffic_run",
        exist_ok=True,
        verbose=True
    )

    best_pt = run_dir / "accident_traffic_run" / "weights" / "best.pt"
    last_pt = run_dir / "accident_traffic_run" / "weights" / "last.pt"
    src_pt = best_pt if best_pt.exists() else last_pt

    target_best = PROJECT_ROOT / "models" / "best_indian_traffic.pt"
    target_compat = PROJECT_ROOT / "models" / "best (12).pt"
    target_accident = PROJECT_ROOT / "models" / "accident_best.pt"

    if src_pt.exists():
        shutil.copy2(str(src_pt), str(target_best))
        shutil.copy2(str(src_pt), str(target_compat))
        shutil.copy2(str(src_pt), str(target_accident))
        print(f"\n[Training] SUCCESS: Exported fine-tuned accident model weights to:")
        print(f"  -> {target_best}")
        print(f"  -> {target_compat}")
        print(f"  -> {target_accident}")
    else:
        print("[Training] Warning: trained weights not found at expected run location.")

    print("=" * 65)
    print("ACCIDENT MODEL RETRAINING COMPLETE")
    print("=" * 65)

if __name__ == "__main__":
    setup_dirs()
    yaml_file = harvest_dataset()
    train_accident_model(yaml_file)
