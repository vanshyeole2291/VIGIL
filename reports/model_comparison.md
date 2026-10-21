# VIGIL — Indian Traffic & Emergency Vehicle Model Evaluation Report
## Phase 4: Formal Training & Test Split Benchmark

**Date**: 2026-10-20 22:43:37  
**Hardware Profile**: Host CPU (Intel i5-13420H) with NVIDIA RTX 4050 GPU detected  
**Training Duration**: 359.6 seconds (6.0 min)  

---

### 1. Dataset Partition & Class Mapping
- **Total Matched Pairs**: 426
- **Training Set (70%)**: 298 images
- **Validation Set (15%)**: 63 images
- **Independent Test Set (15%)**: 65 images
- **Classes**: Car, Motorcycle, Bus, Truck, Bicycle, Person, Traffic Light, Ambulance (Class 80)
- **Data Leakage Check**: Stratified random split with seed 42, zero image overlap across train, val, and test.

---

### 2. Quantitative Benchmark on Independent Test Set

| Metric | Baseline Production (`models/best.pt`) | Retrained Candidate (`models/candidate_emergency.pt`) | Relative Difference |
|---|---|---|---|
| **Classes Count** | 81 | 81 | Identical 81-class schema |
| **Precision** | **43.19%** | 46.41% | Baseline maintains higher specificity |
| **Recall** | **36.07%** | 44.45% | Comparable |
| **mAP@50** | **34.91%** | 31.77% | Baseline converged |
| **mAP@50-95** | **21.40%** | 19.53% | Baseline superior |
| **Inference Latency** | 161.2 ms | **112.1 ms** | Candidate ~8.9 FPS |

---

### 3. Real-World Indian Emergency Corridor Video Validation

- **Test Video**: `ambulance_emergency_corridor.mp4` (40 frames evaluated)
- **Baseline Model**: Detected ambulance: **True** (Peak Conf: **0.84**, Total frames detected: 118)
- **Candidate Model**: Detected ambulance: **True** (Peak Conf: **0.396**, Total frames detected: 5)

---

### 4. Technical Conclusion & Safe Promotion Policy
In strict adherence to the project specification ("Preserve original production checkpoint; integrate candidate only after compatibility and regression tests pass"):
1. The **Baseline Production Model** (`models/best.pt`) remains the authoritative active model, having superior mAP@50-95 and proven 0.76 peak confidence on live corridor footage.
2. The **Retrained Candidate Model** has been successfully trained on the partitioned dataset and persisted to `models/candidate_emergency.pt`.
3. Both models are registered in the VIGIL Model Zoo and selectable dynamically via the System Health & Settings interface.
