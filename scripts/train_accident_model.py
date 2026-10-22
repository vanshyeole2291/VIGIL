"""
scripts/train_accident_model.py
================================
Accident Perception & Multi-Class Retraining Pipeline
- Extracts keyframe pairs for vehicle accidents from all 7 scenes in south.mp4 and ai_south_accident.mp4
- Labels genuine vehicle collisions as Class 6: 'accident'
- Provides explicit negative samples for normal cars (Class 0), buses (Class 2), and trucks/vans (Class 3)
  so normal vehicles, vans, and transit buses in south.mp4 are NEVER misclassified as ambulances
- Curates verified ambulances (Class 5) from west.mp4 and Ambulance-stuck-in-SnapYT.App.mp4
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
    print("HARVESTING GROUND-TRUTH MULTI-CLASS ACCIDENTS & TRAFFIC SAMPLES")
    print("=" * 65)
    
    samples_created = 0

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Harvest All 7 Accident Scenes from assets/videos/south.mp4
    # ──────────────────────────────────────────────────────────────────────────
    south_path = PROJECT_ROOT / "assets" / "videos" / "south.mp4"
    if south_path.exists():
        cap = cv2.VideoCapture(str(south_path))
        print("Processing south.mp4 for all 7 accident scenes...")
        
        # Scene 1: Orange car collision (frames 160-257)
        for f in [160, 180, 200, 220, 235, 238, 242, 248, 252, 255]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"6 {to_yolo(180, 150, 390, 298, fw, fh)}",  # Class 6: accident
                f"0 {to_yolo(48, 117, 182, 196, fw, fh)}"   # Class 0: car
            ]
            split = "val" if (f in [200, 248]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_sc1_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_sc1_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # Scene 2: Smashed white car in dark junction (frames 270-618)
        for f in [280, 320, 360, 400, 440, 480, 518, 530, 550, 580, 600, 615]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"6 {to_yolo(470, 105, 555, 178, fw, fh)}",  # Class 6: accident
                f"0 {to_yolo(398, 166, 499, 359, fw, fh)}"   # Class 0: car
            ]
            split = "val" if (f in [360, 600]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_sc2_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_sc2_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # Scene 3: Truck collision with dust cloud (frames 660-985)
        for f in [660, 700, 760, 820, 880, 920, 960, 970, 975, 980, 985]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"6 {to_yolo(470, 210, 630, 370, fw, fh)}",  # Class 6: accident
                f"0 {to_yolo(90, 117, 171, 163, fw, fh)}"    # Class 0: car
            ]
            split = "val" if (f in [760, 980]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_sc3_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_sc3_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # Scene 4: Damaged white car in roadside rubble (frames 990-1140)
        for f in [1000, 1030, 1060, 1090, 1110, 1120, 1125, 1130, 1135, 1140]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"6 {to_yolo(80, 50, 435, 190, fw, fh)}",    # Class 6: accident (NOT ambulance)
                f"0 {to_yolo(559, 39, 639, 92, fw, fh)}"     # Class 0: car
            ]
            split = "val" if (f in [1060, 1130]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_sc4_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_sc4_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # Scene 5: Highway multi-car crash with people (frames 1180-1740)
        for f in [1200, 1260, 1320, 1380, 1440, 1500, 1560, 1620, 1680, 1710, 1720, 1725, 1730, 1735, 1740]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"6 {to_yolo(20, 120, 480, 358, fw, fh)}",   # Class 6: accident
                f"3 {to_yolo(415, 75, 575, 200, fw, fh)}"    # Class 3: truck/van (NOT ambulance!)
            ]
            split = "val" if (f in [1380, 1730]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_sc5_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_sc5_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # Scene 6: Intersection T-bone collision (frames 1760-1980)
        for f in [1760, 1800, 1840, 1880, 1920, 1960, 1965, 1970, 1975, 1980]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"6 {to_yolo(255, 65, 445, 235, fw, fh)}",   # Class 6: accident
                f"0 {to_yolo(0, 208, 101, 357, fw, fh)}"     # Class 0: car
            ]
            split = "val" if (f in [1840, 1975]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_sc6_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_sc6_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # Scene 7: Guardrail collision (frames 2010-2295)
        for f in [2020, 2050, 2080, 2110, 2140, 2170, 2200, 2230, 2250, 2260, 2270, 2280, 2290]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"6 {to_yolo(85, 105, 225, 175, fw, fh)}",   # Class 6: accident
                f"0 {to_yolo(511, 107, 580, 161, fw, fh)}"   # Class 0: car
            ]
            split = "val" if (f in [2110, 2270]) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_sc7_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_sc7_{f}.txt"
            cv2.imwrite(str(img_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            lbl_file.write_text("\n".join(lines), encoding="utf-8")
            samples_created += 1

        # Transit Bus (Frame 2040) - Class 2: bus (NEVER ambulance)
        for f in [2035, 2040, 2045]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [
                f"2 {to_yolo(0, 74, 244, 241, fw, fh)}",     # Class 2: bus
                f"0 {to_yolo(345, 105, 445, 166, fw, fh)}"   # Class 0: car
            ]
            split = "val" if (f == 2040) else "train"
            img_file = DATASET_DIR / "images" / split / f"south_bus_{f}.jpg"
            lbl_file = DATASET_DIR / "labels" / split / f"south_bus_{f}.txt"
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
        for f in [140, 180, 210, 250, 300, 360]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
            lines = [f"6 {to_yolo(320, 110, 470, 246, fw, fh)}"]
            split = "val" if (f == 210) else "train"
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
        for f in [200, 300, 400, 500, 700]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            fh, fw = frame.shape[:2]
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
        for f in [120, 180, 250, 350]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = cap.read()
            if not ret or frame is None: continue
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
            if not ret or frame is None: continue
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

    epochs = 8
    imgsz = 416
    batch = 8

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
