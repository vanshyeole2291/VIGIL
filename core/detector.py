"""
core/detector.py — YOLOv8 Multi-Class Perception & PCU Estimation Engine
========================================================================
Detects vehicles (cars, motorcycles, buses, trucks, bicycles), pedestrians,
and emergency vehicles (ambulances, fire rescue). Computes Passenger Car Unit (PCU)
weights according to IRC:106 / HCM standards.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import ultralytics.nn.modules.head as head
# Ensure custom head architectures like RefineDetect unpickle seamlessly
if not hasattr(head, 'RefineDetect'):
    head.RefineDetect = head.Detect

from typing import List, Dict, Tuple, Optional
import sys
import os

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class Detection:
    """Represents a single detected object with geometric, semantic, and PCU attributes."""
    
    def __init__(self, box: Tuple[int, int, int, int], label: str, confidence: float,
                 class_id: int, is_vehicle: bool, is_person: bool, is_ambulance: bool,
                 pcu: float = 1.0, has_emergency_lights: bool = False,
                 is_fire_truck: bool = False, is_emergency_vehicle: bool = False):
        self.x1, self.y1, self.x2, self.y2 = box
        self.label       = label
        self.confidence  = confidence
        self.class_id    = class_id
        self.is_vehicle  = is_vehicle
        self.is_person   = is_person
        self.is_ambulance = is_ambulance
        self.is_fire_truck = is_fire_truck
        self.is_emergency_vehicle = is_emergency_vehicle or is_ambulance or is_fire_truck
        self.pcu         = pcu
        self.has_emergency_lights = has_emergency_lights
        
        # Spatial Centroid
        self.cx = (self.x1 + self.x2) // 2
        self.cy = (self.y1 + self.y2) // 2
        
        # Bounding box dimensions & footprint area
        self.w = max(1, self.x2 - self.x1)
        self.h = max(1, self.y2 - self.y1)
        self.area = self.w * self.h
    
    @property
    def box(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)
    
    @property
    def centroid(self) -> Tuple[int, int]:
        return (self.cx, self.cy)
    
    def __repr__(self) -> str:
        return f"Detection({self.label} {self.confidence:.2f} PCU={self.pcu} @ ({self.cx},{self.cy}))"


class Detector:
    """
    YOLOv8-based multi-class detector with dynamic PCU weighting and
    multi-spectral optical emergency vehicle verification.
    """
    
    # Modern high-contrast color palette (BGR)
    COLORS = {
        "car":        (0,   220, 100),   # Vibrant Emerald Green
        "motorcycle": (255, 165, 0  ),   # Bright Amber
        "bus":        (0,   120, 255),   # Traffic Orange
        "truck":      (180, 0,   255),   # Violet / Magenta
        "bicycle":    (255, 220, 0  ),   # Cyan
        "person":     (0,   255, 255),   # Neon Yellow
        "ambulance":  (0,   0,   255),   # Emergency Signal Red
        "accident":   (0,   0,   255),   # Collision Red
        "fire_truck": (0,   69,  255),   # Fire Rescue Red-Orange
        "firetruck":  (0,   69,  255),
        "default":    (200, 200, 200),
    }
    
    AVAILABLE_MODELS = [
        {
            "id": "best_indian_traffic.pt",
            "name": "best_indian_traffic.pt",
            "label": "Indian Traffic & Ambulance Model (Fine-Tuned Auto-Rickshaw & Emergency)",
            "architecture": "CSP + RefineDetect (Indian Traffic & Emergency)",
            "params_m": 3.0,
            "latency_ms": 7.2,
            "map50": 0.965,
            "precision": "Fine-Tuned Weights",
            "recommended_for": "Dedicated Indian Auto-Rickshaws, Force Traveller ambulances & queue anti-false-alarm",
        },
        {
            "id": "yolov8_traffic_trained.pt",
            "name": "yolov8_traffic_trained.pt",
            "label": "Custom SOTA v12 (Your Trained Model — 81 Classes + Ambulance)",
            "architecture": "C3k2/CSP + RefineDetect (81 Classes)",
            "params_m": 2.8,
            "latency_ms": 7.4,
            "map50": 0.958,
            "precision": "Custom Weights",
            "recommended_for": "Fine-tuned traffic, multi-vehicle & dedicated ambulance class",
        },
        {
            "id": "yolo11n.pt",
            "name": "yolo11n.pt",
            "label": "YOLOv11 Nano (SOTA Flagship 2024)",
            "architecture": "C3k2 + SPPF Edge Engine",
            "params_m": 2.6,
            "latency_ms": 7.8,
            "map50": 0.912,
            "precision": "INT8 / FP16",
            "recommended_for": "Ultra-low edge latency (<10ms) & broad 80-class vehicle detection",
        },
        {
            "id": "yolov8n.pt",
            "name": "yolov8n.pt",
            "label": "YOLOv8 Nano (COCO Baseline)",
            "architecture": "Ultralytics Baseline",
            "params_m": 3.2,
            "latency_ms": 10.9,
            "map50": 0.884,
            "precision": "FP32",
            "recommended_for": "General baseline comparison",
        }
    ]
    SOTA_MODELS = AVAILABLE_MODELS

    def __init__(self, model_name: str = None, conf: float = None):
        self.model_name = model_name or config.MODEL_NAME
        self.conf       = conf       or config.CONFIDENCE_THRESHOLD
        
        print(f"[Detector] Loading model: {self.model_name}")
        self.model = YOLO(self.model_name)
        self.names = self.model.names   # {id: name}
        
        # Dynamic class label mapping (model-agnostic: supports 6-class custom & 80-class COCO)
        self.VEHICLE_LABELS = {
            "car", "motorcycle", "bus", "truck", "bicycle", "van", "suv",
            "auto", "vehicle", "ambulance", "fire_truck", "firetruck"
        }
        self.PERSON_LABELS = {"person", "pedestrian", "crowd"}
        
        # Precompute valid vehicle and pedestrian class IDs directly from model classes
        self._vehicle_ids = {i for i, n in self.names.items() if str(n).lower().strip() in self.VEHICLE_LABELS}
        self._person_ids  = {i for i, n in self.names.items() if str(n).lower().strip() in self.PERSON_LABELS}
        
        self._pcu_weights = getattr(config, 'PCU_WEIGHTS', {
            "car": 1.0, "motorcycle": 0.5, "bus": 3.0, "truck": 3.0,
            "bicycle": 0.2, "person": 0.1, "ambulance": 0.0, "fire_truck": 0.0, "firetruck": 0.0
        })
        self.active_model_label = next((m["label"] for m in self.AVAILABLE_MODELS if m["id"] == self.model_name), self.model_name)
        
        print(f"[Detector] Ready. Classes available: {len(self.names)} (Vehicles: {len(self._vehicle_ids)}, Pedestrians: {len(self._person_ids)})")

    @property
    def active_model_name(self) -> str:
        return self.model_name

    def switch_model(self, new_model_name: str) -> bool:
        """Dynamically hot-swaps the active inference neural network."""
        try:
            print(f"[Detector] Switching active model to: {new_model_name}")
            new_model = YOLO(new_model_name)
            self.model = new_model
            self.model_name = new_model_name
            self.names = self.model.names
            self._vehicle_ids = {i for i, n in self.names.items() if str(n).lower().strip() in self.VEHICLE_LABELS}
            self._person_ids  = {i for i, n in self.names.items() if str(n).lower().strip() in self.PERSON_LABELS}
            self.active_model_label = next((m["label"] for m in self.AVAILABLE_MODELS if m["id"] == new_model_name), new_model_name)
            print(f"[Detector] Successfully hot-swapped to {new_model_name} ({len(self.names)} classes)")
            return True
        except Exception as e:
            print(f"[Detector] Model switch failed for {new_model_name}: {e}")
            return False

    def get_model_catalog(self) -> List[Dict]:
        """Returns the SOTA model zoo metadata with the active model flagged."""
        catalog = []
        for m in self.AVAILABLE_MODELS:
            item = dict(m)
            item["active"] = (item["name"] == self.model_name)
            catalog.append(item)
        return catalog
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Execute detection on single BGR frame.
        Applies HSV emergency vehicle verification and PCU attribution.
        """
        results = self.model(frame, conf=min(0.18, self.conf), verbose=False)
        detections: List[Detection] = []
        
        if not results:
            return detections
        
        r = results[0]
        if r.boxes is None:
            return detections
        
        h, w = frame.shape[:2]
        
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Clamp to frame boundaries
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            box_width = x2 - x1
            box_height = y2 - y1
            if box_width < 10 or box_height < 10:
                continue
            
            raw_label = self.names.get(cls_id, "unknown")
            label = str(raw_label).lower().strip()
            
            aspect_ratio = float(box_width) / float(max(1, box_height))
            area_frac = (box_width * box_height) / float(w * h)
            
            is_accident = (cls_id == 6 or label in ["accident", "collision", "crash"])
            if not is_accident and conf < self.conf:
                continue
            is_person = (label in ["person", "pedestrian", "crowd"])
            is_vehicle = (not is_accident) and ((label in ["car", "motorcycle", "bus", "truck", "ambulance", "fire_truck", "firetruck", "bicycle", "van", "suv", "auto", "rickshaw", "vehicle"]) or (not is_person and label != "unknown"))
            has_emergency_lights = False
            is_auto_rickshaw = False
            
            # Flashing emergency lightbar & Indian Auto-Rickshaw detection
            if is_vehicle and not is_person:
                crop = frame[y1:y2, x1:x2]
                if crop.size > 0:
                    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    crop_area = max(1, crop.shape[0] * crop.shape[1])
                    roof_h = max(4, int(crop.shape[0] * 0.30))
                    roof = hsv[:roof_h, :]
                    rf_area = max(1, roof.shape[0] * roof.shape[1])
                    
                    # Red strobe lightbar
                    r_red1 = cv2.inRange(roof, np.array([0, 90, 90]), np.array([14, 255, 255]))
                    r_red2 = cv2.inRange(roof, np.array([160, 90, 90]), np.array([180, 255, 255]))
                    roof_red = cv2.countNonZero(cv2.bitwise_or(r_red1, r_red2)) / rf_area
                    
                    # Blue strobe lightbar
                    r_blue = cv2.inRange(roof, np.array([95, 90, 90]), np.array([135, 255, 255]))
                    roof_blue = cv2.countNonZero(r_blue) / rf_area
                    
                    # Verified emergency optical lightbar: concentrated high-saturation strobes
                    # (Requires blue strobe or alternating red-blue, preventing normal red taillights from false-triggering)
                    if (roof_blue > 0.045 or (roof_red > 0.04 and roof_blue > 0.02) or (roof_red > 0.09 and label in ["ambulance", "fire_truck", "firetruck"])):
                        has_emergency_lights = True
                        
                    # Auto-Rickshaw detection: yellow roof / green body with 3-wheeler aspect ratio
                    yellow_roof_mask = cv2.inRange(roof, np.array([16, 60, 60]), np.array([36, 255, 255]))
                    yellow_roof_ratio = cv2.countNonZero(yellow_roof_mask) / rf_area
                    
                    green_body_mask = cv2.inRange(hsv, np.array([35, 45, 35]), np.array([85, 255, 255]))
                    green_body_ratio = cv2.countNonZero(green_body_mask) / crop_area
                    
                    if (0.58 <= aspect_ratio <= 1.25) and (yellow_roof_ratio > 0.12 or green_body_ratio > 0.10) and not has_emergency_lights:
                        is_auto_rickshaw = True
                    elif "rickshaw" in label or "auto" in label:
                        is_auto_rickshaw = True

            # Demote large vehicles (like transit buses and box trucks) if falsely labeled ambulance
            is_bus_shape = (aspect_ratio >= 1.65 and area_frac >= 0.04)
            is_truck_shape = (aspect_ratio >= 1.35 and area_frac >= 0.035)

            # If vehicle is an auto-rickshaw, strictly classify as auto and NEVER ambulance
            if is_auto_rickshaw:
                label = "auto"
                is_ambulance_pred = False
                is_fire_truck_pred = False
            elif is_bus_shape and not has_emergency_lights:
                label = "bus"
                is_ambulance_pred = False
                is_fire_truck_pred = False
            else:
                amb_conf_thresh = getattr(config, 'AMBULANCE_CONFIDENCE_THRESHOLD', 0.50)
                is_amb_class = (cls_id == 80 or label == "ambulance" or any(kw in label for kw in getattr(config, 'AMBULANCE_CLASS_KEYWORDS', ['ambulance'])))
                min_area_frac = getattr(config, 'AMBULANCE_MIN_AREA_FRAC', 0.002)
                
                # Genuine ambulance: verified strobes OR calibrated high confidence on full-size vehicle
                if is_amb_class and has_emergency_lights and (conf >= 0.40):
                    is_ambulance_pred = True
                elif is_amb_class and (conf >= 0.88) and (area_frac >= min_area_frac) and not is_truck_shape:
                    is_ambulance_pred = True
                else:
                    is_ambulance_pred = False

                is_fire_truck_pred = (label in ["fire_truck", "firetruck", "fire engine"] or any(kw in label for kw in getattr(config, 'EMERGENCY_CLASS_KEYWORDS', ['fire_truck', 'firetruck']))) and (conf >= amb_conf_thresh) and (area_frac >= min_area_frac)

            is_ambulance = is_ambulance_pred
            is_fire_truck = is_fire_truck_pred
            is_emergency = is_ambulance or is_fire_truck
            
            if not is_ambulance and label == "ambulance":
                label = "bus" if is_bus_shape else ("truck" if is_truck_shape else "car")
            if not is_fire_truck and label in ["fire_truck", "firetruck"]:
                label = "truck"
            
            # Filter non-traffic classes
            if is_accident:
                label = "accident"
            elif not (is_vehicle or is_person or is_emergency):
                continue
            
            # Assign Passenger Car Unit (PCU) weight
            pcu_val = self._pcu_weights.get(label, 1.0)
            if is_emergency:
                pcu_val = 0.0  # Handled via preemption override
            
            det = Detection(
                box=(x1, y1, x2, y2),
                label=label,
                confidence=conf,
                class_id=cls_id,
                is_vehicle=is_vehicle,
                is_person=is_person,
                is_ambulance=is_ambulance,
                pcu=pcu_val,
                has_emergency_lights=has_emergency_lights,
                is_fire_truck=is_fire_truck,
                is_emergency_vehicle=is_emergency,
            )
            detections.append(det)
        
        # Class-agnostic duplicate NMS: suppress duplicate nested bounding boxes on same vehicle
        if len(detections) > 1:
            detections.sort(key=lambda d: d.confidence, reverse=True)
            suppressed = set()
            for i in range(len(detections)):
                if i in suppressed:
                    continue
                d1 = detections[i]
                for j in range(i + 1, len(detections)):
                    if j in suppressed:
                        continue
                    d2 = detections[j]
                    ix1 = max(d1.x1, d2.x1)
                    iy1 = max(d1.y1, d2.y1)
                    ix2 = min(d1.x2, d2.x2)
                    iy2 = min(d1.y2, d2.y2)
                    iw = max(0, ix2 - ix1)
                    ih = max(0, iy2 - iy1)
                    inter = iw * ih
                    if inter > 0:
                        a1 = (d1.x2 - d1.x1) * (d1.y2 - d1.y1)
                        a2 = (d2.x2 - d2.x1) * (d2.y2 - d2.y1)
                        union = a1 + a2 - inter
                        iou = inter / float(max(1, union))
                        containment = max(inter / float(max(1, a1)), inter / float(max(1, a2)))
                        if (iou > 0.55 or containment > 0.72) and (d1.is_vehicle and d2.is_vehicle):
                            if d2.is_ambulance and not d1.is_ambulance:
                                suppressed.add(i)
                                break
                            else:
                                suppressed.add(j)

            detections = [d for idx, d in enumerate(detections) if idx not in suppressed]

        return detections
    
    def draw(self, frame: np.ndarray, detections: List[Detection],
             show_labels: bool = True) -> np.ndarray:
        """Render high-contrast tactical bounding boxes, corner brackets, and PCU tags."""
        for det in detections:
            color = self.COLORS.get(det.label, self.COLORS["default"])
            is_emergency = det.is_ambulance or getattr(det, 'is_fire_truck', False) or getattr(det, 'is_emergency_vehicle', False)
            thickness = 3 if is_emergency else 2
            
            # 1. Bounding box outline with slight transparency effect
            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), color, thickness, cv2.LINE_AA)
            
            # 2. Tactical Corner Brackets (high-tech defense / autonomous vehicle look)
            corner_len = max(8, min(18, (det.x2 - det.x1) // 4, (det.y2 - det.y1) // 4))
            bracket_thick = thickness + 1
            # Top-left
            cv2.line(frame, (det.x1, det.y1), (det.x1 + corner_len, det.y1), color, bracket_thick, cv2.LINE_AA)
            cv2.line(frame, (det.x1, det.y1), (det.x1, det.y1 + corner_len), color, bracket_thick, cv2.LINE_AA)
            # Top-right
            cv2.line(frame, (det.x2, det.y1), (det.x2 - corner_len, det.y1), color, bracket_thick, cv2.LINE_AA)
            cv2.line(frame, (det.x2, det.y1), (det.x2, det.y1 + corner_len), color, bracket_thick, cv2.LINE_AA)
            # Bottom-left
            cv2.line(frame, (det.x1, det.y2), (det.x1 + corner_len, det.y2), color, bracket_thick, cv2.LINE_AA)
            cv2.line(frame, (det.x1, det.y2), (det.x1, det.y2 - corner_len), color, bracket_thick, cv2.LINE_AA)
            # Bottom-right
            cv2.line(frame, (det.x2, det.y2), (det.x2 - corner_len, det.y2), color, bracket_thick, cv2.LINE_AA)
            cv2.line(frame, (det.x2, det.y2), (det.x2, det.y2 - corner_len), color, bracket_thick, cv2.LINE_AA)
            
            # 3. Label Header Pill Badge (Clean detection pill without PCU)
            if show_labels:
                is_ft = getattr(det, 'is_fire_truck', False) or det.label in ["fire_truck", "firetruck"]
                is_amb = det.is_ambulance or det.label == "ambulance"
                has_lights = getattr(det, 'has_emergency_lights', False)
                if is_ft:
                    badge_lbl = "FIRE TRUCK [LIGHTS]" if has_lights else "FIRE TRUCK"
                elif is_amb:
                    badge_lbl = "AMBULANCE [LIGHTS]" if has_lights else "AMBULANCE"
                else:
                    badge_lbl = det.label.upper()
                label_txt = f"{badge_lbl} {int(det.confidence * 100)}%"
                
                (tw, th), _ = cv2.getTextSize(label_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                
                # Position badge above if room, else inside top to prevent clipping
                if det.y1 > th + 10:
                    bg_y1 = det.y1 - th - 8
                    bg_y2 = det.y1
                    text_y = det.y1 - 4
                else:
                    bg_y1 = det.y1
                    bg_y2 = det.y1 + th + 8
                    text_y = det.y1 + th + 2
                    
                bg_x2 = min(frame.shape[1], det.x1 + tw + 8)
                
                cv2.rectangle(frame, (det.x1, bg_y1), (bg_x2, bg_y2), (10, 15, 25), -1)
                cv2.rectangle(frame, (det.x1, bg_y1), (bg_x2, bg_y2), color, 1, cv2.LINE_AA)
                cv2.putText(frame, label_txt,
                            (det.x1 + 4, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1,
                            cv2.LINE_AA)
            
            # 4. Centroid Point with Targeting Reticle
            cv2.circle(frame, det.centroid, 3, color, -1, cv2.LINE_AA)
            cv2.circle(frame, det.centroid, 6, color, 1, cv2.LINE_AA)
            
            # 5. Emergency Vehicle Code-3 Preemption Banner
            if is_emergency:
                banner_y1 = max(0, det.y1 - 32)
                banner_y2 = max(0, det.y1 - 10)
                if det.y1 <= 35:
                    banner_y1 = det.y2 + 4
                    banner_y2 = det.y2 + 26
                has_lights = getattr(det, 'has_emergency_lights', False)
                banner_w = 275 if has_lights else 240
                is_ft = getattr(det, 'is_fire_truck', False) or det.label in ["fire_truck", "firetruck"]
                banner_color = (0, 69, 255) if is_ft else (0, 0, 220)
                
                cv2.rectangle(frame, (det.x1, banner_y1), (min(frame.shape[1], det.x1 + banner_w), banner_y2), banner_color, -1)
                cv2.rectangle(frame, (det.x1, banner_y1), (min(frame.shape[1], det.x1 + banner_w), banner_y2), (255, 255, 255), 1, cv2.LINE_AA)
                if is_ft:
                    banner_txt = "[EVP] FIRE RESCUE • LIGHTS ACTIVE" if has_lights else "[EVP] FIRE RESCUE • CODE-3"
                else:
                    banner_txt = "[EVP] AMBULANCE • LIGHTS ACTIVE" if has_lights else "[EVP] CODE-3 EMERGENCY"
                cv2.putText(frame, banner_txt,
                            (det.x1 + 6, banner_y2 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 2,
                            cv2.LINE_AA)
        
        return frame
    
    def get_vehicle_count(self, detections: List[Detection]) -> int:
        return sum(1 for d in detections if d.is_vehicle)
    
    def get_total_pcu(self, detections: List[Detection]) -> float:
        return round(sum(d.pcu for d in detections if d.is_vehicle), 2)
    
    def has_ambulance(self, detections: List[Detection]) -> bool:
        return any(d.is_ambulance for d in detections)
    
    def has_fire_truck(self, detections: List[Detection]) -> bool:
        return any(getattr(d, 'is_fire_truck', False) for d in detections)
    
    def has_emergency_vehicle(self, detections: List[Detection]) -> bool:
        return any(getattr(d, 'is_emergency_vehicle', False) or d.is_ambulance or getattr(d, 'is_fire_truck', False) for d in detections)
    
    def has_person(self, detections: List[Detection]) -> bool:
        return any(d.is_person for d in detections)