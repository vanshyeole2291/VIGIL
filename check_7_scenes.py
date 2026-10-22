import cv2
import sys
from ultralytics import YOLO

sys.stdout.reconfigure(line_buffering=True)

model = YOLO("models/best_indian_traffic.pt")
cap = cv2.VideoCapture("assets/videos/south.mp4")

scenes = [
    (1, 0, 257, "Orange car crash"),
    (2, 259, 618, "Night junction car crash"),
    (3, 619, 986, "Truck collision & dust"),
    (4, 987, 1141, "Damaged car on roadside"),
    (5, 1142, 1741, "Highway multi-car crash with people"),
    (6, 1742, 1981, "T-bone collision"),
    (7, 1983, 2297, "Guardrail crash")
]

print("=== CHECKING YOLO ON ALL 7 ACCIDENT SCENES (SOUTH.MP4) ===")
for s_num, s_start, s_end, name in scenes:
    print(f"\nScene {s_num}: frames {s_start}..{s_end} ({name})")
    acc_frames = []
    # Sample 10 frames evenly in this scene
    step = max(1, (s_end - s_start) // 10)
    for f in range(s_start, s_end, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if not ret: break
        res = model(frame, conf=0.15, verbose=False)[0]
        acc_boxes = []
        for b in res.boxes:
            cls_id = int(b.cls[0])
            lbl = model.names[cls_id]
            conf = float(b.conf[0])
            if cls_id == 6 or lbl == "accident":
                acc_boxes.append((conf, tuple(map(int, b.xyxy[0]))))
        if acc_boxes:
            acc_frames.append((f, acc_boxes))
    print(f"  Total frames checked with 'accident': {len(acc_frames)}/{11}")
    if acc_frames:
        for f, bxs in acc_frames[:3]:
            print(f"    Frame {f}: {[f'conf={c:.2f} box={bx}' for c, bx in bxs]}")
    else:
        print("  --> NO ACCIDENT DETECTIONS in this scene!")

cap.release()
