"""
core/tracker.py — Kinematic Multi-Object Tracker (IoU + Centroid Hybrid)
========================================================================
Maintains persistent vehicle identities across frames with:
  - Hybrid Hungarian IoU + Centroid distance association (ByteTrack principles)
  - Trajectory history & smooth motion modeling
  - Instantaneous velocity vector (dx, dy), calibrated speed (km/h) & acceleration
  - Stationary dwell-time tracking for accurate collision & obstruction analysis
  - Passenger Car Unit (PCU) retention
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Deque
from collections import deque
from dataclasses import dataclass, field
import time
import sys, os
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou


@dataclass
class Track:
    """Represents a tracked vehicle or agent with kinematic state."""
    track_id:     int
    label:        str
    cx:           int
    cy:           int
    x1:           int
    y1:           int
    x2:           int
    y2:           int
    is_vehicle:   bool
    is_person:    bool
    is_ambulance: bool
    is_fire_truck: bool = False
    is_emergency_vehicle: bool = False
    ambulance_votes: int = 0
    pcu:          float = 1.0
    confidence:   float = 0.85
    
    # Temporal & Trajectory data
    created_at:     float = field(default_factory=time.time)
    last_seen:      float = field(default_factory=time.time)
    frames_tracked: int   = 0
    frames_missing: int   = 0
    history:        Deque[Tuple[int, int, float]] = field(default_factory=lambda: deque(maxlen=30))
    
    # Kinematics
    prev_cx:      int   = 0
    prev_cy:      int   = 0
    prev_speed:   float = 0.0
    speed_px_sec: float = 0.0   # Pixels per second
    speed_kmh:    float = 0.0   # Calibrated estimate (km/h)
    acceleration: float = 0.0   # Acceleration px/s²
    had_sudden_decel: bool = False
    last_decel_spike_time: float = 0.0
    velocity_vec: Tuple[float, float] = (0.0, 0.0)
    
    # Quadrant / Lane
    lane: Optional[str] = None
    
    # Stationary / Dwell Tracking
    wait_start:    Optional[float] = None
    total_wait:    float = 0.0
    is_stopped:    bool = False
    stopped_since: float = 0.0
    
    @property
    def w(self) -> int:
        return max(1, self.x2 - self.x1)
    
    @property
    def h(self) -> int:
        return max(1, self.y2 - self.y1)
    
    @property
    def box(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)
    
    @property
    def centroid(self) -> Tuple[int, int]:
        return (self.cx, self.cy)
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at
    
    @property
    def wait_time(self) -> float:
        """Current wait time in seconds (continuous stopped duration)."""
        if self.is_stopped and self.stopped_since > 0:
            return time.time() - self.stopped_since + self.total_wait
        return self.total_wait
    
    def update_kinematics(self, dt: float = 0.033):
        """Update velocity, speed in km/h, acceleration, and stopped status with jitter suppression."""
        dt = max(0.001, dt)
        dx = self.cx - self.prev_cx
        dy = self.cy - self.prev_cy
        dist_moved = float(np.sqrt(dx**2 + dy**2))
        
        # Deadband filter: Suppress bounding box pixel jitter (1.5-2px jitter at 30fps creates false 45-60px/s spikes)
        if dist_moved < 2.5:
            curr_speed_px = 0.0
            dx, dy = 0, 0
        else:
            curr_speed_px = dist_moved / dt
        
        # Pixels per second
        self.velocity_vec = (dx / dt, dy / dt)
        
        # Acceleration
        self.acceleration = (curr_speed_px - self.speed_px_sec) / dt
        # Kinematic deceleration impact: moving vehicle experiencing sudden deceleration
        # Calibrated for both wide-angle junction views and quadrant sub-frames
        is_abrupt_decel = (self.speed_px_sec > 30.0 and curr_speed_px < 15.0 and self.acceleration < -35.0) or (self.speed_px_sec > 25.0 and curr_speed_px < 5.0)
        if is_abrupt_decel:
            self.had_sudden_decel = True
            self.last_decel_spike_time = time.time()
        elif time.time() - getattr(self, 'last_decel_spike_time', 0.0) > 4.5:
            self.had_sudden_decel = False

        self.speed_px_sec = 0.80 * self.speed_px_sec + 0.20 * curr_speed_px  # Smooth motion estimate
        
        # Calibrated km/h conversion heuristic (approx. 15 px ≈ 1 meter in standard urban camera angle)
        # 1 m/s = 3.6 km/h -> speed_px_sec / 15 * 3.6
        self.speed_kmh = round(max(0.0, (self.speed_px_sec / 15.0) * 3.6), 1)
        
        # Stopped threshold with hysteresis:
        # Enter stopped if speed < 25 px/sec (~6 km/h)
        # Exit stopped only with sustained real movement (speed > 40 px/sec and dist_moved >= 3.0 px)
        now = time.time()
        
        if not self.is_stopped:
            if self.speed_px_sec < 25.0:
                self.is_stopped = True
                self.stopped_since = now
                self.wait_start = now
        else:
            if self.speed_px_sec > 40.0 and dist_moved >= 3.0:
                self.is_stopped = False
                if time.time() - getattr(self, 'last_decel_spike_time', 0.0) > 4.0:
                    self.had_sudden_decel = False
                if self.stopped_since > 0:
                    self.total_wait += (now - self.stopped_since)
                    self.stopped_since = 0.0
                self.wait_start = None

    def to_dict(self) -> Dict:
        """Serialize track state for frontend telemetry and scanning HUD."""
        priors = {
            "car":        {"length_m": 4.6, "width_m": 1.8, "height_m": 1.5, "footprint_m2": 8.28, "dist_to_stopline_m": 12.5},
            "motorcycle": {"length_m": 2.0, "width_m": 0.8, "height_m": 1.2, "footprint_m2": 1.60, "dist_to_stopline_m": 14.0},
            "bus":        {"length_m": 11.5, "width_m": 2.5, "height_m": 3.2, "footprint_m2": 28.75, "dist_to_stopline_m": 18.0},
            "truck":      {"length_m": 12.0, "width_m": 2.5, "height_m": 3.6, "footprint_m2": 30.00, "dist_to_stopline_m": 20.0},
            "bicycle":    {"length_m": 1.7, "width_m": 0.6, "height_m": 1.1, "footprint_m2": 1.02, "dist_to_stopline_m": 8.0},
            "person":     {"length_m": 0.5, "width_m": 0.5, "height_m": 1.7, "footprint_m2": 0.25, "dist_to_stopline_m": 4.0},
            "ambulance":  {"length_m": 5.8, "width_m": 2.1, "height_m": 2.5, "footprint_m2": 12.18, "dist_to_stopline_m": 10.0},
        }
        dim = self.dimensions if getattr(self, 'dimensions', None) else priors.get(self.label, priors["car"])
        return {
            "id": self.track_id,
            "label": self.label,
            "confidence": round(getattr(self, 'confidence', 0.85), 2),
            "lane": self.lane or "Approach",
            "pcu": self.pcu,
            "speed_kmh": round(self.speed_kmh, 1),
            "wait_time": round(self.wait_time, 1),
            "cx": self.cx,
            "cy": self.cy,
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "is_stopped": self.is_stopped,
            "is_ambulance": self.is_ambulance,
            "is_fire_truck": getattr(self, 'is_fire_truck', False),
            "is_emergency_vehicle": getattr(self, 'is_emergency_vehicle', False) or self.is_ambulance or getattr(self, 'is_fire_truck', False),
            "is_person": self.is_person,
            "dimensions": dim,
            "dist_to_stopline_m": dim.get("dist_to_stopline_m", 12.0),
            "footprint_m2": dim.get("footprint_m2", 8.28),
            "ground_x_m": getattr(self, 'ground_x_m', 0.0),
            "ground_y_m": getattr(self, 'ground_y_m', round(dim.get("dist_to_stopline_m", 12.0), 1)),
        }


class CentroidTracker:
    """
    High-accuracy multi-object tracking engine blending IoU overlap and
    centroid proximity matching with kinematic trajectory modeling.
    """
    
    def __init__(self, max_disappeared: int = 12, max_distance: int = 120, iou_weight: float = 0.5):
        self.max_disappeared = max_disappeared
        self.max_distance    = max_distance
        self.iou_weight      = iou_weight
        
        self._next_id = 1
        self.tracks: Dict[int, Track] = {}
        self._last_update_time = time.time()
    
    def update(self, detections) -> List[Track]:
        """Update tracker with incoming frame detections."""
        now = time.time()
        dt = max(0.01, now - self._last_update_time)
        self._last_update_time = now
        
        # If no detections in frame, age all active tracks
        if not detections:
            missing_ids = []
            for tid, track in self.tracks.items():
                track.frames_missing += 1
                if track.frames_missing > self.max_disappeared:
                    missing_ids.append(tid)
            for tid in missing_ids:
                del self.tracks[tid]
            return list(self.tracks.values())
        
        # If no prior tracks exist, register all as new
        if not self.tracks:
            for det in detections:
                self._register(det)
            return list(self.tracks.values())
        
        # ── Multi-Metric Matching Cost Matrix (Distance + 1-IoU) ─────────────
        track_ids = list(self.tracks.keys())
        active_tracks = [self.tracks[tid] for tid in track_ids]
        
        num_tracks = len(active_tracks)
        num_dets   = len(detections)
        cost_matrix = np.zeros((num_tracks, num_dets), dtype=float)
        
        for t_idx, track in enumerate(active_tracks):
            t_box = track.box
            for d_idx, det in enumerate(detections):
                d_box = det.box
                
                # Spatial Centroid distance
                dist = np.linalg.norm(np.array([track.cx, track.cy]) - np.array([det.cx, det.cy]))
                dist_norm = min(1.0, dist / float(self.max_distance))
                
                # IoU overlap
                iou = compute_iou(t_box, d_box)
                iou_cost = 1.0 - iou
                
                # Weighted hybrid cost
                cost_matrix[t_idx, d_idx] = (1.0 - self.iou_weight) * dist_norm + self.iou_weight * iou_cost
                
                # Hard distance cutoff
                if dist > self.max_distance and iou < 0.05:
                    cost_matrix[t_idx, d_idx] = 999.0
        
        matched_tracks = set()
        matched_dets   = set()
        
        # Greedy assignment based on minimum cost
        rows, cols = np.unravel_index(np.argsort(cost_matrix, axis=None), cost_matrix.shape)
        
        for r, c in zip(rows, cols):
            if r in matched_tracks or c in matched_dets:
                continue
            if cost_matrix[r, c] > 2.0:  # Beyond threshold
                break
            
            tid = track_ids[r]
            det = detections[c]
            track = self.tracks[tid]
            
            # Record trajectory
            track.history.append((track.cx, track.cy, now))
            
            # Update kinematics
            track.prev_cx = track.cx
            track.prev_cy = track.cy
            track.cx = det.cx
            track.cy = det.cy
            track.x1, track.y1, track.x2, track.y2 = det.box
            track.confidence = round(float(getattr(det, 'confidence', track.confidence)), 2)
            track.lane = getattr(det, 'lane', track.lane)
            # Strictly verify this specific detection's emergency credentials (never bleed to other cars)
            is_this_det_amb = bool(getattr(det, 'is_ambulance', False) or (det.label == "ambulance" and getattr(det, 'has_emergency_lights', False)))
            is_this_det_fire = bool(getattr(det, 'is_fire_truck', False) or (det.label in ["fire_truck", "firetruck"] and getattr(det, 'has_emergency_lights', False)))
            
            if is_this_det_amb or is_this_det_fire:
                track.ambulance_votes = min(10, track.ambulance_votes + 2)
                if track.ambulance_votes >= 2:
                    track.is_ambulance = is_this_det_amb
                    track.is_fire_truck = is_this_det_fire
                    track.is_emergency_vehicle = True
                    track.label = "fire_truck" if is_this_det_fire else "ambulance"
                    track.pcu = 0.0
                    track.last_ambulance_time = now
            else:
                track.ambulance_votes = max(0, track.ambulance_votes - 1)
                # Demote immediately to detected normal vehicle class
                if track.ambulance_votes <= 0:
                    track.is_ambulance = False
                    track.is_fire_truck = False
                    track.is_emergency_vehicle = False
                    track.label = det.label
                    track.pcu = getattr(det, 'pcu', 1.0)
                else:
                    # If this track was not genuinely an ambulance, clear emergency status
                    if not track.is_ambulance and not track.is_fire_truck:
                        track.is_emergency_vehicle = False
                        track.label = det.label
                        track.pcu = getattr(det, 'pcu', 1.0)
            track.last_seen = now
            track.frames_tracked += 1
            track.frames_missing = 0
            
            track.update_kinematics(dt)
            
            matched_tracks.add(r)
            matched_dets.add(c)
        
        # Register new detections
        for i, det in enumerate(detections):
            if i not in matched_dets:
                self._register(det)
        
        # Clean up stale vanished tracks
        missing_ids = []
        for i, tid in enumerate(track_ids):
            if i not in matched_tracks:
                track = self.tracks[tid]
                track.frames_missing += 1
                if track.frames_missing > self.max_disappeared:
                    missing_ids.append(tid)
        
        for tid in missing_ids:
            del self.tracks[tid]
        
        return list(self.tracks.values())
    
    def _register(self, det) -> Track:
        """Instantiate and track a new object detection."""
        is_this_det_amb = bool(getattr(det, 'is_ambulance', False) or (det.label == "ambulance" and getattr(det, 'has_emergency_lights', False)))
        is_this_det_fire = bool(getattr(det, 'is_fire_truck', False) or (det.label in ["fire_truck", "firetruck"] and getattr(det, 'has_emergency_lights', False)))
        is_em = is_this_det_amb or is_this_det_fire
        assigned_label = "fire_truck" if is_this_det_fire else ("ambulance" if is_this_det_amb else det.label)
        track = Track(
            track_id=self._next_id,
            label=assigned_label,
            cx=det.cx, cy=det.cy,
            x1=det.x1, y1=det.y1,
            x2=det.x2, y2=det.y2,
            is_vehicle=det.is_vehicle,
            is_person=det.is_person,
            is_ambulance=is_this_det_amb,
            is_fire_truck=is_this_det_fire,
            is_emergency_vehicle=is_em,
            ambulance_votes=2 if is_em else 0,
            pcu=0.0 if is_em else getattr(det, 'pcu', 1.0),
            confidence=round(float(getattr(det, 'confidence', 0.85)), 2),
            lane=getattr(det, 'lane', None),
        )
        track.prev_cx = det.cx
        track.prev_cy = det.cy
        track.history.append((det.cx, det.cy, time.time()))
        self.tracks[self._next_id] = track
        self._next_id += 1
        return track
    
    def get_vehicle_tracks(self) -> List[Track]:
        return [t for t in self.tracks.values() if t.is_vehicle]
    
    def get_ambulance_tracks(self) -> List[Track]:
        return [t for t in self.tracks.values() if t.is_ambulance]
    
    def get_fire_truck_tracks(self) -> List[Track]:
        return [t for t in self.tracks.values() if getattr(t, 'is_fire_truck', False)]
    
    def get_emergency_tracks(self) -> List[Track]:
        return [t for t in self.tracks.values() if t.is_ambulance or getattr(t, 'is_fire_truck', False) or getattr(t, 'is_emergency_vehicle', False)]
    
    def get_stopped_vehicles(self, min_wait: float = 3.0) -> List[Track]:
        return [t for t in self.tracks.values() if t.is_vehicle and t.is_stopped and t.wait_time >= min_wait]
    
    @property
    def total_active(self) -> int:
        return len(self.tracks)
    
    def draw_tracks(self, frame: np.ndarray, track_list: Optional[List[Track]] = None) -> np.ndarray:
        """Draw trajectory trails, ID badges, and kinematic speed tags on frame."""
        tracks = track_list or list(self.tracks.values())
        h, w = frame.shape[:2]
        for track in tracks:
            # Trajectory motion trail with glowing anti-aliased gradient
            pts = [(int(pt[0]), int(pt[1])) for pt in track.history]
            if len(pts) > 1:
                for i in range(1, len(pts)):
                    alpha = i / len(pts)
                    thick = 1 if i < (len(pts) // 2) else 2
                    color = (int(56 * alpha), int(189 * alpha), int(248 * alpha))
                    cv2.line(frame, pts[i - 1], pts[i], color, thick, cv2.LINE_AA)
            
            # Unified tactical HUD tag
            if track.is_ambulance:
                tag = f"[EVP] #{track.track_id} AMBULANCE"
                tag_color = (0, 0, 255)
            elif track.is_person:
                tag = f"#{track.track_id} PEDESTRIAN"
                tag_color = (255, 200, 50)
            else:
                speed_str = f"{track.speed_kmh:.0f} km/h" if not track.is_stopped else f"STOP {track.wait_time:.0f}s"
                lbl = getattr(track, 'label', 'CAR').upper()
                tag = f"#{track.track_id} {lbl} · {speed_str}"
                tag_color = (0, 180, 255) if track.is_stopped else (50, 220, 120)

            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            
            tag_x1 = max(0, track.x1)
            tag_y1 = min(h - th - 6, track.y2 + 4)
            tag_x2 = min(w, tag_x1 + tw + 6)
            tag_y2 = tag_y1 + th + 4
            
            cv2.rectangle(frame, (tag_x1, tag_y1), (tag_x2, tag_y2), (10, 15, 25), -1)
            cv2.rectangle(frame, (tag_x1, tag_y1), (tag_x2, tag_y2), tag_color, 1, cv2.LINE_AA)
            cv2.putText(frame, tag,
                        (tag_x1 + 3, tag_y2 - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, tag_color, 1,
                        cv2.LINE_AA)
        
        return frame
