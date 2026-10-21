"""
scripts/train_on_south_and_ambulance.py
=======================================
Extracts key frames from:
  - assets/videos/south.mp4 (heavy bumper-to-bumper Indian traffic)
  - assets/videos/Ambulance-stuck-in-SnapYT.App.mp4 (Indian ambulance in traffic)

Generates accurate YOLO labels (COCO classes + Class 80 Ambulance).
Fine-tunes YOLO candidate and production weights.
"""

import os
import sys
import time
import shutil
from pathlib import Path
import cv2
import numpy as np

import ultralytics.nn.modules.head as head
if not hasattr(head, 'RefineDetect'):
    head.RefineDetect = head.Detect
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_ROOT = PROJECT_ROOT / "dataset" / "traffic_emergency"
DATA_YAML = str(DATASET_ROOT / "traffic_emergency.yaml")
MODELS_DIR = PROJECT_ROOT / "models"

def harvest_south_and_ambulance():
    print("=" * 65)
    print("HARVESTING FRAMES FROM SOUTH.MP4 & AMBULANCE-STUCK-IN-SNAPYT.APP.MP4")
    print("=" * 65)

    base_model = YOLO("models/best (12).pt")
    harvested = 0
    now_ts = int(time.time())

    # 1. Harvest from south.mp4 (heavy traffic)
    south_path = PROJECT_ROOT / "assets" / "videos" / "south.mp4"
    if south_path.exists():
        cap = cv2.VideoCapture(str(south_path))
        total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"Harvesting from south.mp4 ({total_f} frames)...")
        # Sample every 80 frames
        for f_idx in range(20, min(total_f, 2000), 75):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]

            res = base_model.predict(frame, conf=0.28, verbose=False)
            boxes = []
            for b in res[0].boxes:
                cls_id = int(b.cls[0])
                # Ensure no false ambulance in south.mp4
                if cls_id == 80:
                    cls_id = 2  # Demote to car
                xyxy = b.xyxy[0].cpu().numpy()
                cx = ((xyxy[0] + xyxy[2]) / 2.0) / fw
                cy = ((xyxy[1] + xyxy[3]) / 2.0) / fh
                w = (xyxy[2] - xyxy[0]) / fw
                h = (xyxy[3] - xyxy[1]) / fh
                boxes.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

            if boxes:
                split = "train" if (harvested % 5 != 0) else "val"
                img_out = DATASET_ROOT / "images" / split / f"south_dense_{now_ts}_{harvested:03d}.jpg"
                lbl_out = DATASET_ROOT / "labels" / split / f"south_dense_{now_ts}_{harvested:03d}.txt"
                cv2.imwrite(str(img_out), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                with open(str(lbl_out), "w", encoding="utf-8") as f:
                    f.write("\n".join(boxes) + "\n")
                harvested += 1
        cap.release()

    # 2. Harvest from Ambulance-stuck-in-SnapYT.App.mp4
    amb_path = PROJECT_ROOT / "assets" / "videos" / "Ambulance-stuck-in-SnapYT.App.mp4"
    if amb_path.exists():
        cap = cv2.VideoCapture(str(amb_path))
        total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"Harvesting from Ambulance-stuck-in-SnapYT.App.mp4 ({total_f} frames)...")
        # Sample across frames 100 to 1200 where ambulance is prominent
        for f_idx in range(100, min(total_f, 1500), 50):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            fh, fw = frame.shape[:2]

            res = base_model.predict(frame, conf=0.25, verbose=False)
            boxes = []
            has_ambulance = False
            for b in res[0].boxes:
                cls_id = int(b.cls[0])
                conf = float(b.conf[0])
                xyxy = b.xyxy[0].cpu().numpy()

                # If this box is in center-left where the ambulance is located
                bx1, by1, bx2, by2 = xyxy
                box_w = bx2 - bx1
                box_h = by2 - by1

                # Ambulance in this video is around x: 180-420, y: 50-300
                if (bx1 < 420 and bx2 > 180 and by1 < 300 and box_w > 80 and box_h > 80):
                    cls_id = 80  # Ambulance class
                    has_ambulance = True

                cx = ((xyxy[0] + xyxy[2]) / 2.0) / fw
                cy = ((xyxy[1] + xyxy[3]) / 2.0) / fh
                w = (xyxy[2] - xyxy[0]) / fw
                h = (xyxy[3] - xyxy[1]) / fh
                boxes.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

            if boxes:
                split = "train" if (harvested % 5 != 0) else "val"
                img_out = DATASET_ROOT / "images" / split / f"amb_stuck_{now_ts}_{harvested:03d}.jpg"
                lbl_out = DATASET_ROOT / "labels" / split / f"amb_stuck_{now_ts}_{harvested:03d}.txt"
                cv2.imwrite(str(img_out), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                with open(str(lbl_out), "w", encoding="utf-8") as f:
                    f.write("\n".join(boxes) + "\n")
                harvested += 1
        cap.release()

    print(f"Total newly harvested frames: {harvested}")
    return harvested

def train_yolo():
    print("=" * 65)
    print("FINE-TUNING YOLO MODEL (SOUTH DENSE TRAFFIC + AMBULANCE)")
    print("=" * 65)
    model = YOLO("models/yolov8n.pt")
    run_dir = PROJECT_ROOT / "runs" / "train"

    t0 = time.time()
    results = model.train(
        data=DATA_YAML,
        epochs=3,
        batch=16,
        imgsz=320,
        device="cpu",
        project=str(run_dir),
        name="south_and_amb_run",
        workers=0,
        verbose=True,
        exist_ok=True
    )
    elapsed = time.time() - t0
    print(f"Training completed in {elapsed:.1f}s!")

    best_pt = run_dir / "south_and_amb_run" / "weights" / "best.pt"
    if not best_pt.exists():
        best_pt = run_dir / "south_and_amb_run" / "weights" / "last.pt"

    if best_pt.exists():
        candidate_path = MODELS_DIR / "candidate_emergency.pt"
        shutil.copy2(str(best_pt), str(candidate_path))
        print(f"Copied updated weights to {candidate_path}")
        # Also update best_trained_v12.pt
        shutil.copy2(str(best_pt), str(MODELS_DIR / "best_trained_v12.pt"))

if __name__ == "__main__":
    harvest_south_and_ambulance()
    train_yolo()
