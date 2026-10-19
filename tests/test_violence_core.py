"""
tests/test_violence_core.py — Automated Tests for VIGIL Module 2 (AI Violence Detection)
==========================================================================================
Validates:
  1. Video sequence sampling (uniform 16 frames extraction and tensor preprocessing)
  2. Missing model checkpoint handling (returns explicit MODEL_NOT_CONFIGURED; no fake outputs)
  3. Temporal validation (rejects single-frame false alarms, triggers on sustained events, respects cooldown)
  4. Rolling evidence buffer & video clip generation (writes valid MP4 video to disk)
  5. Test simulation event flags (ensures is_simulation=True and is_real_inference=False)
"""

import os
import sys
import time
import numpy as np
import pytest
import torch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.violence_detector import (
    VideoSequenceSampler,
    CNN_LSTM_ViolenceClassifier,
    TemporalValidator,
    RollingEvidenceBuffer,
    ViolenceDetector,
    ModelStatus
)


class TestVideoSequenceSampler:
    def test_sampling_indices(self):
        sampler = VideoSequenceSampler(sequence_length=16)
        # Window of 64 frames
        indices = sampler.sample_indices(64)
        assert len(indices) == 16
        assert indices[0] == 0
        assert indices[-1] < 64
        # Verify strictly increasing
        for i in range(len(indices) - 1):
            assert indices[i] < indices[i + 1]

    def test_preprocessing_and_tensor_shape(self):
        sampler = VideoSequenceSampler(sequence_length=16, frame_size=(224, 224))
        # Create 30 synthetic frames (720x1280 BGR)
        dummy_frames = [np.zeros((720, 1280, 3), dtype=np.uint8) for _ in range(30)]
        tensor, sampled_raw = sampler.sample_and_preprocess(dummy_frames)

        assert tensor is not None
        assert len(sampled_raw) == 16
        # Expected shape: (1, C=3, T=16, H=224, W=224)
        assert tensor.shape == (1, 3, 16, 224, 224)
        assert tensor.dtype == torch.float32


class TestModelConfiguration:
    def test_missing_weights_returns_model_not_configured(self):
        """Must return MODEL_NOT_CONFIGURED and refuse to fake predictions when weights are missing."""
        detector = ViolenceDetector(model_weights_path="non_existent_weights.pt")
        assert detector.status == ModelStatus.MODEL_NOT_CONFIGURED

        dummy_frames = [np.zeros((224, 224, 3), dtype=np.uint8) for _ in range(20)]
        res = detector.predict_sequence(dummy_frames)

        assert res["status"] == ModelStatus.MODEL_NOT_CONFIGURED.value
        assert res["is_real_inference"] is False
        assert res["confidence"] == 0.0
        assert res["label"] == "MODEL_UNAVAILABLE"

    def test_model_architecture_instantiation(self):
        """Verifies the PyTorch CNN-LSTM model graph can be built and evaluated."""
        model = CNN_LSTM_ViolenceClassifier(num_classes=2, hidden_dim=64, lstm_layers=1)
        model.eval()
        dummy_input = torch.randn(1, 3, 16, 224, 224)
        with torch.no_grad():
            out = model(dummy_input)
        assert out.shape == (1, 2)


class TestTemporalValidator:
    def test_isolated_prediction_rejected(self):
        """Single-frame anomaly must NOT trigger confirmed incident."""
        validator = TemporalValidator(confidence_threshold=0.75, min_consecutive=3, cooldown_sec=10.0)
        now = time.time()

        # Step 1: One isolated positive prediction
        is_alert, reason = validator.update(is_positive=True, confidence=0.88, timestamp=now)
        assert is_alert is False, "Single isolated prediction must not trigger alert"
        assert "suspected_anomaly" in reason

        # Step 2: Negative prediction immediately resets
        is_alert2, reason2 = validator.update(is_positive=False, confidence=0.30, timestamp=now + 0.1)
        assert is_alert2 is False
        assert validator.consecutive_positives == 0

    def test_sustained_predictions_trigger_alert(self):
        """Three consecutive positive predictions MUST trigger confirmed incident."""
        validator = TemporalValidator(confidence_threshold=0.75, min_consecutive=3, cooldown_sec=10.0)
        now = time.time()

        validator.update(is_positive=True, confidence=0.82, timestamp=now)
        validator.update(is_positive=True, confidence=0.85, timestamp=now + 0.1)
        is_alert, reason = validator.update(is_positive=True, confidence=0.90, timestamp=now + 0.2)

        assert is_alert is True, "Sustained predictions must trigger confirmed incident"
        assert reason == "confirmed_temporal_incident"

    def test_cooldown_suppresses_duplicate_alerts(self):
        """Subsequent predictions within cooldown window must be throttled."""
        validator = TemporalValidator(confidence_threshold=0.75, min_consecutive=2, cooldown_sec=10.0)
        now = time.time()

        validator.update(is_positive=True, confidence=0.80, timestamp=now)
        is_alert1, _ = validator.update(is_positive=True, confidence=0.85, timestamp=now + 0.1)
        assert is_alert1 is True

        # Next check during cooldown
        is_alert2, reason2 = validator.update(is_positive=True, confidence=0.90, timestamp=now + 2.0)
        assert is_alert2 is False, "Alert must be suppressed during cooldown"
        assert reason2 == "throttled_cooldown"


class TestRollingEvidenceBuffer:
    def test_buffer_and_clip_export(self, tmp_path):
        buffer = RollingEvidenceBuffer(max_buffer_sec=3.0, target_fps=10.0)
        start_time = time.time()

        # Add 25 frames (~2.5 seconds at 10 fps)
        for i in range(25):
            frame = np.full((120, 160, 3), fill_value=i * 10, dtype=np.uint8)
            buffer.add_frame(frame, timestamp=start_time + i * 0.1)

        clip_output = str(tmp_path / "test_evidence.mp4")
        meta = buffer.export_clip(clip_output, pre_sec=2.0)

        assert meta is not None, "Evidence clip must be generated"
        assert os.path.exists(meta["file_path"])
        assert meta["file_size_bytes"] > 0
        assert meta["duration_sec"] > 0


class TestTestEventSimulation:
    def test_simulation_event_tagging(self):
        detector = ViolenceDetector()
        # Add a few frames to the buffer
        for _ in range(10):
            detector.evidence_buffer.add_frame(np.zeros((100, 100, 3), dtype=np.uint8))

        incident = detector.trigger_test_incident(
            camera_id="CAM_SEC_01",
            description="Operator demo simulation",
            severity="high"
        )
        assert incident["is_simulation"] is True, "Simulated event must be explicitly marked"
        assert incident["is_real_inference"] is False, "Simulated event must never claim real AI inference"
        assert incident["validation_status"] == "test_simulation"
        assert incident["incident_type"] == "violence_test"
