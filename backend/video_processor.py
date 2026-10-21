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
import hashlib
from typing import Callable, Optional, Dict, List, Tuple

# Path resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from core.detector   import Detector
from core.tracker    import CentroidTracker
from core.lane_manager  import LaneManager
from core.traffic_analyzer import TrafficAnalyzer
from core.signal_optimizer import SignalOptimizer
from core.violence_detector import RollingEvidenceBuffer
from backend.database import SessionLocal
import backend.models.db_models as db_models


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
        self.is_paused = False
        self.evidence_buffer = RollingEvidenceBuffer(max_buffer_sec=12.0, target_fps=config.TARGET_FPS)
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

    def pause(self):
        """Immediately halt video processing and freeze inference frames."""
        self.is_paused = True
        print("[Single VideoProcessor] Processing PAUSED")

    def resume(self):
        """Resume video processing and inference."""
        self.is_paused = False
        print("[Single VideoProcessor] Processing RESUMED")

    def toggle_pause(self) -> bool:
        """Toggle pause state."""
        if self.is_paused:
            self.resume()
        else:
            self.pause()
        return self.is_paused
    
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
            if self.is_paused:
                time.sleep(0.04)
                continue

            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))

            if hasattr(self, 'evidence_buffer') and self.evidence_buffer is not None:
                self.evidence_buffer.add_frame(frame, start_time)
            
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
                    em_source = getattr(self.optimizer, 'emergency_source', 'visual')
                    em_lane = getattr(self.optimizer, 'emergency_lane', 'Approach') or 'Approach'
                    self.record_incident(
                        inc_type="ambulance",
                        description=f"Class-1 Emergency Corridor ({em_source.upper()}) active on {em_lane}.",
                        frame=annotated,
                        lane=em_lane
                    )
                    self._last_incident_time = now

                # 2. Physical Emergency Vehicle Tracks
                amb_tracks = [t for t in current_tracks if getattr(t, 'is_ambulance', False) and getattr(t, 'label', '') != 'bus']
                if amb_tracks:
                    lead_amb = amb_tracks[0]
                    amb_box = (lead_amb.x1, lead_amb.y1, lead_amb.x2, lead_amb.y2)
                    self.record_incident(
                        inc_type="ambulance",
                        description=f"Class-1 Emergency Priority: Ambulance detected in traffic flow.",
                        frame=annotated,
                        lane="Single Feed",
                        bbox=amb_box
                    )
                    self._last_incident_time = now

                # 3. Latest alerts from analyzer
                for a in self.latest_alerts:
                    a_type = a.get("type", "").lower()
                    a_msg = a.get("message", "")
                    a_lane = a.get("lane") or "Single Feed"
                    a_box = a.get("bbox")
                    
                    if "accident" in a_type or "accident" in a_msg.lower() or "collision" in a_msg.lower():
                        self.record_incident("accident", a_msg, annotated, a_lane, bbox=a_box)
                        self._last_incident_time = now
                        break
                    elif "ambulance" in a_type or "ambulance" in a_msg.lower():
                        self.record_incident("ambulance", a_msg, annotated, a_lane, bbox=a_box)
                        self._last_incident_time = now
                        break
                    elif "pedestrian" in a_type or "crowd" in a_type or "pedestrian" in a_msg.lower():
                        self.record_incident("crowd", a_msg, annotated, a_lane, bbox=a_box)
                        self._last_incident_time = now
                        break
                    elif "stall" in a_type or "parking" in a_type or "immobilized" in a_msg.lower():
                        self.record_incident("parking", a_msg, annotated, a_lane, bbox=a_box)
                        self._last_incident_time = now
                        break

                # 4. Check for stalls (> 15s)
                stall_limit = getattr(config, 'ILLEGAL_PARKING_TIME', 15.0)
                for lane, stats in current_lane_stats.items():
                    if getattr(stats, 'max_wait_time', 0.0) >= stall_limit:
                        stalled_box = None
                        for t in current_tracks:
                            if t.is_stopped and t.wait_time >= stall_limit:
                                stalled_box = (t.x1, t.y1, t.x2, t.y2)
                                break
                        self.record_incident(
                            "parking",
                            f"Vehicle queue delay / stall in {lane} ({stats.max_wait_time:.0f}s).",
                            annotated,
                            lane,
                            bbox=stalled_box
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
            if self.is_paused:
                time.sleep(0.04)
                continue
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
            
            _ = self.analyzer.update(
                tracks, lane_stats, list(detections),
                signals=self.optimizer.signals,
                current_phase=self.optimizer.current_lane,
                optimizer=self.optimizer,
                frame=frame_to_process
            )
            
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

    def record_incident(self, inc_type: str, description: str, frame: Optional[np.ndarray] = None, lane: Optional[str] = None, bbox: Optional[Tuple[int, int, int, int]] = None):
        """Thread-safe recording of an incident with base64 snapshot, video evidence buffer export, and persistent SQLite DB commit."""
        now = time.time()
        cctv_filename = os.path.basename(str(self.video_path)) if self.video_path else "single_cam.mp4"
        exact_camera_id = f"CCTV: {cctv_filename}"
        exact_lane_id = f"{lane} ({cctv_filename})" if lane else exact_camera_id
        display_description = f"CCTV: {cctv_filename} — {description}" if not description.startswith("CCTV:") else description

        dedup_key = f"{inc_type}:{exact_camera_id}"
        with self.state_lock:
            last_logged = getattr(self, '_active_logged_events', {}).get(dedup_key, 0.0)
            if now - last_logged < 600.0:  # 10 minute cooldown prevents repeated flooding
                return
            if not hasattr(self, '_active_logged_events'):
                self._active_logged_events = {}
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
                    
                    badge = f"INCIDENT: {inc_type.upper()} | {cctv_filename}"
                    if lane:
                        badge += f" | {lane.upper()}"
                    badge += f" | {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}"
                    
                    cv2.putText(snap, badge, (16, 26),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(snap, "[FORENSIC EVIDENCE CAPTURE]", (fw - 270, 26),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, banner_color, 1, cv2.LINE_AA)
                    
                    _, buf = cv2.imencode(".jpg", snap, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    b64_frame = base64.b64encode(buf.tobytes()).decode("utf-8")

                    # Accurate ROI contextual crop if bbox provided
                    if bbox is not None and len(bbox) == 4:
                        bx1, by1, bx2, by2 = map(int, bbox)
                        pad_x = max(int((bx2 - bx1) * 0.4), 40)
                        pad_y = max(int((by2 - by1) * 0.4), 30)
                        cx1 = max(0, bx1 - pad_x)
                        cy1 = max(0, by1 - pad_y)
                        cx2 = min(fw, bx2 + pad_x)
                        cy2 = min(fh, by2 + pad_y)
                        if (cx2 - cx1) >= 40 and (cy2 - cy1) >= 30:
                            crop_img = target_frame[cy1:cy2, cx1:cx2].copy()
                            _, crop_buf = cv2.imencode(".jpg", crop_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                            cropped_b64 = base64.b64encode(crop_buf.tobytes()).decode("utf-8")
                            crop_coords = [cx1, cy1, cx2 - cx1, cy2 - cy1]
                except Exception as e:
                    print(f"[Single Cam Incident] Snapshot capture error: {e}")

            inc_id = f"INC_{int(now * 1000) % 100000}"
            ev_id = f"EVD_{int(now * 1000) % 1000000}"

            # Export 5-10 second MP4 video proof from Rolling Evidence Buffer
            output_dir = os.path.join(config.BASE_DIR, "evidence", "videos")
            os.makedirs(output_dir, exist_ok=True)
            clip_filename = f"single_{int(now * 1000) % 1000000}.mp4"
            clip_path = os.path.join(output_dir, clip_filename)

            evidence_clip_meta = None
            if hasattr(self, 'evidence_buffer') and self.evidence_buffer is not None:
                try:
                    evidence_clip_meta = self.evidence_buffer.export_clip(clip_path, pre_sec=6.0)
                except Exception as ev_err:
                    print(f"[Single Cam Incident] Evidence clip export error: {ev_err}")

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

            # Persist to SQLite Database
            try:
                db_session = SessionLocal()
                try:
                    # Database-level deduplication: suppress duplicate if logged within 600 seconds
                    recent_db = db_session.query(db_models.Incident).filter_by(
                        incident_type=inc_type,
                        camera_id=exact_camera_id
                    ).filter(db_models.Incident.timestamp > now - 600.0).first()
                    if recent_db:
                        return

                    cam_rec = db_session.query(db_models.Camera).filter_by(id=exact_camera_id).first()
                    if not cam_rec:
                        cam_rec = db_models.Camera(
                            id=exact_camera_id,
                            name=f"CCTV: {cctv_filename}",
                            location=f"Single Camera Source: {cctv_filename}",
                            stream_url=str(self.video_path),
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
                        snapshot_b64=cropped_b64 or b64_frame,
                        notes=f"Auto-captured from single-camera perception pipeline ({exact_camera_id}).",
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
                    print(f"[Single Cam DB] Logged incident {inc_id} ({inc_type}) at {exact_camera_id} with video proof: {rel_clip_path}")
                except Exception as db_e:
                    db_session.rollback()
                    print(f"[Single Cam DB] Database commit error: {db_e}")
                finally:
                    db_session.close()
            except Exception as e:
                print(f"[Single Cam DB] Session error: {e}")

            incident_item = {
                "id": inc_id,
                "type": inc_type,
                "lane": exact_lane_id,
                "camera_id": exact_camera_id,
                "description": display_description,
                "timestamp": now,
                "frame_b64": b64_frame,
                "snapshot_b64": cropped_b64 or b64_frame,
                "evidence_id": ev_id if rel_clip_path else None,
                "evidence_path": rel_clip_path,
                "checksum_sha256": checksum
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

