"""
core/violence_detector.py — AI Violence Detection & Security Surveillance Engine
==================================================================================
Implements:
  1. Sliding-window uniform 16-frame sequence video sampling & ImageNet preprocessing
  2. Model interface: PyTorch video action classifier (CNN+LSTM / 3D CNN)
  3. Explicit MODEL_NOT_CONFIGURED state when trained weights are not present
     (strictly refuses to fabricate predictions or masquerade as real AI)
  4. Temporal validation engine: multi-window thresholding & hysteresis to filter single-frame false positives
  5. Rolling circular frame buffer with configurable pre-event and post-event MP4 evidence clipping
  6. Safe filesystem and OpenCV video codec handling
"""

import os
import sys
import time
import threading
from collections import deque
from enum import Enum
from typing import List, Dict, Tuple, Optional, Callable

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "evidence", "videos")
os.makedirs(EVIDENCE_DIR, exist_ok=True)


class ModelStatus(str, Enum):
    MODEL_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"
    MODEL_READY          = "MODEL_READY"
    INFERENCE_ERROR      = "INFERENCE_ERROR"


class VideoSequenceSampler:
    """
    Extracts and normalizes a fixed number of frames (default 16) from a
    sliding temporal window for input to a video classification network.
    """

    def __init__(self, sequence_length: int = 16, frame_size: Tuple[int, int] = (224, 224)):
        self.sequence_length = sequence_length
        self.frame_size = frame_size

        # ImageNet standardization parameters
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
        self.std  = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

    def sample_indices(self, total_frames: int) -> List[int]:
        """Compute uniform integer indices across the total frame window."""
        if total_frames <= 0:
            return []
        if total_frames <= self.sequence_length:
            # Repeat frames if fewer than sequence length
            return [min(i, total_frames - 1) for i in range(self.sequence_length)]
        step = total_frames / float(self.sequence_length)
        return [int(i * step) for i in range(self.sequence_length)]

    def sample_and_preprocess(self, frames: List[np.ndarray]) -> Tuple[Optional[torch.Tensor], List[np.ndarray]]:
        """
        Samples 16 frames uniformly and prepares normalized PyTorch tensor: (1, 3, T, H, W).
        Returns:
            (preprocessed_tensor, raw_sampled_frames)
        """
        if not frames:
            return None, []

        indices = self.sample_indices(len(frames))
        sampled_raw = [frames[i] for i in indices]

        processed_frames = []
        for f in sampled_raw:
            # Resize
            resized = cv2.resize(f, self.frame_size, interpolation=cv2.INTER_LINEAR)
            # Convert BGR to RGB
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            # Standardize
            norm = (rgb - self.mean) / self.std
            # Transpose to (C, H, W)
            chw = np.transpose(norm, (2, 0, 1))
            processed_frames.append(chw)

        # Stack into (T, C, H, W)
        tensor_tchw = torch.from_numpy(np.stack(processed_frames, axis=0)).float()
        # Permute to (C, T, H, W) and add batch dimension -> (1, C, T, H, W)
        tensor_1cthw = tensor_tchw.permute(1, 0, 2, 3).unsqueeze(0)

        return tensor_1cthw, sampled_raw


class CNN_LSTM_ViolenceClassifier(nn.Module):
    """
    Standard PyTorch video classification architecture for violence vs non-violence.
    Feature Extractor: Pretrained MobileNetV2 Backbone
    Temporal Aggregator: 2-layer Bidirectional LSTM
    Classifier Head: 2-class Logits (NON_VIOLENCE, VIOLENCE)
    """

    def __init__(self, num_classes: int = 2, hidden_dim: int = 256, lstm_layers: int = 2):
        super().__init__()
        backbone = models.mobilenet_v2(weights=None)
        self.feature_dim = backbone.last_channel  # 1280
        self.backbone = backbone.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))

        self.lstm = nn.LSTM(
            input_size=self.feature_dim,
            hidden_size=hidden_dim,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Input x: (B, C, T, H, W)
        Output logits: (B, 2)
        """
        b, c, t, h, w = x.shape
        # Collapse B and T for spatial feature extraction
        x = x.permute(0, 2, 1, 3, 4).contiguous().view(b * t, c, h, w)
        feats = self.backbone(x)
        feats = self.pool(feats).view(b, t, self.feature_dim)

        lstm_out, _ = self.lstm(feats)
        # Use final step output
        last_step = lstm_out[:, -1, :]
        logits = self.fc(last_step)
        return logits


class TemporalValidator:
    """
    Validates model predictions across a temporal window to eliminate isolated
    false positives, and enforces a cooldown between consecutive incident alerts.
    """

    def __init__(self, confidence_threshold: float = 0.70, min_consecutive: int = 3, cooldown_sec: float = 15.0):
        self.confidence_threshold = confidence_threshold
        self.min_consecutive = min_consecutive
        self.cooldown_sec = cooldown_sec

        self.consecutive_positives: int = 0
        self.last_alert_time: float = 0.0
        self.prediction_history: deque = deque(maxlen=20)

    def update(self, is_positive: bool, confidence: float, timestamp: float = None) -> Tuple[bool, str]:
        """
        Updates validator state with latest window classification.
        Returns:
            (is_validated_alert, reason_status)
        """
        now = timestamp or time.time()
        self.prediction_history.append((now, is_positive, confidence))

        if is_positive and confidence >= self.confidence_threshold:
            self.consecutive_positives += 1
        else:
            self.consecutive_positives = 0
            return False, "normal_flow"

        # Check temporal consistency
        if self.consecutive_positives < self.min_consecutive:
            return False, f"suspected_anomaly (consecutive={self.consecutive_positives}/{self.min_consecutive})"

        # Check incident cooldown
        if (now - self.last_alert_time) < self.cooldown_sec:
            return False, "throttled_cooldown"

        self.last_alert_time = now
        return True, "confirmed_temporal_incident"

    def reset(self):
        self.consecutive_positives = 0
        self.prediction_history.clear()


class RollingEvidenceBuffer:
    """
    Thread-safe circular frame buffer that captures and safely writes
    pre-event and post-event video clips to disk as MP4 files.
    """

    def __init__(self, max_buffer_sec: float = 10.0, target_fps: float = 25.0):
        self.max_buffer_sec = max_buffer_sec
        self.target_fps = target_fps
        self.max_frames = int(max_buffer_sec * target_fps)
        self.buffer: deque = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()

    def add_frame(self, frame: np.ndarray, timestamp: float = None):
        """Add a frame to the rolling buffer."""
        t = timestamp or time.time()
        with self.lock:
            # Store copy to avoid external mutations
            self.buffer.append((t, frame.copy()))

    def export_clip(self, output_path: str, pre_sec: float = 5.0, post_frames: List[Tuple[float, np.ndarray]] = None) -> Optional[Dict]:
        """
        Safely writes buffered frames + optional post-event frames to an MP4 video file.
        Returns metadata dict or None on write failure.
        """
        with self.lock:
            if not self.buffer:
                return None
            buffered_list = list(self.buffer)

        # Cut to pre_sec duration
        cutoff_time = buffered_list[-1][0] - pre_sec
        selected_frames = [f for t, f in buffered_list if t >= cutoff_time]

        # Append post-event frames if available
        if post_frames:
            selected_frames.extend([f for _, f in post_frames])

        if not selected_frames:
            return None

        h, w = selected_frames[0].shape[:2]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Codec negotiation: try mp4v, fallback to XVID
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.target_fps, (w, h))

        if not out.isOpened():
            # Fallback codec
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            alt_path = output_path.replace('.mp4', '.avi')
            out = cv2.VideoWriter(alt_path, fourcc, self.target_fps, (w, h))
            if not out.isOpened():
                print(f"[EvidenceBuffer] ERROR: Failed to open VideoWriter for {output_path}")
                return None
            output_path = alt_path

        try:
            for frame in selected_frames:
                out.write(frame)
        finally:
            out.release()

        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        duration = len(selected_frames) / float(self.target_fps)

        return {
            "file_path": output_path,
            "duration_sec": round(duration, 2),
            "file_size_bytes": file_size,
            "frame_count": len(selected_frames),
            "resolution": f"{w}x{h}",
        }


class ViolenceDetector:
    """
    Complete VIGIL Module 2 Security Surveillance Pipeline:
      - Sliding-window sequence creation (16 frames)
      - PyTorch model loading or explicit MODEL_NOT_CONFIGURED status
      - Temporal validation
      - Rolling evidence video buffering and clip export
    """

    def __init__(self, model_weights_path: Optional[str] = None,
                 confidence_threshold: float = 0.75,
                 min_consecutive_windows: int = 3,
                 device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_weights_path = model_weights_path

        self.sampler = VideoSequenceSampler(sequence_length=16, frame_size=(224, 224))
        self.validator = TemporalValidator(
            confidence_threshold=confidence_threshold,
            min_consecutive=min_consecutive_windows,
            cooldown_sec=15.0
        )
        self.evidence_buffer = RollingEvidenceBuffer(max_buffer_sec=10.0, target_fps=25.0)

        self.model: Optional[CNN_LSTM_ViolenceClassifier] = None
        self.status: ModelStatus = ModelStatus.MODEL_NOT_CONFIGURED
        self.model_metadata: Dict = {
            "model_architecture": "CNN-LSTM Action Recognition (MobileNetV2 + BiLSTM)",
            "expected_input_shape": "(1, 3, 16, 224, 224)",
            "classes": ["NON_VIOLENCE", "VIOLENCE"],
            "weights_file": None,
            "device": self.device,
        }

        # Attempt to load weights if a valid path was specified
        if model_weights_path and os.path.isfile(model_weights_path):
            self.load_model_weights(model_weights_path)

        # Callbacks
        self.on_incident_confirmed: Optional[Callable[[Dict], None]] = None

    def load_model_weights(self, weights_path: str) -> bool:
        """
        Safely loads PyTorch weights into the CNN-LSTM video classification model.
        Returns True on success, False if file is invalid or missing.
        """
        if not os.path.isfile(weights_path):
            print(f"[ViolenceDetector] Checkpoint not found: {weights_path}")
            self.status = ModelStatus.MODEL_NOT_CONFIGURED
            return False

        try:
            print(f"[ViolenceDetector] Loading model weights from: {weights_path}")
            model = CNN_LSTM_ViolenceClassifier(num_classes=2)
            state_dict = torch.load(weights_path, map_location=self.device)
            # Support both direct state_dict and checkpoint dictionaries
            if "state_dict" in state_dict:
                state_dict = state_dict["state_dict"]
            model.load_state_dict(state_dict, strict=False)
            model.to(self.device)
            model.eval()

            self.model = model
            self.model_weights_path = weights_path
            self.model_metadata["weights_file"] = weights_path
            self.status = ModelStatus.MODEL_READY
            print("[ViolenceDetector] Successfully configured and loaded violence model.")
            return True
        except Exception as e:
            print(f"[ViolenceDetector] Error loading weights: {e}")
            self.status = ModelStatus.INFERENCE_ERROR
            return False

    def predict_sequence(self, frames: List[np.ndarray]) -> Dict:
        """
        Classifies a window of video frames.
        If no compatible weights are loaded, returns MODEL_NOT_CONFIGURED
        and refuses to fabricate predictions.
        """
        if self.status != ModelStatus.MODEL_READY or self.model is None:
            return {
                "status": ModelStatus.MODEL_NOT_CONFIGURED.value,
                "label": "MODEL_UNAVAILABLE",
                "is_violence": False,
                "confidence": 0.0,
                "is_real_inference": False,
                "detail": "No trained violence-classification weights configured in models directory."
            }

        tensor, sampled_raw = self.sampler.sample_and_preprocess(frames)
        if tensor is None:
            return {
                "status": "INSUFFICIENT_FRAMES",
                "label": "UNKNOWN",
                "is_violence": False,
                "confidence": 0.0,
                "is_real_inference": False
            }

        tensor = tensor.to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

        non_violence_prob = float(probs[0])
        violence_prob     = float(probs[1])
        is_violence       = violence_prob > non_violence_prob
        conf              = violence_prob if is_violence else non_violence_prob

        return {
            "status": "INFERENCE_SUCCESS",
            "label": "VIOLENCE" if is_violence else "NON_VIOLENCE",
            "is_violence": is_violence,
            "confidence": round(conf, 4),
            "violence_probability": round(violence_prob, 4),
            "non_violence_probability": round(non_violence_prob, 4),
            "is_real_inference": True
        }

    def process_frame_stream(self, frame: np.ndarray, timestamp: float = None, camera_id: str = "CAM_SEC_01") -> Dict:
        """
        Processes an incoming video frame:
          1. Appends frame to rolling evidence buffer
          2. Evaluates sequence with model (if ready)
          3. Evaluates temporal validator
          4. If incident validated, exports evidence clip and triggers alert
        """
        now = timestamp or time.time()
        self.evidence_buffer.add_frame(frame, now)

        # Check model status
        if self.status != ModelStatus.MODEL_READY:
            return {
                "status": self.status.value,
                "alert_triggered": False,
                "camera_id": camera_id,
                "timestamp": now
            }

        # Buffer frames for sequence sampling
        with self.evidence_buffer.lock:
            recent_frames = [f for _, f in list(self.evidence_buffer.buffer)]

        # Classify sequence when at least 16 frames are available
        if len(recent_frames) >= 16:
            pred = self.predict_sequence(recent_frames)
            is_pos = pred.get("is_violence", False)
            conf   = pred.get("confidence", 0.0)

            is_alert, reason = self.validator.update(is_pos, conf, now)

            if is_alert:
                # Export evidence clip
                clip_filename = f"violence_incident_{int(now * 1000) % 100000}.mp4"
                clip_path = os.path.join(EVIDENCE_DIR, clip_filename)
                clip_meta = self.evidence_buffer.export_clip(clip_path, pre_sec=5.0)

                incident_data = {
                    "incident_type": "violence",
                    "source_module": "security",
                    "camera_id": camera_id,
                    "timestamp": now,
                    "confidence": conf,
                    "severity": "critical" if conf >= 0.85 else "high",
                    "description": f"AI Violence Detection: Confirmed physical aggression anomaly ({conf*100:.1f}% confidence).",
                    "evidence_clip": clip_meta.get("file_path") if clip_meta else None,
                    "is_real_inference": True
                }

                if self.on_incident_confirmed:
                    try:
                        self.on_incident_confirmed(incident_data)
                    except Exception as e:
                        print(f"[ViolenceDetector] Callback error: {e}")

                return {
                    "status": "INCIDENT_CONFIRMED",
                    "alert_triggered": True,
                    "incident": incident_data,
                    "reason": reason
                }

            return {
                "status": "MONITORING",
                "alert_triggered": False,
                "prediction": pred,
                "temporal_status": reason
            }

        return {
            "status": "BUFFERING",
            "alert_triggered": False,
            "buffered_frames": len(recent_frames)
        }

    def trigger_test_incident(self, camera_id: str = "CAM_SEC_01",
                              description: str = "Security Operator Demonstration: Simulated crowd altercation scenario.",
                              severity: str = "high") -> Dict:
        """
        Generates a clearly demarcated TEST incident and evidence clip for live demonstration.
        Explicitly flagged as `is_simulation=True` to never deceive operators.
        """
        now = time.time()
        clip_filename = f"test_security_incident_{int(now * 1000) % 100000}.mp4"
        clip_path = os.path.join(EVIDENCE_DIR, clip_filename)
        clip_meta = self.evidence_buffer.export_clip(clip_path, pre_sec=4.0)

        incident_data = {
            "id": f"SEC_{int(now * 1000) % 100000}",
            "incident_type": "violence_test",
            "source_module": "security",
            "camera_id": camera_id,
            "timestamp": now,
            "confidence": 1.0,
            "severity": severity,
            "validation_status": "test_simulation",
            "status": "new",
            "description": f"[MANUAL TEST EVENT] {description}",
            "evidence_clip": clip_meta.get("file_path") if clip_meta else None,
            "is_simulation": True,
            "is_real_inference": False
        }

        if self.on_incident_confirmed:
            try:
                self.on_incident_confirmed(incident_data)
            except Exception as e:
                print(f"[ViolenceDetector] Test callback error: {e}")

        return incident_data
