import React, { useState, useEffect } from 'react';

export default function IPWebcamView() {
  const [url, setUrl] = useState('http://192.168.1.100:8080/video');
  const [name, setName] = useState('North Junction IP Camera');
  const [direction, setDirection] = useState('North');
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [streamActive, setStreamActive] = useState(false);
  const [telemetry, setTelemetry] = useState({
    connected: false,
    status: 'stopped',
    fps: 0,
    latency_ms: 0,
    vehicle_counts: {},
    total_vehicles: 0,
    density_score: 0,
    emergency_detected: false,
    last_frame_time: null,
  });

  // Load saved config on mount
  useEffect(() => {
    fetch('/api/ip-webcam/config')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          if (data.raw_url) setUrl(data.raw_url);
          if (data.name) setName(data.name);
          if (data.direction) setDirection(data.direction);
          if (data.is_running) setStreamActive(true);
        }
      })
      .catch(() => {});
  }, []);

  // Poll state
  useEffect(() => {
    let isMounted = true;
    const fetchState = async () => {
      try {
        const res = await fetch('/api/ip-webcam/state');
        if (res.ok && isMounted) {
          const data = await res.json();
          setTelemetry(data);
          setStreamActive(data.connected);
        }
      } catch (e) {
        console.debug('Error polling IP webcam state', e);
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 1500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/ip-webcam/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({
        success: false,
        message: `Client request failed: ${e.message}`,
        latency_ms: 0,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveConfig = async () => {
    try {
      const res = await fetch('/api/ip-webcam/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, name, direction }),
      });
      if (res.ok) {
        alert('IP Webcam configuration saved successfully.');
      }
    } catch {
      alert('Failed to save configuration.');
    }
  };

  const handleStartStream = async () => {
    try {
      // First save config
      await fetch('/api/ip-webcam/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, name, direction }),
      });

      const res = await fetch('/api/ip-webcam/start', { method: 'POST' });
      if (res.ok) {
        setStreamActive(true);
      }
    } catch (e) {
      console.error('Failed to start IP webcam', e);
    }
  };

  const handleStopStream = async () => {
    try {
      const res = await fetch('/api/ip-webcam/stop', { method: 'POST' });
      if (res.ok) {
        setStreamActive(false);
      }
    } catch (e) {
      console.error('Failed to stop IP webcam', e);
    }
  };

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* 1. Header Toolbar */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2.5 h-2.5 rounded-full ${streamActive ? 'bg-teal-400 animate-pulse' : 'bg-slate-500'}`}></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-teal-400">
              Network Camera Interface
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            IP Webcam & RTSP Ingestion
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Support for Android IP Webcam apps, surveillance encoders, and RTSP/HTTP video streams with reachability verification.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <span className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold border ${streamActive ? 'bg-emerald-950 text-emerald-400 border-emerald-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'}`}>
            {streamActive ? 'STREAM ONLINE' : 'STREAM OFFLINE'}
          </span>
        </div>
      </section>

      {/* 2. Configuration & Reachability Testing */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: URL Configuration */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
          <h2 className="text-sm font-bold text-white flex items-center gap-2 pb-3 border-b border-slate-800 mb-4">
            <span className="material-symbols-outlined text-teal-400 text-base">settings_input_antenna</span>
            Camera Endpoint Configuration
          </h2>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-mono text-slate-300 block mb-1 font-semibold">
                Endpoint URL (HTTP MJPEG / RTSP)
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="e.g. http://192.168.1.100:8080/video or rtsp://camera-ip:554/live"
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-teal-500"
                />
                <button
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs transition-all flex items-center gap-1.5 shrink-0"
                >
                  <span className="material-symbols-outlined text-sm">{testing ? 'sync' : 'network_check'}</span>
                  <span>{testing ? 'Testing...' : 'Test Reachability'}</span>
                </button>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Tip: Works with Android IP Webcam app (default port 8080, e.g. <code className="text-teal-400">http://192.168.x.x:8080/video</code>).
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1 font-semibold">
                  Camera Identification Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1 font-semibold">
                  Assigned Intersection Approach
                </label>
                <select
                  value={direction}
                  onChange={(e) => setDirection(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-teal-500"
                >
                  <option value="North">North Approach</option>
                  <option value="South">South Approach</option>
                  <option value="East">East Approach</option>
                  <option value="West">West Approach</option>
                </select>
              </div>
            </div>

            {/* Test Connection Diagnostics Box */}
            {testResult && (
              <div
                className={`p-3.5 rounded-xl border text-xs font-mono ${
                  testResult.success
                    ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300'
                    : 'bg-red-950/40 border-red-500/50 text-red-300'
                }`}
              >
                <div className="flex items-center gap-2 font-bold mb-1">
                  <span className="material-symbols-outlined text-base">
                    {testResult.success ? 'check_circle' : 'error'}
                  </span>
                  <span>{testResult.success ? 'CONNECTION SUCCESSFUL' : 'CONNECTION FAILED'}</span>
                  {testResult.latency_ms > 0 && (
                    <span className="ml-auto text-[10px] text-slate-400">Latency: {testResult.latency_ms} ms</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-200">{testResult.message}</p>
                {testResult.status_code && (
                  <p className="text-[10px] text-slate-400 mt-1">HTTP Status: {testResult.status_code} · Type: {testResult.content_type || 'N/A'}</p>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
              <button
                onClick={handleSaveConfig}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Save Settings
              </button>

              <div className="flex gap-2">
                {!streamActive ? (
                  <button
                    onClick={handleStartStream}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md"
                  >
                    <span className="material-symbols-outlined text-sm">play_arrow</span>
                    Start Stream Processing
                  </button>
                ) : (
                  <button
                    onClick={handleStopStream}
                    className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md"
                  >
                    <span className="material-symbols-outlined text-sm">stop</span>
                    Stop Stream
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Stream Metrics Card */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2 pb-3 border-b border-slate-800 mb-4">
              <span className="material-symbols-outlined text-cyan-400 text-base">sensors</span>
              Feed Diagnostics
            </h2>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Stream Status:</span>
                <span className={`font-bold ${streamActive ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {streamActive ? 'ACTIVE' : 'IDLE'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Inference Rate:</span>
                <span className="font-bold text-white">{telemetry.fps || 0.0} FPS</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Inference Latency:</span>
                <span className="font-bold text-cyan-400">{telemetry.latency_ms || 0.0} ms</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Vehicles in Sight:</span>
                <span className="font-bold text-white">{telemetry.total_vehicles || 0}</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Density Score:</span>
                <span className="font-bold text-indigo-400">{Math.round(telemetry.density_score || 0)}%</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Emergency Detected:</span>
                <span className={`font-bold ${telemetry.emergency_detected ? 'text-red-400' : 'text-emerald-400'}`}>
                  {telemetry.emergency_detected ? 'YES (AMBULANCE)' : 'NO'}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 text-[11px] font-mono text-slate-500 text-center">
            Security: Credentials are automatically masked and encrypted.
          </div>
        </div>
      </section>

      {/* 3. Live IP Stream Display */}
      <section className="rounded-2xl bg-[#0D1424] border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-slate-300">
            <span className={streamActive ? 'text-emerald-400 font-bold' : 'text-slate-500'}>
              ● {streamActive ? 'LIVE IP STREAM' : 'FEED OFFLINE'}
            </span>
            <span>{name} ({direction} Approach)</span>
          </div>
          {telemetry.last_frame_time && (
            <span className="text-slate-400 text-[11px]">
              Last frame: {new Date(telemetry.last_frame_time * 1000).toLocaleTimeString()}
            </span>
          )}
        </div>

        <div className="relative bg-black flex items-center justify-center min-h-[420px] aspect-video">
          {streamActive ? (
            <img
              src="/api/ip-webcam/stream"
              alt="Live IP Webcam Feed"
              className="w-full h-full object-contain"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <div className="text-center p-8">
              <span className="material-symbols-outlined text-5xl text-slate-600 block mb-3">linked_camera</span>
              <p className="text-slate-300 text-sm font-semibold mb-1">IP Webcam Stream Offline</p>
              <p className="text-slate-500 text-xs font-mono mb-4">
                Verify device IP reachability using the tool above, then click Start Stream Processing.
              </p>
              <button
                onClick={handleStartStream}
                className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs inline-flex items-center gap-1.5 shadow-md"
              >
                <span className="material-symbols-outlined text-sm">play_arrow</span>
                Start Stream
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
