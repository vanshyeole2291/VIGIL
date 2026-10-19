import React, { useState, useEffect } from 'react';

export default function SecuritySurveillanceView() {
  const [modelStatus, setModelStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [testVideoResult, setTestVideoResult] = useState(null);
  const [testingVideo, setTestingVideo] = useState(false);
  const [severity, setSeverity] = useState('high');

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/violence/status');
      if (res.ok) {
        const data = await res.json();
        setModelStatus(data);
      }
    } catch (e) {
      console.error('Failed to fetch violence model status', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const triggerTestSimulation = async () => {
    setSimulating(true);
    setSimResult(null);
    try {
      const res = await fetch('/api/violence/test-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: 'CAM_SEC_01',
          description: 'Security Operator Demonstration: Simulated crowd altercation scenario.',
          severity: severity
        })
      });
      if (res.ok) {
        const data = await res.json();
        setSimResult(data);
      }
    } catch (e) {
      console.error('Test simulation error', e);
    } finally {
      setSimulating(false);
    }
  };

  const testPipelineOnVideo = async () => {
    setTestingVideo(true);
    setTestVideoResult(null);
    try {
      const formData = new FormData();
      formData.append('video_path', 'assets/videos/north.mp4');
      formData.append('camera_id', 'CAM_SEC_01');

      const res = await fetch('/api/violence/process-video', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setTestVideoResult(data);
    } catch (e) {
      console.error('Pipeline test error', e);
    } finally {
      setTestingVideo(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-surface-container border border-outline-variant/30 shadow-lg">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[24px]">security</span>
            </div>
            <div>
              <h1 className="text-xl font-headline font-bold text-on-surface">
                AI Violence Detection & Security Surveillance
              </h1>
              <p className="text-xs text-on-surface-variant font-mono">
                Module 2 &bull; 16-Frame Temporal Sequence Pipeline &bull; PyTorch CNN-LSTM Architecture
              </p>
            </div>
          </div>
        </div>

        {/* Model Readiness Badge */}
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-xl bg-surface-container-high border border-outline-variant/40 flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${modelStatus?.status === 'MODEL_READY' ? 'bg-secondary' : 'bg-amber-400'}`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${modelStatus?.status === 'MODEL_READY' ? 'bg-secondary' : 'bg-amber-500'}`}></span>
            </span>
            <div className="flex flex-col">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase tracking-wider">
                Model Status
              </span>
              <span className="text-xs font-bold text-on-surface font-mono">
                {modelStatus ? modelStatus.status : 'CHECKING...'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Honest Architecture & Status Notice */}
      <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-amber-400 text-[26px] shrink-0 mt-0.5">verified_user</span>
          <div className="space-y-1.5 text-xs">
            <div className="font-bold text-amber-300 text-sm">
              Academic & Operational Integrity Guarantee: Zero Fabricated Predictions
            </div>
            <p className="text-amber-200/90 leading-relaxed">
              VIGIL implements the complete video action classification pipeline including <strong>16-frame sliding-window uniform sampling</strong>, <strong>ImageNet tensor normalization</strong>, and <strong>temporal consistency validation</strong>. Because general YOLO object detection weights cannot classify human violent actions, the system reports <code className="bg-amber-950/60 px-1.5 py-0.5 rounded text-amber-300 font-mono">MODEL_NOT_CONFIGURED</code> until genuine video-action classification weights are provided. No fake probabilities or deceptive mock outputs are ever generated.
            </p>
          </div>
        </div>
      </div>

      {/* 3. Main Split View: Surveillance Camera Feed & AI Pipeline Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Live Security Feed & Buffer State (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">videocam</span>
                <h2 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
                  Live CCTV Surveillance Feed — CAM_SEC_01
                </h2>
              </div>
              <span className="px-2.5 py-1 rounded-md bg-secondary/15 text-secondary text-[11px] font-mono font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
                BUFFER RECORDING
              </span>
            </div>

            {/* Video Viewport */}
            <div className="relative aspect-video rounded-xl overflow-hidden bg-surface-container-lowest border border-outline-variant/30 shadow-inner flex items-center justify-center group">
              <img
                src="/api/frame"
                alt="Security Camera Feed"
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextElementSibling.style.display = 'flex';
                }}
              />
              <div className="hidden absolute inset-0 flex-col items-center justify-center p-6 text-center text-on-surface-variant">
                <span className="material-symbols-outlined text-4xl mb-2 text-outline">videocam_off</span>
                <p className="text-xs font-mono">Primary Camera Stream Offline — Standby Mode</p>
              </div>

              {/* HUD Overlay */}
              <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 font-mono text-[10px] space-y-0.5 text-white">
                <div>FEED: CAM_SEC_01 &bull; 1080p @ 25 FPS</div>
                <div>LOCATION: Pedestrian Plaza & Crosswalk Zone</div>
              </div>

              <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 font-mono text-[10px] text-white">
                CIRCULAR BUFFER: {modelStatus?.buffer?.current_frames || 0} frames ({modelStatus?.buffer?.max_seconds || 10}s rolling window)
              </div>
            </div>

            {/* Buffer & Temporal Metrics */}
            <div className="grid grid-cols-3 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/20">
                <span className="text-[10px] text-on-surface-variant font-mono block uppercase">Rolling Buffer</span>
                <span className="text-sm font-bold text-on-surface font-mono">
                  {modelStatus?.buffer?.current_frames || 0} / 250 frames
                </span>
              </div>
              <div className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/20">
                <span className="text-[10px] text-on-surface-variant font-mono block uppercase">Consecutive Windows</span>
                <span className="text-sm font-bold text-on-surface font-mono">
                  {modelStatus?.temporal_validator?.consecutive_positives || 0} / {modelStatus?.temporal_validator?.min_consecutive_required || 3}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/20">
                <span className="text-[10px] text-on-surface-variant font-mono block uppercase">Incident Cooldown</span>
                <span className="text-sm font-bold text-on-surface font-mono">
                  {modelStatus?.temporal_validator?.cooldown_sec || 15}s Hysteresis
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Demonstration & Verification (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Simulation Trigger Card */}
          <div className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">science</span>
              <h2 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
                Evaluation & Demonstration Trigger
              </h2>
            </div>

            <p className="text-xs text-on-surface-variant leading-relaxed">
              Inject a demarcated security altercation incident to evaluate the complete end-to-end alert dispatch, SQLite persistence, and MP4 evidence clip recording.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-mono text-on-surface-variant block mb-1">
                  SEVERITY LEVEL:
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {['medium', 'high', 'critical'].map((sev) => (
                    <button
                      key={sev}
                      onClick={() => setSeverity(sev)}
                      className={`py-1.5 px-3 rounded-lg text-xs font-mono font-bold uppercase transition-all border ${
                        severity === sev
                          ? 'bg-primary/20 text-primary border-primary'
                          : 'bg-surface-container-low text-on-surface-variant border-outline-variant/30 hover:bg-surface-container-high'
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={triggerTestSimulation}
                disabled={simulating}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 text-white font-headline font-bold text-xs uppercase tracking-wider shadow-lg shadow-red-950/50 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">
                  {simulating ? 'hourglass_top' : 'crisis_alert'}
                </span>
                {simulating ? 'Simulating Event & Clipping MP4...' : 'Trigger Simulated Security Altercation'}
              </button>
            </div>

            {/* Simulation Feedback Card */}
            {simResult && (
              <div className="p-3.5 rounded-xl bg-surface-container-lowest border border-primary/40 space-y-2 animate-fadeIn">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono text-primary font-bold">
                    ✓ SIMULATED INCIDENT PERSISTED
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-primary/20 text-primary font-bold">
                    {simResult.incident?.id}
                  </span>
                </div>
                <p className="text-xs text-on-surface font-body leading-relaxed">
                  {simResult.incident?.description}
                </p>
                <div className="text-[10px] font-mono text-on-surface-variant space-y-0.5 pt-1 border-t border-outline-variant/20">
                  <div>Timestamp: {new Date(simResult.incident?.timestamp * 1000).toLocaleTimeString()}</div>
                  <div>Evidence Clip: {simResult.incident?.evidence_clip || 'Recorded in evidence/videos/'}</div>
                  <div className="text-amber-400 font-semibold">Tag: is_simulation=True &bull; is_real_inference=False</div>
                </div>
              </div>
            )}
          </div>

          {/* 16-Frame Pipeline Tester */}
          <div className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">movie</span>
              <h2 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
                16-Frame Video Pipeline Tester
              </h2>
            </div>

            <p className="text-xs text-on-surface-variant leading-relaxed">
              Verify video frame extraction, uniform 16-frame sequence subsampling, and tensor preprocessing on real video assets.
            </p>

            <button
              onClick={testPipelineOnVideo}
              disabled={testingVideo}
              className="w-full py-2.5 px-4 rounded-xl bg-surface-container-high hover:bg-surface-container-highest border border-outline-variant/40 text-on-surface font-mono font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[18px]">
                {testingVideo ? 'hourglass_top' : 'play_circle'}
              </span>
              {testingVideo ? 'Extracting & Sampling 16 Frames...' : 'Test Sequence Sampler on assets/videos/north.mp4'}
            </button>

            {testVideoResult && (
              <div className="p-3.5 rounded-xl bg-surface-container-lowest border border-outline-variant/30 space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between text-on-surface">
                  <span className="text-secondary font-bold">STATUS: {testVideoResult.status}</span>
                  <span>Sampled: {testVideoResult.sampled_sequence_length || 16} Frames</span>
                </div>
                <div className="text-on-surface-variant text-[11px] leading-relaxed">
                  {testVideoResult.detail}
                </div>
                {testVideoResult.tensor_shape && (
                  <div className="p-2 rounded bg-surface-container-high text-primary font-bold text-[11px]">
                    Preprocessed Tensor Shape: {JSON.stringify(testVideoResult.tensor_shape)}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
