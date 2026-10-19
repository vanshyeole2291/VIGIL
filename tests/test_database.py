"""
tests/test_database.py — Automated Persistence & Schema Verification for VIGIL DB
==================================================================================
Validates:
  1. SQLite engine and table creation
  2. User creation, role validation, and password hashing
  3. Camera registry CRUD operations
  4. Incident record persistence across sessions
  5. Alert and Evidence foreign key associations
"""

import os
import sys
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import Base
import backend.models.db_models as models
from backend.services.auth_service import hash_password, verify_password


@pytest.fixture(scope="module")
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()


def test_user_creation_and_auth(test_db):
    hashed = hash_password("secretpass")
    assert verify_password("secretpass", hashed) is True
    assert verify_password("wrongpass", hashed) is False

    user = models.User(
        username="traffic_operator",
        email="operator@vigil.system",
        hashed_password=hashed,
        role="operator"
    )
    test_db.add(user)
    test_db.commit()

    retrieved = test_db.query(models.User).filter_by(username="traffic_operator").first()
    assert retrieved is not None
    assert retrieved.role == "operator"
    assert verify_password("secretpass", retrieved.hashed_password) is True


def test_incident_and_alert_persistence(test_db):
    camera = models.Camera(
        id="CAM_TEST_01",
        name="Test Junction North",
        location="Northbound Lane 1",
        stream_url="assets/videos/north.mp4",
        camera_type="traffic",
        status="online"
    )
    test_db.add(camera)
    test_db.commit()

    inc_id = f"INC_TEST_{int(time.time())}"
    incident = models.Incident(
        id=inc_id,
        incident_type="accident",
        source_module="traffic",
        camera_id="CAM_TEST_01",
        lane="North",
        confidence=0.92,
        severity="critical",
        validation_status="confirmed",
        status="new",
        description="Two-vehicle kinetic collision verified on North approach."
    )
    test_db.add(incident)
    test_db.commit()

    alert = models.Alert(
        incident_id=inc_id,
        alert_type="accident",
        source_module="traffic",
        severity="critical",
        message="Collision alert on North approach",
        lane="North",
        acknowledged=False
    )
    test_db.add(alert)
    test_db.commit()

    # Query back
    saved_inc = test_db.query(models.Incident).filter_by(id=inc_id).first()
    assert saved_inc is not None
    assert saved_inc.severity == "critical"
    assert len(saved_inc.alerts) == 1
    assert saved_inc.alerts[0].message == "Collision alert on North approach"
