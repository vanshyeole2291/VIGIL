# VIGIL — YOLOv8 Emergency Vehicle Retraining & Deployment Guide
## Visual Detection Pipeline (Primary) with Acoustic Fallback (Secondary)

---

## 1. Architectural Overview & Priority Hierarchy

In **VIGIL**, the emergency corridor clearance system operates on a **two-tier priority hierarchy**:

```
                                  +---------------------------------------+
                                  |   Intersection Approach CCTV Feeds    |
                                  +---------------------------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |     YOLOv8 Edge Perception Engine     |
                                  |  (Class: ambulance, fire_truck, etc.) |
                                  +---------------------------------------+
                                                      |
                          [Visual Detection Positive] | [Visual Detection Negative/Occluded]
                                                      v                      v
                             ==================================   +--------------------+
                             | PRIMARY TRIGGER (Visual)       |   | Acoustic Siren FFT |
                             | Immediate Class-1 Preemption   |   | Energy 600-1600 Hz |
                             ==================================   +--------------------+
                                                      |                      |
                                                      |      [Siren Sound]   v
                                                      |   ================================
                                                      |   | SECONDARY FALLBACK (Acoustic)|
                                                      |   | Preempts on Siren Audio      |
                                                      |   ================================
                                                      |                      |
                                                      +----------+-----------+
                                                                 |
                                                                 v
                                  +-----------------------------------------------+
                                  |      ATSC Signal Optimizer (Webster/Phase)    |
                                  |  All-Red Clearance -> GREEN Corridor Granted |
                                  +-----------------------------------------------+
```

1. **PRIMARY TRIGGER — Visual Detection (YOLOv8)**:
   Visual detection of an **Ambulance** or **Fire Truck** in any intersection approach quadrant is the authoritative, primary trigger. Upon visual recognition, the signal optimizer immediately initiates clearance and holds a continuous green wave corridor for the emergency vehicle.
   
2. **SECONDARY FALLBACK — Acoustic Siren FFT (600–1600 Hz)**:
   If visual line-of-sight is obstructed (e.g., dense vehicle occlusion, blind building corners, or bad weather), the Acoustic Siren FFT spectral analyzer detects approaching siren harmonics and engages green preemption before the vehicle is visually acquired.

---

## 2. Step 1: Downloading an Emergency Vehicle Dataset from Roboflow

Standard generic COCO models (80 classes) often misclassify emergency vehicles as standard cars, trucks, or buses. To achieve reliable visual detection, we fine-tune YOLOv8 on an emergency vehicle dataset.

### Recommended Datasets on Roboflow Universe
Search on [Roboflow Universe](https://universe.roboflow.com):
- **Search Query**: `"Emergency Vehicles Detection YOLOv8"` or `"Ambulance and Fire Truck Detection"`
- **Target Classes**:
  - `ambulance`
  - `fire_truck` (or `fire engine`)
  - Standard vehicles (`car`, `motorcycle`, `bus`, `truck`)

### Download Options

#### Option A: Direct Web Download (Easiest)
1. Go to your selected dataset page on Roboflow Universe.
2. Click **Download Dataset** in the top-right corner.
3. Select Format: **YOLOv8**.
4. Choose **download zip to computer**.
5. Extract the downloaded ZIP contents into:
   ```
   c:\Users\yeole\Downloads\VIGIL\dataset\emergency_vehicles\
   ```

#### Option B: Programmatic Python Download
If you have a Roboflow API key:
```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")
project = rf.workspace("roboflow-100").project("emergency-vehicles-nxw0s")
version = project.version(2)
dataset = version.download("yolov8", location="../dataset/emergency_vehicles")
```

---

## 3. Step 2: Verifying Directory Structure & Config

Verify that your extracted dataset matches the following directory layout:

```
VIGIL/
├── dataset/
│   └── emergency_vehicles/
│       ├── images/
│       │   ├── train/        # Training images (.jpg, .png)
│       │   └── val/          # Validation images (.jpg, .png)
│       └── labels/
│           ├── train/        # Bounding box annotations (.txt)
│           └── val/          # Bounding box annotations (.txt)
├── scripts/
│   ├── emergency_data.yaml   # Dataset YAML configuration
│   └── train_emergency_yolo.py # Fine-tuning script
└── models/
    └── best.pt               # Deployed model weights
```

### Inspecting `scripts/emergency_data.yaml`
Ensure `scripts/emergency_data.yaml` matches your dataset's class mapping:
```yaml
path: ../dataset/emergency_vehicles
train: images/train
val: images/val
test: images/test

names:
  0: car
  1: motorcycle
  2: bus
  3: truck
  4: ambulance
  5: fire_truck
```

---

## 4. Step 3: Running Local GPU Training

### Prerequisites
- Python 3.11 with virtual environment activated (`.venv`).
- NVIDIA GPU with CUDA drivers installed (e.g., RTX 3050, 3060, 4060 or higher).

### Execute Training
Run the training pipeline from the project root:

```powershell
# Standard GPU Fine-Tuning (50 Epochs, Batch 16, 640px)
.\.venv\Scripts\python.exe scripts/train_emergency_yolo.py --epochs 50 --batch 16 --imgsz 640 --device 0

# Lower VRAM Setup (4GB - 6GB GPUs)
.\.venv\Scripts\python.exe scripts/train_emergency_yolo.py --epochs 50 --batch 8 --imgsz 640 --device 0

# Quick Smoke Test (Verify pipeline on CPU)
.\.venv\Scripts\python.exe scripts/train_emergency_yolo.py --epochs 1 --batch 2 --imgsz 320 --device cpu
```

The script automatically:
1. Validates image paths in `scripts/emergency_data.yaml`.
2. Loads existing weights (`models/best.pt` or `models/yolov8n.pt`).
3. Applies strobe-light and emergency-beacon HSV augmentations.
4. Validates mAP@0.5 and class-specific metrics for `ambulance` and `fire_truck`.
5. Backs up the old checkpoint and copies `best.pt` to `models/best.pt`.

---

## 5. Step 4: Training on Google Colab (Free T4 GPU)

If your local machine does not have a dedicated NVIDIA GPU, use Google Colab:

1. Open [Google Colab](https://colab.research.google.com) and create a **New Notebook**.
2. Select **Runtime > Change runtime type > T4 GPU**.
3. Run the following cells in sequence:

```python
# Cell 1: Install Ultralytics and dependencies
!pip install -q ultralytics pyyaml

# Cell 2: Check GPU availability
import torch
print("GPU Available:", torch.cuda.is_available(), "-", torch.cuda.get_device_name(0))
```

```python
# Cell 3: Download your Roboflow dataset
!pip install -q roboflow
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")
project = rf.workspace("WORKSPACE_NAME").project("PROJECT_NAME")
version = project.version(1)
dataset = version.download("yolov8")
```

```python
# Cell 4: Train YOLOv8 with Ultralytics
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # or upload your models/best.pt

results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    device=0,
    name="emergency_vehicle_colab",
    hsv_h=0.025,
    hsv_s=0.7,
    hsv_v=0.4
)
```

```python
# Cell 5: Download the trained best.pt
from google.colab import files
files.download("runs/detect/emergency_vehicle_colab/weights/best.pt")
```

4. Place the downloaded `best.pt` into your local `VIGIL/models/best.pt`.

---

## 6. Step 5: Verifying in the VIGIL Command Center

Once the trained weights are saved in `models/best.pt`:

1. **Launch VIGIL**:
   ```powershell
   .\.venv\Scripts\python.exe run_4way.py --port 8000
   ```
2. Open your browser to `http://localhost:8000`.
3. In the **Traffic Perception** view, observe visual detections:
   - When an **Ambulance** or **Fire Truck** enters any lane, a prominent Class-1 Emergency HUD banner appears.
   - The signal optimizer automatically grants an immediate **GREEN corridor** to that lane.
   - If visual detection is momentarily obstructed, the **Acoustic Siren FFT** indicator acts as the secondary guarantee.
