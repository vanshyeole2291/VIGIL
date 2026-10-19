"""
backend/models/db_models.py — VIGIL Unified SQLAlchemy ORM Entities
===================================================================
Defines schemas for:
  - Users & Roles (Authentication & Authorization)
  - Cameras & Stream configurations (Traffic & Security)
  - Incidents (Accidents, Stalled Vehicles, Violence, Emergency Preemptions)
  - Alerts (Live incident notifications)
  - Evidence (Forensic images, video clips, metadata)
  - TrafficObservations (Persisted lane counts & density history)
  - AuditLogs (Operator action logging)
"""

import time
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), default="operator")  # "admin", "operator", "viewer"
    is_active = Column(Boolean, default=True)
    created_at = Column(Float, default=time.time)

    audit_logs = relationship("AuditLog", back_populates="user")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    location = Column(String(256), nullable=False)
    stream_url = Column(String(512), nullable=False)
    camera_type = Column(String(32), default="traffic")  # "traffic", "security"
    status = Column(String(32), default="online")        # "online", "offline", "degraded"
    is_active = Column(Boolean, default=True)
    created_at = Column(Float, default=time.time)

    incidents = relationship("Incident", back_populates="camera")
    traffic_observations = relationship("TrafficObservation", back_populates="camera")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, index=True)
    incident_type = Column(String(64), index=True, nullable=False)  # accident, stalled_vehicle, ambulance, crowd, violence, weapon
    source_module = Column(String(32), index=True, nullable=False)  # "traffic", "security"
    camera_id = Column(String(64), ForeignKey("cameras.id"), nullable=True)
    lane = Column(String(32), nullable=True)
    timestamp = Column(Float, default=time.time, index=True)
    confidence = Column(Float, default=0.85)
    severity = Column(String(32), default="medium")                 # "low", "medium", "high", "critical"
    validation_status = Column(String(32), default="confirmed")     # "suspected", "confirmed", "false_positive"
    status = Column(String(32), default="new")                      # "new", "acknowledged", "resolved"
    description = Column(Text, nullable=False)
    evidence_id = Column(String(64), nullable=True)
    snapshot_b64 = Column(Text, nullable=True)                      # Thumbnail preview

    camera = relationship("Camera", back_populates="incidents")
    alerts = relationship("Alert", back_populates="incident", cascade="all, delete-orphan")
    evidence_records = relationship("Evidence", back_populates="incident", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=True)
    alert_type = Column(String(64), nullable=False)
    source_module = Column(String(32), nullable=False)
    severity = Column(String(32), default="high")
    message = Column(Text, nullable=False)
    lane = Column(String(32), nullable=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(64), nullable=True)
    created_at = Column(Float, default=time.time, index=True)

    incident = relationship("Incident", back_populates="alerts")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=True)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(32), default="image/jpeg")  # "image/jpeg", "video/mp4"
    file_size_bytes = Column(Integer, default=0)
    duration_sec = Column(Float, default=0.0)
    created_at = Column(Float, default=time.time, index=True)

    incident = relationship("Incident", back_populates="evidence_records")


class TrafficObservation(Base):
    __tablename__ = "traffic_observations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(String(64), ForeignKey("cameras.id"), nullable=True)
    lane_id = Column(String(32), index=True, nullable=False)
    vehicle_count = Column(Integer, default=0)
    pcu_count = Column(Float, default=0.0)
    density_ratio = Column(Float, default=0.0)
    congestion_level = Column(String(32), default="free")
    signal_phase = Column(String(32), default="red")
    timestamp = Column(Float, default=time.time, index=True)

    camera = relationship("Camera", back_populates="traffic_observations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(128), nullable=False)
    target_type = Column(String(64), nullable=True)
    target_id = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(Float, default=time.time, index=True)

    user = relationship("User", back_populates="audit_logs")
