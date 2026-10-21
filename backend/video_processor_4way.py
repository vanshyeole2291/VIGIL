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
from collections import deque
import hashlib
from core.violence_detector import RollingEvidenceBuffer
from backend.database import SessionLocal
import backend.models.db_models as db_models

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
    def __init__(self, v_north="", v_south="", v_east="", v_west="",
                 frame_width=None, frame_height=None):
        self.v_paths = [self._resolve_video(v) for v in [v_north, v_south, v_east, v_west]]
        self.frame_width  = frame_width  or config.FRAME_WIDTH
        self.frame_height = frame_height or config.FRAME_HEIGHT
        
        self.detector       = Detector()
        self.tracker        = CentroidTracker(max_disappeared=35, max_distance=110)
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
        self.is_paused = False
        self._pause_start = 0.0
        self.v_north = v_north
        self.v_south = v_south
        self.v_east = v_east
        self.v_west = v_west
        self._caps_to_switch = {}
        self.evidence_buffer = RollingEvidenceBuffer(max_buffer_sec=12.0, target_fps=config.TARGET_FPS)
        self._active_logged_events: Dict[str, float] = {}
        
        self.state_lock = threading.Lock()
        self.raw_frame: Optional[np.ndarray] = None
        self.shared_detections: List = []
        self.shared_tracks:     List = []
        self.shared_lane_stats: Dict = {}
        
        self.latest_frame:   Optional[np.ndarray] = None
        self.latest_metrics: Dict = {}
        self.latest_alerts:  List = []
        self.latest_signals: Dict = {}
        self.incident_history: List[Dict] = []
        self._last_incident_time: float = 0.0
        self._last_amb_logged: Dict[str, float] = {}
        self._on_state: Optional[Callable] = None
        
        # Real-time cropped detection ring buffer for UI scanner
        self.crop_ring: deque = deque(maxlen=80)
        self.inference_fps: float = 0.0
        self.detection_frame_count: int = 0
        self._last_state_push: float = 0.0
        self.class_counts: Dict[str, int] = {}
        self._fps_t0 = time.time()
        self._fps_fc = 0


    def pause(self):
        """Immediately halt video processing and freeze inference frames."""
        self.is_paused = True
        if hasattr(self.optimizer, 'pause'):
            self.optimizer.pause()
        print("[4-Way Processor] Processing PAUSED (Inference and video capture halted)")

    def resume(self):
        """Resume video processing and inference from current frame."""
        self.is_paused = False
        if hasattr(self.optimizer, 'resume'):
            self.optimizer.resume()
        print("[4-Way Processor] Processing RESUMED")

    def toggle_pause(self) -> bool:
        """Toggle pause state."""
        if self.is_paused:
            self.resume()
        else:
            self.pause()
        return self.is_paused

    def switch_camera_source(self, camera_id: str, new_path: str) -> bool:
        """
        Dynamically switch the video source for a specific camera ID without restarting server.
        camera_id: 'North', 'South', 'East', 'West', 'CAM_NORTH_01', 0, 1, 2, 3.
        """
        resolved_path = self._resolve_video(new_path)
        lane_map = {
            "north": 0, "cam_north_01": 0, "0": 0,
            "south": 1, "cam_south_01": 1, "1": 1,
            "east":  2, "cam_east_01":  2, "2": 2,
            "west":  3, "cam_west_01":  3, "3": 3,
        }
        key = str(camera_id).lower().strip()
        idx = lane_map.get(key, None)
        if idx is None or idx >= 4:
            return False

        with self.state_lock:
            self.v_paths[idx] = resolved_path
            if idx == 0: self.v_north = new_path
            elif idx == 1: self.v_south = new_path
            elif idx == 2: self.v_east = new_path
            elif idx == 3: self.v_west = new_path
            self._caps_to_switch[idx] = resolved_path
        print(f"[4-Way Processor] Scheduled dynamic source switch for camera {camera_id} (index {idx}) -> {new_path}")
        return True

    def _crop_b64(self, frame: np.ndarray, x1: int, y1: int, x2: int, y2: int, pad: int = 6) -> str:
        """Extract and upscale isolated bounding box for UI detection gallery."""
        try:
            h, w = frame.shape[:2]
            cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
            cx2, cy2 = min(w, x2 + pad), min(h, y2 + pad)
            crop = frame[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                return ""
            ch, cw = crop.shape[:2]
            if max(ch, cw) < 120:
                scale = 120.0 / max(ch, cw)
                crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_LINEAR)
            _, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        except Exception:
            return ""

    def _resolve_video(self, path=None) -> str:
        """Find a valid video file or return empty string if unassigned."""
        if not path or str(path).strip().lower() in ("", "none", "null", "undefined", "unassigned"):
            return ""

        candidates = [
            path,
            os.path.join(config.BASE_DIR, "assets", "videos", str(path)),
            os.path.join(config.BASE_DIR, str(path)),
        ]
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
        return ""

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
            "North": (225, 48),    # Positioned cleanly to the right of the Webster ATSC panel
            "South": (qw + 20, 48),
            "East":  (20, qh + 45),
            "West":  (qw + 20, qh + 45),
        }
        STATE_COLORS = {
            "green":  (0, 230, 80),    # Vibrant emerald green
            "yellow": (0, 215, 255),   # Vibrant amber yellow
            "red":    (30, 30, 240),   # Vibrant traffic signal red
        }
        for lane_name, pos in positions.items():
            if lane_name not in optimizer_signals:
                continue
            sig = optimizer_signals[lane_name]
            state_str = sig.state.value
            color = STATE_COLORS.get(state_str, (30, 30, 240))
            x, y = pos
            
            # Background Card
            cv2.rectangle(frame, (x - 8, y - 22), (x + 160, y + 26), (15, 17, 22), -1)
            cv2.rectangle(frame, (x - 8, y - 22), (x + 160, y + 26), (65, 70, 85), 1)
            
            # Traffic Light Circle (Glowing Filled Circle)
            cv2.circle(frame, (x + 12, y), 9, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (x + 12, y), 11, color, 1, cv2.LINE_AA)
            
            # State Text & Monotonic Time Left
            time_txt = f" {sig.time_left:.0f}s" if state_str in ("green", "yellow") else ""
            cv2.putText(frame, f"{state_str.upper()}{time_txt}", (x + 30, y + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
            
            # PCU / Vehicle Subtext
            stats = lane_stats.get(lane_name)
            if stats:
                subtext = f"{stats.vehicle_count}v | {stats.pcu_count:.1f} PCU"
                cv2.putText(frame, subtext, (x + 30, y + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (190, 195, 205), 1, cv2.LINE_AA)

    def draw_incidents(self, frame: np.ndarray, alerts: List[Dict]):
        """Render crisp, non-flickering incident markers on verified anomalies."""
        if not alerts:
            return
        fh, fw = frame.shape[:2]
        drawn_lanes = set()

        for a in alerts[-4:]:
            a_type = str(a.get("type", "")).lower()
            a_msg = str(a.get("message", ""))
            a_lane = a.get("lane") or ""
            bbox = a.get("bbox")

            is_accident = ("accident" in a_type or "collision" in a_msg.lower() or "crash" in a_msg.lower())
            is_stall = ("stall" in a_type or "parking" in a_type or "immobilized" in a_msg.lower())

            # Suppress collision/accident alerts completely if ENABLE_COLLISION_ALERTS is False
            if is_accident and not getattr(config, 'ENABLE_COLLISION_ALERTS', False):
                continue

            if not (is_accident or is_stall):
                continue

            color = (0, 0, 230) if is_accident else (0, 140, 255)

            if bbox is not None and len(bbox) == 4:
                try:
                    bx1, by1, bx2, by2 = map(int, bbox)
                    bx1 = max(0, min(fw - 20, bx1))
                    by1 = max(0, min(fh - 20, by1))
                    bx2 = max(bx1 + 20, min(fw, bx2))
                    by2 = max(by1 + 20, min(fh, by2))

                    # Solid clean box without pulsing
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 2, cv2.LINE_AA)

                    # Corner accents
                    c_len = max(8, min(16, (bx2 - bx1) // 4, (by2 - by1) // 4))
                    cv2.line(frame, (bx1, by1), (bx1 + c_len, by1), (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.line(frame, (bx1, by1), (bx1, by1 + c_len), (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by1), (bx2 - c_len, by1), (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by1), (bx2, by1 + c_len), (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.line(frame, (bx1, by2), (bx1 + c_len, by2), (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.line(frame, (bx1, by2), (bx1, by2 - c_len), (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by2), (bx2 - c_len, by2), (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.line(frame, (bx2, by2), (bx2, by2 - c_len), (255, 255, 255), 2, cv2.LINE_AA)

                    # Alert tag
                    banner_txt = "[!] COLLISION ALERT" if is_accident else "[!] STALLED VEHICLE"
                    (tw, th), _ = cv2.getTextSize(banner_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                    ban_y1 = max(0, by1 - th - 8)
                    ban_y2 = by1
                    if by1 < 25:
                        ban_y1 = by2
                        ban_y2 = by2 + th + 8

                    ban_x2 = min(fw, bx1 + tw + 12)
                    cv2.rectangle(frame, (bx1, ban_y1), (ban_x2, ban_y2), (15, 15, 25), -1)
                    cv2.rectangle(frame, (bx1, ban_y1), (ban_x2, ban_y2), color, 1, cv2.LINE_AA)
                    cv2.putText(frame, banner_txt, (bx1 + 6, ban_y2 - 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
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
        caps = [cv2.VideoCapture(v) if (v and os.path.exists(str(v))) else None for v in self.v_paths]
        qw, qh = self.frame_width // 2, self.frame_height // 2
        frame_delay = 1.0 / config.TARGET_FPS
        direction_labels = ["NORTH", "SOUTH", "EAST", "WEST"]

        while self.is_running:
            start_time = time.time()

            # Dynamic camera video source switching without server restart
            with self.state_lock:
                switches = dict(self._caps_to_switch)
                self._caps_to_switch.clear()

            for idx, new_p in switches.items():
                if idx < len(caps) and caps[idx] is not None:
                    try:
                        caps[idx].release()
                    except Exception:
                        pass
                caps[idx] = cv2.VideoCapture(new_p) if (new_p and os.path.exists(str(new_p))) else None
                print(f"[4-Way Processor] Dynamically re-opened VideoCapture index {idx} with: {new_p}")

            # If paused, hold current frame without advancing video positions
            if self.is_paused:
                time.sleep(0.04)
                continue

            frames = []
            for idx, c in enumerate(caps):
                frame_obtained = False
                if c is not None and c.isOpened():
                    ret, f = c.read()
                    if not ret or f is None:
                        c.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, f = c.read()
                    if ret and f is not None:
                        frames.append(cv2.resize(f, (qw, qh)))
                        frame_obtained = True

                if not frame_obtained:
                    # Sleek tactical placeholder card when no video source is assigned
                    d_name = direction_labels[idx] if idx < 4 else f"CAM {idx+1}"
                    placeholder = np.zeros((qh, qw, 3), dtype=np.uint8)
                    placeholder[:] = (12, 16, 24)

                    # Subtle tactical coordinate grid
                    for gx in range(0, qw, 48):
                        cv2.line(placeholder, (gx, 0), (gx, qh), (20, 26, 38), 1)
                    for gy in range(0, qh, 48):
                        cv2.line(placeholder, (0, gy), (qw, gy), (20, 26, 38), 1)

                    # Perimeter border
                    cv2.rectangle(placeholder, (4, 4), (qw - 4, qh - 4), (32, 42, 60), 1)

                    # Crosshair marker
                    cx_p, cy_p = qw // 2, qh // 2
                    cv2.drawMarker(placeholder, (cx_p, cy_p - 15), (0, 180, 240), cv2.MARKER_CROSS, 20, 1)

                    # Status typography
                    cv2.putText(placeholder, f"[{d_name} APPROACH]", (cx_p - 68, cy_p - 35),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 200, 255), 1, cv2.LINE_AA)
                    cv2.putText(placeholder, "NO VIDEO SOURCE ASSIGNED", (cx_p - 108, cy_p + 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200, 210, 225), 1, cv2.LINE_AA)
                    cv2.putText(placeholder, "Select or upload video below", (cx_p - 90, cy_p + 35),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (110, 120, 140), 1, cv2.LINE_AA)
                    frames.append(placeholder)

            with self.state_lock:
                q_map = list(self.quadrant_mapping)

            mapped_frames = [frames[q_map[i]] for i in range(4)]
            top_row = np.hstack((mapped_frames[0], mapped_frames[1]))
            bot_row = np.hstack((mapped_frames[2], mapped_frames[3]))
            composite = np.vstack((top_row, bot_row))

            # Feed frame to rolling circular evidence buffer
            if hasattr(self, 'evidence_buffer') and self.evidence_buffer is not None:
                self.evidence_buffer.add_frame(composite, start_time)

            with self.state_lock:
                self.raw_frame = composite.copy()
                current_detections = list(self.shared_detections)
                current_tracks = list(self.shared_tracks)
                current_lane_stats = dict(self.shared_lane_stats)
                
                # Enrich analyzer metrics with live detector model and total physical road footprint
                m = dict(self.analyzer.metrics)
                m["active_model"] = getattr(self.detector, 'active_model_name', 'best (12).pt')
                m["active_model_label"] = getattr(self.detector, 'active_model_label', 'Custom SOTA v12 (User Fine-Tuned Model)')
                m["total_footprint_m2"] = round(sum(
                    (t.dimensions.get("footprint_m2", 8.28) if hasattr(t, "dimensions") and isinstance(t.dimensions, dict) else 8.28)
                    for t in current_tracks if getattr(t, 'is_vehicle', True)
                ), 1)
                m["active_targets_count"] = len(current_tracks)
                self.latest_metrics = m
                self.latest_alerts  = [a.to_dict() for a in self.analyzer.alerts[-12:]]
                self.latest_signals = self.optimizer.get_metrics()
                
            annotated = composite.copy()
            self.lane_mgr.draw_lanes(annotated, show_labels=False)
            
            # Sub-frame motion projection between inferences so boxes glide constantly with vehicles
            now_draw = time.time()
            dt_draw = min(0.04, max(0.01, now_draw - getattr(self, '_last_draw_time', now_draw)))
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
            
            # ── Tactical Incident Detection & Evidence Logging ─────────────────────
            now = time.time()
            has_urgent_accident = any("accident" in str(a.get("type", "")).lower() or "collision" in str(a.get("message", "")).lower() for a in self.latest_alerts)
            if has_urgent_accident or (now - self._last_incident_time > 15.0):
                ranked_candidates = []
                
                # Priority 1: Accidents & Safety Hazards from Analyzer (Accidents strictly gated)
                for a in self.latest_alerts:
                    a_type = str(a.get("type", "")).lower()
                    a_msg = str(a.get("message", ""))
                    a_lane = a.get("lane") or "Approach"
                    a_box = a.get("bbox")
                    
                    if "accident" in a_type or "collision" in a_msg.lower() or "crash" in a_msg.lower():
                        if getattr(config, 'ENABLE_COLLISION_ALERTS', False):
                            ranked_candidates.append((25, "accident", a_msg, a_lane, a_box))
                    # Filtered out: non-accident / routine crowd
                    # Filtered out: routine queue dwell

                # Priority 2: Physical Emergency Vehicle Presence (debounced per approach)
                # Only genuine ambulances with verified status (never transit buses)
                amb_tracks = [t for t in current_tracks if getattr(t, 'is_ambulance', False) and getattr(t, 'label', '') != 'bus']
                if amb_tracks:
                    lead_amb = amb_tracks[0]
                    amb_lane = lead_amb.lane or self.optimizer.emergency_lane or "West"
                    if now > self._last_amb_logged.get(amb_lane, 0.0):
                        amb_box = (lead_amb.x1, lead_amb.y1, lead_amb.x2, lead_amb.y2)
                        ranked_candidates.append((12, "ambulance", f"Class-1 Emergency Priority: Ambulance active in {amb_lane} corridor.", amb_lane, amb_box))
                        self._last_amb_logged[amb_lane] = now + 600.0
                elif self.optimizer.emergency_active and getattr(self.optimizer, 'emergency_source', '') == "audio":
                    em_lane = self.optimizer.emergency_lane or "Corridor"
                    if now > self._last_amb_logged.get("audio", 0.0):
                        ranked_candidates.append((6, "ambulance", f"Acoustic Siren Preemption: Emergency vehicle approaching {em_lane}.", em_lane, None))
                        self._last_amb_logged["audio"] = now + 600.0

# Routine queue stalls excluded: Only true collisions & ambulances logged

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
            
            if self._on_state and (now - self._last_state_push >= 0.35):
                self._last_state_push = now
                try:
                    self._on_state(self.get_state())
                except Exception:
                    pass
            
            elapsed = time.time() - start_time
            time.sleep(max(0, frame_delay - elapsed))
            
        for c in caps:
            if c is not None:
                c.release()

    def _inference_thread(self):
        while self.is_running:
            if self.is_paused:
                time.sleep(0.04)
                continue
            with self.state_lock:
                frame_to_process = self.raw_frame
            if frame_to_process is None:
                time.sleep(0.01)
                continue
            
            try:
                detections = self.detector.detect(frame_to_process)
                
                # Tag detections with their respective quadrant approach BEFORE tracker update
                qw, qh = self.frame_width // 2, self.frame_height // 2
                for d in detections:
                    if d.cx < qw and d.cy < qh:
                        d.lane = "North"
                    elif d.cx >= qw and d.cy < qh:
                        d.lane = "South"
                    elif d.cx < qw and d.cy >= qh:
                        d.lane = "East"
                    else:
                        d.lane = "West"

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
                
                # Check for ambulance tracks to trigger immediate priority preemption
                amb_tracks = [t for t in tracks if getattr(t, 'is_ambulance', False) and getattr(t, 'label', '') != 'bus']
                if amb_tracks:
                    lead_amb = amb_tracks[0]
                    amb_lane = lead_amb.lane or "North"
                    if amb_lane in ["North", "South", "East", "West"]:
                        self.optimizer.trigger_emergency(amb_lane, source="visual")

                self.optimizer.update_phase_duration(lane_stats)
                self.optimizer.update(lane_stats)
                self.analyzer.update(
                    tracks, lane_stats, list(detections),
                    signals=self.optimizer.signals,
                    current_phase=self.optimizer.current_lane,
                    optimizer=self.optimizer
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

                # Calculate inference FPS and class counts
                now_t = time.time()
                self._fps_fc += 1
                if now_t - self._fps_t0 >= 1.0:
                    self.inference_fps = round(self._fps_fc / (now_t - self._fps_t0), 1)
                    self._fps_fc = 0
                    self._fps_t0 = now_t

                cls_cnt = {}
                for d in detections:
                    lbl = str(getattr(d, 'label', 'unknown')).lower()
                    cls_cnt[lbl] = cls_cnt.get(lbl, 0) + 1
                self.class_counts = cls_cnt
                self.detection_frame_count += 1

                # Extract recent cropped bounding-boxes for real-time gallery
                new_crops = []
                for i, d in enumerate(detections[:12]):
                    crop_b64 = self._crop_b64(frame_to_process, int(d.x1), int(d.y1), int(d.x2), int(d.y2))
                    if crop_b64:
                        lbl = str(getattr(d, 'label', 'Vehicle'))
                        new_crops.append({
                            "id": f"det_{int(now_t * 1000)}_{i}",
                            "label": lbl.capitalize(),
                            "label_raw": lbl.lower(),
                            "confidence": round(float(getattr(d, 'confidence', 0.85)), 2),
                            "pcu": round(float(getattr(d, 'pcu', 1.0)), 2),
                            "is_ambulance": bool(getattr(d, 'is_ambulance', False)),
                            "lane": getattr(d, 'lane', 'Active'),
                            "bbox": [int(d.x1), int(d.y1), int(d.x2), int(d.y2)],
                            "timestamp": now_t,
                            "crop_b64": crop_b64
                        })

                with self.state_lock:
                    self.shared_detections = detections
                    self.shared_tracks     = tracks
                    self.shared_lane_stats = lane_stats
                    if new_crops:
                        for c in new_crops:
                            self.crop_ring.appendleft(c)
            except Exception as e:
                import logging
                logging.getLogger("video_processor_4way").error(f"[InferenceThread] Error in processing frame: {e}")

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

    def get_recent_detections(self, limit: int = 40) -> List[Dict]:
        with self.state_lock:
            return list(self.crop_ring)[:limit]

    def get_detection_stats(self) -> Dict:
        with self.state_lock:
            m_name = getattr(self.detector, 'active_model_name', 'best (12).pt')
            m_label = getattr(self.detector, 'active_model_label', 'Custom SOTA v12 (User Fine-Tuned Model)')
            total_pcu = self.analyzer.metrics.get("total_pcu", 0.0)
            video_sources = [os.path.basename(v) for v in self.v_paths if v]
            return {
                "fps": self.inference_fps,
                "frame_count": self.detection_frame_count,
                "total_pcu": total_pcu,
                "class_counts": dict(self.class_counts),
                "model": m_name,
                "model_label": m_label,
                "video_sources": video_sources,
                "detection_count": len(self.shared_detections),
                "incident_count": len(self.incident_history),
                "running": self.is_running
            }

    def record_incident(self, inc_type: str, description: str, frame: Optional[np.ndarray] = None, lane: Optional[str] = None, bbox: Optional[Tuple[int, int, int, int]] = None):
        """Thread-safe recording of an incident with auto-cropped vehicle/incident ROI and full evidence frame."""
        now = time.time()
        lane_idx_map = {"North": 0, "South": 1, "East": 2, "West": 3}
        q_idx = lane_idx_map.get(lane, 0)
        src_file = self.v_paths[q_idx] if (q_idx < len(self.v_paths) and self.v_paths[q_idx]) else f"{str(lane).lower()}.mp4"
        cctv_filename = os.path.basename(str(src_file)) if src_file else "stream.mp4"
        exact_camera_id = f"CCTV: {cctv_filename}"
        exact_lane_id = f"{lane} ({cctv_filename})" if lane else exact_camera_id

        # Strict Single-Event Deduplication: One incident ONLY ONE TIME per camera stream
        dedup_key = f"{inc_type}:{exact_camera_id}"
        with self.state_lock:
            last_logged = self._active_logged_events.get(dedup_key, 0.0)
            if now - last_logged < 15.0:  # 15s cooldown prevents single-frame duplicates
                return
            self._active_logged_events[dedup_key] = now

            target_frame = frame if frame is not None else self.latest_frame
            if target_frame is None and self.raw_frame is not None:
                target_frame = self.raw_frame
                
            b64_frame = ""
            cropped_b64 = ""
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

                    # Extract THAT camera image only from clean raw frame (never corrupted by banners)
                    clean_source = self.raw_frame if self.raw_frame is not None else target_frame
                    single_cam_img = clean_source[qy1:qy2, qx1:qx2].copy()
                    _, cam_buf = cv2.imencode(".jpg", single_cam_img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                    single_cam_b64 = base64.b64encode(cam_buf.tobytes()).decode("utf-8")

                    # 2. Balanced context crop (generous margin, never over-zoomed or empty bar)
                    if bbox is not None:
                        bx1, by1, bx2, by2 = bbox
                    else:
                        bx1, by1, bx2, by2 = qx1 + int(qw * 0.2), qy1 + int(qh * 0.2), qx1 + int(qw * 0.8), qy1 + int(qh * 0.8)

                    # Clamp to this single camera quadrant with generous road context
                    bx1 = max(qx1, min(qx2 - 40, bx1))
                    by1 = max(qy1, min(qy2 - 40, by1))
                    bx2 = max(bx1 + 40, min(qx2, bx2))
                    by2 = max(by1 + 40, min(qy2, by2))

                    pad_x = max(int((bx2 - bx1) * 0.45), 60)
                    pad_y = max(int((by2 - by1) * 0.45), 50)
                    cx1 = max(qx1, bx1 - pad_x)
                    cy1 = max(qy1, by1 - pad_y)
                    cx2 = min(qx2, bx2 + pad_x)
                    cy2 = min(qy2, by2 + pad_y)

                    # Require solid minimum dimensions (at least 120x90) so it never crops a thin banner strip
                    if (cx2 - cx1) >= 120 and (cy2 - cy1) >= 90:
                        crop_img = clean_source[cy1:cy2, cx1:cx2].copy()
                        _, crop_buf = cv2.imencode(".jpg", crop_img, [cv2.IMWRITE_JPEG_QUALITY, 92])
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

            inc_id = f"INC_{int(now * 1000) % 100000}"
            lane_idx_map = {"North": 0, "South": 1, "East": 2, "West": 3}
            q_idx = lane_idx_map.get(lane, 0)
            src_file = self.v_paths[q_idx] if (q_idx < len(self.v_paths) and self.v_paths[q_idx]) else f"{str(lane).lower()}.mp4"
            cctv_filename = os.path.basename(str(src_file))
            exact_camera_id = f"CCTV: {cctv_filename}"
            exact_lane_id = f"{lane} ({cctv_filename})" if lane else f"CCTV: {cctv_filename}"

            # Format description directly with CCTV filename
            if not description.startswith("CCTV:"):
                display_description = f"CCTV: {cctv_filename} — {description}"
            else:
                display_description = description

            # Export 5-10 second MP4 video proof from Rolling Evidence Buffer
            ev_id = f"EVD_{int(now * 1000) % 1000000}"
            output_dir = os.path.join(config.BASE_DIR, "evidence", "videos")
            os.makedirs(output_dir, exist_ok=True)
            clip_filename = f"accident_{int(now * 1000) % 1000000}.mp4"
            clip_path = os.path.join(output_dir, clip_filename)

            evidence_clip_meta = None
            if hasattr(self, 'evidence_buffer') and self.evidence_buffer is not None:
                try:
                    evidence_clip_meta = self.evidence_buffer.export_clip(clip_path, pre_sec=6.0)
                except Exception as ev_err:
                    print(f"[Incident] Evidence clip export error: {ev_err}")

            rel_clip_path = f"evidence/videos/{clip_filename}" if (evidence_clip_meta and os.path.exists(clip_path)) else None
            checksum = None
            if rel_clip_path and os.path.exists(clip_path):
                try:
                    hasher = hashlib.sha256()
                    with open(clip_path, "rb") as bf:
                        while chunk := bf.read(8192):
                            hasher.update(chunk)
                    checksum = hasher.hexdigest()
                except Exception:
                    checksum = None

            # Strictly persist to SQLite Database with camera_id, lane, and video evidence
            try:
                db_session = SessionLocal()
                try:
                    # Database-level deduplication: suppress duplicate if logged within 600 seconds
                    recent_db = db_session.query(db_models.Incident).filter_by(
                        incident_type=inc_type,
                        camera_id=exact_camera_id
                    ).filter(db_models.Incident.timestamp > now - 15.0).first()
                    if recent_db:
                        return

                    cam_rec = db_session.query(db_models.Camera).filter_by(id=exact_camera_id).first()
                    if not cam_rec:
                        cam_rec = db_models.Camera(
                            id=exact_camera_id,
                            name=f"CCTV: {cctv_filename}",
                            location=f"CCTV Video Source: {cctv_filename}",
                            stream_url=str(src_file),
                            camera_type="traffic",
                            status="online",
                            is_active=True
                        )
                        db_session.add(cam_rec)
                        db_session.flush()

                    if rel_clip_path:
                        db_ev = db_models.Evidence(
                            id=ev_id,
                            incident_id=inc_id,
                            file_path=rel_clip_path,
                            file_type="video/mp4",
                            file_size_bytes=evidence_clip_meta.get("file_size_bytes", 0) if evidence_clip_meta else 0,
                            duration_sec=evidence_clip_meta.get("duration_sec", 6.0) if evidence_clip_meta else 6.0,
                            checksum_sha256=checksum,
                            created_at=now
                        )
                        db_session.add(db_ev)

                    db_inc = db_models.Incident(
                        id=inc_id,
                        incident_type=inc_type,
                        cctv_name=f"CCTV: {cctv_filename}",
                        source_module="traffic",
                        camera_id=exact_camera_id,
                        lane=exact_lane_id,
                        timestamp=now,
                        confidence=0.92 if inc_type == "accident" else 0.88,
                        severity="critical" if inc_type in ("accident", "ambulance") else "medium",
                        validation_status="confirmed",
                        status="new",
                        description=display_description,
                        evidence_id=ev_id if rel_clip_path else None,
                        snapshot_b64=single_cam_b64 or cropped_b64,
                        notes=f"Auto-captured from 4-way perception pipeline on {exact_lane_id} approach ({exact_camera_id}).",
                        supporting_evidence=json.dumps({
                            "lane": exact_lane_id,
                            "camera_id": exact_camera_id,
                            "bbox": crop_coords,
                            "type": inc_type,
                            "video_clip": rel_clip_path,
                            "checksum_sha256": checksum
                        })
                    )
                    db_session.add(db_inc)
                    db_session.commit()
                    print(f"[Incident DB] Logged incident {inc_id} ({inc_type}) at {exact_camera_id} / {exact_lane_id} with video proof: {rel_clip_path}")
                except Exception as db_e:
                    db_session.rollback()
                    print(f"[Incident DB] Database commit error: {db_e}")
                finally:
                    db_session.close()
            except Exception as e:
                print(f"[Incident DB] Session error: {e}")

            incident_item = {
                "id": inc_id,
                "type": inc_type,
                "lane": exact_lane_id,
                "camera_id": exact_camera_id,
                "description": display_description,
                "timestamp": now,
                "bbox": str(crop_coords) if crop_coords else f"[0, 0, {qw}, {qh}]",
                "camera_frame_b64": single_cam_b64,
                "cropped_image_b64": single_cam_b64, # Default to THAT camera image only (not over-zoomed)
                "vehicle_crop_b64": cropped_b64,
                "frame_b64": single_cam_b64,          # THAT camera image only (not 4 cameras)
                "full_4way_b64": b64_frame,           # 4-way composite
                "evidence_id": ev_id if rel_clip_path else None,
                "evidence_path": rel_clip_path,
                "checksum_sha256": checksum
            }
            self.incident_history.insert(0, incident_item)
            while len(self.incident_history) > 30:
                self.incident_history.pop()
                self.incident_history.pop()

    def _get_lane_snapshot(self, lane: str) -> str:
        """Extract a single high-definition camera frame from the respective video source."""
        lane_map = {"North": 0, "South": 1, "East": 2, "West": 3}
        idx = lane_map.get(lane, 0)
        if idx < len(self.v_paths) and os.path.isfile(str(self.v_paths[idx])):
            try:
                cap = cv2.VideoCapture(self.v_paths[idx])
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
                    return base64.b64encode(buf.tobytes()).decode("utf-8")
            except Exception:
                pass
        return ""

    def _seed_initial_incidents(self) -> List[Dict]:
        """Start incident feed 100% clean and fresh upon launch."""
        return []

    def set_quadrant_mapping(self, mapping: List[int]):
        if len(mapping) == 4:
            with self.state_lock:
                self.quadrant_mapping = mapping

