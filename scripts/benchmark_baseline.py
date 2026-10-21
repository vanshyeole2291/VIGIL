"""
scripts/benchmark_baseline.py — Baseline Performance & Latency Benchmark
=========================================================================
Runs baseline inference with models/best.pt on the 4 intersection videos,
recording latency (ms), throughput (FPS), class counts, and detection stats.
Saves results to reports/baseline_benchmark.json.
"""

import time
import os
import json
import cv2
import numpy as np

import ultralytics.nn.modules.head as head
if not hasattr(head, 'RefineDetect'):
    head.RefineDetect = head.Detect
from ultralytics import YOLO

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def benchmark_baseline(num_frames=60):
    model_path = os.path.join(config.BASE_DIR, "models", "best.pt")
    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        return

    print(f"[Benchmark] Loading baseline model: {model_path}")
    t0 = time.time()
    model = YOLO(model_path)
    load_time_sec = round(time.time() - t0, 3)
    
    num_params = sum(p.numel() for p in model.model.parameters()) if hasattr(model, 'model') else 0
    names = model.names
    
    video_sources = [
        ("north", os.path.join(config.BASE_DIR, "assets", "videos", "north.mp4")),
        ("south", os.path.join(config.BASE_DIR, "assets", "videos", "south.mp4")),
        ("east",  os.path.join(config.BASE_DIR, "assets", "videos", "east.mp4")),
        ("west",  os.path.join(config.BASE_DIR, "assets", "videos", "ambulance_emergency_corridor.mp4")),
    ]
    
    latencies = []
    class_detections = {name: 0 for name in names.values()}
    total_detections = 0
    frames_processed = 0

    print(f"[Benchmark] Warming up inference engine on 10 dummy frames...")
    dummy = np.zeros((720, 1280, 3), dtype=np.uint8)
    for _ in range(10):
        _ = model.predict(dummy, imgsz=640, verbose=False)

    print(f"[Benchmark] Benchmarking across intersection video feeds ({num_frames} frames per video)...")
    for feed_name, v_path in video_sources:
        if not os.path.exists(v_path):
            print(f"[Benchmark] Skipping {feed_name}: {v_path} not found.")
            continue
        
        cap = cv2.VideoCapture(v_path)
        feed_frames = 0
        while cap.isOpened() and feed_frames < num_frames:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            
            t_start = time.perf_counter()
            results = model.predict(frame, imgsz=640, conf=0.30, verbose=False)
            t_inf = (time.perf_counter() - t_start) * 1000.0  # ms
            
            latencies.append(t_inf)
            feed_frames += 1
            frames_processed += 1
            
            for r in results:
                for b in r.boxes:
                    cls_id = int(b.cls[0].item())
                    label = names.get(cls_id, f"class_{cls_id}")
                    class_detections[label] = class_detections.get(label, 0) + 1
                    total_detections += 1
        cap.release()

    latencies_arr = np.array(latencies)
    avg_latency = float(np.mean(latencies_arr))
    p50_latency = float(np.median(latencies_arr))
    p95_latency = float(np.percentile(latencies_arr, 95))
    fps = round(1000.0 / avg_latency, 1) if avg_latency > 0 else 0.0

    # Top detected classes
    sorted_classes = sorted([(k, v) for k, v in class_detections.items() if v > 0], key=lambda x: x[1], reverse=True)

    metrics = {
        "model_file": os.path.relpath(model_path, config.BASE_DIR),
        "model_size_bytes": os.path.getsize(model_path),
        "parameters": num_params,
        "classes_count": len(names),
        "classes": names,
        "load_time_sec": load_time_sec,
        "frames_evaluated": frames_processed,
        "latency_ms": {
            "mean": round(avg_latency, 2),
            "p50": round(p50_latency, 2),
            "p95": round(p95_latency, 2),
            "min": round(float(np.min(latencies_arr)), 2),
            "max": round(float(np.max(latencies_arr)), 2),
        },
        "approx_fps": fps,
        "total_detections": total_detections,
        "class_detections": dict(sorted_classes),
    }

    os.makedirs(os.path.join(config.BASE_DIR, "reports"), exist_ok=True)
    report_path = os.path.join(config.BASE_DIR, "reports", "baseline_benchmark.json")
    with open(report_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print("\n" + "=" * 60)
    print("BASELINE MODEL AUDIT & BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Model Checkpoint:     {metrics['model_file']} ({metrics['model_size_bytes']:,} bytes)")
    print(f"Total Parameters:     {metrics['parameters']:,}")
    print(f"Number of Classes:    {metrics['classes_count']}")
    print(f"Ambulance Class 80:   '{names.get(80, 'MISSING')}'")
    print(f"Mean Latency:         {metrics['latency_ms']['mean']} ms ({fps} FPS)")
    print(f"Median (p50) Latency: {metrics['latency_ms']['p50']} ms")
    print(f"p95 Latency:          {metrics['latency_ms']['p95']} ms")
    print(f"Frames Evaluated:     {frames_processed}")
    print(f"Total Detections:     {total_detections}")
    print("Top Detections Breakdown:")
    for cls_name, count in sorted_classes[:8]:
        print(f"  - {cls_name}: {count} detections")
    print(f"\nReport written to: {report_path}")
    print("=" * 60)

if __name__ == '__main__':
    benchmark_baseline()
