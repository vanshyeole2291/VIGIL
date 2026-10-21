"""
tests/test_accident_detector.py — Test Suite for VIGIL Multi-Tier Accident Detection
=====================================================================================
Verifies:
1. Missing visual weights cleanly reports ACCIDENT_MODEL_NOT_CONFIGURED (no fake AI scores).
2. Multi-tier kinematic collision confirmation (overlap + sudden deceleration + stationary dwell).
3. Red-light queuing exclusion invariant (dense stopline queues do not trigger false alarms).
4. Per-lane debouncing cooldown prevents alert floods.
5. Test/demo accident event generation with explicit simulation flags.
6. Incident resolution workflow.
"""

import pytest
import time
from core.tracker import Track
from core.lane_manager import LaneStats
from core.signal_optimizer import SignalState, LaneSignal
from core.accident_detector import AccidentDetector, AccidentState


class TestAccidentDetector:
    
    def test_missing_weights_reports_unconfigured(self):
        """When no custom accident weights exist, reports ACCIDENT_MODEL_NOT_CONFIGURED."""
        detector = AccidentDetector(visual_model_path="models/non_existent_accident_model.pt")
        status = detector.get_status()
        assert status["visual_model_status"] == "ACCIDENT_MODEL_NOT_CONFIGURED"
        assert status["visual_model_configured"] is False
        assert status["kinematic_rules_active"] is True

    def test_kinematic_collision_confirmation_lifecycle(self):
        """Suspected collision transitions to confirmed by configured rules after stationary dwell."""
        detector = AccidentDetector(visual_model_path="models/non_existent_accident_model.pt")
        
        # Two vehicles with severe overlap and sudden deceleration
        t1 = Track(
            track_id=1, label="car", cx=200, cy=200,
            x1=160, y1=160, x2=240, y2=240,
            is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0
        )
        t1.lane = "East"
        t1.had_sudden_decel = True
        t1.is_stopped = True
        
        t2 = Track(
            track_id=2, label="truck", cx=210, cy=210,
            x1=170, y1=170, x2=250, y2=250,
            is_vehicle=True, is_person=False, is_ambulance=False, pcu=3.0
        )
        t2.lane = "East"
        t2.is_stopped = True
        
        # Tick 1: Candidates created as SUSPECTED
        events_t0 = detector.evaluate(tracks=[t1, t2])
        # Still awaiting dwell confirmation threshold (confirm_time = 2.0s)
        assert len(events_t0) == 0
        assert len(detector._pending_candidates) == 1
        
        # Simulate elapsed dwell time > 2.0s
        pair_key = (1, 2)
        detector._pending_candidates[pair_key]["start_time"] -= 2.5
        
        # Tick 2: Dwell satisfied -> CONFIRMED
        events_t1 = detector.evaluate(tracks=[t1, t2])
        assert len(events_t1) == 1
        inc = events_t1[0]
        assert inc.state == AccidentState.CONFIRMED_RULES
        assert inc.lane == "East"
        assert inc.had_sudden_decel is True
        assert inc.max_iou > 0.20
        assert inc.is_simulation is False

    def test_red_light_queue_exclusion_prevents_false_alarm(self):
        """Vehicles stopping bumper-to-bumper at red light without decel shockwave are not flagged."""
        detector = AccidentDetector(visual_model_path="models/non_existent_accident_model.pt")
        
        t1 = Track(
            track_id=10, label="car", cx=130, cy=130,
            x1=100, y1=100, x2=160, y2=160,
            is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0
        )
        t1.lane = "North"
        t1.is_stopped = True
        t1.had_sudden_decel = False
        
        t2 = Track(
            track_id=11, label="car", cx=130, cy=170,
            x1=100, y1=140, x2=160, y2=200,
            is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0
        )
        t2.lane = "North"
        t2.is_stopped = True
        t2.had_sudden_decel = False
        
        signals = {
            "North": LaneSignal(name="North", state=SignalState.RED, time_left=15.0)
        }
        
        # Tick 1
        _ = detector.evaluate(tracks=[t1, t2], signals=signals, current_phase="South")
        
        # Fast-forward dwell time beyond 2.5s
        for cand in detector._pending_candidates.values():
            cand["start_time"] -= 3.0
            
        # Tick 2: Should be excluded and pruned due to red light
        events = detector.evaluate(tracks=[t1, t2], signals=signals, current_phase="South")
        assert len(events) == 0
        assert len(detector._pending_candidates) == 0

    def test_debouncing_cooldown_suppresses_duplicate_alerts(self):
        """Per-lane debouncing cooldown prevents generating repeated alerts for the same scene."""
        detector = AccidentDetector(visual_model_path="models/non_existent_accident_model.pt")
        
        t1 = Track(
            track_id=20, label="car", cx=300, cy=300,
            x1=260, y1=260, x2=340, y2=340,
            is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0
        )
        t1.lane = "West"
        t1.is_stopped = True
        t1.had_sudden_decel = True
        
        t2 = Track(
            track_id=21, label="motorcycle", cx=310, cy=310,
            x1=270, y1=270, x2=350, y2=350,
            is_vehicle=True, is_person=False, is_ambulance=False, pcu=0.5
        )
        t2.lane = "West"
        t2.is_stopped = True
        
        detector.evaluate(tracks=[t1, t2])
        detector._pending_candidates[(20, 21)]["start_time"] -= 2.5
        
        # First confirmation
        first_events = detector.evaluate(tracks=[t1, t2])
        assert len(first_events) == 1
        
        # New overlapping pair arrives in the same lane immediately (within 15s cooldown)
        t3 = Track(
            track_id=22, label="car", cx=305, cy=305,
            x1=265, y1=265, x2=345, y2=345,
            is_vehicle=True, is_person=False, is_ambulance=False, pcu=1.0
        )
        t3.lane = "West"
        t3.is_stopped = True
        t3.had_sudden_decel = True
        
        detector.evaluate(tracks=[t1, t3])
        if (20, 22) in detector._pending_candidates:
            detector._pending_candidates[(20, 22)]["start_time"] -= 2.5
        second_events = detector.evaluate(tracks=[t1, t3])
        
        # Suppressed by cooldown
        assert len(second_events) == 0

    def test_test_demo_accident_event(self):
        """Test/demo accident event is tagged with is_simulation=True and TEST_EVENT state."""
        detector = AccidentDetector(visual_model_path="models/non_existent_accident_model.pt")
        demo = detector.trigger_test_accident(lane="South", description="Synthetic Multi-Car Collision")
        assert demo.state == AccidentState.TEST_EVENT
        assert demo.is_simulation is True
        assert demo.lane == "South"
        assert "[DEMO / TEST EVENT]" in demo.description
        
        active = detector.get_active_incidents()
        assert len(active) == 1
        assert active[0]["is_simulation"] is True

    def test_incident_resolution(self):
        """Resolving an active incident marks state as RESOLVED and records resolved_at."""
        detector = AccidentDetector(visual_model_path="models/non_existent_accident_model.pt")
        demo = detector.trigger_test_accident(lane="North")
        assert len(detector.get_active_incidents()) == 1
        
        success = detector.resolve_accident(demo.incident_id)
        assert success is True
        assert demo.state == AccidentState.RESOLVED
        assert demo.resolved_at is not None
        assert len(detector.get_active_incidents()) == 0
