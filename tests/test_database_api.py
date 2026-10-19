"""
tests/test_database_api.py — Unit Tests for Database & Data Sources APIs
=======================================================================
Verifies:
  - GET /api/database/status returns valid SQLite metadata and table counts
  - POST /api/database/test-connection safely tests SQLite and handles validation
  - GET /api/data-sources/status returns honest catalog of 8 verified sources
"""

import pytest
from fastapi.testclient import TestClient
from backend.main_4way import app

client = TestClient(app)


def test_database_status_endpoint():
    response = client.get("/api/database/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["connected", "disconnected"]
    assert "engine" in data
    assert "tables" in data
    assert "incidents" in data["tables"]
    assert "cameras" in data["tables"]
    assert "schema_version" in data


def test_database_test_connection_sqlite():
    payload = {"db_type": "sqlite"}
    response = client.post("/api/database/test-connection", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "SQLite" in data["engine"]
    assert data["latency_ms"] >= 0


def test_database_test_connection_postgres_validation():
    # Empty host/database should return 400 validation error
    payload = {"db_type": "postgresql", "host": "", "database": "", "username": ""}
    response = client.post("/api/database/test-connection", json=payload)
    assert response.status_code == 400


def test_data_sources_status_endpoint():
    response = client.get("/api/data-sources/status")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    sources = data["sources"]
    assert len(sources) >= 7
    source_ids = [s["id"] for s in sources]
    assert "video_assets" in source_ids
    assert "camera_network" in source_ids
    assert "traffic_model" in source_ids
    assert "emergency_model" in source_ids
    assert "accident_detector" in source_ids
    assert "violence_model" in source_ids
    assert "audio_siren" in source_ids
    assert "database_storage" in source_ids
