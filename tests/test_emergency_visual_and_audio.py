"""
tests/test_emergency_visual_and_audio.py
=========================================
Comprehensive test suite verifying:
1. Visual Detection of Ambulances as primary EVP trigger.
2. Visual Detection of Fire Trucks as primary EVP trigger.
3. Acoustic Siren FFT as strictly a secondary fallback when visual is absent.
4. Visual priority override: Visual detection immediately preempts active acoustic fallback.
5. Invariant: Acoustic siren cannot override or interfere with active visual preemption.
6. Tracking & lifecycle for multi-class emergency vehicles.
"""

import pytest
import time
import numpy as np

from core.detector import Detection, Detector
from core.tracker import Track, CentroidTracker
from core.lane_manager import LaneManager, LaneStats
from core.signal_optimizer import SignalOptimizer, SignalState
import config


class TestEmergencyVisualAndAudio:
    """Test suite for primary visual EVP and secondary acoustic fallback."""
    
    def test_visual_ambulance_detection_and_preemption(self):
        """Visual detection of ambulance immediately triggers preemption with source='visual'."""
        opt = SignalOptimizer()
        lane_stats = {
            "North": LaneStats(name="North", vehicle_count=3, pcu_count=3.5, ambulance_present=True, emergency_present=True),
            "South": LaneStats(name="South", vehicle_count=2, pcu_count=2.0),
            "East":  LaneStats(name="East",  vehicle_count=1, pcu_count=1.0),
            "West":  LaneStats(name="West",  vehicle_count=0, pcu_count=0.0),
        }
        
        # Initial update
        signals = opt.update(lane_stats, has_audio_siren=False)
        assert opt.emergency_active is True
        assert opt.emergency_lane == "North"
        assert opt.emergency_source == "visual"
    
    def test_visual_fire_truck_detection_and_preemption(self):
        """Visual detection of fire truck immediately triggers preemption with source='visual'."""
        opt = SignalOptimizer()
        lane_stats = {
            "North": LaneStats(name="North", vehicle_count=1, pcu_count=1.0),
            "South": LaneStats(name="South", vehicle_count=2, pcu_count=2.0),
            "East":  LaneStats(name="East",  vehicle_count=4, pcu_count=0.0, fire_truck_present=True, emergency_present=True),
            "West":  LaneStats(name="West",  vehicle_count=0, pcu_count=0.0),
        }
        
        signals = opt.update(lane_stats, has_audio_siren=False)
        assert opt.emergency_active is True
        assert opt.emergency_lane == "East"
        assert opt.emergency_source == "visual"

    def test_audio_siren_secondary_fallback_when_visual_absent(self):
        """When no visual emergency vehicle is visible, acoustic siren triggers secondary fallback."""
        opt = SignalOptimizer()
        lane_stats = {
            "North": LaneStats(name="North", vehicle_count=2, pcu_count=2.0),
            "South": LaneStats(name="South", vehicle_count=3, pcu_count=3.0),
            "East":  LaneStats(name="East",  vehicle_count=1, pcu_count=1.0),
            "West":  LaneStats(name="West",  vehicle_count=1, pcu_count=1.0),
        }
        
        # Audio siren active, no visual vehicle
        signals = opt.update(lane_stats, has_audio_siren=True, audio_lane="West")
        assert opt.emergency_active is True
        assert opt.emergency_lane == "West"
        assert opt.emergency_source == "audio"

    def test_visual_priority_overrides_active_audio_fallback(self):
        """If acoustic preemption is running and visual detection occurs, visual immediately overrides."""
        opt = SignalOptimizer()
        
        # 1. Acoustic preemption engaged on East
        lane_stats_empty = {
            "North": LaneStats(name="North"),
            "South": LaneStats(name="South"),
            "East":  LaneStats(name="East"),
            "West":  LaneStats(name="West"),
        }
        opt.update(lane_stats_empty, has_audio_siren=True, audio_lane="East")
        assert opt.emergency_active is True
        assert opt.emergency_source == "audio"
        assert opt.emergency_lane == "East"
        
        # 2. Visual ambulance appears on North
        lane_stats_visual = {
            "North": LaneStats(name="North", ambulance_present=True, emergency_present=True),
            "South": LaneStats(name="South"),
            "East":  LaneStats(name="East"),
            "West":  LaneStats(name="West"),
        }
        opt.update(lane_stats_visual, has_audio_siren=True, audio_lane="East")
        
        # Visual must have taken precedence over audio
        assert opt.emergency_active is True
        assert opt.emergency_source == "visual"
        assert opt.emergency_lane == "North"

    def test_audio_cannot_override_active_visual_preemption(self):
        """When visual preemption is active, acoustic calls are ignored."""
        opt = SignalOptimizer()
        
        # 1. Visual fire truck engaged on South
        lane_stats_visual = {
            "North": LaneStats(name="North"),
            "South": LaneStats(name="South", fire_truck_present=True, emergency_present=True),
            "East":  LaneStats(name="East"),
            "West":  LaneStats(name="West"),
        }
        opt.update(lane_stats_visual, has_audio_siren=False)
        assert opt.emergency_active is True
        assert opt.emergency_source == "visual"
        assert opt.emergency_lane == "South"
        
        # 2. Audio trigger attempts to preempt on West
        opt.trigger_emergency("West", source="audio")
        
        # Invariant maintained: South remains active with visual source
        assert opt.emergency_active is True
        assert opt.emergency_source == "visual"
        assert opt.emergency_lane == "South"

    def test_detector_fire_truck_and_ambulance_attributes(self):
        """Detection instances have correct flags and PCU values for fire trucks & ambulances."""
        amb_det = Detection(
            box=(100, 100, 200, 200),
            label="ambulance",
            confidence=0.92,
            class_id=80,
            is_vehicle=True,
            is_person=False,
            is_ambulance=True,
            pcu=0.0,
            has_emergency_lights=True,
            is_fire_truck=False,
            is_emergency_vehicle=True
        )
        assert amb_det.is_ambulance is True
        assert amb_det.is_emergency_vehicle is True
        assert amb_det.pcu == 0.0

        fire_det = Detection(
            box=(150, 150, 300, 300),
            label="fire_truck",
            confidence=0.88,
            class_id=5,
            is_vehicle=True,
            is_person=False,
            is_ambulance=False,
            pcu=0.0,
            has_emergency_lights=True,
            is_fire_truck=True,
            is_emergency_vehicle=True
        )
        assert fire_det.is_fire_truck is True
        assert fire_det.is_emergency_vehicle is True
        assert fire_det.pcu == 0.0

        d = Detector()
        assert d.has_ambulance([amb_det]) is True
        assert d.has_fire_truck([fire_det]) is True
        assert d.has_emergency_vehicle([amb_det]) is True
        assert d.has_emergency_vehicle([fire_det]) is True

    def test_tracker_emergency_vehicle_attribution(self):
        """CentroidTracker correctly attributes and persists fire truck and emergency flags."""
        tracker = CentroidTracker(max_disappeared=5)
        
        fire_det = Detection(
            box=(200, 200, 320, 320),
            label="fire_truck",
            confidence=0.90,
            class_id=5,
            is_vehicle=True,
            is_person=False,
            is_ambulance=False,
            pcu=0.0,
            has_emergency_lights=True,
            is_fire_truck=True,
            is_emergency_vehicle=True
        )
        
        tracks = tracker.update([fire_det])
        assert len(tracks) == 1
        t = tracks[0]
        assert t.is_fire_truck is True
        assert t.is_emergency_vehicle is True
        assert t.pcu == 0.0
        
        em_tracks = tracker.get_emergency_tracks()
        assert len(em_tracks) == 1
        assert em_tracks[0].track_id == t.track_id
        
        # Test serialization to dict
        t_dict = t.to_dict()
        assert t_dict["is_fire_truck"] is True
        assert t_dict["is_emergency_vehicle"] is True

    def test_traffic_analyzer_visual_emergency_trigger(self):
        """TrafficAnalyzer.update() generates emergency alerts and triggers optimizer EVP on visual track."""
        from core.traffic_analyzer import TrafficAnalyzer
        analyzer = TrafficAnalyzer()
        optimizer = SignalOptimizer()
        
        fire_track = Track(
            track_id=10,
            label="fire_truck",
            cx=200, cy=200,
            x1=150, y1=150, x2=250, y2=250,
            is_vehicle=True,
            is_person=False,
            is_ambulance=False,
            is_fire_truck=True,
            is_emergency_vehicle=True,
            pcu=0.0
        )
        fire_track.lane = "East"
        
        lane_stats = {
            "North": LaneStats(name="North"),
            "South": LaneStats(name="South"),
            "East":  LaneStats(name="East", fire_truck_present=True, emergency_present=True),
            "West":  LaneStats(name="West"),
        }
        
        alerts = analyzer.update(
            tracks=[fire_track],
            lane_stats=lane_stats,
            detections=[],
            signals=optimizer.signals,
            current_phase=optimizer.current_lane,
            optimizer=optimizer
        )
        
        # Verify alert creation
        assert any(a.alert_type == "fire_truck" and a.lane == "East" for a in alerts)
        # Verify immediate optimizer preemption
        assert optimizer.emergency_active is True
        assert optimizer.emergency_lane == "East"
        assert optimizer.emergency_source == "visual"
        
        # Verify metrics
        metrics = analyzer.get_metrics([fire_track], lane_stats)
        assert metrics["fire_truck_active"] is True
        assert metrics["emergency_active"] is True
