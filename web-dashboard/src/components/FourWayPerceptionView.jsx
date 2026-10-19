import React, { useState, useEffect } from 'react';

export default function FourWayPerceptionView({
  selectedIntersection,
  onSwitchView,
  signals,
  emergencyActive,
}) {
  const [showLiveStream, setShowLiveStream] = useState(true);
  const [phaseTimer, setPhaseTimer] = useState(16.2);
  const [frameNumber, setFrameNumber] = useState(184920);

  // Dynamic AI Filter Toggles
  const [filters, setFilters] = useState({
    boxes: true,
    vectors: true,
    footpath: true,
    plates: true,
    heatmap: true,
    medical: true,
  });

  // Action Toast Notification State
  const [toast, setToast] = useState({ show: false, text: '', icon: '', isError: false });

  const triggerToast = (text, icon, isError = false) => {
    setToast({ show: true, text, icon, isError });
    setTimeout(() => {
      setToast({ show: false, text: '', icon: '', isError: false });
    }, 4000);
  };

  useEffect(() => {
    const timer = setInterval(() => {
      setPhaseTimer((prev) => (prev <= 0.2 ? 24.0 : parseFloat((prev - 0.1).toFixed(1))));
    }, 100);
    const frameInterval = setInterval(() => {
      setFrameNumber((prev) => prev + 4);
    }, 66);
    return () => {
      clearInterval(timer);
      clearInterval(frameInterval);
    };
  }, []);

  const junctionNames = {
    j04: 'Junction 04: Grand Ave & 5th St',
    j05: 'Junction 05: Metro Blvd & 8th St',
    j02: 'Junction 02: Riverside & King Way',
    j07: 'Junction 07: Central Square Cross',
  };

  const currentJunctionTitle = junctionNames[selectedIntersection] || 'Junction 04: Grand Ave & 5th St';

  const emSource = signals?.emergency_source || '';
  const emLane = signals?.emergency_lane || 'North';

  const vehicleClasses = [
    { name: 'Car', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30', pcu: '1.0' },
    { name: 'Motorcycle', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30', pcu: '0.5' },
    { name: 'Bus', color: 'text-purple-400 bg-purple-500/10 border-purple-500/30', pcu: '3.0' },
    { name: 'Truck', color: 'text-orange-400 bg-orange-500/10 border-orange-500/30', pcu: '3.0' },
    { name: 'Ambulance', color: 'text-red-400 bg-red-500/20 border-red-500/60 shadow-glow animate-pulse font-bold', pcu: 'PRIORITY', icon: 'e911_emergency' },
    { name: 'Fire Truck', color: 'text-rose-400 bg-rose-500/20 border-rose-500/60 shadow-glow animate-pulse font-bold', pcu: 'PRIORITY', icon: 'local_fire_department' },
    { name: 'Pedestrian', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30', pcu: '0.1' },
  ];

  const approaches = [
    { id: 'north', name: 'North Approach', cam: 'CAM_NORTH_01', pos: 'top-3 left-3' },
    { id: 'south', name: 'South Approach', cam: 'CAM_SOUTH_01', pos: 'top-3 right-3' },
    { id: 'east', name: 'East Approach', cam: 'CAM_EAST_01', pos: 'bottom-3 left-3' },
    { id: 'west', name: 'West Approach', cam: 'CAM_WEST_01', pos: 'bottom-3 right-3' },
  ];

  return (
    <div className="flex flex-col w-full gap-space-md pb-space-xl">
      {/* 1. Operational Sub-Header Bar */}
      <section className="bg-surface-container-low/80 backdrop-blur-md rounded-xl p-space-md flex flex-col xl:flex-row xl:items-center xl:justify-between gap-space-md border border-outline-variant/30 shadow-md">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-space-sm">
            <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-mono text-[10px] uppercase tracking-wider font-bold border border-primary/20">
              Live Vision Matrix
            </span>
            <h1 className="font-headline text-[18px] text-on-surface font-bold tracking-tight">
              {currentJunctionTitle} — 4-Way Spatial Multi-Camera Perception
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-on-surface-variant font-mono text-[10px]">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
              <span>4 Synchronized RTSP Streams (North, South, East, West)</span>
            </span>
            <span className="text-outline/40">/</span>
            <span className="text-primary font-medium">YOLOv8 Emergency Model Active (11.4ms)</span>
            <span className="text-outline/40">/</span>
            <span className="text-on-surface font-bold">Kinematic Tracker + IoU Collision Anomaly</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-space-sm">
          {/* Active Phase Pill */}
          <div className="flex items-center gap-2 px-3 py-1 bg-secondary-container/20 rounded-lg text-secondary border border-secondary/30">
            <span className="material-symbols-outlined text-[18px] animate-spin" style={{ animationDuration: '9s' }}>
              sync
            </span>
            <div className="flex flex-col font-mono leading-tight">
              <span className="text-[9px] uppercase tracking-widest text-secondary/80 font-bold">Signal Phase</span>
              <span className="text-[11px] font-bold text-secondary flex items-center gap-1">
                Phase Active: {signals?.current_lane || 'North'} Approach
                <span className="text-[12px] text-primary">({phaseTimer}s)</span>
              </span>
            </div>
          </div>

          {/* Toggle Live Feed vs Graphic Canvas */}
          <button
            onClick={() => setShowLiveStream(!showLiveStream)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-[11px] font-bold transition-all border ${
              showLiveStream
                ? 'bg-secondary/20 text-secondary border-secondary/40'
                : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface border-outline-variant/30'
            }`}
            title="Toggle Live Camera Stream from Engine"
          >
            <span className="material-symbols-outlined text-[16px]">
              {showLiveStream ? 'videocam' : 'visibility'}
            </span>
            <span>{showLiveStream ? 'Live Video Mode' : 'AI HUD Matrix'}</span>
          </button>

          {/* Buffer Frame Counter */}
          <div className="hidden sm:flex flex-col items-end px-3 py-1 bg-surface-container rounded-lg border border-outline-variant/20 font-mono">
            <span className="text-[9px] text-on-surface-variant font-semibold">BUFFER SYNC</span>
            <span className="text-[11px] text-primary font-bold tracking-wider">
              FRAME #{frameNumber.toLocaleString()}
            </span>
          </div>
        </div>
      </section>

      {/* 2. Vehicle Class Pills & Emergency Recognition Legend */}
      <section className="bg-surface-container-low/70 backdrop-blur-md rounded-xl p-space-sm border border-white/5 flex flex-wrap items-center justify-between gap-space-sm shadow-sm font-mono text-[11px]">
        <div className="flex items-center gap-2 text-on-surface-variant uppercase text-[10px] font-bold tracking-wider">
          <span className="material-symbols-outlined text-primary text-[16px]">category</span>
          <span>Target Classification Schema:</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {vehicleClasses.map((vc) => (
            <span
              key={vc.name}
              className={`px-2.5 py-1 rounded-lg border flex items-center gap-1.5 ${vc.color}`}
            >
              {vc.icon && <span className="material-symbols-outlined text-[13px]">{vc.icon}</span>}
              <span>{vc.name}</span>
              <span className="opacity-70 text-[9px]">({vc.pcu})</span>
            </span>
          ))}
        </div>
      </section>

      {/* 3. Live Stream Full Panel with Tactical Corner Brackets & Approach Overlays */}
      {showLiveStream && (
        <section className="bg-surface-container-lowest rounded-xl overflow-hidden border border-primary/40 shadow-2xl relative">
          {/* Header Bar */}
          <div className="p-space-sm bg-surface-container-low flex items-center justify-between border-b border-outline-variant/20 font-mono text-[11px]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
              <span className="text-on-surface font-bold">4-WAY MULTI-PERSPECTIVE COMPOSITE FEED</span>
            </div>
            <div className="flex items-center gap-3">
              {emergencyActive && (
                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-error/20 text-error border border-error/40 font-bold animate-pulse">
                  <span className="material-symbols-outlined text-[14px]">e911_emergency</span>
                  <span>EVP CORRIDOR ACTIVE: {emLane.toUpperCase()}</span>
                </div>
              )}
              <span className="text-secondary">Hardware Accelerated · 30 FPS Stream</span>
            </div>
          </div>

          {/* Video Container with Tactical HUD Brackets */}
          <div className="w-full max-h-[580px] bg-black flex items-center justify-center relative overflow-hidden">
            {/* Tactical Corner Brackets */}
            <div className="absolute top-2 left-2 w-6 h-6 border-t-2 border-l-2 border-primary pointer-events-none z-10"></div>
            <div className="absolute top-2 right-2 w-6 h-6 border-t-2 border-r-2 border-primary pointer-events-none z-10"></div>
            <div className="absolute bottom-2 left-2 w-6 h-6 border-b-2 border-l-2 border-primary pointer-events-none z-10"></div>
            <div className="absolute bottom-2 right-2 w-6 h-6 border-b-2 border-r-2 border-primary pointer-events-none z-10"></div>

            {/* Approach Quadrant Corner Badges */}
            {approaches.map((app) => {
              const laneSig = signals?.signals?.[app.name.split(' ')[0]] || {};
              const state = laneSig.state || 'red';
              const isTargetEm = emergencyActive && emLane.toLowerCase() === app.name.split(' ')[0].toLowerCase();
              return (
                <div
                  key={app.id}
                  className={`absolute ${app.pos} z-10 pointer-events-none px-2.5 py-1 rounded-lg backdrop-blur-md font-mono text-[10px] border flex items-center gap-1.5 ${
                    isTargetEm
                      ? 'bg-red-950/80 text-red-200 border-red-500 shadow-glow animate-pulse'
                      : 'bg-black/70 text-on-surface border-white/10'
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      state === 'green'
                        ? 'bg-emerald-400 shadow-[0_0_8px_#10b981]'
                        : state === 'yellow'
                        ? 'bg-amber-400'
                        : 'bg-red-500'
                    }`}
                  ></span>
                  <span className="font-bold">{app.name}</span>
                  <span className="text-on-surface-variant">({app.cam})</span>
                </div>
              );
            })}

            {/* Live Composite Image */}
            <img
              src="/api/stream"
              alt="4-Way Composite Real-Time Live Feed"
              className="w-full max-h-[580px] object-contain"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.parentNode.innerHTML =
                  '<div class="text-on-surface-variant font-mono text-[13px] flex flex-col items-center gap-2 py-12"><span class="material-symbols-outlined text-[36px] text-primary">videocam_off</span><span>Backend stream active at /api/stream</span></div>';
              }}
            />
          </div>
        </section>
      )}

      {/* 4. Bottom Telemetry & Quick Action Command Dock */}
      <section className="bg-surface-container-low/90 backdrop-blur-md rounded-xl p-space-md flex flex-col xl:flex-row xl:items-center xl:justify-between gap-space-md border border-outline-variant/30 shadow-lg">
        {/* Dynamic AI Perception Filters & Toggles */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-1.5 text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">
            <span className="material-symbols-outlined text-primary text-[16px]">layers</span>
            <span>Active AI Perception Filters & Toggles</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: 'boxes', label: 'Vehicle Bounding Boxes' },
              { id: 'vectors', label: 'Speed & Trajectory Vectors' },
              { id: 'footpath', label: 'Crosswalk Conflict Zones' },
              { id: 'plates', label: 'License Plate Triggers' },
              { id: 'heatmap', label: 'Congestion Heatmap' },
              { id: 'medical', label: 'Emergency Vehicle Badges', highlight: true },
            ].map((f) => (
              <label
                key={f.id}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg cursor-pointer transition-colors border select-none font-mono text-[11px] ${
                  f.highlight
                    ? 'bg-tertiary-container/20 text-tertiary border-tertiary/40 font-bold'
                    : 'bg-surface-container-high/80 text-on-surface border-outline-variant/30 hover:bg-surface-container-highest'
                }`}
              >
                <input
                  type="checkbox"
                  checked={filters[f.id]}
                  onChange={(e) => setFilters({ ...filters, [f.id]: e.target.checked })}
                  className="w-3.5 h-3.5 rounded bg-surface text-primary focus:ring-0 cursor-pointer"
                />
                <span>{f.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Operational Triggers */}
        <div className="flex flex-wrap items-center gap-space-sm font-mono text-[12px]">
          <button
            onClick={() => {
              triggerToast('Frame Flagged: Traffic anomaly logged to Incident & Forensic Archive.', 'gavel', true);
              if (onSwitchView) {
                setTimeout(() => onSwitchView('incidents'), 1200);
              }
            }}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-error-container/40 hover:bg-error-container/60 text-error transition-all font-bold border border-error/40 shadow-sm"
          >
            <span className="material-symbols-outlined text-[18px]">gavel</span>
            <span>Flag Frame to Incident Archive</span>
          </button>

          <button
            onClick={() => triggerToast('Export Initiated: 4-Way Synchronized Video Clip Queued for Download.', 'download', false)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary hover:bg-primary-container text-on-primary font-bold transition-all shadow-md"
          >
            <span className="material-symbols-outlined text-[18px]">video_file</span>
            <span>Export 4-Cam Sync Clip (1080p60)</span>
          </button>
        </div>
      </section>

      {/* Floating Action Toast Notification */}
      {toast.show && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg bg-surface-container-highest text-on-surface shadow-2xl flex items-center gap-3 border border-outline-variant/40 animate-slideIn">
          <span className={`material-symbols-outlined text-[22px] ${toast.isError ? 'text-error' : 'text-secondary'}`}>
            {toast.icon}
          </span>
          <span className="font-mono text-[12px] font-semibold">{toast.text}</span>
        </div>
      )}
    </div>
  );
}
