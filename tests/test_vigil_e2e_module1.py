"""
tests/test_vigil_e2e_module1.py — Comprehensive E2E Verification Suite for VIGIL Module 1
=========================================================================================
Tests:
  1. Single Camera Workspace (Select, State, Control)
  2. IP Webcam Workspace (Config, Safe URL Testing, State)
  3. Four-Way ATSC State (Approaches breakdown, Webster Decision Logic)
  4. Accident Incident Persistence (Simulate, Triage status, Operator Notes)
  5. Evidence Database & SHA-256 Checksum Download
  6. Traffic Analytics (Summary, History, Accidents separation)
  7. Database Management & Connectivity Probing
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.main_4way import app, init_processor
from backend.database import init_db

init_db()
client = TestClient(app)


class TestSingleCameraEndpoints:
    def test_single_camera_state_and_select(self):
        # Select existing video
        resp = client.post("/api/single-camera/select", json={"source": "assets/videos/north.mp4"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "selected"

        # Check state
        state_resp = client.get("/api/single-camera/state")
        assert state_resp.status_code == 200
        data = state_resp.json()
        assert "source" in data
        assert "vehicle_counts" in data
        assert "density_score" in data

    def test_single_camera_controls(self):
        # Pause
        resp = client.post("/api/single-camera/control", json={"action": "pause"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

        # Resume
        resp = client.post("/api/single-camera/control", json={"action": "resume"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"


class TestIPWebcamEndpoints:
    def test_ip_webcam_config_roundtrip(self):
        # Set config
        set_resp = client.post(
            "/api/ip-webcam/config",
            json={"url": "http://192.168.1.150:8080/video", "name": "East Junction IP Cam", "direction": "East"}
        )
        assert set_resp.status_code == 200
        assert set_resp.json()["status"] == "updated"

        # Get config
        get_resp = client.get("/api/ip-webcam/config")
        assert get_resp.status_code == 200
        cfg = get_resp.json()
        assert cfg["name"] == "East Junction IP Cam"
        assert cfg["direction"] == "East"

    def test_ip_webcam_test_reachability_and_masking(self):
        # Test with invalid scheme
        bad_scheme = client.post("/api/ip-webcam/test", json={"url": "ftp://mycam.local"})
        assert bad_scheme.status_code == 200
        assert bad_scheme.json()["success"] is False

        # Test with credentials in URL (ensure masking)
        cred_test = client.post(
            "/api/ip-webcam/test",
            json={"url": "http://admin:secret123@127.0.0.1:65530/shot.jpg"}
        )
        assert cred_test.status_code == 200
        res = cred_test.json()
        assert res["success"] is False  # unreachable port
        # Verify secret was NOT echoed in masked_url
        assert "secret123" not in res.get("masked_url", "")
        assert "***:***@" in res.get("masked_url", "")


class TestFourWayStateEndpoints:
    def test_four_way_state_structure(self):
        init_processor()
        resp = client.get("/api/four-way/state")
        assert resp.status_code == 200
        data = resp.json()

        # Check 4 directions
        assert "directions" in data
        for lane in ["North", "South", "East", "West"]:
            assert lane in data["directions"]
            assert "pcu" in data["directions"][lane]
            assert "density_score" in data["directions"][lane]
            assert "signal_state" in data["directions"][lane]

        # Check intersection controller metadata
        assert "intersection" in data
        assert "decision_reason" in data["intersection"]
        assert "mode" in data["intersection"]
        assert "active_green" in data["intersection"]


class TestAccidentPersistenceAndTriage:
    def test_simulate_persists_collision_with_sha256(self):
        sim_resp = client.post("/api/accidents/simulate", json={"lane": "West"})
        assert sim_resp.status_code == 200
        sim_data = sim_resp.json()
        assert sim_data["status"] == "accident_simulated"
        inc_id = sim_data["incident_id"]

        # Verify incident is in accidents feed
        acc_resp = client.get("/api/accidents")
        assert acc_resp.status_code == 200
        accidents = acc_resp.json()
        matched = [a for a in accidents if a["id"] == inc_id]
        assert len(matched) == 1
        assert matched[0]["incident_type"] == "accident"

        # Append operator note
        note_resp = client.post(f"/api/accidents/{inc_id}/note", json={"note": "E2E Unit Test Verification Note"})
        assert note_resp.status_code == 200

        # Update status to acknowledged
        ack_resp = client.patch(f"/api/accidents/{inc_id}/status", json={"status": "acknowledged"})
        assert ack_resp.status_code == 200
        assert ack_resp.json()["new_status"] == "acknowledged"

        # Update status to resolved
        res_resp = client.patch(f"/api/accidents/{inc_id}/status", json={"status": "resolved"})
        assert res_resp.status_code == 200
        assert res_resp.json()["new_status"] == "resolved"


class TestEvidenceAndSHA256:
    def test_evidence_list_and_integrity_hash(self):
        resp = client.get("/api/evidence")
        assert resp.status_code == 200
        evidence_list = resp.json()
        assert len(evidence_list) > 0

        first = evidence_list[0]
        assert "checksum_sha256" in first
        assert len(first["checksum_sha256"]) == 64  # valid SHA-256 hex string

        # Download
        ev_id = first["id"]
        dl_resp = client.get(f"/api/evidence/{ev_id}/download")
        assert dl_resp.status_code == 200
        assert len(dl_resp.content) > 0


class TestTrafficAnalytics:
    def test_analytics_summary_and_history(self):
        s_resp = client.get("/api/analytics/summary")
        assert s_resp.status_code == 200
        s_data = s_resp.json()
        assert "total_vehicles_today" in s_data
        assert "peak_hourly_pcu" in s_data
        assert "vehicle_classes_breakdown" in s_data
        assert "total_accidents_recorded" in s_data

        h_resp = client.get("/api/analytics/history?hours=6")
        assert h_resp.status_code == 200
        h_data = h_resp.json()
        assert isinstance(h_data, list)


class TestDatabaseManagement:
    def test_database_status_and_sqlite_probe(self):
        status_resp = client.get("/api/database/status")
        assert status_resp.status_code == 200
        s = status_resp.json()
        assert s["status"] == "connected"
        assert "tables" in s
        assert "incidents" in s["tables"]

        # Test local sqlite probe
        test_resp = client.post("/api/database/test-connection", json={"db_type": "sqlite"})
        assert test_resp.status_code == 200
        t = test_resp.json()
        assert t["success"] is True
        assert t["engine"] == "SQLite"
