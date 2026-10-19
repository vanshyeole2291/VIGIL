"""
backend/routers/vigil_api.py — VIGIL Unified REST API Router
==============================================================
Provides end-to-end endpoints for:
  1. Authentication (login, register, me)
  2. Camera Network (list, create, update, delete)
  3. Module 2: AI Violence Detection & Security Surveillance
  4. Unified Incident Management
  5. Alert Feed & Acknowledgment
  6. Forensic Evidence Vault & Clip Delivery
  7. Comprehensive System Diagnostics
"""

import os
import sys
import time
import shutil
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.database import get_db
import backend.models.db_models as models
import backend.models.schemas as schemas
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_payload
)
from core.violence_detector import ViolenceDetector, ModelStatus

router = APIRouter()

# Module 2: Violence Detector Singleton
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "evidence", "videos")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

violence_detector = ViolenceDetector()


# ==============================================================================
# 1. AUTHENTICATION & OPERATOR PROFILES
# ==============================================================================

@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(creds: schemas.UserLogin, db: Session = Depends(get_db)):
    """Authenticate operator credentials and issue a JWT bearer token."""
    user = db.query(models.User).filter(models.User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(data={"sub": user.username, "role": user.role, "id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/auth/register", response_model=schemas.UserOut)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register a new VIGIL surveillance operator."""
    existing = db.query(models.User).filter(
        (models.User.username == user_data.username) | (models.User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role or "operator",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/auth/me", response_model=schemas.UserOut)
def get_current_user(
    payload: Optional[Dict] = Depends(get_current_user_payload),
    db: Session = Depends(get_db)
):
    """Return profile of currently logged in operator."""
    if not payload:
        # Fallback to default admin for local dev
        admin = db.query(models.User).filter_by(username="admin").first()
        if admin:
            return admin
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(models.User).filter_by(username=payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ==============================================================================
# 2. CAMERA NETWORK MANAGEMENT
# ==============================================================================

@router.get("/cameras", response_model=List[schemas.CameraOut])
def list_cameras(
    camera_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all configured traffic and security CCTV cameras."""
    q = db.query(models.Camera)
    if camera_type:
        q = q.filter(models.Camera.camera_type == camera_type)
    return q.all()


@router.post("/cameras", response_model=schemas.CameraOut, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: schemas.CameraCreate, db: Session = Depends(get_db)):
    """Register a new camera feed in VIGIL."""
    existing = db.query(models.Camera).filter_by(id=camera_in.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Camera with ID '{camera_in.id}' already exists")

    cam = models.Camera(**camera_in.model_dump())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam


@router.patch("/cameras/{camera_id}", response_model=schemas.CameraOut)
def update_camera(camera_id: str, updates: schemas.CameraUpdate, db: Session = Depends(get_db)):
    """Update camera configuration or operational status."""
    cam = db.query(models.Camera).filter_by(id=camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    for field, val in updates.model_dump(exclude_unset=True).items():
        setattr(cam, field, val)

    db.commit()
    db.refresh(cam)
    return cam


@router.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    """Remove a camera feed from VIGIL."""
    cam = db.query(models.Camera).filter_by(id=camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    db.delete(cam)
    db.commit()
    return {"status": "camera_deleted", "id": camera_id}


# ==============================================================================
# 3. MODULE 2: AI VIOLENCE DETECTION & SECURITY SURVEILLANCE
# ==============================================================================

@router.get("/violence/status")
def get_violence_model_status():
    """
    Returns AI violence model configuration, architecture, and deployment status.
    Reflects MODEL_NOT_CONFIGURED if weights have not been trained/configured.
    """
    return {
        "status": violence_detector.status.value,
        "is_model_ready": violence_detector.status == ModelStatus.MODEL_READY,
        "metadata": violence_detector.model_metadata,
        "weights_file": violence_detector.model_weights_path,
        "device": violence_detector.device,
        "buffer": {
            "current_frames": len(violence_detector.evidence_buffer.buffer),
            "max_seconds": violence_detector.evidence_buffer.max_buffer_sec,
            "target_fps": violence_detector.evidence_buffer.target_fps
        },
        "temporal_validator": {
            "consecutive_positives": violence_detector.validator.consecutive_positives,
            "min_consecutive_required": violence_detector.validator.min_consecutive,
            "confidence_threshold": violence_detector.validator.confidence_threshold,
            "cooldown_sec": violence_detector.validator.cooldown_sec
        }
    }


class ConfigureWeightsRequest(schemas.BaseModel):
    weights_path: str


@router.post("/violence/load-weights")
def load_violence_weights(req: ConfigureWeightsRequest):
    """Hot-load or switch PyTorch weights for the CNN-LSTM violence classifier."""
    success = violence_detector.load_model_weights(req.weights_path)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to load weights from {req.weights_path}. Check file format and path."
        )
    return {
        "status": violence_detector.status.value,
        "weights_file": violence_detector.model_weights_path,
        "device": violence_detector.device
    }


class TestSecurityIncidentRequest(schemas.BaseModel):
    camera_id: str = "CAM_SEC_01"
    description: Optional[str] = "Security Operator Demonstration: Simulated physical altercation scenario."
    severity: str = "high"


@router.post("/violence/test-event")
def trigger_violence_test_event(
    req: TestSecurityIncidentRequest,
    db: Session = Depends(get_db)
):
    """
    Manually triggers a clearly labeled simulation event for testing and evaluation.
    Exports an MP4 evidence clip, persists to SQLite DB, and returns the incident record.
    """
    # 1. Trigger incident in violence detector
    inc = violence_detector.trigger_test_incident(
        camera_id=req.camera_id,
        description=req.description or "Simulated security event",
        severity=req.severity
    )

    evd_id = f"EVD_{inc['id']}" if inc.get("evidence_clip") else None

    # 2. Persist to DB: Incident
    db_inc = models.Incident(
        id=inc["id"],
        incident_type="violence",
        source_module="security",
        camera_id=req.camera_id,
        lane="CCTV-Zone",
        timestamp=inc["timestamp"],
        confidence=1.0,
        severity=req.severity,
        validation_status="test_simulation",
        status="new",
        description=inc["description"],
        evidence_id=evd_id
    )
    db.add(db_inc)

    # 3. Persist to DB: Alert
    db_alert = models.Alert(
        incident_id=inc["id"],
        alert_type="violence",
        source_module="security",
        severity=req.severity,
        message=inc["description"],
        lane="CCTV-Zone",
        acknowledged=False,
        created_at=inc["timestamp"]
    )
    db.add(db_alert)

    # 4. Persist to DB: Evidence
    if inc.get("evidence_clip") and os.path.exists(inc["evidence_clip"]):
        clip_path = inc["evidence_clip"]
        db_evd = models.Evidence(
            id=evd_id,
            incident_id=inc["id"],
            file_path=clip_path,
            file_type="video/mp4",
            file_size_bytes=os.path.getsize(clip_path),
            duration_sec=4.0,
            created_at=inc["timestamp"]
        )
        db.add(db_evd)

    db.commit()

    return {
        "status": "security_incident_triggered",
        "incident": inc,
        "persisted_to_db": True
    }


@router.post("/violence/process-video")
async def process_violence_video(
    file: Optional[UploadFile] = File(None),
    video_path: Optional[str] = Form(None),
    camera_id: str = Form("CAM_SEC_01")
):
    """
    Processes video through VIGIL 16-frame sliding-window sequence sampler.
    If compatible trained weights are configured, runs model classification.
    If no trained weights exist, returns honest MODEL_NOT_CONFIGURED status.
    """
    temp_path = None
    try:
        if file:
            temp_path = os.path.join(EVIDENCE_DIR, f"temp_upload_{int(time.time()*1000)}.mp4")
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            source_file = temp_path
        elif video_path and os.path.exists(video_path):
            source_file = video_path
        else:
            raise HTTPException(status_code=400, detail="Must provide either an uploaded video file or valid local video_path")

        # Open video and extract frames
        cap = cv2.VideoCapture(source_file)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail=f"Could not open video file: {source_file}")

        frames = []
        while len(frames) < 300:  # Sample up to first 300 frames (~10-12s)
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()

        if len(frames) < 16:
            raise HTTPException(
                status_code=400,
                detail=f"Video too short ({len(frames)} frames). Module requires at least 16 frames for sequence classification."
            )

        # 16-frame sequence uniform sampling
        tensor, sampled_raw = violence_detector.sampler.sample_and_preprocess(frames)

        # Honest check: Is model configured with trained weights?
        if violence_detector.status != ModelStatus.MODEL_READY or violence_detector.model is None:
            return JSONResponse({
                "status": ModelStatus.MODEL_NOT_CONFIGURED.value,
                "is_model_ready": False,
                "detail": "Video frames were successfully extracted and sampled into the standard (1, 3, 16, 224, 224) sequence tensor. However, no trained PyTorch violence classification weights (.pt) are currently configured. Per VIGIL specification, no fake predictions or fabricated probabilities are generated.",
                "total_frames_extracted": len(frames),
                "sampled_sequence_length": 16,
                "tensor_shape": list(tensor.shape) if tensor is not None else None,
                "model_architecture": violence_detector.model_metadata["model_architecture"]
            })

        # Real inference if weights are present
        prediction = violence_detector.predict_sequence(frames)
        return JSONResponse({
            "status": "SUCCESS",
            "is_model_ready": True,
            "prediction": prediction,
            "total_frames": len(frames),
            "sampled_sequence_length": 16
        })

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ==============================================================================
# 4. UNIFIED INCIDENTS (TRAFFIC + SECURITY)
# ==============================================================================

@router.get("/incidents-unified")
def list_incidents_unified(
    source_module: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Returns unified tactical incident records from SQLite database,
    covering both Module 1 Traffic Safety and Module 2 Security Surveillance.
    """
    q = db.query(models.Incident).order_by(desc(models.Incident.timestamp))
    if source_module and source_module != "all":
        q = q.filter(models.Incident.source_module == source_module)
    if status_filter and status_filter != "all":
        q = q.filter(models.Incident.status == status_filter)

    incidents = q.limit(limit).all()

    # Formatted to support both frontend schemas
    results = []
    for inc in incidents:
        results.append({
            "id": inc.id,
            "incident_id": inc.id,
            "type": inc.incident_type,
            "incident_type": inc.incident_type,
            "source_module": inc.source_module,
            "camera_id": inc.camera_id,
            "lane": inc.lane,
            "timestamp": inc.timestamp,
            "time_str": time.strftime("%H:%M:%S", time.localtime(inc.timestamp)),
            "confidence": inc.confidence,
            "severity": inc.severity,
            "validation_status": inc.validation_status,
            "status": inc.status,
            "description": inc.description,
            "evidence_id": inc.evidence_id,
            "frame_b64": inc.snapshot_b64,
            "has_clip": bool(inc.evidence_id)
        })
    return results


@router.patch("/incidents/{incident_id}/status")
def update_incident_status(
    incident_id: str,
    status_update: schemas.IncidentStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update operational triage status of an incident ('new', 'acknowledged', 'resolved')."""
    inc = db.query(models.Incident).filter_by(id=incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    inc.status = status_update.status
    db.commit()
    db.refresh(inc)
    return {"status": "ok", "incident_id": inc.id, "new_status": inc.status}


# ==============================================================================
# 5. ALERTS & LIVE NOTIFICATIONS
# ==============================================================================

@router.get("/alerts", response_model=List[schemas.AlertOut])
def list_alerts(
    source_module: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List surveillance alerts with optional module and severity filtering."""
    q = db.query(models.Alert).order_by(desc(models.Alert.created_at))
    if source_module and source_module != "all":
        q = q.filter(models.Alert.source_module == source_module)
    if acknowledged is not None:
        q = q.filter(models.Alert.acknowledged == acknowledged)
    if severity and severity != "all":
        q = q.filter(models.Alert.severity == severity)

    return q.limit(limit).all()


@router.post("/alerts/{alert_id}/ack")
def acknowledge_alert(
    alert_id: int,
    acknowledged_by: Optional[str] = "operator",
    db: Session = Depends(get_db)
):
    """Mark an alert as acknowledged by the operator."""
    alert = db.query(models.Alert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_by = acknowledged_by
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/alerts/ack-all")
def acknowledge_all_alerts(
    acknowledged_by: Optional[str] = "operator",
    db: Session = Depends(get_db)
):
    """Acknowledge all unacknowledged alerts."""
    alerts = db.query(models.Alert).filter_by(acknowledged=False).all()
    for a in alerts:
        a.acknowledged = True
        a.acknowledged_by = acknowledged_by
    db.commit()
    return {"status": "all_alerts_acknowledged", "count": len(alerts)}


# ==============================================================================
# 6. FORENSIC EVIDENCE VAULT
# ==============================================================================

@router.get("/evidence", response_model=List[schemas.EvidenceOut])
def list_evidence(limit: int = 50, db: Session = Depends(get_db)):
    """List forensic video clips and image captures saved on disk."""
    return db.query(models.Evidence).order_by(desc(models.Evidence.created_at)).limit(limit).all()


@router.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """Download forensic evidence file by evidence ID."""
    evd = db.query(models.Evidence).filter_by(id=evidence_id).first()
    if not evd or not os.path.exists(evd.file_path):
        raise HTTPException(status_code=404, detail="Evidence file not found on disk")

    filename = os.path.basename(evd.file_path)
    return FileResponse(
        path=evd.file_path,
        media_type=evd.file_type or "video/mp4",
        filename=filename
    )


@router.get("/evidence/file/{filename}")
def stream_evidence_file(filename: str):
    """Directly stream an evidence video clip for inline browser playback."""
    file_path = os.path.join(EVIDENCE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Evidence clip not found")

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename
    )


# ==============================================================================
# 7. SYSTEM HEALTH & DIAGNOSTICS
# ==============================================================================

@router.get("/system/health")
def get_system_health(db: Session = Depends(get_db)):
    """Comprehensive diagnostic endpoint checking database, models, and runtimes."""
    # Check DB
    db_ok = True
    incidents_count = 0
    alerts_count = 0
    cameras_count = 0
    try:
        incidents_count = db.query(models.Incident).count()
        alerts_count = db.query(models.Alert).count()
        cameras_count = db.query(models.Camera).count()
    except Exception as e:
        db_ok = False

    # Check weights files
    models_dir = os.path.join(PROJECT_ROOT, "models")
    model_files = os.listdir(models_dir) if os.path.exists(models_dir) else []

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": time.time(),
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "type": "SQLite",
            "database_path": "vigil.db",
            "total_incidents": incidents_count,
            "total_alerts": alerts_count,
            "total_cameras": cameras_count
        },
        "modules": {
            "module_1_traffic": {
                "name": "Traffic Management & Road Safety ATSC",
                "status": "ready",
                "yolo_models_detected": [f for f in model_files if f.endswith(".pt")],
                "acoustic_detector": "Acoustic Siren FFT Engine Active"
            },
            "module_2_security": {
                "name": "AI Violence Detection & Security Surveillance",
                "status": violence_detector.status.value,
                "is_model_ready": violence_detector.status == ModelStatus.MODEL_READY,
                "weights_configured": violence_detector.model_weights_path is not None,
                "device": violence_detector.device,
                "evidence_buffer_active": True
            }
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "os": sys.platform
        }
    }
