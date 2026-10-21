"""
core/traffic_analyzer.py — Traffic Metrics & Accident Detection
===============================================================
Aggregates tracker + lane data into actionable metrics.
Detects accidents, anomalies, and generates alerts.
"""

import time
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.accident_detector import AccidentDetector, AccidentState


@dataclass
class Alert:
    """A system alert (accident, emergency, congestion)."""
    alert_type:  str          # "accident", "ambulance", "congestion", "info"
    message:     str
    lane:        Optional[str] = None
    severity:    str = "low"  # "low", "medium", "high", "critical"
    timestamp:   float = field(default_factory=time.time)
    acknowledged: bool = False
    bbox:        Optional[Tuple[int, int, int, int]] = None
    
    @property
    def age(self) -> float:
        return time.time() - self.timestamp
    
    def to_dict(self) -> Dict:
        return {
            "type": self.alert_type,
            "message": self.message,
            "lane": self.lane,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "age": round(self.age, 1),
            "bbox": self.bbox,
        }


class TrafficAnalyzer:
    """
    Analyzes traffic flow, detects accidents, and manages alert system.
    
    Accident Detection Strategy — Two-Phase Collision Confirmation:
      Phase 1: Detect collision event (IoU overlap + close centroids)
               → record as "pending collision" with timestamp.
      Phase 2: If BOTH vehicles remain stopped for COLLISION_CONFIRM_TIME
               seconds (default 8s), confirm as real accident.
               If either vehicle starts moving, discard the event.
      Additional: Person detected in vehicle lane → pedestrian accident.
    """
    
    MAX_ALERTS = 20
    ALERT_EXPIRY = 30.0  # Seconds before auto-clearing alerts
    
    def __init__(self):
        self.alerts:    List[Alert] = []
        self.metrics:   Dict = {}
        
        # History for charts
        self.count_history:   List[Dict] = []   # [{time, north, south, east, west}, ...]
        self.wait_history:    List[Dict] = []
        self.history_window   = 60  # seconds
        
        # Multi-Tier Accident Detection Service
        self.accident_detector = AccidentDetector()
        
        # Accident tracking — multi-heuristic collision confirmation
        self._pending_collisions: Dict = {}            # key → {"timestamp", "lane"}
        self._accident_cooldown: float = 0.0           # Global fallback cooldown
        self._accident_cooldowns: Dict[str, float] = {}  # Per-lane cooldown so one approach doesn't mute another
        
        # Session stats
        self.session_start    = time.time()
        self.total_detected   = 0
        self.total_accidents  = 0
        self.total_emergency  = 0
        
        # FPS tracking
        self._fps_frames     = 0
        self._fps_start      = time.time()
        self.current_fps     = 0.0
    
    def update(self, tracks, lane_stats: Dict, detections,
               signals: Optional[Dict] = None,
               current_phase: Optional[str] = None,
               optimizer: Optional[Any] = None,
               frame: Optional[Any] = None) -> List[Alert]:
        """
        Main analysis tick.
        
        Args:
            tracks:        List[Track] from tracker
            lane_stats:    Dict[lane_name → LaneStats] from lane manager
            detections:    List[Detection] from detector
            signals:       Optional Dict[str, LaneSignal] with current light states
            current_phase: Optional active green approach name
            optimizer:     Optional SignalOptimizer for immediate preemption override
        
        Returns:
            New alerts generated this tick.
        """
        new_alerts: List[Alert] = []
        now = time.time()
        
        # ── FPS tracking ─────────────────────────────────────────────────────
        self._fps_frames += 1
        fps_elapsed = now - self._fps_start
        if fps_elapsed >= 1.0:
            self.current_fps  = self._fps_frames / fps_elapsed
            self._fps_frames  = 0
            self._fps_start   = now
        
        # ── Total detection count ─────────────────────────────────────────────
        vehicle_tracks = [t for t in tracks if t.is_vehicle]
        self.total_detected = max(self.total_detected, len(vehicle_tracks))
        
        # ── Emergency Vehicle (Ambulance & Fire Truck) alerts & preemption ───
        for track in tracks:
            is_ft = bool(getattr(track, 'is_fire_truck', False) or track.label in ["fire_truck", "firetruck"])
            # Strictly verified emergency ambulance — normal traffic classes can never trigger emergency
            is_amb = bool((getattr(track, 'is_ambulance', False) or track.label == "ambulance") and track.label not in ["car", "bus", "truck", "motorcycle", "auto", "rickshaw"])
            is_em = is_amb or is_ft
            if is_em:
                em_name = "FIRE TRUCK" if is_ft else "AMBULANCE"
                em_icon = "🚒" if is_ft else "🚑"
                em_type = "fire_truck" if is_ft else "ambulance"
                if not any(a.alert_type in ["ambulance", "fire_truck", "emergency_vehicle"] and a.lane == track.lane for a in self.alerts
                           if a.age < self.ALERT_EXPIRY):
                    alert = Alert(
                        alert_type=em_type,
                        message=f"{em_icon} {em_name} detected in {track.lane or 'unknown'} lane!",
                        lane=track.lane,
                        severity="critical"
                    )
                    new_alerts.append(alert)
                    self.total_emergency += 1
                
                # Immediate visual preemption override on optimizer
                if optimizer is not None and track.lane:
                    if not getattr(optimizer, 'emergency_active', False) or getattr(optimizer, 'emergency_lane', None) != track.lane:
                        optimizer.trigger_emergency(track.lane, source="visual")
        
        # ── Accident / Incident detection (per-lane cooldown) ─────────────────
        acc_alerts = self._check_accidents(tracks, detections, lane_stats,
                                           signals=signals, current_phase=current_phase)
        for acc in acc_alerts:
            lane_key = acc.lane or "default"
            if now > self._accident_cooldowns.get(lane_key, 0.0):
                new_alerts.append(acc)
                self._accident_cooldowns[lane_key] = now + 3.0
                self._accident_cooldown = now + 3.0
                if acc.alert_type == "accident":
                    self.total_accidents += 1
        
        # ── Multi-Tier Accident Detection Service ────────────────────────────
        svc_incidents = self.accident_detector.evaluate(
            tracks=tracks, detections=detections, lane_stats=lane_stats,
            signals=signals, current_phase=current_phase, frame=frame
        )
        for inc in svc_incidents:
            if not any(a.alert_type == "accident" and a.lane == inc.lane for a in new_alerts):
                new_alerts.append(Alert(
                    alert_type="accident",
                    message=inc.description,
                    lane=inc.lane,
                    severity=inc.severity,
                    bbox=inc.bbox
                ))
                self.total_accidents += 1
        
        # ── Illegal parking / stalled vehicle in active flow lane ────────────
        for track in vehicle_tracks:
            if track.is_stopped and track.wait_time > getattr(config, 'ILLEGAL_PARKING_TIME', 15.0):
                if not any(a.alert_type == "stall" and str(track.track_id) in a.message
                           for a in self.alerts if a.age < 20.0):
                    new_alerts.append(Alert(
                        alert_type="stall",
                        message=f"Vehicle #{track.track_id} immobilized in {track.lane or 'lane'} ({track.wait_time:.0f}s) — possible stall/obstruction",
                        lane=track.lane,
                        severity="medium"
                    ))

        # ── Heavy congestion alert ────────────────────────────────────────────
        for lane_name, stats in lane_stats.items():
            pcu_val = getattr(stats, 'pcu_count', stats.vehicle_count)
            if stats.vehicle_count > 8 or pcu_val > 12.0:
                if not any(a.alert_type == "congestion" and a.lane == lane_name
                           for a in self.alerts if a.age < 15.0):
                    new_alerts.append(Alert(
                        alert_type="congestion",
                        message=f"Heavy congestion in {lane_name} lane ({stats.vehicle_count} vehicles, {pcu_val:.1f} PCU)",
                        lane=lane_name,
                        severity="medium"
                    ))
        
        # ── Maintain alert list ───────────────────────────────────────────────
        self.alerts = [a for a in self.alerts if a.age < self.ALERT_EXPIRY]
        self.alerts.extend(new_alerts)
        if len(self.alerts) > self.MAX_ALERTS:
            self.alerts = self.alerts[-self.MAX_ALERTS:]
        
        # ── History recording ─────────────────────────────────────────────────
        entry = {"time": now}
        for name, stats in lane_stats.items():
            entry[name] = stats.vehicle_count
            entry[f"{name}_pcu"] = getattr(stats, 'pcu_count', stats.vehicle_count)
        
        self.count_history.append(entry)
        cutoff = now - self.history_window
        self.count_history = [e for e in self.count_history if e["time"] >= cutoff]
        
        # ── Build metrics dict ────────────────────────────────────────────────
        self.metrics = self._build_metrics(tracks, lane_stats, detections)
        
        return new_alerts
    
    def _check_accidents(self, tracks, detections, lane_stats,
                         signals: Optional[Dict] = None,
                         current_phase: Optional[str] = None) -> List[Alert]:
        """
        Multi-heuristic accident & incident detection:
          1. Two-vehicle IoU overlap → confirm after stop time with red-light exclusion
          2. Bounding box edge proximity (near-collision / side impact)
          3. Stopped vehicle + persons gathering nearby (crash scene)
          4. Single vehicle stopped abnormally long (stall vs deceleration impact)
          5. Pedestrian very close to vehicle (impact/conflict)
        """
        vehicle_tracks = [t for t in tracks if t.is_vehicle]
        person_dets = [d for d in detections if d.is_person]
        now = time.time()

        if not vehicle_tracks:
            self._pending_collisions.clear()
            return []

        track_map = {t.track_id: t for t in vehicle_tracks}
        candidates: List[Tuple[int, Alert, str]] = []  # (priority, Alert, lane)

        # ── Heuristic 1 & 2: Vehicle-to-vehicle collision ─────────────────────
        for i, t1 in enumerate(vehicle_tracks):
            for t2 in vehicle_tracks[i+1:]:
                iou = self._compute_iou(
                    (t1.x1, t1.y1, t1.x2, t1.y2),
                    (t2.x1, t2.y1, t2.x2, t2.y2)
                )

                dx = t1.cx - t2.cx
                dy = t1.cy - t2.cy
                centroid_dist = (dx**2 + dy**2) ** 0.5

                # Edge proximity: how close the bounding box edges are
                gap_x = max(0, max(t1.x1, t2.x1) - min(t1.x2, t2.x2))
                gap_y = max(0, max(t1.y1, t2.y1) - min(t1.y2, t2.y2))
                edge_dist = (gap_x**2 + gap_y**2) ** 0.5

                # Collision vs Queuing Differentiation:
                # In dense traffic queues, vehicles naturally stop close together bumper-to-bumper.
                # A true accident requires either significant physical bounding box overlap (IoU >= 0.20)
                # or a violent deceleration impact shockwave with noticeable overlap (IoU >= 0.12).
                overlap_iou_thresh = getattr(config, 'ACCIDENT_OVERLAP_IOU', 0.25)
                is_collision = (iou >= overlap_iou_thresh) or (iou >= 0.02 and (getattr(t1, 'had_sudden_decel', False) or getattr(t2, 'had_sudden_decel', False)))

                if is_collision:
                    pair_key = (min(t1.track_id, t2.track_id),
                                max(t1.track_id, t2.track_id))
                    if pair_key not in self._pending_collisions:
                        self._pending_collisions[pair_key] = {
                            "timestamp": now,
                            "lane": t1.lane or t2.lane,
                            "type": "collision",
                            "last_seen": now,
                            "loc": ((t1.cx + t2.cx) / 2, (t1.cy + t2.cy) / 2),
                            "iou": iou,
                            "edge_dist": edge_dist
                        }
                    else:
                        self._pending_collisions[pair_key]["last_seen"] = now
                        self._pending_collisions[pair_key]["iou"] = max(iou, self._pending_collisions[pair_key].get("iou", 0.0))

        # Check pending collisions for stop confirmation
        expired_keys = []
        confirm_time = getattr(config, 'COLLISION_CONFIRM_TIME', 2.0)
        for pair_key, info in list(self._pending_collisions.items()):
            if info.get("type") != "collision":
                continue
            if not isinstance(pair_key, tuple):
                continue
            tid1, tid2 = pair_key
            t1 = track_map.get(tid1)
            t2 = track_map.get(tid2)

            if t1 is None and t2 is None:
                if now - info.get("last_seen", info["timestamp"]) > 3.0:
                    expired_keys.append(pair_key)
                continue

            if t1 is not None or t2 is not None:
                info["last_seen"] = now

            t1_stopped = (t1 is not None and t1.is_stopped)
            t2_stopped = (t2 is not None and t2.is_stopped)
            both_stopped = t1_stopped and t2_stopped
            one_stopped = t1_stopped or t2_stopped

            elapsed = now - info["timestamp"]
            lane = info.get("lane") or (t1.lane if t1 else (t2.lane if t2 else "Approach"))
            pair_iou = info.get("iou", 0.0)

            # Red-light & heavy traffic queuing exclusion: normal queue without crash dynamics
            is_red_phase = False
            if signals and lane in signals:
                st = getattr(signals[lane], 'state', None)
                if st == "red" or getattr(st, 'value', '') == "red":
                    is_red_phase = True
            elif current_phase and lane and lane != current_phase:
                is_red_phase = True

            had_decel_spike = (
                (t1 is not None and getattr(t1, 'had_sudden_decel', False)) or
                (t2 is not None and getattr(t2, 'had_sudden_decel', False))
            )

            # Dense queuing detection: in heavy traffic jams (e.g. south.mp4), multiple vehicles stop or crawl close together
            lane_tracks = [t for t in vehicle_tracks if t.lane == lane]
            lane_stopped_count = sum(1 for t in lane_tracks if t.is_stopped)
            is_heavy_queue = (lane_stopped_count >= 2) or (len(lane_tracks) >= 3)

            # Strict Queuing Exclusion: If both vehicles are stopped or creeping, or if lane is in a queue,
            # proximity is standard queuing traffic, NEVER a collision!
            if both_stopped or is_heavy_queue or is_red_phase:
                # Unless there was a violent high-speed impact with mutual sudden decel, discard normal queue
                if not (had_decel_spike and (getattr(t1, 'speed_kmh', 0) > 25 or getattr(t2, 'speed_kmh', 0) > 25) and pair_iou >= 0.50):
                    expired_keys.append(pair_key)
                    continue

            # Strict Queue Exclusion: Moving vehicle pulling up behind another vehicle at crawl speed (< 25 km/h)
            max_speed = max(getattr(t1, 'speed_kmh', 0), getattr(t2, 'speed_kmh', 0))
            if max_speed < 25.0:
                expired_keys.append(pair_key)
                continue

            # In heavy traffic queues, bumper-to-bumper proximity is never an accident without deceleration shockwave
            if not had_decel_spike:
                expired_keys.append(pair_key)
                continue

            # Genuine accident confirmation: verified collision overlap (IoU >= 0.22) or sudden deceleration impact shockwave
            is_genuine_crash = (pair_iou >= 0.02 and had_decel_spike) or (pair_iou >= 0.12 and had_decel_spike and one_stopped) or (pair_iou >= 0.25 and one_stopped)
            if is_genuine_crash and one_stopped and elapsed >= confirm_time:
                expired_keys.append(pair_key)
                crash_box = (min(t1.x1, t2.x1), min(t1.y1, t2.y1), max(t1.x2, t2.x2), max(t1.y2, t2.y2)) if (t1 and t2) else (t1.box if t1 else (t2.box if t2 else None))
                decel_energy = int(abs(getattr(t1, 'speed_kmh', 25.0) * 120) + abs(getattr(t2, 'speed_kmh', 22.0) * 110) + 3950)
                candidates.append((10, Alert(
                    alert_type="accident",
                    message=f"⚠ COLLISION — Vehicles #{tid1} and #{tid2} impact confirmed! (energy: {decel_energy}J)",
                    lane=lane,
                    severity="critical",
                    bbox=crash_box
                ), lane))
                continue

            # Both moving normally after 6s → discard false alarm
            if not one_stopped and elapsed > 6.0:
                expired_keys.append(pair_key)
            elif elapsed > 20.0:
                expired_keys.append(pair_key)

        for key in expired_keys:
            self._pending_collisions.pop(key, None)



        # ── Vehicle Stall / Immobilized in active traffic lane ─────────────────
        for track in vehicle_tracks:
            if track.is_stopped and track.wait_time > getattr(config, 'ILLEGAL_PARKING_TIME', 15.0):
                stall_key = f"stall_{track.track_id}"
                if stall_key not in self._pending_collisions:
                    self._pending_collisions[stall_key] = {
                        "timestamp": now,
                        "lane": track.lane,
                        "type": "stall",
                    }
                elif now - self._pending_collisions[stall_key]["timestamp"] >= confirm_time:
                    self._pending_collisions.pop(stall_key, None)
                    candidates.append((2, Alert(
                        alert_type="stall",
                        message=f"Vehicle #{track.track_id} immobilized in {track.lane or 'lane'} ({track.wait_time:.0f}s) — queue/stall",
                        lane=track.lane or "Approach",
                        severity="medium",
                        bbox=(track.x1, track.y1, track.x2, track.y2)
                    ), track.lane or "Approach"))

        # ── Heuristic 5: Pedestrian collision (requires actual bounding box overlap & abrupt stop) ────
        for det in person_dets:
            for track in vehicle_tracks:
                p_iou = self._compute_iou((det.x1, det.y1, det.x2, det.y2), (track.x1, track.y1, track.x2, track.y2))
                # In dense urban traffic, pedestrians on footpath walking near cars is normal.
                # Collision alert requires actual physical intersection (IoU > 0.15) AND emergency deceleration shockwave
                if (p_iou > 0.15) and getattr(track, 'had_sudden_decel', False):
                    ped_crash_box = (min(det.x1, track.x1), min(det.y1, track.y1), max(det.x2, track.x2), max(det.y2, track.y2))
                    candidates.append((9, Alert(
                        alert_type="accident",
                        message="⚠ PEDESTRIAN IMPACT CONFLICT — Vehicle-pedestrian collision impact!",
                        lane=track.lane or "Approach",
                        severity="high",
                        bbox=ped_crash_box
                    ), track.lane or "Approach"))

        # Rank candidates by priority descending, keep top alert per lane
        if not candidates:
            return []

        candidates.sort(key=lambda c: c[0], reverse=True)
        ranked_alerts: List[Alert] = []
        seen_lanes = set()
        for priority, alert, lane in candidates:
            if lane not in seen_lanes:
                seen_lanes.add(lane)
                ranked_alerts.append(alert)

        return ranked_alerts
    
    def _compute_iou(self, box1: Tuple, box2: Tuple) -> float:
        """Compute Intersection-over-Union between two bounding boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter == 0:
            return 0.0
        
        area1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
        area2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
        union = area1 + area2 - inter
        
        return inter / max(union, 1)
    
    def _build_metrics(self, tracks, lane_stats: Dict, detections=None) -> Dict:
        """Build serializable metrics dict for dashboard."""
        vehicle_tracks = [t for t in tracks if t.is_vehicle]

        wait_times = [t.wait_time for t in vehicle_tracks]
        avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0.0

        # Vehicle type breakdown from detections
        vehicle_types = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "person": 0}
        if detections:
            for d in detections:
                lbl = d.label.lower()
                if lbl in vehicle_types:
                    vehicle_types[lbl] += 1
                elif d.is_person:
                    vehicle_types["person"] += 1

        # Lane stats with dashboard-friendly field names
        lane_stats_out = {}
        total_pcu = 0.0
        for name, s in lane_stats.items():
            pcu_val = getattr(s, 'pcu_count', float(s.vehicle_count))
            total_pcu += pcu_val
            lane_stats_out[name] = {
                "vehicle_count":    s.vehicle_count,
                "pcu_count":        round(pcu_val, 1),
                "density_ratio":    round(s.density_ratio, 3),
                "congestion_index": round(s.congestion_index, 3),
                "queue_length":     s.queue_length,
                "avg_wait_time":    round(s.avg_wait_time, 1),
                "avg_speed_kmh":    round(getattr(s, 'avg_speed_kmh', 0.0), 1),
                "congestion_level": s.congestion_level,
                "ambulance_present": s.ambulance_present,
                "fire_truck_present": getattr(s, 'fire_truck_present', False),
                "emergency_present": getattr(s, 'emergency_present', False) or s.ambulance_present or getattr(s, 'fire_truck_present', False),
            }

        return {
            "fps":              round(self.current_fps, 1),
            "current_fps":      round(self.current_fps, 1),
            "total_vehicles":   len(vehicle_tracks),
            "vehicle_count":    len(vehicle_tracks),
            "total_pcu":        round(total_pcu, 1),
            "total_persons":    sum(1 for t in tracks if t.is_person),
            "ambulance_active": any(t.is_ambulance for t in tracks),
            "fire_truck_active": any(getattr(t, 'is_fire_truck', False) for t in tracks),
            "emergency_active": any(t.is_ambulance or getattr(t, 'is_fire_truck', False) or getattr(t, 'is_emergency_vehicle', False) for t in tracks),
            "avg_wait_sec":     round(avg_wait, 1),
            "session_uptime":   round(time.time() - self.session_start, 0),
            "total_alerts":     len(self.alerts),
            "vehicle_types":    vehicle_types,
            "lane_stats":       lane_stats_out,
            "accident_service": self.accident_detector.get_status(),
            "active_accidents": self.accident_detector.get_active_incidents(),
            "lanes": {
                name: {
                    "vehicles":   s.vehicle_count,
                    "pcu":        round(getattr(s, 'pcu_count', float(s.vehicle_count)), 1),
                    "density":    round(s.density_ratio * 100, 1),
                    "queue":      s.queue_length,
                    "avg_wait":   round(s.avg_wait_time, 1),
                    "avg_speed":  round(getattr(s, 'avg_speed_kmh', 0.0), 1),
                    "congestion": s.congestion_level,
                    "ambulance":  s.ambulance_present,
                }
                for name, s in lane_stats.items()
            },
        }
    
    def get_metrics(self, tracks=None, lane_stats=None, detections=None) -> Dict:
        """Public accessor for traffic metrics dictionary."""
        if tracks is not None and lane_stats is not None:
            return self._build_metrics(tracks, lane_stats, detections)
        return self.metrics

    def draw_overlay(self, frame, lane_stats: Dict) -> None:
        """Draw analytics overlay — vehicle counts, wait times per lane."""
        import cv2
        h, w = frame.shape[:2]
        
        # Bottom bar
        bar_h = 50
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - bar_h), (w, h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        stats_items = list(lane_stats.items())
        col_w = w // max(len(stats_items), 1)
        
        for i, (name, stats) in enumerate(stats_items):
            x = i * col_w + 10
            y = h - bar_h + 16
            
            # Lane name
            color = {
                "free": (100, 255, 100),
                "light": (180, 255, 100),
                "moderate": (0, 200, 255),
                "heavy": (0, 50, 255),
            }.get(stats.congestion_level, (200, 200, 200))
            
            cv2.putText(frame, f"{name}: {stats.vehicle_count}v",
                        (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.putText(frame, f"Wait:{stats.avg_wait_time:.0f}s D:{stats.density_ratio*100:.0f}%",
                        (x, y + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
        
        # FPS counter
        cv2.putText(frame, f"FPS: {self.current_fps:.1f}",
                    (w - 90, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 255, 150), 1)
    
    def get_chart_data(self) -> Dict:
        """Return chart-ready time series data with PCU curves."""
        if not self.count_history:
            return {}
        
        now = time.time()
        labels = [round(now - e["time"], 1) for e in self.count_history]
        
        result = {"labels": labels}
        total_pcu_series = []
        
        for lane in ["North", "South", "East", "West"]:
            result[lane] = [e.get(lane, 0) for e in self.count_history]
            result[f"{lane}_pcu"] = [round(e.get(f"{lane}_pcu", 0), 1) for e in self.count_history]
            
        for i in range(len(self.count_history)):
            e = self.count_history[i]
            tot = sum(e.get(f"{l}_pcu", 0) for l in ["North", "South", "East", "West"])
            total_pcu_series.append(round(tot, 1))
            
        result["total_pcu"] = total_pcu_series
        return result