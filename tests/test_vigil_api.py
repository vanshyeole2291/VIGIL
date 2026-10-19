"""
tests/test_vigil_api.py — End-to-End Test Suite for VIGIL Unified API Endpoints
===============================================================================
Tests:
  1. System Health Diagnostics
  2. Violence Detection API (Status, Refusal to fake predictions, Test Event, Evidence clipping)
  3. Camera CRUD Operations
  4. Alert Feed & Acknowledgment Workflow
  5. Authentication (JWT generation, Bcrypt check, Profile endpoint)
  6. Unified Incident Feed
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.main_4way import app
from backend.database import init_db, SessionLocal
import backend.models.db_models as models

# Initialize test database tables and seed
init_db()
client = TestClient(app)


class TestSystemHealth:
    def test_health_check_returns_ok_and_metadata(self):
        resp = client.get("/api/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["database"]["status"] == "connected"
        assert data["database"]["type"] == "SQLite"
        assert "module_1_traffic" in data["modules"]
        assert "module_2_security" in data["modules"]


class TestViolenceAPI:
    def test_status_returns_model_not_configured_when_no_weights(self):
        resp = client.get("/api/violence/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "MODEL_NOT_CONFIGURED"
        assert data["is_model_ready"] is False
        assert "MobileNetV2" in data["metadata"]["model_architecture"]

    def test_test_event_simulation_persists_incident_and_alert(self):
        resp = client.post(
            "/api/violence/test-event",
            json={
                "camera_id": "CAM_SEC_01",
                "description": "Verification of security altercation alert",
                "severity": "critical"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "security_incident_triggered"
        assert data["incident"]["is_simulation"] is True
        assert data["incident"]["is_real_inference"] is False
        inc_id = data["incident"]["id"]

        # Check in DB
        db = SessionLocal()
        try:
            db_inc = db.query(models.Incident).filter_by(id=inc_id).first()
            assert db_inc is not None
            assert db_inc.source_module == "security"
            assert db_inc.severity == "critical"

            db_alert = db.query(models.Alert).filter_by(incident_id=inc_id).first()
            assert db_alert is not None
            assert db_alert.acknowledged is False
        finally:
            db.close()

    def test_process_video_returns_explicit_model_not_configured(self):
        import cv2
        import numpy as np

        # Create synthetic 20-frame test video
        test_video_path = "test_video_sampling_api.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(test_video_path, fourcc, 10.0, (64, 64))
        for _ in range(20):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            out.write(frame)
        out.release()

        try:
            resp = client.post(
                "/api/violence/process-video",
                data={"video_path": os.path.abspath(test_video_path), "camera_id": "CAM_SEC_01"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "MODEL_NOT_CONFIGURED"
            assert data["is_model_ready"] is False
            assert "Per VIGIL specification, no fake predictions" in data["detail"]
            assert data["sampled_sequence_length"] == 16
            assert data["tensor_shape"] == [1, 3, 16, 224, 224]
        finally:
            if os.path.exists(test_video_path):
                os.remove(test_video_path)


class TestCameraManagement:
    def test_get_cameras_returns_seeded_cameras(self):
        resp = client.get("/api/cameras")
        assert resp.status_code == 200
        cameras = resp.json()
        assert len(cameras) >= 4
        cam_ids = [c["id"] for c in cameras]
        assert "CAM_NORTH_01" in cam_ids

    def test_create_and_delete_camera(self):
        new_cam = {
            "id": "CAM_TEST_99",
            "name": "Test Parking CCTV",
            "location": "North Lot Zone B",
            "stream_url": "assets/videos/north.mp4",
            "camera_type": "security",
            "is_active": True
        }
        resp = client.post("/api/cameras", json=new_cam)
        assert resp.status_code == 201
        assert resp.json()["id"] == "CAM_TEST_99"

        # Update
        patch_resp = client.patch("/api/cameras/CAM_TEST_99", json={"status": "offline"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "offline"

        # Delete
        del_resp = client.delete("/api/cameras/CAM_TEST_99")
        assert del_resp.status_code == 200


class TestAlertsAndIncidents:
    def test_alert_acknowledgment_workflow(self):
        # Fetch alerts
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        if len(alerts) > 0:
            target_alert = alerts[0]
            alert_id = target_alert["id"]

            # Acknowledge
            ack_resp = client.post(f"/api/alerts/{alert_id}/ack?acknowledged_by=test_operator")
            assert ack_resp.status_code == 200
            assert ack_resp.json()["acknowledged"] is True
            assert ack_resp.json()["acknowledged_by"] == "test_operator"

    def test_incidents_unified_endpoint(self):
        resp = client.get("/api/incidents-unified")
        assert resp.status_code == 200
        incidents = resp.json()
        assert isinstance(incidents, list)
        if len(incidents) > 0:
            assert "source_module" in incidents[0]
            assert "severity" in incidents[0]


class TestAuthAPI:
    def test_admin_login_success(self):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    def test_invalid_login_rejected(self):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
        assert resp.status_code == 401

    def test_auth_me_with_token(self):
        login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        token = login_resp.json()["access_token"]

        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "admin"
