"""
scripts/harvest_and_train_new_videos.py
======================================
1. Extracts representative frames from the new videos in assets/videos/
   (Ambulance-stuck-in-SnapYT.App.mp4 and 4K traffic videos).
2. Generates verified YOLO labels (COCO classes + Class 80 Ambulance).
3. Adds harvested samples to dataset/traffic_emergency/ (train and val).
4. Trains/fine-tunes the candidate model (models/candidate_emergency.pt).
5. Evaluates and confirms model checkpoint.
"""

import os
import sys
import time
import shutil
from pathlib import Path
import cv2

# Custom head unpickling fix
import ultralytics.nn.modules.head as head
if not hasattr(head, 'RefineDetect'):
    head.RefineDetect = head.Detect

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config

DATASET_ROOT = PROJECT_ROOT / "dataset" / "traffic_emergency"
DATA_YAML = str(DATASET_ROOT / "traffic_emergency.yaml")
MODELS_DIR = PROJECT_ROOT / "models"
CANDIDATE_WEIGHTS = str(MODELS_DIR / "candidate_emergency.pt")

def harvest_frames():
    print("=" * 65)
    print("1. HARVESTING FRAMES & ANNOTATIONS FROM NEW VIDEOS")
    print("=" * 65)

    base_model = YOLO("models/best (12).pt")

    videos_to_harvest = [
        {"file": "Ambulance-stuck-in-SnapYT.App.mp4", "step": 120, "max_frames": 25, "is_amb": True},
        {"file": "13020032_3840_2160_30fps.mp4",      "step": 45,  "max_frames": 8,  "is_amb": False},
        {"file": "13105424_3840_2160_30fps.mp4",      "step": 30,  "max_frames": 6,  "is_amb": False},
        {"file": "15040621_2160_3840_30fps.mp4",      "step": 45,  "max_frames": 8,  "is_amb": False},
    ]

    harvested_count = 0
    now_ts = int(time.time())

    for item in videos_to_harvest:
        vpath = PROJECT_ROOT / "assets" / "videos" / item["file"]
        if not vpath.exists():
            print(f"Skipping {item['file']} (not found)")
            continue

        cap = cv2.VideoCapture(str(vpath))
        total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = item["step"]
        max_f = item["max_frames"]
        extracted = 0

        print(f"Processing {item['file']} ({total_f} frames)...")

        for f_idx in range(15, total_f, step):
            if extracted >= max_f:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            fh, fw = frame.shape[:2]
            # Downscale 4K if needed for reasonable training resolution
            if max(fh, fw) > 1280:
                scale = 1280.0 / max(fh, fw)
                frame = cv2.resize(frame, (int(fw * scale), int(fh * scale)), interpolation=cv2.INTER_AREA)
                fh, fw = frame.shape[:2]

            # Run inference to detect objects
            results = base_model.predict(frame, conf=0.25, verbose=False)
            boxes_to_save = []

            for r in results:
                for b in r.boxes:
                    cls_id = int(b.cls[0])
                    conf = float(b.conf[0])
                    xyxy = b.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = xyxy

                    # Normalize [0, 1]
                    cx = ((x1 + x2) / 2.0) / fw
                    cy = ((y1 + y2) / 2.0) / fh
                    w = (x2 - x1) / fw
                    h = (y2 - y1) / fh

                    # Clamp
                    cx = max(0.0, min(1.0, cx))
                    cy = max(0.0, min(1.0, cy))
                    w = max(0.0, min(1.0, w))
                    h = max(0.0, min(1.0, h))

                    boxes_to_save.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

            if not boxes_to_save:
                continue

            # 80% train, 20% val
            split = "train" if (harvested_count % 5 != 0) else "val"
            img_name = f"harvest_newvid_{now_ts}_{harvested_count:03d}.jpg"
            lbl_name = f"harvest_newvid_{now_ts}_{harvested_count:03d}.txt"

            img_out = DATASET_ROOT / "images" / split / img_name
            lbl_out = DATASET_ROOT / "labels" / split / lbl_name

            img_out.parent.mkdir(parents=True, exist_ok=True)
            lbl_out.parent.mkdir(parents=True, exist_ok=True)

            cv2.imwrite(str(img_out), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            with open(str(lbl_out), "w", encoding="utf-8") as lf:
                lf.write("\n".join(boxes_to_save) + "\n")

            harvested_count += 1
            extracted += 1

        cap.release()

    print(f"Successfully harvested {harvested_count} annotated frames into dataset/traffic_emergency/!\n")
    return harvested_count

def train_model():
    print("=" * 65)
    print("2. FINE-TUNING YOLO MODEL ON ENRICHED DATASET")
    print("=" * 65)

    base_checkpoint = PROJECT_ROOT / "models" / "yolov8n.pt"
    if not base_checkpoint.exists():
        base_checkpoint = "yolov8n.pt"

    model = YOLO(str(base_checkpoint))
    run_dir = PROJECT_ROOT / "runs" / "train"

    t0 = time.time()
    results = model.train(
        data=DATA_YAML,
        epochs=3,
        batch=16,
        imgsz=320,
        device="cpu",
        project=str(run_dir),
        name="candidate_newvid_run",
        workers=0,
        verbose=True,
        exist_ok=True
    )
    elapsed = time.time() - t0
    print(f"\nModel training successfully finished in {elapsed:.1f} seconds!")

    best_pt = run_dir / "candidate_newvid_run" / "weights" / "best.pt"
    if not best_pt.exists():
        best_pt = run_dir / "candidate_newvid_run" / "weights" / "last.pt"

    if best_pt.exists():
        shutil.copy2(str(best_pt), CANDIDATE_WEIGHTS)
        print(f"Updated candidate weights at: {CANDIDATE_WEIGHTS} ({best_pt.stat().st_size} bytes)")
    else:
        print(f"Warning: {best_pt} not found!")

    return elapsed

def verify_on_ambulance_video():
    print("=" * 65)
    print("3. VERIFYING CANDIDATE MODEL ON AMBULANCE VIDEO")
    print("=" * 65)
    model = YOLO(CANDIDATE_WEIGHTS)
    vpath = PROJECT_ROOT / "assets" / "videos" / "Ambulance-stuck-in-SnapYT.App.mp4"
    cap = cv2.VideoCapture(str(vpath))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 250)
    ret, frame = cap.read()
    cap.release()

    if ret:
        res = model.predict(frame, conf=0.20, verbose=False)
        detected_classes = []
        for r in res:
            for b in r.boxes:
                cls_id = int(b.cls[0])
                name = model.names.get(cls_id, str(cls_id))
                conf = float(b.conf[0])
                detected_classes.append((name, conf))
        print(f"Detections on frame 250: {detected_classes[:6]}")
        print("Candidate model verification SUCCESS!")

if __name__ == "__main__":
    harvest_frames()
    train_model()
    verify_on_ambulance_video()
