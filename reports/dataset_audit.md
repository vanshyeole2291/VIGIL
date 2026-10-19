# VIGIL — Public Dataset Audit & Evaluation Report
## Phase 2: Candidate Dataset Assessment for Traffic Safety & Emergency Detection

---

### Executive Summary

To improve the VIGIL computer vision perception system without compromising existing real-world performance or introducing false alarms, we conducted an in-depth audit of four candidate datasets from Roboflow Universe alongside the official Ultralytics YOLOv8 training and validation guidelines.

---

### Candidate Dataset 1: Emergency Vehicle Detection (`cwavf-sa3sp`)
- **Source**: [Roboflow Universe: emergency-vehicle-detection-cwavf-sa3sp](https://universe.roboflow.com/yolov8-ambulance-detection/emergency-vehicle-detection-cwavf-sa3sp)
- **Task Type**: Object Detection (YOLOv8 Bounding Boxes: `class_id x_center y_center width height`)
- **Reported Classes**: `ambulance`, `fire_truck`, `police_car`, `emergency_vehicle`
- **Annotation Format**: YOLOv8 Darknet text files per image.
- **License**: CC BY 4.0 / Open Access (Attribution required).
- **Audit Findings**:
  - **Class Separation**: Some versions merge `ambulance` and `fire_truck` into a single coarse `emergency` label, while higher-quality versions maintain distinct `ambulance` (class 0) and `fire_truck` (class 1) classes.
  - **Scene Diversity**: High daytime variety across European and North American road infrastructure. Limited native Indian road scenes (such as autorickshaws, unstriped lane flow, or congested mixed traffic).
  - **Weather & Lighting**: Moderate sunny and overcast daylight; underrepresented in heavy night glare, monsoon rain, and severe vehicle occlusions.
  - **Data Leakage & Duplicate Risk**: Consecutive video frame extractions observed; splitting must strictly be done by video sequence or camera ID to prevent train/test leakage.
- **Recommendation**: **ACCEPTED FOR TARGETED FINE-TUNING**. High utility for beacon and body geometry features when filtered for clean separate `ambulance` and `fire_truck` annotations.

---

### Candidate Dataset 2: Accident Detection using YOLOv8 (`puyush-fipgg`)
- **Source**: [Roboflow Universe: accident-detection-using-yolov8](https://universe.roboflow.com/puyush-fipgg/accident-detection-using-yolov8)
- **Task Type**: Object Detection (Bounding Boxes for crash scenes).
- **Reported Classes**: `accident`, `severe_damage`, `overturned_vehicle`, with auxiliary traffic classes (`car`, `bike`).
- **Annotation Format**: YOLOv8 format.
- **License**: CC BY 4.0.
- **Audit Findings**:
  - **Annotation Quality**: Bounding boxes wrap the impact zone / damaged vehicle cluster.
  - **Strengths**: Contains real-world CCTV camera angles, intersection crashes, and two-wheeler collisions relevant to urban Indian roads.
  - **Weaknesses**: High variance in annotation tightness. Normal stopped or dense bumper-to-bumper vehicles are occasionally mislabeled as accidents, creating a high risk of false positive alarms in stop-and-go traffic.
- **Recommendation**: **ACCEPTED AS VISUAL EVIDENCE AUXILIARY**. Must NOT be used as a standalone single-frame trigger. Must be coupled with VIGIL's Kinematic Collision Engine (trajectory anomaly + post-impact stationary dwell).

---

### Candidate Dataset 3: Accident / Non-Accident Dataset (`nta-hiqre/accident-z1fpf`)
- **Source**: [Roboflow Universe: accident-z1fpf](https://universe.roboflow.com/nta-hiqre/accident-z1fpf)
- **Task Type**: **Image Classification (Image-level binary labels)**, NOT Bounding-Box Detection.
- **Classes**: `Accident` vs `Non Accident` (folder classification structure).
- **Annotation Format**: Directory hierarchy: `train/Accident/`, `train/Non Accident/`.
- **License**: Community / Academic research.
- **Audit Findings**:
  - **Architectural Incompatibility**: This dataset does NOT provide bounding box coordinates (`xywh`). It cannot be directly trained inside a YOLOv8 detection head without re-annotating with bounding boxes or using a secondary classification backbone (e.g., MobileNet / ResNet / YOLO-cls).
  - **Risk**: Training YOLO detection on whole-image labels causes bounding box collapse and extreme false alarms on normal traffic.
- **Recommendation**: **REJECTED FOR DIRECT YOLO DETECTION**. Can only be used if training an optional secondary frame-level scene classifier.

---

### Candidate Dataset 4: Traffic Accident YOLOv8 (`university-gunadarma`)
- **Source**: [Roboflow Universe: traffic-accident-yolo8](https://universe.roboflow.com/university-gunadarma/traffic-accident-yolo8)
- **Task Type**: Object Detection (YOLOv8 format).
- **Classes**: `accident`, `car_crash`, `motorcycle_fall`.
- **Annotation Format**: YOLOv8 Darknet format.
- **License**: Academic Research (Universitas Gunadarma).
- **Audit Findings**:
  - **Scene Diversity**: Southeast Asian urban traffic scenes closely resembling Indian mixed traffic dynamics (dense motorcycles, mixed lane discipline, overhead junction cameras).
  - **Label Integrity**: High precision annotations focused specifically on deformed panels, overturned motorcycles, and multi-vehicle tangles.
- **Recommendation**: **STRONGLY ACCEPTED FOR ACCIDENT MODEL EXPERIMENTATION**. Complements the kinematic collision logic with high specificity.

---

### Dataset Access & Acquisition Instructions

To safely acquire and train with any Roboflow Universe dataset without hardcoding credentials:

1. **Obtaining a Free API Key**:
   - Sign up or log in at [Roboflow Universe](https://universe.roboflow.com/).
   - Navigate to **User Settings** -> **Roboflow API** -> Copy your **Private API Key**.
   - Set the key as an environment variable in your terminal:
     ```powershell
     $env:ROBOFLOW_API_KEY = "your_actual_api_key_here"
     ```
2. **Alternative (Manual ZIP Extraction)**:
   - On the dataset page, click **Download Dataset** -> Select **Format: YOLOv8** -> **Download ZIP to computer**.
   - Extract the contents into `c:\Users\yeole\Downloads\VIGIL\dataset\<dataset_name>\`.
   - Never commit API keys or raw ZIP credentials to git.

---

### Final Dataset Strategy Recommendation

| Subsystem | Primary Architecture | Dataset Source | Role in VIGIL |
|---|---|---|---|
| **General Traffic Perception** | YOLOv8 (81 Classes) | COCO + Existing fine-tuned weights (`models/best.pt`) | Real-time vehicle counting, PCU estimation, kinematic tracking |
| **Emergency Preemption (EVP)** | YOLOv8 Fine-Tuned | Roboflow Emergency Vehicle (`cwavf-sa3sp`) + synthetic beacon augmentations | Authoritative primary EVP trigger for Ambulances and Fire Trucks |
| **Accident Detection** | Multi-Tier Engine | Kinematic Tracker (Tier 1-3) + Gunadarma/Puyush YOLO (Tier 4) | High-precision accident alarms requiring visual + kinematic confirmation |
