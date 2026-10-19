import React, { useState, useEffect } from 'react';

export default function EmergencyResponseView({ signals, emergencyActive, onTriggerEmergency }) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedApproach, setSelectedApproach] = useState('North');
  const [overrideMsg, setOverrideMsg] = useState('');

  const fetchAmbulanceIncidents = async () => {
    try {
      const res = await fetch('/api/incidents');
      if (res.ok) {
        const data = await res.json();
        const evpOnly = (data || []).filter(
          (i) => (i.type || i.incident_type || '').toLowerCase() === 'ambulance'
        );
        setIncidents(evpOnly);
      }
    } catch (e) {
      console.error('Failed to fetch emergency incidents', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAmbulanceIncidents();
    const interval = setInterval(fetchAmbulanceIncidents, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleManualOverride = async (approach) => {
    try {
      if (onTriggerEmergency) {
        onTriggerEmergency(approach);
      } else {
        await fetch('/api/emergency', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lane: approach }),
        });
      }
      setOverrideMsg(`✓ Emergency green wave preemption triggered on ${approach} approach`);
      setTimeout(() => setOverrideMsg(''), 4000);
      fetchAmbulanceIncidents();
    } catch (e) {
      setOverrideMsg(`Override failed: ${e.message}`);
    }
  };

  const isPreempted = emergencyActive || signals?.emergency_active;
  const preemptedLane = signals?.emergency_lane || 'North';

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto text-slate-200 pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0a101f]/90 border border-cyan-500/15 rounded-2xl shadow-lg backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-600/30 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-inner">
            <span className="material-symbols-outlined text-[22px]">e911_emergency</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[16px] font-headline font-bold text-slate-100 uppercase tracking-wide">
                Emergency Vehicle Preemption (EVP) Console
              </h2>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border flex items-center gap-1 ${
                  isPreempted
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                    : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isPreempted ? 'bg-rose-400' : 'bg-emerald-400'}`}></span>
                {isPreempted ? `CORRIDOR ACTIVE: ${preemptedLane.toUpperCase()}` : 'EVP STANDBY (RADAR ARMED)'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Primary: Visual YOLOv8 Model &bull; Secondary: Acoustic Siren FFT &bull; Starvation Timer: 45s Max
            </p>
          </div>
        </div>

        {/* Model Transparency Tag */}
        <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-[10.5px] font-mono flex items-center gap-2">
          <span className="text-slate-400">CANDIDATE MODEL:</span>
          <span className="text-amber-400 font-bold">Candidate Not Trained (Download in progress)</span>
          <span className="text-slate-400">&bull; Active: models/best.pt</span>
        </div>
      </div>

      {overrideMsg && (
        <div className="p-3 rounded-xl bg-cyan-500/15 border border-cyan-500/40 text-cyan-300 text-[12px] font-mono font-semibold">
          {overrideMsg}
        </div>
      )}

      {/* Main Grid: Telemetry & Manual Override Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Preemption Status & Pipeline Architecture (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-purple-400 text-[18px]">
                  crisis_alert
                </span>
                <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
                  Dual-Tier Detection Pipeline Status
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400">SAE J2735 High Priority</span>
            </div>

            {/* Pipeline Comparison Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-[11px]">
              {/* Primary Visual Tier */}
              <div className="p-3.5 rounded-xl bg-[#0a101f]/80 border border-cyan-500/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-300 font-bold uppercase text-[10px]">
                    1. Visual Perception (Primary)
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[8.5px] bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                    ACTIVE BACKBONE
                  </span>
                </div>
                <div className="text-slate-200 text-[12px] font-bold">
                  YOLOv8 Detection Matrix
                </div>
                <p className="text-[10.5px] text-slate-400 font-sans leading-relaxed">
                  Scans optical feeds for vehicle bounding boxes matching emergency profile (flashing beacon, vehicle livery). Active weights: <code className="text-cyan-300">models/best.pt</code>.
                </p>
                <div className="pt-1 text-[9.5px] text-slate-400">
                  LATENCY: ~18ms &bull; IO: 4 Cameras
                </div>
              </div>

              {/* Secondary Acoustic Tier */}
              <div className="p-3.5 rounded-xl bg-[#0a101f]/80 border border-purple-500/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-purple-300 font-bold uppercase text-[10px]">
                    2. Acoustic Siren FFT (Fallback)
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[8.5px] bg-purple-500/20 text-purple-300 border border-purple-500/40">
                    SENSING FALLBACK
                  </span>
                </div>
                <div className="text-slate-200 text-[12px] font-bold">
                  Spectral Power Density Scanner
                </div>
                <p className="text-[10.5px] text-slate-400 font-sans leading-relaxed">
                  Performs STFT frequency analysis scanning 650–1750 Hz band for characteristic Doppler Yelp/Wail siren audio patterns when line-of-sight is obstructed.
                </p>
                <div className="pt-1 text-[9.5px] text-slate-400">
                  SAMPLE RATE: 44.1 kHz &bull; FFT SIZE: 2048
                </div>
              </div>
            </div>

            {/* Preemption Corridor Rules */}
            <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2 font-mono text-[11px]">
              <div className="text-slate-300 font-bold uppercase text-[10.5px]">
                Preemption Corridor Safe-Switch Rules
              </div>
              <div className="space-y-1.5 text-slate-300 font-sans text-[11px]">
                <div className="flex items-start gap-2">
                  <span className="text-cyan-400 font-mono font-bold">01.</span>
                  <span><strong>Immediate Yellow Clearance:</strong> Conflicting phases transition through mandatory 3.5s yellow + 1.0s all-red before corridor activation.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-cyan-400 font-mono font-bold">02.</span>
                  <span><strong>Pedestrian Hold:</strong> Crosswalk pedestrian phases are held red to ensure conflict-free corridor traversal.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-rose-400 font-mono font-bold">03.</span>
                  <span><strong>Starvation Safeguard:</strong> Preemption maximum dwell is hard-capped at 45 seconds to prevent cross-street vehicular starvation.</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Manual Operator Override & History (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Manual Approach Override Panel */}
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-rose-400 text-[18px]">
                  touch_app
                </span>
                <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
                  Manual Approach Preemption Override
                </span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
              Dispatch operators can manually grant preemptive green waves to any approach. Signal controllers will transition instantly through standard safety yellow clearance.
            </p>

            <div className="grid grid-cols-2 gap-2.5 font-mono text-[11px]">
              {['North', 'South', 'East', 'West'].map((app) => (
                <button
                  key={app}
                  onClick={() => handleManualOverride(app)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    isPreempted && preemptedLane.toLowerCase() === app.toLowerCase()
                      ? 'bg-rose-500/25 border-rose-500/60 text-rose-300 shadow-[0_0_15px_rgba(244,63,94,0.3)] ring-1 ring-rose-500'
                      : 'bg-slate-900/70 border-slate-800 hover:border-purple-500/40 hover:bg-[#0c1427] text-slate-200'
                  }`}
                >
                  <div className="text-[10px] text-slate-400 uppercase">APPROACH</div>
                  <div className="text-[14px] font-bold text-slate-100 mt-0.5">{app}</div>
                  <div className="text-[9px] text-cyan-400 mt-1">Force Preemption &rarr;</div>
                </button>
              ))}
            </div>
          </div>

          {/* Emergency Vehicle Incident Archive */}
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-cyan-500/10">
              <span className="text-[12px] font-bold text-slate-200 uppercase font-mono">
                Recent EVP Events ({incidents.length})
              </span>
              <span className="text-[10px] font-mono text-slate-400">Auto-Logged</span>
            </div>

            <div className="max-h-64 overflow-y-auto custom-scrollbar space-y-2">
              {loading && incidents.length === 0 ? (
                <div className="text-center py-6 text-slate-500 font-mono text-[11px]">
                  Loading EVP events...
                </div>
              ) : incidents.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-[11px]">
                  No emergency vehicle preemption events recorded.
                </div>
              ) : (
                incidents.map((inc) => (
                  <div
                    key={inc.id}
                    className="p-2.5 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-1 font-mono text-[11px]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-cyan-300 font-bold">[{inc.id}]</span>
                      <span className="text-slate-400 text-[10px]">
                        {new Date(inc.timestamp * 1000).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-slate-200 font-sans text-[11.5px]">
                      {inc.description}
                    </div>
                    <div className="flex items-center justify-between text-[9.5px] text-slate-400 pt-0.5">
                      <span>APPROACH: {inc.lane || 'North'}</span>
                      <span className="text-purple-400">PRIORITY CORRIDOR</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
