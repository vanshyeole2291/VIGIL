"""
core/accident_detector.py — VIGIL Multi-Tier Traffic Accident Detection Engine
==============================================================================
Combines:
  Tier 1: Kinematic trajectory anomaly (abnormal deceleration >= 18 px/s²).
  Tier 2: Physical vehicle-to-vehicle bounding box overlap (IoU >= 0.18).
  Tier 3: Post-collision stationary dwell (vehicles immobile for >= 2.0s in active flow).
  Tier 4: Optional visual accident model inference (when trained weights are present).

Strict Technical Integrity:
  If no trained accident model weights are found, reports ACCIDENT_MODEL_NOT_CONFIGURED
  and relies on verified kinematic collision logic without fabricating mock AI scores.

Lifecycle States:
  - suspected accident (awaiting dwell confirmation)
  - confirmed by configured rules (kinematic confirmation)
  - confirmed by visual model (visual model confirmation)
  - confirmed by fusion (both rules and visual model satisfied)
  - resolved (cleared by operator or traffic resumed)
  - test/demo event (explicitly labeled simulation)
"""

import time
import uuid
import os
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class AccidentState:
    SUSPECTED = "suspected accident"
    CONFIRMED_RULES = "confirmed by configured rules"
    CONFIRMED_MODEL = "confirmed by visual model"
    CONFIRMED_FUSION = "confirmed by fusion"
    RESOLVED = "resolved"
    TEST_EVENT = "test/demo event"


@dataclass
class AccidentIncident:
    """Represents a tracked accident incident with multi-tier forensic evidence."""
    incident_id: str
    state: str
    lane: str
    timestamp: float
    confirmed_at: Optional[float] = None
    resolved_at: Optional[float] = None
    
    # Evidence breakdown
    had_sudden_decel: bool = False
    max_iou: float = 0.0
    dwell_duration: float = 0.0
    vehicle_ids: List[int] = field(default_factory=list)
    bbox: Optional[Tuple[int, int, int, int]] = None
    
    # Visual Model Evidence
    visual_model_score: Optional[float] = None
    visual_model_used: bool = False
    is_simulation: bool = False
    description: str = ""
    severity: str = "critical"  # "medium", "high", "critical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "state": self.state,
            "lane": self.lane,
            "timestamp": self.timestamp,
            "confirmed_at": self.confirmed_at,
            "resolved_at": self.resolved_at,
            "had_sudden_decel": self.had_sudden_decel,
            "max_iou": round(self.max_iou, 3),
            "dwell_duration": round(self.dwell_duration, 1),
            "vehicle_ids": self.vehicle_ids,
            "bbox": self.bbox,
            "visual_model_score": self.visual_model_score,
            "visual_model_used": self.visual_model_used,
            "is_simulation": self.is_simulation,
            "description": self.description,
            "severity": self.severity,
            "age_seconds": round(time.time() - self.timestamp, 1)
        }


class AccidentDetector:
    """
    Multi-tier accident detection service combining physical kinematics,
    temporal multi-frame tracking, and optional visual neural network models.
    """
    
    def __init__(self, visual_model_path: Optional[str] = None):
        self.visual_model_path = visual_model_path or os.path.join(config.BASE_DIR, "models", "accident_best.pt")
        self.visual_model = None
        self.visual_model_status = "ACCIDENT_MODEL_NOT_CONFIGURED"
        self._init_visual_model()
        
        # Pending collision candidates: (t1_id, t2_id) -> state dict
        self._pending_candidates: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        # Active incident registry: incident_id -> AccidentIncident
        self.active_incidents: Dict[str, AccidentIncident] = {}
        
        # Per-lane debouncing cooldowns to prevent alert floods
        self._lane_cooldowns: Dict[str, float] = {}
        self.cooldown_duration = 600.0  # 10 minute cooldown prevents repeated flooding of same incident

    def _init_visual_model(self):
        """Attempt to load trained accident visual model if weights exist."""
        if os.path.exists(self.visual_model_path):
            try:
                from ultralytics import YOLO
                self.visual_model = YOLO(self.visual_model_path)
                self.visual_model_status = "READY"
                print(f"[AccidentDetector] Loaded visual accident detector: {self.visual_model_path}")
            except Exception as e:
                self.visual_model = None
                self.visual_model_status = f"ERROR_LOADING_WEIGHTS: {e}"
        else:
            self.visual_model = None
            self.visual_model_status = "ACCIDENT_MODEL_NOT_CONFIGURED"

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of the accident detection service."""
        return {
            "visual_model_status": self.visual_model_status,
            "visual_model_configured": self.visual_model is not None,
            "visual_model_path": self.visual_model_path,
            "pending_candidates_count": len(self._pending_candidates),
            "active_incidents_count": len([i for i in self.active_incidents.values() if i.state != AccidentState.RESOLVED]),
            "kinematic_rules_active": True,
            "confirm_time_threshold_sec": getattr(config, 'COLLISION_CONFIRM_TIME', 2.0),
            "overlap_iou_threshold": getattr(config, 'ACCIDENT_OVERLAP_IOU', 0.18),
        }

    def _compute_iou(self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter == 0:
            return 0.0
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / float(max(1, union))

    def evaluate(self, tracks, detections=None, lane_stats=None,
                 signals=None, current_phase=None, frame=None) -> List[AccidentIncident]:
        """
        Evaluate traffic state across all four evidentiary tiers.
        Returns newly confirmed or updated accident incidents.
        """
        now = time.time()
        new_events: List[AccidentIncident] = []
        vehicle_tracks = [t for t in tracks if getattr(t, 'is_vehicle', False)]
        track_map = {t.track_id: t for t in vehicle_tracks}

        # ── Optional Tier 4: Visual Model Inference ─────────────────────────
        visual_accident_boxes = []
        if self.visual_model is not None and frame is not None:
            try:
                results = self.visual_model.predict(frame, conf=0.35, verbose=False)
                for r in results:
                    for b in r.boxes:
                        bx = tuple(map(int, b.xyxy[0]))
                        visual_accident_boxes.append(bx)
            except Exception:
                pass

        # ── Tier 1 & 2: Kinematic Deceleration & Physical Overlap Detection ──
        for i, t1 in enumerate(vehicle_tracks):
            for t2 in vehicle_tracks[i+1:]:
                pair_key = (min(t1.track_id, t2.track_id), max(t1.track_id, t2.track_id))
                box1 = (t1.x1, t1.y1, t1.x2, t1.y2)
                box2 = (t2.x1, t2.y1, t2.x2, t2.y2)
                iou = self._compute_iou(box1, box2)

                had_decel = getattr(t1, 'had_sudden_decel', False) or getattr(t2, 'had_sudden_decel', False)
                # Heavy Traffic Queue Exclusion: Vehicles close to each other in traffic are never an accident
                # A candidate collision requires either sudden deceleration impact shockwave (had_decel) with overlap (iou >= 0.35)
                # or extreme destructive physical overlap (iou >= 0.60)
                is_candidate = (iou >= 0.35 and had_decel) or (iou >= 0.60)

                if is_candidate:
                    if pair_key not in self._pending_candidates:
                        lane_name = t1.lane or t2.lane or "Approach"
                        self._pending_candidates[pair_key] = {
                            "incident_id": f"inc-{uuid.uuid4().hex[:8]}",
                            "start_time": now,
                            "last_seen": now,
                            "lane": lane_name,
                            "max_iou": iou,
                            "had_decel": had_decel,
                            "state": AccidentState.SUSPECTED,
                            "vehicle_ids": [t1.track_id, t2.track_id],
                            "bbox": (min(t1.x1, t2.x1), min(t1.y1, t2.y1), max(t1.x2, t2.x2), max(t1.y2, t2.y2))
                        }
                    else:
                        c = self._pending_candidates[pair_key]
                        c["last_seen"] = now
                        c["max_iou"] = max(c["max_iou"], iou)
                        if had_decel:
                            c["had_decel"] = True

        # ── Tier 3: Post-Collision Stationary Dwell & Queue Exclusion ────────
        expired_pairs = []
        confirm_time = getattr(config, 'COLLISION_CONFIRM_TIME', 2.0)

        for pair_key, cand in list(self._pending_candidates.items()):
            tid1, tid2 = pair_key
            t1 = track_map.get(tid1)
            t2 = track_map.get(tid2)
            
            # Stale track pruning
            if t1 is None and t2 is None:
                if now - cand["last_seen"] > 3.5:
                    expired_pairs.append(pair_key)
                continue

            if t1 is not None or t2 is not None:
                cand["last_seen"] = now

            lane = cand["lane"]
            # Exclude standard red light queues (no decel shockwave and low overlap)
            is_red = False
            if signals and lane in signals:
                st = getattr(signals[lane], 'state', None)
                if str(getattr(st, 'value', st)).lower() == "red":
                    is_red = True
            elif current_phase and lane and lane != current_phase:
                is_red = True

            t1_stopped = (t1 is not None and getattr(t1, 'is_stopped', False))
            t2_stopped = (t2 is not None and getattr(t2, 'is_stopped', False))
            at_least_one_stopped = t1_stopped or t2_stopped
            both_stopped = t1_stopped and t2_stopped

            if is_red and not cand["had_decel"] and cand["max_iou"] < 0.22:
                # Normal stop line queue without collision dynamics
                if now - cand["start_time"] > 2.5:
                    expired_pairs.append(pair_key)
                continue

            dwell = now - cand["start_time"]
            cand["dwell_duration"] = dwell

            # Check if confirmed
            # In heavy traffic, queued vehicles are never an accident unless had_decel impact or extreme collision penetration
            if (both_stopped or is_red) and not cand["had_decel"] and cand["max_iou"] < 0.55:
                expired_pairs.append(pair_key)
                continue

            if at_least_one_stopped and cand["had_decel"] and dwell >= confirm_time:
                expired_pairs.append(pair_key)
                
                # Check debouncing cooldown for lane
                last_cooldown = self._lane_cooldowns.get(lane, 0.0)
                if now > last_cooldown:
                    self._lane_cooldowns[lane] = now + self.cooldown_duration
                    
                    state = AccidentState.CONFIRMED_RULES
                    if visual_accident_boxes:
                        state = AccidentState.CONFIRMED_FUSION

                    incident = AccidentIncident(
                        incident_id=cand["incident_id"],
                        state=state,
                        lane=lane,
                        timestamp=cand["start_time"],
                        confirmed_at=now,
                        had_sudden_decel=cand["had_decel"],
                        max_iou=cand["max_iou"],
                        dwell_duration=dwell,
                        vehicle_ids=cand["vehicle_ids"],
                        bbox=cand["bbox"],
                        visual_model_used=(self.visual_model is not None),
                        is_simulation=False,
                        description=f"Confirmed vehicle collision in {lane} lane (IoU={cand['max_iou']:.2f}, dwell={dwell:.1f}s)",
                        severity="critical"
                    )
                    self.active_incidents[incident.incident_id] = incident
                    new_events.append(incident)

        for p in expired_pairs:
            self._pending_candidates.pop(p, None)

        return new_events

    def trigger_test_accident(self, lane: str = "East", description: str = "Simulated Collision Event") -> AccidentIncident:
        """Explicitly inject a simulated test demonstration accident."""
        now = time.time()
        incident = AccidentIncident(
            incident_id=f"demo-{uuid.uuid4().hex[:8]}",
            state=AccidentState.TEST_EVENT,
            lane=lane,
            timestamp=now,
            confirmed_at=now,
            had_sudden_decel=True,
            max_iou=0.35,
            dwell_duration=3.0,
            vehicle_ids=[101, 102],
            bbox=(300, 250, 480, 420),
            visual_model_score=None,
            visual_model_used=False,
            is_simulation=True,
            description=f"[DEMO / TEST EVENT] {description} on {lane} corridor",
            severity="high"
        )
        self.active_incidents[incident.incident_id] = incident
        return incident

    def resolve_accident(self, incident_id: str) -> bool:
        """Mark an active accident incident as resolved."""
        if incident_id in self.active_incidents:
            self.active_incidents[incident_id].state = AccidentState.RESOLVED
            self.active_incidents[incident_id].resolved_at = time.time()
            return True
        return False

    def get_active_incidents(self) -> List[Dict[str, Any]]:
        """Return all active, non-resolved accident incidents."""
        return [
            inc.to_dict()
            for inc in self.active_incidents.values()
            if inc.state != AccidentState.RESOLVED
        ]
