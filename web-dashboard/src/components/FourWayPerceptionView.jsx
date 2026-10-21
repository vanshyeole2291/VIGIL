import React, { useState, useEffect, useRef } from 'react';

export default function FourWayPerceptionView({ onSwitchView }) {
  const [streamTs, setStreamTs] = useState(() => Date.now());
  const [isPaused, setIsPaused] = useState(false);
  const [fourWayState, setFourWayState] = useState(null);
  const [controlNotice, setControlNotice] = useState(null);
  const [availableVideos, setAvailableVideos] = useState([]);
  const [switchingCamera, setSwitchingCamera] = useState({});
  const [uploadingCamera, setUploadingCamera] = useState({});
  const fileInputRefs = {
    North: useRef(null),
    South: useRef(null),
    East: useRef(null),
    West: useRef(null),
  };

  // 1. Fetch available videos catalog from assets/videos
  const fetchVideos = async () => {
    try {
      const res = await fetch('/api/videos');
      if (res.ok) {
        const data = await res.json();
        setAvailableVideos(data || []);
      }
    } catch (e) {
      console.debug('Failed to fetch videos catalog', e);
    }
  };

  useEffect(() => {
    fetchVideos();
  }, []);

  // 2. Poll 4-way intersection telemetry
  useEffect(() => {
    let isMounted = true;
    const fetchState = async () => {
      try {
        const res = await fetch('/api/four-way/state');
        if (res.ok && isMounted) {
          const data = await res.json();
          setFourWayState(data);
          if (data.is_paused !== undefined) {
            setIsPaused(data.is_paused);
          }
        }
      } catch (e) {
        console.debug('Failed to fetch 4-way state', e);
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 1200);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const notify = (msg) => {
    setControlNotice(msg);
    setTimeout(() => setControlNotice(null), 4000);
  };

  // 3. Pause / Resume Handler (Task 2)
  const handleTogglePause = async () => {
    try {
      const res = await fetch('/api/four-way/toggle-pause', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setIsPaused(data.is_paused);
        setStreamTs(Date.now());
        notify(
          data.is_paused
            ? '⏸ Video capture & YOLO inference PAUSED'
            : '▶ Video capture & YOLO inference RESUMED'
        );
      }
    } catch (e) {
      notify('Failed to toggle pause state.');
    }
  };

  // 4. Dynamic Video Source Switching (Task 1)
  const handleSwitchSource = async (direction, sourcePath) => {
    if (!sourcePath) return;
    setSwitchingCamera((prev) => ({ ...prev, [direction]: true }));
    try {
      const res = await fetch('/api/four-way/switch-source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: direction, source: sourcePath }),
      });
      if (res.ok) {
        const filename = sourcePath.split(/[\\/]/).pop();
        notify(`✓ Camera [${direction.toUpperCase()}] video source switched to: ${filename}`);
        setStreamTs(Date.now());
      } else {
        notify(`Failed to switch camera [${direction}] source.`);
      }
    } catch {
      notify(`Network error switching camera [${direction}] source.`);
    } finally {
      setSwitchingCamera((prev) => ({ ...prev, [direction]: false }));
    }
  };

  // 5. Upload Video directly to specific camera quadrant (Task 1)
  const handleUploadSource = async (direction, file) => {
    if (!file) return;
    setUploadingCamera((prev) => ({ ...prev, [direction]: true }));
    const formData = new FormData();
    formData.append('camera_id', direction);
    formData.append('file', file);
    try {
      const res = await fetch('/api/four-way/upload-source', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        notify(`✓ Uploaded & assigned ${file.name} to ${direction.toUpperCase()} camera!`);
        await fetchVideos();
        setStreamTs(Date.now());
      } else {
        notify(`Failed to upload video for ${direction}.`);
      }
    } catch {
      notify(`Error uploading video for ${direction}.`);
    } finally {
      setUploadingCamera((prev) => ({ ...prev, [direction]: false }));
    }
  };

  // 6. Signal & Emergency Manual Overrides
  const handleManualOverride = async (lane) => {
    try {
      const res = await fetch('/api/override-signal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lane, duration: 30.0 }),
      });
      if (res.ok) {
        notify(`Manual green signal override commanded for ${lane} approach (30s hold).`);
      }
    } catch {
      notify('Failed to execute manual override.');
    }
  };

  const handleTriggerEmergency = async (lane) => {
    try {
      const res = await fetch('/api/trigger-emergency', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lane, duration: 30.0 }),
      });
      if (res.ok) {
        notify(`🚑 Emergency preemption engaged for ${lane} approach.`);
      }
    } catch {
      notify('Failed to trigger emergency.');
    }
  };

  const handleClearEmergency = async () => {
    try {
      const res = await fetch('/api/clear-emergency', { method: 'POST' });
      if (res.ok) {
        notify('✓ Emergency hold disengaged. Controller restored to Webster ATSC mode.');
      }
    } catch {
      notify('Failed to clear emergency hold.');
    }
  };

  const handleSirenTest = async () => {
    try {
      const res = await fetch('/api/trigger-siren-test', { method: 'POST' });
      if (res.ok) {
        const d = await res.json();
        notify(`Acoustic Siren FFT Verified: Emergency corridor granted to ${d.target_lane || 'Approach'}.`);
      }
    } catch {
      notify('Siren test failed.');
    }
  };

  const intersection = fourWayState?.intersection || {
    active_green: 'North',
    signal_phase: 'PHASE NORTH',
    time_remaining: 15.0,
    next_direction: 'South',
    emergency_preempted: false,
    decision_reason: 'Phase allocated via Webster ATSC optimization.',
    mode: 'Adaptive Webster ATSC',
    inference_fps: 25.0,
  };

  const directions = fourWayState?.directions || {
    North: { name: 'North', connected: false, source: '', total_vehicles: 0, pcu: 0.0, density_score: 0, signal_state: 'RED', emergency_detected: false, class_counts: {} },
    South: { name: 'South', connected: false, source: '', total_vehicles: 0, pcu: 0.0, density_score: 0, signal_state: 'RED', emergency_detected: false, class_counts: {} },
    East:  { name: 'East',  connected: false, source: '', total_vehicles: 0, pcu: 0.0, density_score: 0, signal_state: 'RED', emergency_detected: false, class_counts: {} },
    West:  { name: 'West',  connected: false, source: '', total_vehicles: 0, pcu: 0.0, density_score: 0, signal_state: 'RED', emergency_detected: false, class_counts: {} },
  };

  const camConfig = [
    { key: 'North', label: 'North Approach', camId: 'CAM_NORTH_01', quad: 'Q1' },
    { key: 'South', label: 'South Approach', camId: 'CAM_SOUTH_01', quad: 'Q2' },
    { key: 'East',  label: 'East Corridor',  camId: 'CAM_EAST_01',  quad: 'Q3' },
    { key: 'West',  label: 'West Corridor',  camId: 'CAM_WEST_01',  quad: 'Q4' },
  ];

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* 1. Header Toolbar */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
              Synchronized 4-Directional Intersection Workspace
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Four-Way ATSC Perception & Signal Controller
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Real-time Webster saturation flow optimization across North, South, East, and West quad camera arrays.
          </p>
        </div>

        {/* Phase & Live Controls */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {intersection.emergency_preempted && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-950/80 border border-red-500/60 text-red-300 animate-pulse text-xs font-bold shadow-md">
              <span>🚑</span>
              <span>EMERGENCY PREEMPTION ACTIVE</span>
            </div>
          )}

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold text-white">
              GREEN: <strong className="text-emerald-400">{intersection.active_green.toUpperCase()}</strong> ({Math.round(intersection.time_remaining)}s)
            </span>
          </div>

          <button
            onClick={() => setStreamTs(Date.now())}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-semibold flex items-center gap-1"
            title="Reload Video Stream"
          >
            <span className="material-symbols-outlined text-[15px]">refresh</span>
            <span>Refresh</span>
          </button>

          {/* Responsive Pause/Resume Button (Task 2) */}
          <button
            onClick={handleTogglePause}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all shadow-sm ${
              isPaused
                ? 'bg-amber-600 hover:bg-amber-500 text-white border-amber-400 animate-pulse'
                : 'bg-slate-800 text-slate-200 border-slate-700 hover:bg-slate-700'
            }`}
            title={isPaused ? 'Resume video stream and YOLO inference' : 'Halt video capture and freeze inference'}
          >
            <span className="material-symbols-outlined text-[16px]">
              {isPaused ? 'play_arrow' : 'pause'}
            </span>
            <span>{isPaused ? 'Resume Processing' : 'Pause Processing'}</span>
          </button>
        </div>
      </section>

      {/* Control Notice */}
      {controlNotice && (
        <div className="p-3.5 rounded-xl bg-cyan-950/90 border border-cyan-500/50 text-white flex items-center justify-between text-xs font-mono shadow-lg">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-cyan-400 text-base">info</span>
            <span>{controlNotice}</span>
          </div>
          <button onClick={() => setControlNotice(null)} className="text-slate-400 hover:text-white font-bold px-1">✕</button>
        </div>
      )}

      {/* 2. Main Live 4-Way Composite Video */}
      <section className="bg-[#0D1424] rounded-2xl overflow-hidden border border-slate-800 shadow-xl">
        <div className="p-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-slate-300">
            <span className={`w-2.5 h-2.5 rounded-full ${isPaused ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'}`}></span>
            <span className="font-bold text-white">
              {isPaused ? 'FEED PAUSED (FRAME FROZEN)' : 'LIVE PERCEPTION MATRIX'}
            </span>
            <span className="hidden sm:inline text-slate-400">
              — 1280 × 720 Synchronized Quad Array (Q1: North, Q2: South, Q3: East, Q4: West)
            </span>
          </div>
          <div className="flex items-center gap-3">
            {isPaused && (
              <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-600/50 text-[10px] font-bold">
                PAUSED
              </span>
            )}
            <span className="text-slate-400 text-[11px]">
              Inference: <strong className="text-cyan-400">{intersection.inference_fps} FPS</strong>
            </span>
          </div>
        </div>

        <div className="relative bg-black flex items-center justify-center min-h-[440px] aspect-video">
          <img
            key={streamTs}
            src={isPaused ? `/api/frame?ts=${streamTs}` : `/api/stream?ts=${streamTs}`}
            alt="4-Way Multi-Camera Live Composite Feed"
            className="w-full h-full object-contain"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />

          {/* Paused Overlay */}
          {isPaused && (
            <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] flex flex-col items-center justify-center gap-3 z-10">
              <div className="w-14 h-14 rounded-full bg-amber-500/20 border-2 border-amber-400 flex items-center justify-center">
                <span className="material-symbols-outlined text-amber-400 text-3xl">pause</span>
              </div>
              <div className="text-center">
                <h3 className="text-base font-bold text-white tracking-wide">VIDEO STREAM PAUSED</h3>
                <p className="text-xs text-amber-300/90 font-mono mt-1">YOLOv8 inference and video capture are halted on current frame.</p>
              </div>
              <button
                onClick={handleTogglePause}
                className="mt-2 px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg transition-all"
              >
                <span className="material-symbols-outlined text-sm">play_arrow</span>
                Resume Live Processing
              </button>
            </div>
          )}

          {/* Corner Watermarks */}
          <div className="absolute top-2 left-2 bg-slate-900/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-slate-700 text-[10px] font-mono text-cyan-300 flex items-center gap-1.5 shadow-md">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            NORTH APPROACH (Q1)
          </div>
          <div className="absolute top-2 right-2 bg-slate-900/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-slate-700 text-[10px] font-mono text-cyan-300 flex items-center gap-1.5 shadow-md">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            SOUTH APPROACH (Q2)
          </div>
          <div className="absolute bottom-2 left-2 bg-slate-900/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-slate-700 text-[10px] font-mono text-cyan-300 flex items-center gap-1.5 shadow-md">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            EAST CORRIDOR (Q3)
          </div>
          <div className="absolute bottom-2 right-2 bg-slate-900/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-slate-700 text-[10px] font-mono text-cyan-300 flex items-center gap-1.5 shadow-md">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            WEST CORRIDOR (Q4)
          </div>
        </div>
      </section>

      {/* 3. DYNAMIC VIDEO SOURCE SELECTORS PER CAMERA (TASK 1) */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-xl">
        <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-cyan-400 text-lg">videocam</span>
            <h2 className="text-sm sm:text-base font-bold text-white">
              Dynamic Camera Feed Selection & Uploads
            </h2>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
            Hot-Swappable Pipeline (No Server Restart)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {camConfig.map(({ key, label, camId, quad }) => {
            const d = directions[key] || {};
            const isGreen = d.signal_state === 'GREEN' || intersection.active_green === key;
            const rawSrc = d.source || '';
            const currentFilename = rawSrc.split(/[\\/]/).pop();
            const hasVideo = Boolean(currentFilename && currentFilename.trim() !== '' && d.connected);
            const isSwitching = switchingCamera[key];
            const isUploading = uploadingCamera[key];

            return (
              <div
                key={key}
                className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col justify-between gap-3 shadow-md hover:border-slate-700 transition-all"
              >
                {/* Header */}
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div>
                    <span className="text-[10px] font-mono text-cyan-400 font-bold block">{quad} · {camId}</span>
                    <h3 className="text-xs font-bold text-white">{label}</h3>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${hasVideo ? (isGreen ? 'bg-emerald-400 animate-pulse' : 'bg-red-400') : 'bg-slate-600'}`}></span>
                    <span className={`text-[10px] font-mono font-bold ${hasVideo ? (isGreen ? 'text-emerald-400' : 'text-red-400') : 'text-slate-500'}`}>
                      {hasVideo ? (isGreen ? 'GREEN' : 'RED') : 'UNASSIGNED'}
                    </span>
                  </div>
                </div>

                {/* Telemetry pill */}
                <div className="flex items-center justify-between text-[11px] font-mono bg-slate-950/60 p-2 rounded-lg border border-slate-800/80">
                  <span className="text-slate-400">Demand: <strong className="text-cyan-400">{d.pcu?.toFixed(1) || '0.0'} PCU</strong></span>
                  <span className="text-slate-400">Vehicles: <strong className="text-white">{d.total_vehicles || 0}</strong></span>
                </div>

                {/* Current Active Video */}
                <div>
                  <label className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
                    Active Video Source:
                  </label>
                  <div className={`text-[11px] font-mono truncate px-2 py-1.5 rounded border ${hasVideo ? 'text-cyan-300 bg-slate-950 border-slate-800' : 'text-amber-400/90 bg-amber-950/20 border-amber-900/40'}`}>
                    {hasVideo ? `🎬 ${currentFilename}` : '⚠️ No Video Assigned'}
                  </div>
                </div>

                {/* Dropdown Selector */}
                <div>
                  <label className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
                    Select Video from Library:
                  </label>
                  <select
                    disabled={isSwitching || isUploading}
                    value={availableVideos.find(v => v.filename === currentFilename)?.path || ''}
                    onChange={(e) => handleSwitchSource(key, e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono disabled:opacity-50"
                  >
                    <option value="">-- Choose Video to Place in {key} --</option>
                    {availableVideos.map((vid) => (
                      <option key={vid.filename} value={vid.path}>
                        {vid.filename} ({vid.size_mb} MB)
                      </option>
                    ))}
                  </select>
                </div>

                {/* File Upload Control */}
                <div>
                  <input
                    type="file"
                    ref={fileInputRefs[key]}
                    accept="video/mp4,video/x-m4v,video/*"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        handleUploadSource(key, e.target.files[0]);
                        e.target.value = '';
                      }
                    }}
                  />
                  <button
                    disabled={isSwitching || isUploading}
                    onClick={() => fileInputRefs[key].current?.click()}
                    className="w-full py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                  >
                    <span className="material-symbols-outlined text-[15px]">upload_file</span>
                    <span>{isUploading ? 'Uploading Clip...' : isSwitching ? 'Switching...' : 'Upload Video to Camera'}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. Central Intersection Visualizer & Webster Controller Reasoning */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Top-Down Intersection Visualizer */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="material-symbols-outlined text-cyan-400 text-base">hub</span>
              Junction Geometry
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              4-LEG JUNCTION
            </span>
          </div>

          {/* Top-Down Schematic */}
          <div className="relative w-full aspect-square max-w-[260px] mx-auto bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-center p-4">
            {/* Cross Roads */}
            <div className="absolute w-12 h-full bg-slate-800/80"></div>
            <div className="absolute h-12 w-full bg-slate-800/80"></div>

            {/* Center Junction Box */}
            <div className="relative z-10 w-16 h-16 rounded-xl bg-slate-900 border-2 border-slate-700 flex flex-col items-center justify-center shadow-lg">
              <span className="text-[9px] font-mono text-slate-400">ACTIVE</span>
              <span className="text-xs font-black text-emerald-400 font-headline">
                {intersection.active_green.slice(0, 1)}
              </span>
              <span className="text-[9px] font-mono text-white font-bold">{Math.round(intersection.time_remaining)}s</span>
            </div>

            {/* Approach Nodes */}
            <div className={`absolute top-2 left-1/2 -translate-x-1/2 px-2.5 py-1 rounded text-[10px] font-mono font-bold border ${directions.North?.signal_state === 'GREEN' || intersection.active_green === 'North' ? 'bg-emerald-950 text-emerald-400 border-emerald-500/50' : 'bg-red-950 text-red-400 border-red-500/50'}`}>
              N · {directions.North?.pcu?.toFixed(1) || '5.5'} PCU
            </div>
            <div className={`absolute bottom-2 left-1/2 -translate-x-1/2 px-2.5 py-1 rounded text-[10px] font-mono font-bold border ${directions.South?.signal_state === 'GREEN' || intersection.active_green === 'South' ? 'bg-emerald-950 text-emerald-400 border-emerald-500/50' : 'bg-red-950 text-red-400 border-red-500/50'}`}>
              S · {directions.South?.pcu?.toFixed(1) || '7.0'} PCU
            </div>
            <div className={`absolute left-2 top-1/2 -translate-y-1/2 px-2 py-1 rounded text-[10px] font-mono font-bold border ${directions.West?.signal_state === 'GREEN' || intersection.active_green === 'West' ? 'bg-emerald-950 text-emerald-400 border-emerald-500/50' : 'bg-red-950 text-red-400 border-red-500/50'}`}>
              W · {directions.West?.pcu?.toFixed(1) || '4.0'}
            </div>
            <div className={`absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 rounded text-[10px] font-mono font-bold border ${directions.East?.signal_state === 'GREEN' || intersection.active_green === 'East' ? 'bg-emerald-950 text-emerald-400 border-emerald-500/50' : 'bg-red-950 text-red-400 border-red-500/50'}`}>
              E · {directions.East?.pcu?.toFixed(1) || '5.5'}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-center">
            <span className="text-[11px] font-mono text-slate-400">
              Next Scheduled Phase: <strong className="text-white">{intersection.next_direction}</strong>
            </span>
          </div>
        </div>

        {/* Webster Controller Decision & Diagnostics */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-indigo-400 text-base">psychology</span>
                Adaptive ATSC Optimization Logic (Density-Proportional Webster)
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                {intersection.mode}
              </span>
            </div>

            {/* Decision Narrative */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 mb-4">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1 font-bold">
                Controller Phase Allocation Rationale:
              </span>
              <p className="text-xs text-slate-200 font-mono leading-relaxed">
                {intersection.decision_reason}
              </p>
            </div>

            {/* Direction Cards Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
              {['North', 'South', 'East', 'West'].map((app) => {
                const d = directions[app] || {};
                const isGreen = d.signal_state === 'GREEN' || intersection.active_green === app;
                return (
                  <div key={app} className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-white">{app}</span>
                      <span className={`w-2 h-2 rounded-full ${isGreen ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
                    </div>
                    <div className="text-base font-bold text-cyan-400 font-mono">
                      {d.pcu?.toFixed(1) || '0.0'} <span className="text-[10px] text-slate-400 font-normal">PCU</span>
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono mt-1">
                      {d.total_vehicles || 0} Veh · {d.density_score || 0}% Occ
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Interactive Controller Overrides */}
          <div className="pt-3 border-t border-slate-800">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-2 font-semibold">
              Live Controller Actions & Benchmarks
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                onClick={() => handleManualOverride('North')}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
              >
                Force North (30s)
              </button>
              <button
                onClick={() => handleManualOverride('South')}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
              >
                Force South (30s)
              </button>
              <button
                onClick={() => handleTriggerEmergency(intersection.active_green)}
                className="px-2.5 py-1.5 rounded-lg bg-red-950 text-red-300 hover:bg-red-900 text-xs font-medium border border-red-500/40"
              >
                Trigger EVP Hold
              </button>
              <button
                onClick={handleSirenTest}
                className="px-2.5 py-1.5 rounded-lg bg-purple-950 text-purple-300 hover:bg-purple-900 text-xs font-medium border border-purple-500/40"
              >
                Acoustic Siren FFT
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
