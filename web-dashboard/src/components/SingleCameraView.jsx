import React, { useState, useEffect, useRef } from 'react';

export default function SingleCameraView() {
  const [videoList, setVideoList] = useState([]);
  const [selectedSource, setSelectedSource] = useState('assets/videos/north.mp4');
  const [status, setStatus] = useState('running'); // running, paused, stopped
  const [telemetry, setTelemetry] = useState({
    fps: 24.5,
    latency_ms: 42.0,
    vehicle_counts: {},
    total_vehicles: 0,
    density_score: 0,
    congestion_level: 'Low',
    model_name: 'best.pt',
    recent_events: [],
  });
  const [uploading, setUploading] = useState(false);
  const [uploadNotice, setUploadNotice] = useState(null);
  const fileInputRef = useRef(null);

  // Fetch available videos
  useEffect(() => {
    fetch('/api/videos')
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setVideoList(data);
        }
      })
      .catch(() => {});
  }, []);

  // Poll state every 1.5 seconds
  useEffect(() => {
    let isMounted = true;
    const fetchState = async () => {
      try {
        const res = await fetch('/api/single-camera/state');
        if (res.ok && isMounted) {
          const data = await res.json();
          if (data.status) setStatus(data.status);
          if (data.source) setSelectedSource(data.source);
          setTelemetry(data);
        }
      } catch (e) {
        console.debug('Error polling single camera state', e);
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 1500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSelectSource = async (newSource) => {
    setSelectedSource(newSource);
    try {
      await fetch('/api/single-camera/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: newSource }),
      });
      setStatus('running');
    } catch (e) {
      console.error('Failed to select single camera source', e);
    }
  };

  const handleControl = async (action) => {
    try {
      const res = await fetch('/api/single-camera/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        const data = await res.json();
        setStatus(data.status);
      }
    } catch (e) {
      console.error('Failed to send control command', e);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadNotice(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/single-camera/upload', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedSource(data.path);
        setStatus('running');
        setUploadNotice(`✓ Successfully uploaded and selected ${file.name}`);
        // Refresh video list
        fetch('/api/videos')
          .then((r) => r.json())
          .then((d) => setVideoList(d));
      } else {
        setUploadNotice('Upload failed. Please check file format.');
      }
    } catch {
      setUploadNotice('Upload request error.');
    } finally {
      setUploading(false);
      setTimeout(() => setUploadNotice(null), 4000);
    }
  };

  const classBadges = [
    { label: 'Cars', key: 'car', icon: 'directions_car' },
    { label: 'Motorcycles', key: 'motorcycle', icon: 'two_wheeler' },
    { label: 'Buses', key: 'bus', icon: 'directions_bus' },
    { label: 'Trucks', key: 'truck', icon: 'local_shipping' },
    { label: 'Auto-Rickshaws', key: 'auto', icon: 'electric_rickshaw' },
    { label: 'Ambulances', key: 'ambulance', icon: 'emergency' },
  ];

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* 1. Header Toolbar */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2.5 h-2.5 rounded-full ${status === 'running' ? 'bg-cyan-400 animate-pulse' : 'bg-amber-400'}`}></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
              Single-Camera Perception Pipeline
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Targeted Corridor Inspection
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Dedicated high-resolution inference stream with multi-class vehicle detection, tracking IDs, and density metrics.
          </p>
        </div>

        {/* Video Source Selector & Upload */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <select
            value={selectedSource}
            onChange={(e) => handleSelectSource(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-xl px-3 py-2 font-mono focus:outline-none focus:border-cyan-500"
          >
            {videoList.map((v) => (
              <option key={v.path} value={v.path}>
                {v.filename} ({v.size_mb} MB)
              </option>
            ))}
            <option value="0">Webcam (Device 0)</option>
          </select>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="video/mp4,video/avi,video/mov"
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all"
          >
            <span className="material-symbols-outlined text-base text-cyan-400">upload_file</span>
            <span>{uploading ? 'Uploading...' : 'Upload Video'}</span>
          </button>
        </div>
      </section>

      {/* Upload Notification */}
      {uploadNotice && (
        <div className="p-3 rounded-xl bg-cyan-950/80 border border-cyan-500/50 text-white flex items-center justify-between text-xs font-mono">
          <span>{uploadNotice}</span>
          <button onClick={() => setUploadNotice(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* 2. Main Video Feed & Telemetry Grid */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Video Canvas (2 Cols) */}
        <div className="lg:col-span-2 rounded-2xl bg-[#0D1424] border border-slate-800 overflow-hidden flex flex-col">
          {/* Stream Header & Controls */}
          <div className="px-4 py-3 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2 font-mono text-xs">
              <span className="font-bold text-white uppercase">{selectedSource.split('/').pop()}</span>
              <span className="text-slate-400">·</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${status === 'running' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40' : 'bg-amber-950 text-amber-400 border border-amber-500/40'}`}>
                {status.toUpperCase()}
              </span>
            </div>

            {/* Playback Controls */}
            <div className="flex items-center gap-1.5">
              {status !== 'running' ? (
                <button
                  onClick={() => handleControl('start')}
                  className="px-2.5 py-1 rounded-lg bg-emerald-950 text-emerald-300 hover:bg-emerald-900 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-sm">play_arrow</span> Start
                </button>
              ) : (
                <button
                  onClick={() => handleControl('pause')}
                  className="px-2.5 py-1 rounded-lg bg-amber-950 text-amber-300 hover:bg-amber-900 border border-amber-500/40 text-xs font-semibold flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-sm">pause</span> Pause
                </button>
              )}
              <button
                onClick={() => handleControl('stop')}
                className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 text-xs font-semibold flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-sm">stop</span> Stop
              </button>
            </div>
          </div>

          {/* Video Stream Viewer */}
          <div className="relative bg-black flex items-center justify-center min-h-[420px] aspect-video">
            {status === 'running' ? (
              <img
                src="/api/single-camera/stream"
                alt="Single Camera Live Inference Feed"
                className="w-full h-full object-contain"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            ) : (
              <div className="text-center p-8">
                <span className="material-symbols-outlined text-5xl text-slate-600 block mb-3">videocam_off</span>
                <p className="text-slate-300 text-sm font-semibold mb-1">Camera Stream Standby</p>
                <p className="text-slate-500 text-xs font-mono mb-4">Click Start to initiate real-time AI perception</p>
                <button
                  onClick={() => handleControl('start')}
                  className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shadow-md transition-all inline-flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-sm">play_arrow</span> Start Perception
                </button>
              </div>
            )}

            {/* Live Watermark / HUD */}
            <div className="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-sm px-2.5 py-1 rounded border border-slate-700 text-[10px] font-mono text-cyan-300">
              AI OVERLAY ACTIVE · PCU WEIGHTED
            </div>
          </div>
        </div>

        {/* Right: Live Telemetry & Detection Matrix */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-cyan-400 text-base">analytics</span>
                Stream Telemetry
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {telemetry.model_name || 'best.pt'}
              </span>
            </div>

            {/* Inference Stats */}
            <div className="grid grid-cols-2 gap-2.5 mb-4">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Processing FPS</span>
                <span className="text-xl font-bold font-mono text-emerald-400">{telemetry.fps || 24.5}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Latency</span>
                <span className="text-xl font-bold font-mono text-cyan-400">{telemetry.latency_ms || 42.0} ms</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Total Vehicles</span>
                <span className="text-xl font-bold font-mono text-white">{telemetry.total_vehicles || 0}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Congestion</span>
                <span className={`text-xl font-bold font-mono ${telemetry.congestion_level === 'High' ? 'text-red-400' : telemetry.congestion_level === 'Medium' ? 'text-amber-400' : 'text-cyan-400'}`}>
                  {telemetry.congestion_level || 'Low'}
                </span>
              </div>
            </div>

            {/* Class Breakdown */}
            <h3 className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider mb-2">
              Detected Classes
            </h3>
            <div className="space-y-1.5 mb-5">
              {classBadges.map((badge) => {
                const count = telemetry.vehicle_counts?.[badge.key] ?? 0;
                return (
                  <div
                    key={badge.key}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-900/70 border border-slate-800/80 text-xs"
                  >
                    <div className="flex items-center gap-2 text-slate-300">
                      <span className="material-symbols-outlined text-sm text-cyan-400">{badge.icon}</span>
                      <span>{badge.label}</span>
                    </div>
                    <span className="font-mono font-bold text-white">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Density Indicator */}
          <div className="pt-3 border-t border-slate-800">
            <div className="flex justify-between text-xs font-mono text-slate-400 mb-1.5">
              <span>Road Density Score</span>
              <span className="text-cyan-400 font-bold">{Math.round(telemetry.density_score || 0)} / 100</span>
            </div>
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, telemetry.density_score || 0)}%` }}
              ></div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
