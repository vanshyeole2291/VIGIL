"""
backend/video_processor_4way.py — Multi-Camera Video & Multi-Modal Audio Processing Pipeline
=============================================================================================
Orchestrates:
  - Real-time 4-camera video capture & composition
  - YOLOv8 multi-class detection with PCU weighting
  - Kinematic multi-object tracking (IoU + Centroid)
  - Webster ATSC signal optimization & emergency corridor preemption
  - Acoustic siren detection & audio-visual sensor fusion
  - Incident snapshot logging with base64 serialization
"""

import cv2
import numpy as np
import threading
import time
import base64
import json
import os
import sys
from typing import Callable, Optional, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.detector             import Detector
from core.tracker              import CentroidTracker
from core.lane_manager         import LaneManager
from core.traffic_analyzer     import TrafficAnalyzer, Alert
from core.signal_optimizer     import SignalOptimizer
from core.audio_siren_detector import AudioSirenDetector
from core.v2x_engine           import V2XEngine
from core.green_wave_coordinator import GreenWaveCoordinator
from core.pedestrian_safety    import PedestrianSafetyEngine
from core.homography_bev       import IntersectionBEVEngine
from core.active_learning      import ActiveLearningFlywheel


LANE_POLYGONS_4WAY = getattr(config, 'LANE_POLYGONS_4WAY', {
    "North": [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
    "South": [(0.5, 0.0), (1.0, 0.0), (1.0, 0.5), (0.5, 0.5)],
    "East":  [(0.0, 0.5), (0.5, 0.5), (0.5, 1.0), (0.0, 1.0)],
    "West":  [(0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.5, 1.0)],
})


class VideoProcessor4Way:
    def __init__(self, v_north="north.mp4", v_south="south.mp4", v_east="east.mp4", v_west="west.mp4",
                 frame_width=None, frame_height=None):
        self.v_paths = [self._resolve_video(v) for v in [v_north, v_south, v_east, v_west]]
        self.frame_width  = frame_width  or config.FRAME_WIDTH
        self.frame_height = frame_height or config.FRAME_HEIGHT
        
        self.detector       = Detector()
        self.tracker        = CentroidTracker(max_disappeared=10, max_distance=110)
        self.lane_mgr       = LaneManager(self.frame_width, self.frame_height, polygons=LANE_POLYGONS_4WAY)
        self.analyzer       = TrafficAnalyzer()
        self.optimizer      = SignalOptimizer()
        self.audio_detector = AudioSirenDetector()
        self.v2x_engine     = V2XEngine()
        self.green_wave     = GreenWaveCoordinator()
        self.ped_safety     = PedestrianSafetyEngine()
        self.bev_engine     = IntersectionBEVEngine()
        self.active_learning = ActiveLearningFlywheel()
        
        self.is_running = False
        self._capture_thread_obj:   Optional[threading.Thread] = None
        self._inference_thread_obj: Optional[threading.Thread] = None
        self._audio_thread_obj:     Optional[threading.Thread] = None
        
        self.quadrant_mapping = [0, 1, 2, 3]  # Default N, S, E, W
        
        self.state_lock = threading.Lock()
        self.raw_frame: Optional[np.ndarray] = None
        self.shared_detections: List = []
        self.shared_tracks:     List = []
        self.shared_lane_stats: Dict = {}
        
        self.latest_frame:   Optional[np.ndarray] = None
        self.latest_metrics: Dict = {}
        self.latest_alerts:  List = []
        self.latest_signals: Dict = {}
        self.incident_history: List[Dict] = self._load_recent_incidents_from_db()
        self._last_incident_time: float = 0.0
        self._last_amb_logged: Dict[str, float] = {}
        self._on_state: Optional[Callable] = None

    def _resolve_video(self, path=None) -> str:
        candidates = [path, config.VIDEO_PATH] + config.FALLBACK_VIDEO_PATHS
        for c in candidates:
            if c is None:
                continue
            if c == 0:
                return 0
            
            s_c = str(c)
            if s_c.startswith(("http://", "https://", "rtsp://", "rtmp://")):
                return s_c
                
            if os.path.isfile(s_c):
                return c
        return None

    def start(self, on_state: Optional[Callable] = None):
        self._on_state = on_state
        self.is_running = True
        
        self._capture_thread_obj = threading.Thread(target=self._capture_thread, daemon=True)
        self._inference_thread_obj = threading.Thread(target=self._inference_thread, daemon=True)
        self._audio_thread_obj = threading.Thread(target=self._audio_thread, daemon=True)
        
        self._capture_thread_obj.start()
        self._inference_thread_obj.start()
        self._audio_thread_obj.start()
        print("[4-Way Processor] Started capture, inference, and acoustic threads.")

    def stop(self):
        self.is_running = False
        if self._capture_thread_obj:
            self._capture_thread_obj.join(timeout=3.0)
        if self._inference_thread_obj:
            self._inference_thread_obj.join(timeout=3.0)
        if self._audio_thread_obj:
            self._audio_thread_obj.join(timeout=3.0)

    def draw_quadrant_signals(self, frame, optimizer_signals, qw, qh, lane_stats: Dict):
        """Render glowing signal states with countdown badges and PCU counts per quadrant."""
        positions = {
            "North": (20, 50),
            "South": (qw + 20, 50),
            "East":  (20, qh + 40),
            "West":  (qw + 20, qh + 40),
        }
        STATE_COLORS = {
            "green":  (0, 230, 110),
            "yellow": (0, 210, 255),
            "red":    (80, 80, 80),
        }
        for lane_name, pos in positions.items():
            if lane_name not in optimizer_signals:
                continue
            sig = optimizer_signals[lane_name]
            state_str = sig.state.value
            color = STATE_COLORS.get(state_str, (80, 80, 80))
            x, y = pos
            
            # Background Card
            cv2.rectangle(frame, (x - 8, y - 22), (x + 160, y + 26), (15, 15, 15), -1)
            cv2.rectangle(frame, (x - 8, y - 22), (x + 160, y + 26), (70, 70, 70), 1)
            
            # Traffic Light Circle
            cv2.circle(frame, (x + 12, y), 10, color, -1)
            
            # State Text & Time Left
            time_txt = f" {sig.time_left:.0f}s" if state_str in ("green", "yellow") else ""
            cv2.putText(frame, f"{state_str.upper()}{time_txt}", (x + 30, y + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
            
            # PCU / Vehicle Subtext
            stats = lane_stats.get(lane_name)
            if stats:
                subtext = f"{stats.vehicle_count}v | {stats.pcu_count:.1f} PCU"
                cv2.putText(frame, subtext, (x + 30, y + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1, cv2.LINE_AA)

    def draw_incidents(self, frame: np.ndarray, alerts: List[Dict]):
        """Render high-contrast tactical bounding boxes, collision impact brackets, and alert banners."""
        if not alerts:
            return
        fh, fw = frame.shape[:2]
        now = time.time()
        pulse = int(abs(np.sin(now * 5.0)) * 255)
        drawn_lanes = set()
        
        for a in alerts[-6:]:
            a_type = str(a.get("type", "")).lower()
            a_msg = str(a.get("message", ""))
            a_lane = a.get("lane", "")
            bbox = a.get("bbox")
            
            is_accident = ("accident" in a_type or "collision" in a_msg.lower() or "crash" in a_msg.lower())
            is_ped = ("pedestrian" in a_type or "conflict" in a_msg.lower() or "crowd" in a_type)
            is_stall = ("stall" in a_type or "parking" in a_type or "immobilized" in a_msg.lower())
            
            if not (is_accident or is_ped or is_stall):
                continue
                
            color = (0, pulse, 255) if is_accident else ((0, 180, 255) if is_ped else (0, 140, 255))
            
            if bbox is not None and len(bbox) == 4:
                try:
                    bx1, by1, bx2, by2 = map(int, bbox)
                    bx1 = max(0, min(fw - 20, bx1))
                    by1 = max(0, min(fh - 20, by1))
                    bx2 = max(bx1 + 20, min(fw, bx2))
                    by2 = max(by1 + 20, min(fh, by2))
                    
                    # Highlight bounding box
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 3, cv2.LINE_AA)
                    
                    # Tactical corner brackets
                    c_len = max(12, min(28, (bx2 - bx1) // 4, (by2 - by1) // 4))
                    cv2.line(frame, (bx1, by1), (bx1 + c_len, by1), (255, 255, 255), 3, cv2.LINE_AA)
                    cv2.line(frame, (bx1, by1), (bx1, by1 + c_len), (255, 255, 255), 3, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by1), (bx2 - c_len, by1), (255, 255, 255), 3, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by1), (bx2, by1 + c_len), (255, 255, 255), 3, cv2.LINE_AA)
                    cv2.line(frame, (bx1, by2), (bx1 + c_len, by2), (255, 255, 255), 3, cv2.LINE_AA)
                    cv2.line(frame, (bx1, by2), (bx1, by2 - c_len), (255, 255, 255), 3, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by2), (bx2 - c_len, by2), (255, 255, 255), 3, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by2), (bx2, by2 - c_len), (255, 255, 255), 3, cv2.LINE_AA)
                    
                    # Hazard banner above box
                    banner_txt = "CRITICAL: COLLISION DETECTED" if is_accident else ("PEDESTRIAN CONFLICT" if is_ped else "STALLED VEHICLE")
                    (tw, th), _ = cv2.getTextSize(banner_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.44, 1)
                    ban_y1 = max(0, by1 - th - 10)
                    ban_y2 = by1
                    if by1 < 30:
                        ban_y1 = by2
                        ban_y2 = by2 + th + 10
                        
                    ban_x2 = min(fw, bx1 + tw + 16)
                    cv2.rectangle(frame, (bx1, ban_y1), (ban_x2, ban_y2), (0, 0, 220) if is_accident else (10, 10, 20), -1)
                    cv2.rectangle(frame, (bx1, ban_y1), (ban_x2, ban_y2), (255, 255, 255), 1, cv2.LINE_AA)
                    cv2.putText(frame, banner_txt, (bx1 + 8, ban_y2 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 2, cv2.LINE_AA)
                except Exception:
                    pass
            
            # Quadrant warning badge in the corner of the approach
            if a_lane and a_lane not in drawn_lanes:
                drawn_lanes.add(a_lane)
                qw, qh = fw // 2, fh // 2
                lane_origins = {
                    "North": (10, qh - 25),
                    "South": (qw + 10, qh - 25),
                    "East":  (10, fh - 25),
                    "West":  (qw + 10, fh - 25),
                }
                if a_lane in lane_origins:
                    lx, ly = lane_origins[a_lane]
                    pill_txt = f"{a_lane.upper()}: {a_type.upper()} DETECTED"
                    cv2.rectangle(frame, (lx, ly - 16), (lx + 230, ly + 8), (0, 0, 180), -1)
                    cv2.rectangle(frame, (lx, ly - 16), (lx + 230, ly + 8), (255, 255, 255), 1, cv2.LINE_AA)
                    cv2.putText(frame, pill_txt, (lx + 6, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

    def _audio_thread(self):
        """Background thread monitoring acoustic siren status and triggering preemption."""
        while self.is_running:
            time.sleep(2.0)
            if not getattr(config, 'AUDIO_SIREN_ENABLED', True):
                continue
            
            # Test synthetic benchmark or live buffer
            status = self.audio_detector.get_status()
            if status.get("siren_active", False) and not self.optimizer.emergency_active:
                # Preempt highest priority waiting lane
                high_lane = self.optimizer.current_lane
                print(f"[4-Way Processor] Acoustic Siren Triggered Preemption on {high_lane}")
                self.optimizer.trigger_emergency(high_lane, source="audio")

    def _capture_thread(self):
        caps = [cv2.VideoCapture(v) for v in self.v_paths]
        qw, qh = self.frame_width // 2, self.frame_height // 2
        frame_delay = 1.0 / config.TARGET_FPS

        while self.is_running:
            start_time = time.time()
            frames = []
            for c in caps:
                ret, f = c.read()
                if not ret or f is None:
                    c.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, f = c.read()
                if ret and f is not None:
                    frames.append(cv2.resize(f, (qw, qh)))
                else:
                    # Black placeholder frame if video source unavailable
                    black = np.zeros((qh, qw, 3), dtype=np.uint8)
                    cv2.putText(black, "NO SIGNAL", (qw // 4, qh // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    frames.append(black)

            with self.state_lock:
                q_map = list(self.quadrant_mapping)

            mapped_frames = [frames[q_map[i]] for i in range(4)]
            top_row = np.hstack((mapped_frames[0], mapped_frames[1]))
            bot_row = np.hstack((mapped_frames[2], mapped_frames[3]))
            composite = np.vstack((top_row, bot_row))

            with self.state_lock:
                self.raw_frame = composite.copy()
                current_detections = list(self.shared_detections)
                current_tracks = list(self.shared_tracks)
                current_lane_stats = dict(self.shared_lane_stats)
                
                # Enrich analyzer metrics with live detector model and total physical road footprint
                m = dict(self.analyzer.metrics)
                m["active_model"] = getattr(self.detector, 'active_model_name', 'yolo11n.pt')
                m["active_model_label"] = getattr(self.detector, 'active_model_label', 'YOLOv11 Nano SOTA')
                m["total_footprint_m2"] = round(sum(
                    (t.dimensions.get("footprint_m2", 8.28) if hasattr(t, "dimensions") and isinstance(t.dimensions, dict) else 8.28)
                    for t in current_tracks if getattr(t, 'is_vehicle', True)
                ), 1)
                m["active_targets_count"] = len(current_tracks)
                self.latest_metrics = m
                self.latest_alerts  = [a.to_dict() for a in self.analyzer.alerts[-12:]]
                self.latest_signals = self.optimizer.get_metrics()
                
            annotated = composite.copy()
            self.lane_mgr.draw_lanes(annotated)
            if current_detections:
                self.detector.draw(annotated, current_detections, show_labels=False)
            if current_tracks:
                self.tracker.draw_tracks(annotated, current_tracks)
            
            self.optimizer.draw_signal_panel(annotated, x=10, y=10)
            self.draw_quadrant_signals(annotated, self.optimizer.signals, qw, qh, current_lane_stats)
            
            # Render tactical incident overlays (Accident perimeters, pedestrian conflict markers, stall boxes)
            self.draw_incidents(annotated, self.latest_alerts)

            # Acoustic Siren HUD Banner
            audio_status = self.audio_detector.get_status()
            if audio_status.get("siren_active", False):
                cv2.rectangle(annotated, (self.frame_width // 2 - 200, 10),
                              (self.frame_width // 2 + 200, 45), (0, 0, 220), -1)
                cv2.putText(annotated, f"ACOUSTIC SIREN ACTIVE ({audio_status.get('dominant_freq', 0):.0f} Hz)",
                            (self.frame_width // 2 - 180, 34),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
            
            self.latest_frame = annotated
            
            # ── Tactical Incident Detection & Evidence Logging ───────────────────
            now = time.time()
            if now - self._last_incident_time > 1.5:
                ranked_candidates = []
                
                # Priority 1: Accidents & Safety Hazards from Analyzer
                for a in self.latest_alerts:
                    a_type = str(a.get("type", "")).lower()
                    a_msg = str(a.get("message", ""))
                    a_lane = a.get("lane") or "Approach"
                    a_box = a.get("bbox")
                    
                    if "accident" in a_type or "collision" in a_msg.lower() or "crash" in a_msg.lower():
                        ranked_candidates.append((10, "accident", a_msg, a_lane, a_box))
                    elif "pedestrian" in a_type or "conflict" in a_type or "crowd" in a_type:
                        ranked_candidates.append((8, "crowd", a_msg, a_lane, a_box))
                    elif "stall" in a_type or "parking" in a_type or "immobilized" in a_msg.lower():
                        ranked_candidates.append((5, "parking", a_msg, a_lane, a_box))

                # Priority 2: Physical Emergency Vehicle Presence (debounced per approach)
                em_tracks = [t for t in current_tracks if getattr(t, 'is_emergency_vehicle', False) or getattr(t, 'is_ambulance', False) or getattr(t, 'is_fire_truck', False)]
                if em_tracks:
                    lead_em = em_tracks[0]
                    is_ft = getattr(lead_em, 'is_fire_truck', False) or lead_em.label in ["fire_truck", "firetruck"]
                    em_type = "Fire Truck" if is_ft else "Ambulance"
                    em_lane = lead_em.lane or self.optimizer.emergency_lane or "West"
                    if now > self._last_amb_logged.get(em_lane, 0.0):
                        em_box = (lead_em.x1, lead_em.y1, lead_em.x2, lead_em.y2)
                        ranked_candidates.append((7, "ambulance", f"Class-1 Emergency Priority: {em_type} active in {em_lane} corridor.", em_lane, em_box))
                        self._last_amb_logged[em_lane] = now + 25.0
                elif self.optimizer.emergency_active and getattr(self.optimizer, 'emergency_source', '') == "audio":
                    em_lane = self.optimizer.emergency_lane or "Corridor"
                    if now > self._last_amb_logged.get("audio", 0.0):
                        ranked_candidates.append((6, "ambulance", f"Acoustic Siren Preemption (Fallback): Emergency vehicle approaching {em_lane}.", em_lane, None))
                        self._last_amb_logged["audio"] = now + 25.0

                # Priority 3: Check for Stalled Queues (wait time >= ILLEGAL_PARKING_TIME)
                stall_limit = getattr(config, 'ILLEGAL_PARKING_TIME', 15.0)
                for lane, stats in current_lane_stats.items():
                    if getattr(stats, 'max_wait_time', 0.0) >= stall_limit:
                        stalled_box = None
                        for t in current_tracks:
                            if t.lane == lane and t.is_stopped and t.wait_time >= stall_limit:
                                stalled_box = (t.x1, t.y1, t.x2, t.y2)
                                break
                        ranked_candidates.append((4, "parking", f"Vehicle obstruction / standstill in {lane} approach ({stats.max_wait_time:.0f}s wait).", lane, stalled_box))

                if ranked_candidates:
                    ranked_candidates.sort(key=lambda x: x[0], reverse=True)
                    top_priority, top_type, top_msg, top_lane, top_box = ranked_candidates[0]
                    matched_box = top_box
                    if matched_box is None:
                        for t in current_tracks:
                            if t.lane == top_lane and getattr(t, 'is_vehicle', False):
                                matched_box = (t.x1, t.y1, t.x2, t.y2)
                                break
                    self.record_incident(top_type, top_msg, annotated, top_lane, bbox=matched_box)
                    self._last_incident_time = now
            
            if self._on_state:
                try:
                    self._on_state(self.get_state())
                except Exception:
                    pass
            
            elapsed = time.time() - start_time
            time.sleep(max(0, frame_delay - elapsed))
            
        for c in caps:
            c.release()

    def _inference_thread(self):
        while self.is_running:
            with self.state_lock:
                frame_to_process = self.raw_frame
            if frame_to_process is None:
                time.sleep(0.01)
                continue
            
            detections = self.detector.detect(frame_to_process)
            tracks = self.tracker.update(detections)
            
            # Real-World Metric Dimensions & Stopline Proximity Estimation
            for t in tracks:
                appr = t.lane if t.lane in ["North", "South", "East", "West"] else "North"
                t.dimensions = self.bev_engine.estimate_vehicle_dimensions(
                    appr, t.label, (t.x1, t.y1, t.x2, t.y2),
                    self.frame_width, self.frame_height
                )
                gx, gy = self.bev_engine.project_point(appr, t.cx, t.y2)
                t.ground_x_m = round(gx, 2)
                t.ground_y_m = round(gy, 2)
                
            lane_stats = self.lane_mgr.update(tracks)
            
            siren_active = False
            if hasattr(self, 'audio_detector') and self.audio_detector:
                siren_active = getattr(self.audio_detector, 'siren_detected', False) or self.audio_detector.get_status().get("siren_active", False)
            self.optimizer.update_phase_duration(lane_stats)
            self.optimizer.update(lane_stats, has_audio_siren=siren_active, audio_lane=self.optimizer.current_lane)
            self.analyzer.update(
                tracks, lane_stats, list(detections),
                signals=self.optimizer.signals,
                current_phase=self.optimizer.current_lane
            )
            
            # Pedestrian conflict evaluation
            ped_conflicts = self.ped_safety.evaluate_conflicts(
                [d for d in detections if d.is_person],
                tracks,
                self.optimizer.current_lane
            )
            for pc in ped_conflicts:
                self.analyzer.alerts.append(Alert(
                    alert_type="pedestrian_conflict",
                    message=pc["message"],
                    lane=pc["lane"],
                    severity="critical"
                ))

            # Active Learning Uncertainty Harvesting (Data Flywheel)
            if hasattr(self, 'active_learning'):
                try:
                    self.active_learning.evaluate_and_harvest(
                        frame_to_process, detections,
                        has_audio_siren=self.audio_detector.siren_detected,
                        approach_name=self.optimizer.current_lane
                    )
                except Exception as e:
                    import logging
                    logging.getLogger("video_processor_4way").warning(f"[ActiveLearning] Uncertainty harvest error: {e}")

            with self.state_lock:
                self.shared_detections = detections
                self.shared_tracks     = tracks
                self.shared_lane_stats = lane_stats
            time.sleep(0.01)

    def get_jpeg_frame(self, quality: int = None) -> Optional[bytes]:
        if self.latest_frame is None:
            return None
        _, buf = cv2.imencode(".jpg", self.latest_frame,
                              [cv2.IMWRITE_JPEG_QUALITY, quality or config.STREAM_JPEG_QUALITY])
        return buf.tobytes()
        
    def get_b64_frame(self) -> str:
        jpg = self.get_jpeg_frame()
        return base64.b64encode(jpg).decode("utf-8") if jpg else None

    def get_bev_radar_state(self) -> Dict:
        """Projects active tracks into a calibrated 2D metric ground plane coordinate space."""
        with self.state_lock:
            tracks_copy = list(self.shared_tracks[:25])
            
        bev_nodes = []
        for t in tracks_copy:
            approach = t.lane if t.lane in ["North", "South", "East", "West"] else "North"
            gx, gy = self.bev_engine.transform_track_to_ground(approach, t.cx, t.cy, self.frame_width, self.frame_height)
            dims = getattr(t, 'dimensions', {}) or {}
            bev_nodes.append({
                "id": t.track_id,
                "label": t.label,
                "approach": approach,
                "ground_x_m": round(gx, 2),
                "ground_y_m": round(gy, 2),
                "speed_kmh": round(getattr(t, 'speed_kmh', 0.0), 1),
                "is_ambulance": getattr(t, 'is_ambulance', False),
                "is_fire_truck": getattr(t, 'is_fire_truck', False),
                "is_emergency_vehicle": getattr(t, 'is_emergency_vehicle', False) or getattr(t, 'is_ambulance', False) or getattr(t, 'is_fire_truck', False),
                "pcu": getattr(t, 'pcu', 1.0),
                "length_m": dims.get("length_m", 4.6),
                "width_m": dims.get("width_m", 1.8),
                "footprint_m2": dims.get("footprint_m2", 8.28),
                "dist_to_stopline_m": dims.get("dist_to_stopline_m", round(max(0.0, float(gy)), 1)),
            })
            
        return {
            "vehicles": bev_nodes,
            "timestamp": time.time()
        }

    def get_state(self) -> Dict:
        with self.state_lock:
            targets = [t.to_dict() for t in self.shared_tracks[:25]]
        return {
            "metrics":           self.latest_metrics,
            "alerts":            self.latest_alerts,
            "signals":           self.latest_signals,
            "chart":             self.analyzer.get_chart_data(),
            "audio_siren":       self.audio_detector.get_status(),
            "v2x_spat":          self.v2x_engine.generate_spat_message(self.latest_signals),
            "green_wave":        self.green_wave.get_corridor_synchronization_plan(self.optimizer.webster_cycle_length),
            "pedestrian_safety": {"pci_duration": self.ped_safety.pci_duration},
            "active_targets":    targets,
            "bev_radar":         self.get_bev_radar_state(),
            "active_learning":   self.active_learning.get_status() if hasattr(self, 'active_learning') else {},
            "frame_b64":         self.get_b64_frame(),
        }

    def get_incident_history(self) -> List[Dict]:
        with self.state_lock:
            return list(self.incident_history)

    def record_incident(self, inc_type: str, description: str, frame: Optional[np.ndarray] = None, lane: Optional[str] = None, bbox: Optional[Tuple[int, int, int, int]] = None):
        """Thread-safe recording of an incident with auto-cropped vehicle/incident ROI and full evidence frame."""
        now = time.time()
        with self.state_lock:
            # Check recent duplicate of same type & lane within 8 seconds
            for inc in self.incident_history[:5]:
                if inc.get("type") == inc_type and inc.get("lane") == lane:
                    if (now - inc.get("timestamp", 0)) < 8.0:
                        return  # Throttled duplicate
            
            target_frame = frame if frame is not None else self.latest_frame
            if target_frame is None and self.raw_frame is not None:
                target_frame = self.raw_frame
                
            b64_frame = ""
            cropped_b64 = ""
            single_cam_b64 = ""
            qw = getattr(self, 'frame_width', 1280) // 2
            qh = getattr(self, 'frame_height', 720) // 2
            crop_coords = None

            if target_frame is not None:
                try:
                    fh, fw = target_frame.shape[:2]
                    qh, qw = fh // 2, fw // 2

                    # Tactical forensic banner colors
                    COLORS = {
                        "accident":  (0, 0, 220),    # Red
                        "ambulance": (180, 0, 220),  # Crimson / Purple
                        "parking":   (0, 140, 255),  # Orange
                        "crowd":     (240, 140, 0),  # Blue / Amber
                        "red_light": (0, 0, 240),    # Red
                        "footpath":  (0, 180, 240),  # Yellow
                    }
                    banner_color = COLORS.get(inc_type, (0, 0, 200))

                    # 1. Map approach lane to THAT camera image quadrant (Single Camera View, NOT 4 cameras)
                    quadrant_slices = {
                        "North": (0, qh, 0, qw),
                        "South": (0, qh, qw, fw),
                        "East":  (qh, fh, 0, qw),
                        "West":  (qh, fh, qw, fw),
                    }
                    lane_name = lane if (lane in quadrant_slices) else "East"
                    qy1, qy2, qx1, qx2 = quadrant_slices.get(lane_name, (0, qh, 0, qw))

                    # Extract THAT camera image only (clean high-res single-camera frame)
                    single_cam_img = target_frame[qy1:qy2, qx1:qx2].copy()
                    _, cam_buf = cv2.imencode(".jpg", single_cam_img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                    single_cam_b64 = base64.b64encode(cam_buf.tobytes()).decode("utf-8")

                    # 2. Balanced context crop (generous margin, never over-zoomed)
                    if bbox is not None:
                        bx1, by1, bx2, by2 = bbox
                    else:
                        bx1, by1, bx2, by2 = qx1 + int(qw * 0.2), qy1 + int(qh * 0.2), qx1 + int(qw * 0.8), qy1 + int(qh * 0.8)

                    # Clamp to this single camera quadrant with generous 50% road context
                    bx1 = max(qx1, min(qx2 - 40, bx1))
                    by1 = max(qy1, min(qy2 - 40, by1))
                    bx2 = max(bx1 + 40, min(qx2, bx2))
                    by2 = max(by1 + 40, min(qy2, by2))

                    pad_x = max(int((bx2 - bx1) * 0.5), 60)
                    pad_y = max(int((by2 - by1) * 0.5), 50)
                    cx1 = max(qx1, bx1 - pad_x)
                    cy1 = max(qy1, by1 - pad_y)
                    cx2 = min(qx2, bx2 + pad_x)
                    cy2 = min(qy2, by2 + pad_y)

                    if (cx2 - cx1) >= 80 and (cy2 - cy1) >= 60:
                        crop_img = target_frame[cy1:cy2, cx1:cx2].copy()
                        _, crop_buf = cv2.imencode(".jpg", crop_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                        cropped_b64 = base64.b64encode(crop_buf.tobytes()).decode("utf-8")
                        crop_coords = [cx1 - qx1, cy1 - qy1, cx2 - cx1, cy2 - cy1]
                    else:
                        cropped_b64 = single_cam_b64
                        crop_coords = [0, 0, qw, qh]

                    # 3. Full 4-Camera composite with Forensic Banner
                    snap = target_frame.copy()
                    cv2.rectangle(snap, (0, 0), (fw, 40), (10, 10, 15), -1)
                    cv2.rectangle(snap, (0, 38), (fw, 40), banner_color, -1)
                    badge = f"INCIDENT: {inc_type.upper()}"
                    if lane:
                        badge += f" | {lane.upper()} APPROACH"
                    badge += f" | {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}"
                    cv2.putText(snap, badge, (16, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(snap, "[FORENSIC EVIDENCE CAPTURE]", (fw - 270, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.48, banner_color, 1, cv2.LINE_AA)

                    _, buf = cv2.imencode(".jpg", snap, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    b64_frame = base64.b64encode(buf.tobytes()).decode("utf-8")
                except Exception as e:
                    print(f"[Incident] Snapshot capture error: {e}")
                    single_cam_b64 = ""
                    cropped_b64 = ""
                    b64_frame = ""

            incident_item = {
                "id": f"INC_{int(now * 1000) % 100000}",
                "type": inc_type,
                "lane": lane or "Approach",
                "description": description,
                "timestamp": now,
                "bbox": str(crop_coords) if crop_coords else f"[0, 0, {qw}, {qh}]",
                "camera_frame_b64": single_cam_b64,
                "cropped_image_b64": single_cam_b64, # Default to THAT camera image only (not over-zoomed)
                "vehicle_crop_b64": cropped_b64,
                "frame_b64": single_cam_b64,          # THAT camera image only (not 4 cameras)
                "full_4way_b64": b64_frame            # 4-way composite
            }
            self.incident_history.insert(0, incident_item)
            while len(self.incident_history) > 30:
                self.incident_history.pop()

            # Persist to VIGIL SQLite database
            try:
                from backend.database import SessionLocal
                import backend.models.db_models as db_models
                db = SessionLocal()
                cam_map = {"North": "CAM_NORTH_01", "South": "CAM_SOUTH_01", "East": "CAM_EAST_01", "West": "CAM_WEST_01"}
                camera_id = cam_map.get(lane, "CAM_NORTH_01")
                db_inc = db_models.Incident(
                    id=incident_item["id"],
                    incident_type=inc_type,
                    source_module="traffic",
                    camera_id=camera_id,
                    lane=lane or "Approach",
                    timestamp=now,
                    confidence=0.90,
                    severity="critical" if inc_type in ["accident", "ambulance"] else "high" if inc_type == "crowd" else "medium",
                    validation_status="confirmed",
                    status="new",
                    description=description,
                    snapshot_b64=single_cam_b64
                )
                db.merge(db_inc)
                db_alert = db_models.Alert(
                    incident_id=incident_item["id"],
                    alert_type=inc_type,
                    source_module="traffic",
                    severity=db_inc.severity,
                    message=description,
                    lane=lane or "Approach",
                    acknowledged=False
                )
                db.add(db_alert)
                db.commit()
                db.close()
            except Exception as e:
                print(f"[Database] Error persisting incident {incident_item['id']}: {e}")

    def _load_recent_incidents_from_db(self) -> List[Dict]:
        """Loads real persisted incidents from the VIGIL database instead of mock data."""
        try:
            from backend.database import SessionLocal
            import backend.models.db_models as db_models
            db = SessionLocal()
            records = db.query(db_models.Incident).order_by(db_models.Incident.timestamp.desc()).limit(30).all()
            items = []
            for r in records:
                items.append({
                    "id": r.id,
                    "type": r.incident_type,
                    "lane": r.lane or "Approach",
                    "description": r.description,
                    "timestamp": r.timestamp,
                    "frame_b64": r.snapshot_b64 or "",
                    "camera_frame_b64": r.snapshot_b64 or "",
                    "cropped_image_b64": r.snapshot_b64 or ""
                })
            db.close()
            return items
        except Exception as e:
            print(f"[Database] Could not load persisted incidents: {e}")
            return []

    def set_quadrant_mapping(self, mapping: List[int]):
        if len(mapping) == 4:
            with self.state_lock:
                self.quadrant_mapping = mapping

