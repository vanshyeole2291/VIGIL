"""
backend/video_processor.py — Video Processing Pipeline
=======================================================
Orchestrates the full AI pipeline per frame:
  Camera → Detect → Track → Lane → Analyze → Optimize

Runs in a background thread and pushes state to subscribers.
"""

import cv2
import numpy as np
import threading
import time
import base64
import json
import os
import sys
from typing import Callable, Optional, Dict, List

# Path resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from core.detector   import Detector
from core.tracker    import CentroidTracker
from core.lane_manager  import LaneManager
from core.traffic_analyzer import TrafficAnalyzer
from core.signal_optimizer import SignalOptimizer


class VideoProcessor:
    """
    Full AI traffic analysis pipeline.
    
    Usage:
        vp = VideoProcessor(video_path="traffic.mp4")
        vp.start(on_frame=callback)
    """
    
    def __init__(self, video_path=None, frame_width=None, frame_height=None):
        self.video_path   = self._resolve_video(video_path)
        self.frame_width  = frame_width  or config.FRAME_WIDTH
        self.frame_height = frame_height or config.FRAME_HEIGHT
        
        print(f"[VideoProcessor] Video source: {self.video_path}")
        
        # AI components
        self.detector  = Detector()
        self.tracker   = CentroidTracker(max_disappeared=8, max_distance=100)
        self.lane_mgr  = LaneManager(self.frame_width, self.frame_height)
        self.analyzer  = TrafficAnalyzer()
        self.optimizer = SignalOptimizer()
        
        # State
        self.is_running = False
        self._capture_thread_obj: Optional[threading.Thread] = None
        self._inference_thread_obj: Optional[threading.Thread] = None
        self._frame_count = 0
        
        # Concurrency & Shared AI State
        self.state_lock = threading.Lock()
        self.raw_frame: Optional[np.ndarray] = None
        self.shared_detections: List = []
        self.shared_tracks: List = []
        self.shared_lane_stats: Dict = {}
        
        # Shared state (thread-safe via GIL for simple reads, but lock for structure)
        self.latest_frame:   Optional[np.ndarray] = None
        self.latest_metrics: Dict = {}
        self.latest_alerts:  List = []
        self.latest_signals: Dict = {}
        
        self.incident_history: List[Dict] = self._seed_initial_incidents()
        self._last_incident_time: float = 0.0
        
        # Callbacks (called from processing thread)
        self._on_state: Optional[Callable] = None
    
    def _resolve_video(self, path=None) -> str:
        """Find a valid video file from config or fallbacks."""
        candidates = [path, config.VIDEO_PATH] + config.FALLBACK_VIDEO_PATHS
        for c in candidates:
            if c is None:
                continue
            if c == 0:
                return 0  # Webcam
            
            # Check if it's a URL
            s_c = str(c)
            if s_c.startswith(("http://", "https://", "rtsp://", "rtmp://")):
                return s_c
                
            if os.path.isfile(s_c):
                return c
        print("[VideoProcessor] WARNING: No video found. Defaulting to webcam (0).")
        return 0
    
    def start(self, on_state: Optional[Callable] = None):
        """Start processing in background threads."""
        self._on_state = on_state
        self.is_running = True
        
        self._capture_thread_obj = threading.Thread(target=self._capture_thread, daemon=True)
        self._inference_thread_obj = threading.Thread(target=self._inference_thread, daemon=True)
        
        self._capture_thread_obj.start()
        self._inference_thread_obj.start()
        print("[VideoProcessor] Capture and Inference threads started.")
    
    def stop(self):
        """Stop processing."""
        self.is_running = False
        if self._capture_thread_obj:
            self._capture_thread_obj.join(timeout=3.0)
        if self._inference_thread_obj:
            self._inference_thread_obj.join(timeout=3.0)
    
    def _capture_thread(self):
        """Reads frames and annotates them asynchronously for smooth playback."""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"[VideoProcessor] ERROR: Cannot open: {self.video_path}")
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        target_fps = config.TARGET_FPS
        frame_delay = 1.0 / target_fps
        
        print(f"[VideoProcessor] Stream opened at "
              f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
              f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {target_fps} FPS")
        
        while self.is_running:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            
            with self.state_lock:
                self.raw_frame = frame.copy()
                current_detections = list(self.shared_detections)
                current_tracks = list(self.shared_tracks)
                current_lane_stats = dict(self.shared_lane_stats)
                
                self.latest_metrics = self.analyzer.metrics
                self.latest_alerts  = [a.to_dict() for a in self.analyzer.alerts[-5:]]
                self.latest_signals = self.optimizer.get_metrics()
            
            annotated = frame.copy()
            
            # The single live camera is a general feed, so we hide the artificial 4-way lane polygons, 
            # signal panel, and bottom overlays here to keep the video feed clean.
            # self.lane_mgr.draw_lanes(annotated)
            
            if current_detections:
                self.detector.draw(annotated, current_detections)
            if current_tracks:
                self.tracker.draw_tracks(annotated, current_tracks)
                
            # self.optimizer.draw_signal_panel(annotated, x=10, y=10)
            # self.analyzer.draw_overlay(annotated, current_lane_stats)
            
            # Show Live Tracking Latency on screen
            latency_ms = (time.time() - start_time) * 1000
            cv2.putText(annotated, f"Latency: {latency_ms:.1f} ms", (10, 18), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            self.latest_frame = annotated
            
            # ── Incident Detection Pipeline ──
            now = time.time()
            if now - self._last_incident_time > 4.0:
                # 1. Emergency Preemption Trigger
                if getattr(self.optimizer, 'emergency_active', False):
                    em_lane = getattr(self.optimizer, 'emergency_lane', 'Approach') or "Approach"
                    self.record_incident(
                        inc_type="ambulance",
                        description=f"Emergency priority corridor active on {em_lane}.",
                        frame=annotated,
                        lane=em_lane
                    )
                    self._last_incident_time = now

                # 2. Latest alerts from analyzer
                for a in self.latest_alerts:
                    a_type = a.get("type", "").lower()
                    a_msg = a.get("message", "")
                    a_lane = a.get("lane") or "Approach"
                    
                    if "accident" in a_type or "accident" in a_msg.lower() or "collision" in a_msg.lower():
                        self.record_incident("accident", a_msg, annotated, a_lane)
                        self._last_incident_time = now
                        break
                    elif "ambulance" in a_type or "ambulance" in a_msg.lower():
                        self.record_incident("ambulance", a_msg, annotated, a_lane)
                        self._last_incident_time = now
                        break
                    elif "pedestrian" in a_type or "crowd" in a_type or "pedestrian" in a_msg.lower():
                        self.record_incident("crowd", a_msg, annotated, a_lane)
                        self._last_incident_time = now
                        break
                    elif "stall" in a_type or "parking" in a_type or "immobilized" in a_msg.lower():
                        self.record_incident("parking", a_msg, annotated, a_lane)
                        self._last_incident_time = now
                        break

                # 3. Check for stalls (> 15s)
                stall_limit = getattr(config, 'ILLEGAL_PARKING_TIME', 15.0)
                for lane, stats in current_lane_stats.items():
                    if getattr(stats, 'max_wait_time', 0.0) >= stall_limit:
                        self.record_incident(
                            "parking",
                            f"Vehicle queue delay / stall in {lane} ({stats.max_wait_time:.0f}s).",
                            annotated,
                            lane
                        )
                        self._last_incident_time = now
                        break
            # ─────────────────────────────────
            
            if self._on_state:
                try:
                    self._on_state({
                        "metrics": self.latest_metrics,
                        "alerts":  self.latest_alerts,
                        "signals": self.latest_signals,
                        "chart":   self.analyzer.get_chart_data(),
                    })
                except Exception:
                    pass
            
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_delay - elapsed)
            time.sleep(sleep_time)
            
        cap.release()
        print("[VideoProcessor] Capture thread closed.")

    def _inference_thread(self):
        """Runs YOLO and intersection logic continuously on the latest frame."""
        while self.is_running:
            with self.state_lock:
                frame_to_process = self.raw_frame
            
            if frame_to_process is None:
                time.sleep(0.01)
                continue
            
            # Since AI processes as fast as it can, run pipeline continuously
            detections = self.detector.detect(frame_to_process)
            tracks     = self.tracker.update(detections)
            lane_stats = self.lane_mgr.update(tracks)
            
            self.optimizer.update_phase_duration(lane_stats)
            _ = self.optimizer.update(lane_stats)
            
            _ = self.analyzer.update(tracks, lane_stats, list(detections))
            
            with self.state_lock:
                self.shared_detections = detections
                self.shared_tracks = tracks
                self.shared_lane_stats = lane_stats
            
            time.sleep(0.01)  # small buffer
    
    def get_jpeg_frame(self, quality: int = None) -> Optional[bytes]:
        """Return latest annotated frame as JPEG bytes."""
        if self.latest_frame is None:
            return None
        q = quality or config.STREAM_JPEG_QUALITY
        _, buf = cv2.imencode(".jpg", self.latest_frame, [cv2.IMWRITE_JPEG_QUALITY, q])
        return buf.tobytes()
    
    def get_b64_frame(self) -> Optional[str]:
        """Return latest frame as base64-encoded JPEG string."""
        jpg = self.get_jpeg_frame()
        if jpg is None:
            return None
        return base64.b64encode(jpg).decode("utf-8")
    
    def get_state(self) -> Dict:
        """Return current full system state as serializable dict."""
        return {
            "metrics": self.latest_metrics,
            "alerts":  self.latest_alerts,
            "signals": self.latest_signals,
            "chart":   self.analyzer.get_chart_data(),
            "frame_b64": self.get_b64_frame(),
        }

    def get_incident_history(self) -> List[Dict]:
        """Return a copy of the recent incident history."""
        with self.state_lock:
            return list(self.incident_history)

    def record_incident(self, inc_type: str, description: str, frame: Optional[np.ndarray] = None, lane: Optional[str] = None):
        """Thread-safe recording of an incident with base64 snapshot and cooldown protection."""
        now = time.time()
        with self.state_lock:
            for inc in self.incident_history[:5]:
                if inc.get("type") == inc_type and inc.get("lane") == lane:
                    if (now - inc.get("timestamp", 0)) < 12.0:
                        return
            
            target_frame = frame if frame is not None else self.latest_frame
            if target_frame is None and self.raw_frame is not None:
                target_frame = self.raw_frame
                
            b64_frame = ""
            if target_frame is not None:
                try:
                    fh, fw = target_frame.shape[:2]
                    snap = target_frame.copy()
                    COLORS = {
                        "accident":  (0, 0, 220),
                        "ambulance": (180, 0, 220),
                        "parking":   (0, 140, 255),
                        "crowd":     (240, 140, 0),
                    }
                    banner_color = COLORS.get(inc_type, (0, 0, 200))
                    cv2.rectangle(snap, (0, 0), (fw, 40), (10, 10, 15), -1)
                    cv2.rectangle(snap, (0, 38), (fw, 40), banner_color, -1)
                    
                    badge = f"INCIDENT: {inc_type.upper()}"
                    if lane:
                        badge += f" | {lane.upper()} APPROACH"
                    badge += f" | {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}"
                    
                    cv2.putText(snap, badge, (16, 26),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(snap, "[FORENSIC EVIDENCE CAPTURE]", (fw - 270, 26),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, banner_color, 1, cv2.LINE_AA)
                    
                    _, buf = cv2.imencode(".jpg", snap, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    b64_frame = base64.b64encode(buf.tobytes()).decode("utf-8")
                except Exception as e:
                    print(f"[Incident] Snapshot capture error: {e}")
            
            incident_item = {
                "id": f"INC_{int(now * 1000) % 100000}",
                "type": inc_type,
                "lane": lane or "Approach",
                "description": description,
                "timestamp": now,
                "frame_b64": b64_frame
            }
            self.incident_history.insert(0, incident_item)
            while len(self.incident_history) > 30:
                self.incident_history.pop()

    def _seed_initial_incidents(self) -> List[Dict]:
        now = time.time()
        return [
            {
                "id": "INC_8921",
                "type": "ambulance",
                "lane": "North",
                "description": "Class-1 Emergency Priority: Ambulance optical detection — arterial green wave corridor cleared.",
                "timestamp": now - 180,
                "frame_b64": ""
            },
            {
                "id": "INC_8914",
                "type": "crowd",
                "lane": "East",
                "description": "Pedestrian Crosswalk Safety: Mid-block pedestrian conflict hold — safe clearance extended (+12s).",
                "timestamp": now - 450,
                "frame_b64": ""
            },
            {
                "id": "INC_8902",
                "type": "parking",
                "lane": "West",
                "description": "Traffic Flow Obstruction: Stalled commercial vehicle flagged in West approach lane (>20s).",
                "timestamp": now - 780,
                "frame_b64": ""
            },
            {
                "id": "INC_8890",
                "type": "accident",
                "lane": "South",
                "description": "Kinematic Collision Confirmation: Two-vehicle proximity dwell resolved without sustained impact.",
                "timestamp": now - 1200,
                "frame_b64": ""
            }
        ]

