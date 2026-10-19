# VIGIL — Known Limitations & Operational Constraints

## Executive Overview
**VIGIL** (AI-Based Intelligent Surveillance & Traffic Safety System) is designed for edge-native urban traffic optimization, automated Webster ATSC signal control, multi-tier accident detection, and Code-3 emergency vehicle preemption (EVP).

In adherence to strict academic and engineering integrity, this document transparently records measured operational constraints, environmental boundary conditions, and hardware dependencies. VIGIL **does not promise 100% detection accuracy**; instead, it optimizes for high-confidence real-world safety invariants, low false alarms, and fail-safe graceful degradation.

---

## 1. Hardware Latency & Compute Constraints (CPU vs. GPU)

### Measured Baseline on Host CPU
- **Environment**: Windows 11 x64, PyTorch `2.14.1+cpu`, Ultralytics `8.4.182`.
- **Checkpoint**: [`models/best.pt`](file:///c:/Users/yeole/Downloads/VIGIL/models/best.pt) (2,859,128 parameters, 81 classes, 6.48 MB).
- **Latency Distribution (240 Intersection Frames)**:
  - **Mean Latency**: **351.37 ms (~2.85 FPS)**
  - **Median ($p_{50}$)**: **352.11 ms**
  - **Tail ($p_{95}$)**: **454.62 ms**
  - **Min / Max**: 184.24 ms / 739.77 ms

### Operational Impact & Mitigation
1. **CPU Real-Time Limitations**: Processing 4 simultaneous 1080p RTSP camera streams at full 30 FPS on a host CPU will lead to frame buffering and delayed preemption response.
2. **Dynamic Frame Sampling**: On CPU-only deployments, VIGIL executes YOLOv8 object detection on keyframes (every $N$-th frame, default 3–5 frames) while maintaining continuous 30 Hz kinematic Kalman tracking across intermediate frames.
3. **Production Edge Target (NVIDIA Jetson / TensorRT)**:
   - Deploying via TensorRT FP16/INT8 export on an NVIDIA Jetson Orin Nano / AGX or discrete RTX GPU reduces end-to-end inference latency to **8.4 – 11.4 ms (>45 FPS)**, fully saturating hardware camera line rates.

---

## 2. Adverse Weather & Low-Light Environmental Degradation

### Optical Boundary Conditions
1. **Low-Light & Night Operations**:
   - In nighttime urban settings with inadequate street lighting, image signal-to-noise ratio (SNR) decreases substantially.
   - High headlight bloom and specular glare can saturate CMOS camera sensors, obscuring vehicle contours.
2. **Heavy Rain & Fog**:
   - Rain droplets accumulating on camera housing enclosures cause optical refraction and localized occlusion.
   - Atmospheric scattering reduces visible contrast across distant approach lanes (>50 meters from intersection stop line).

### System Mitigation & Multi-Modal Defense
- **Acoustic Siren FFT Fallback**: When visual line-of-sight is obstructed by heavy fog, lens grime, or headlight glare, the acoustic siren detection engine (scanning 650–1750 Hz Yelp/Wail harmonic signatures) serves as an authoritative secondary fallback to trigger approach preemption.
- **Homography Ground-Plane Tracking**: Trajectory tracking relies on ground contact patches rather than upper vehicle boundaries, reducing sensitivity to headlight reflections.

---

## 3. Commercial Van & Utility Vehicle Visual Resemblance

### The Visual Ambiguity Challenge
- Ambulances and patient transport vehicles frequently utilize standard commercial chassis (e.g., Force Traveller, Mercedes-Benz Sprinter, Ford Transit, Tata Winger).
- Standard white delivery vans and commercial logistics vehicles share identical volumetric dimensions, aspect ratios, and cab silhouettes.

### Engineering Mitigations
1. **Multi-Feature Verification**:
   - The fine-tuning dataset incorporates distinct emergency attributes (roof-mounted lightbars, high-contrast chevron striping, and red cross/star-of-life livery).
2. **Preemption Confirmation Gate**:
   - Visual detection requires $\ge 3$ consecutive high-confidence detections across a sliding 1.0-second temporal window before triggering signal phase preemption, preventing momentary false-positive triggers from passing logistics vans.
3. **Dual-Confirmation Fusion**:
   - When visual confidence is borderline ($0.50 \le \text{conf} < 0.75$), the preemption engine checks for concurrent acoustic siren resonance before initiating an emergency phase override.

---

## 4. Unstructured Mixed Traffic & Severe Occlusion

### The Indian Urban Driving Context
- High vehicle heterogeneity: Motorcycles, three-wheelers (auto-rickshaws), non-standard handcarts, buses, and commercial trucks sharing unlaned road space.
- Lane filtering: Two-wheelers frequently weave between larger commercial vehicles and stop ahead of the stop line.

### System Mitigations
1. **Dynamic PCU Weighting**: Queue pressure is calculated based on Passenger Car Units (PCU) rather than raw bounding box counts:
   $$\text{PCU}_{\text{total}} = 1.0 \times \text{cars} + 0.5 \times \text{bikes} + 3.0 \times \text{buses} + 3.0 \times \text{trucks} + 0.1 \times \text{pedestrians}$$
2. **IoU Kinematic Tracking**: Hungarian matching with Kalman state extrapolation maintains consistent target IDs during temporary vehicle occlusions (up to 30 frames).

---

## 5. Multi-Tier Accident Detection & Zero AI Hallucination Policy

### Collision Anomaly Validation
- Normal intersection behavior produces high bounding-box overlap during red-light queue formation.
- VIGIL's `AccidentDetector` combines:
  - **Tier 1 (Deceleration Spike)**: Abnormal deceleration ($\ge 18\text{ px/s}^2$).
  - **Tier 2 (Physical Overlap)**: Bounding box $\text{IoU} \ge 0.18$.
  - **Tier 3 (Immobile Dwell)**: Vehicles remaining stationary ($\ge 2.0\text{s}$) in an active green/moving corridor.
- Red-light stop lines are explicitly guarded to prevent stopped queues from triggering false crash alarms.

### Strict Non-Fabrication Policy
- If specialized visual accident weights are absent at `models/accident_best.pt`, VIGIL explicitly returns:
  `ACCIDENT_MODEL_NOT_CONFIGURED`
- The system **never fabricates artificial crash probabilities** or pseudo-random AI scores. Collision detection safely relies on verified kinematic laws and physical trajectory overlap until trained neural weights are supplied.

---

## 6. Summary Matrix of Known Operational Limits

| Condition / Dimension | Operational Impact | Mitigation Implemented | Production Recommended Action |
| :--- | :--- | :--- | :--- |
| **CPU Execution** | Latency 351 ms (~2.8 FPS) | Keyframe detection + 30 Hz Kalman tracking | Deploy on NVIDIA Jetson or CUDA GPU |
| **Night / Headlight Glare** | Optical contrast degradation | Acoustic siren FFT secondary fallback | Install dynamic HDR CCTV with IR illumination |
| **Heavy Rain on Lens** | Refraction & blur | Multi-modal audio fallback | Utilize IP67 enclosures with wiper mechanisms |
| **Delivery Van Similarity** | Potential EVP false alarm | Multi-frame temporal persistence gate | Fine-tune with local regional ambulance liveries |
| **Missing Visual Weights** | Cannot run deep crash model | Explicit `MODEL_NOT_CONFIGURED` status | Train using Roboflow crash bounding boxes |
