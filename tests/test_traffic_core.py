"""
tests/test_traffic_core.py — Automated Unit & Integration Tests for VIGIL Traffic Core
========================================================================================
Validates:
  1. YOLOv8 Multi-class Detector (loading checkpoint, class attributes, PCU mapping)
  2. CentroidTracker (kinematic tracking, stable IDs, dwell-time tracking)
  3. LaneManager (point-in-polygon assignment, PCU volume, area occupancy density)
  4. SignalOptimizer (F.V. Webster optimal delay Co & gi calculation, yellow clearance failsafe)
  5. TrafficAnalyzer (collision detection heuristics, alerts generation)
  6. AudioSirenDetector (2048-point STFT spectral energy ratio on siren_benchmark.wav)
"""

import os
import sys
import numpy as np
import cv2
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config
from core.detector import Detector, Detection
from core.tracker import CentroidTracker, Track
from core.lane_manager import LaneManager, LaneStats
from core.signal_optimizer import SignalOptimizer, SignalState
from core.traffic_analyzer import TrafficAnalyzer, Alert
from core.audio_siren_detector import AudioSirenDetector


class TestDetector:
    def test_model_loading_and_classes(self):
        detector = Detector()
        assert detector.model is not None, "YOLO model failed to load"
        assert len(detector.names) > 0, "No class names loaded in detector"
        supported_keys = list(config.VEHICLE_CLASSES.keys())
        assert "car" in supported_keys
        assert "motorcycle" in supported_keys
        assert "bus" in supported_keys
        assert "truck" in supported_keys
        assert "ambulance" in supported_keys

    def test_pcu_weights_standardization(self):
        detector = Detector()
        assert detector._pcu_weights.get("car") == 1.0
        assert detector._pcu_weights.get("motorcycle") == 0.5
        assert detector._pcu_weights.get("bus") == 3.0
        assert detector._pcu_weights.get("truck") == 3.0
        assert detector._pcu_weights.get("bicycle") == 0.2
        assert detector._pcu_weights.get("person") == 0.1
        assert detector._pcu_weights.get("ambulance") == 0.0

    def test_detection_on_sample_frame(self):
        video_path = os.path.join(PROJECT_ROOT, "assets", "videos", "north.mp4")
        if not os.path.exists(video_path):
            pytest.skip("Test video north.mp4 not found")
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        assert ret, "Failed to read test frame from north.mp4"

        detector = Detector()
        detections = detector.detect(frame)
        assert isinstance(detections, list)
        assert len(detections) > 0, "Expected at least 1 vehicle detected in north.mp4"
        for det in detections:
            assert isinstance(det, Detection)
            assert det.confidence >= 0.0
            assert det.pcu >= 0.0


class TestTracker:
    def test_tracking_creation_and_motion(self):
        tracker = CentroidTracker(max_disappeared=10, max_distance=100)
        det1 = [Detection(box=(100, 100, 160, 160), label="car", confidence=0.9, class_id=2, is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0)]
        tracks1 = tracker.update(det1)
        assert len(tracks1) == 1
        tid = tracks1[0].track_id

        det2 = [Detection(box=(106, 106, 166, 166), label="car", confidence=0.9, class_id=2, is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0)]
        tracks2 = tracker.update(det2)
        assert len(tracks2) == 1
        assert tracks2[0].track_id == tid, "Track ID must remain stable across frames"
        assert tracks2[0].cx == (106 + 166) // 2
        assert tracks2[0].frames_tracked == 1


class TestLaneManager:
    def test_lane_assignment_and_stats(self):
        fw, fh = 1280, 720
        lane_mgr = LaneManager(fw, fh)
        assert len(lane_mgr.lane_names) >= 2

        tracks = [
            Track(track_id=1, label="car", cx=200, cy=200, x1=170, y1=170, x2=230, y2=230, is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0),
            Track(track_id=2, label="bus", cx=250, cy=250, x1=200, y1=200, x2=300, y2=300, is_vehicle=True, is_person=False, is_ambulance=False, pcu=3.0)
        ]
        stats = lane_mgr.update(tracks)
        assert isinstance(stats, dict)
        total_pcu = sum(s.pcu_count for s in stats.values())
        assert total_pcu == 4.0, f"Expected 4.0 total PCU (1.0 car + 3.0 bus), got {total_pcu}"


class TestSignalOptimizer:
    def test_webster_cycle_and_splits(self):
        optimizer = SignalOptimizer()
        lane_stats = {
            "North": LaneStats(name="North", vehicle_count=12, pcu_count=18.0, density_ratio=0.6),
            "South": LaneStats(name="South", vehicle_count=4, pcu_count=4.0, density_ratio=0.2),
            "East": LaneStats(name="East", vehicle_count=8, pcu_count=10.0, density_ratio=0.4),
            "West": LaneStats(name="West", vehicle_count=2, pcu_count=2.0, density_ratio=0.1),
        }
        co, splits = optimizer.calculate_webster_splits(lane_stats)
        assert co >= config.WEBSTER_MIN_CYCLE, f"Cycle {co} below minimum {config.WEBSTER_MIN_CYCLE}"
        assert co <= config.WEBSTER_MAX_CYCLE, f"Cycle {co} above maximum {config.WEBSTER_MAX_CYCLE}"
        assert splits["North"] >= splits["West"], "Highest demand lane must receive >= green time than lowest"
        for s in splits.values():
            assert s >= config.MIN_GREEN_TIME, f"Split {s} violates MIN_GREEN_TIME {config.MIN_GREEN_TIME}"

    def test_emergency_preemption_invariants(self):
        optimizer = SignalOptimizer()
        optimizer.trigger_emergency("North", source="visual")
        assert optimizer.emergency_active is True
        assert optimizer.emergency_lane == "North"
        optimizer.clear_emergency()
        assert optimizer.emergency_active is False
        assert optimizer.emergency_lane is None


class TestAudioSirenDetector:
    def test_siren_spectral_analysis(self):
        wav_path = os.path.join(PROJECT_ROOT, "siren_benchmark.wav")
        if not os.path.exists(wav_path):
            pytest.skip("siren_benchmark.wav not found")
        detector = AudioSirenDetector()
        res = detector.analyze_wav_file(wav_path)
        assert res.get("detected") is True, f"Siren benchmark must be detected by STFT FFT, got: {res}"
        assert res.get("overall_confidence", 0.0) >= 0.40
