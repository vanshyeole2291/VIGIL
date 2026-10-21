"""
backend/models/schemas.py — Pydantic Request & Response Validation Schemas
===========================================================================
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# ─── Auth Schemas ─────────────────────────────────────────────────────────────
class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "operator"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: float

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Camera Schemas ───────────────────────────────────────────────────────────
class CameraBase(BaseModel):
    name: str
    location: str
    stream_url: str
    camera_type: str = "traffic"  # "traffic", "security"
    is_active: bool = True


class CameraCreate(CameraBase):
    id: str


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    stream_url: Optional[str] = None
    camera_type: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class CameraOut(CameraBase):
    id: str
    status: str
    created_at: float

    class Config:
        from_attributes = True


# ─── Incident Schemas ─────────────────────────────────────────────────────────
class IncidentCreate(BaseModel):
    incident_type: str
    source_module: str = "traffic"
    camera_id: Optional[str] = None
    cctv_name: Optional[str] = None
    lane: Optional[str] = None
    confidence: float = 0.85
    severity: str = "medium"
    validation_status: str = "confirmed"
    description: str
    snapshot_b64: Optional[str] = None


class IncidentStatusUpdate(BaseModel):
    status: str  # "new", "acknowledged", "resolved"


class IncidentOut(BaseModel):
    id: str
    incident_type: str
    source_module: str
    camera_id: Optional[str] = None
    cctv_name: Optional[str] = None
    lane: Optional[str] = None
    timestamp: float
    confidence: float
    severity: str
    validation_status: str
    status: str
    description: str
    snapshot_b64: Optional[str] = None
    evidence_id: Optional[str] = None
    notes: Optional[str] = None
    supporting_evidence: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Alert Schemas ────────────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id: int
    incident_id: Optional[str] = None
    alert_type: str
    source_module: str
    severity: str
    message: str
    lane: Optional[str] = None
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    created_at: float

    class Config:
        from_attributes = True


# ─── Evidence Schemas ─────────────────────────────────────────────────────────
class EvidenceOut(BaseModel):
    id: str
    incident_id: Optional[str] = None
    file_path: str
    file_type: str
    file_size_bytes: int
    duration_sec: float
    checksum_sha256: Optional[str] = None
    created_at: float
    thumbnail_b64: Optional[str] = None
    snapshot_b64: Optional[str] = None
    camera_id: Optional[str] = None
    cctv_name: Optional[str] = None
    lane: Optional[str] = None
    incident_type: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Traffic Observation Schemas ──────────────────────────────────────────────
class TrafficObservationOut(BaseModel):
    id: int
    camera_id: Optional[str] = None
    lane_id: str
    vehicle_count: int
    pcu_count: float
    density_ratio: float
    congestion_level: str
    signal_phase: str
    timestamp: float

    class Config:
        from_attributes = True
