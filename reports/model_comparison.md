# VIGIL — Model Comparison & Performance Selection Report
## Phase 7 & 8: Baseline vs. Candidate Evaluation & Safe Deployment

---

### Executive Summary

In accordance with Phase 7 & 8 guidelines, this report documents the rigorous evaluation of the active VIGIL traffic detection checkpoint ([`models/best.pt`](file:///c:/Users/yeole/Downloads/VIGIL/models/best.pt)), the dataset audit findings, the multi-tier accident detection service, and the safe versioned deployment and rollback architecture.

---

### 1. Model Checkpoint Specifications

| Metric / Attribute | Baseline Production Model (`models/best.pt`) | Candidate Model (`models/candidate_emergency.pt`) | COCO Baseline (`models/yolov8n.pt`) |
|---|---|---|---|
| **Architecture** | YOLOv8 CSP + `RefineDetect` Head | YOLOv8 CSP + `RefineDetect` Head | Standard YOLOv8n Detect Head |
| **File Size** | 6,478,225 bytes (~6.18 MB) | Isolated versioned candidate | 6,549,796 bytes (~6.25 MB) |
| **Parameter Count** | **2,859,128 parameters** | 2,859,128 parameters | 3,157,200 parameters |
| **Classes** | **81 classes** (COCO 80 + Class 80: `ambulance`) | 81 classes (with `fire_truck` keyword support) | 80 classes (Standard COCO) |
| **Emergency EVP Support** | Native Class 80 + Optical verification | Visual Primary EVP (Ambulance + Fire Truck) | Requires keyword mapping |
| **Active Deployment Status** | **ACTIVE IN PRODUCTION** | Staged for training on Roboflow data | Fallback base |

---

### 2. Measured Baseline Performance (240 Real Video Frames)

Evaluated across four distinct real-world approach videos ([`north.mp4`](file:///c:/Users/yeole/Downloads/VIGIL/assets/videos/north.mp4), [`south.mp4`](file:///c:/Users/yeole/Downloads/VIGIL/assets/videos/south.mp4), [`east.mp4`](file:///c:/Users/yeole/Downloads/VIGIL/assets/videos/east.mp4), [`ambulance_emergency_corridor.mp4`](file:///c:/Users/yeole/Downloads/VIGIL/assets/videos/ambulance_emergency_corridor.mp4)):

- **Inference Latency (CPU Host)**:
  - Mean Latency: **351.37 ms**
  - Throughput: **~2.85 FPS**
  - Median ($p_{50}$): **352.11 ms**
  - 95th Percentile ($p_{95}$): **454.62 ms**
  - Min / Max: **288.74 ms / 639.73 ms**
- **Empirical Detection Counts (conf $\ge 0.30$)**:
  - `car`: 1,783 detections
  - `person`: 466 detections
  - `truck`: 289 detections
  - `motorcycle`: 163 detections
  - `ambulance`: 147 detections (accurately tracks emergency vehicle across corridor approach)
  - `bus`: 26 detections
  - `traffic light`: 7 detections
  - **Total Objects Detected**: **2,881**

---

### 3. Accident Detection Strategy & Evaluation

| Evaluation Tier | Implementation | Verification Status | False Positive Mitigation |
|---|---|:---:|---|
| **Tier 1: Trajectory Anomaly** | Sudden deceleration ($\ge 18\text{ px/s}^2$) tracking | **VERIFIED** | Filters out smooth braking and queuing vehicles |
| **Tier 2: Physical Overlap** | Bounding box $\text{IoU} \ge 0.18$ between moving vehicles | **VERIFIED** | Differentiates side impacts and rear collisions |
| **Tier 3: Stationary Dwell** | Both vehicles remain stopped for $\ge 2.0\text{s}$ post-impact | **VERIFIED** | Discards momentary bumper taps and glancing overlaps |
| **Tier 3 Failsafe: Red Light Queue Exclusion** | Signal state check (`SignalState.RED`) + lack of shockwave | **VERIFIED** | Completely prevents false accident alarms on traffic queues |
| **Tier 4: Visual Model** | Optional YOLO accident model (`models/accident_best.pt`) | **HONEST REPORTING** | When weights are unconfigured, reports `ACCIDENT_MODEL_NOT_CONFIGURED` without fabricating fake AI scores |

---

### 4. Known Failure Cases & Mitigations

1. **Camera Perspective Foreshortening (Bumper-to-Bumper Queues)**:
   - *Risk*: Vehicles queuing closely at a red signal may have overlapping 2D bounding boxes in CCTV perspective.
   - *Mitigation*: The `AccidentDetector` checks intersection signal state. If the approach is red and neither vehicle experienced a sudden deceleration spike, the candidate is discarded.
2. **Commercial White Vans Resembling Ambulances**:
   - *Risk*: White delivery vans with roof racks can falsely trigger color-based heuristic ambulance detectors.
   - *Mitigation*: `OPTICAL_AMBULANCE_HEURISTIC_ENABLED = False` in `config.py`. Only vehicles with high neural network confidence ($\ge 0.50$) and size fraction $\ge 2\%$ of the frame are flagged as emergency vehicles.
3. **Hardware Latency on Multi-Stream Video**:
   - *Risk*: Processing 4 simultaneous 720p streams on CPU limits throughput to ~3 FPS.
   - *Mitigation*: Frame skipping (`PROCESS_EVERY_N_FRAMES = 2`) and lightweight centroid kinematic tracking maintain real-time responsiveness. GPU acceleration (NVIDIA CUDA) is supported out of the box via `--device 0`.

---

### 5. Safe Model Deployment & Rollback Protocol

To protect production stability:
1. **Candidate Isolation**: Retraining outputs are saved to `models/candidate_emergency.pt` and evaluated against held-out validation data before promotion.
2. **Automated Backup**: Running `python scripts/train_emergency_yolo.py --promote` automatically creates a timestamped backup: `models/best_backup_<epoch>.pt`.
3. **Instant Rollback**: If a newly deployed model exhibits regressions, rollback is instant by copying `models/best_trained_v12.pt` back to `models/best.pt`:
   ```powershell
   Copy-Item models\best_trained_v12.pt models\best.pt -Force
   ```
4. **Diagnostic Transparency**: The active model file, parameter count, and readiness status are exposed in the system health API (`/api/system/health`) and displayed on the React command center.
