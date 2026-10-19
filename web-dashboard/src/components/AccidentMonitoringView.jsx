import React, { useState, useEffect } from 'react';

export default function AccidentMonitoringView() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLane, setSelectedLane] = useState('North');
  const [simulating, setSimulating] = useState(false);
  const [msg, setMsg] = useState('');

  const fetchAccidents = async () => {
    try {
      const res = await fetch('/api/incidents');
      if (res.ok) {
        const data = await res.json();
        const accs = (data || []).filter(
          (i) => (i.type || i.incident_type || '').toLowerCase() === 'accident'
        );
        setIncidents(accs);
      }
    } catch (e) {
      console.error('Failed to fetch accident records', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccidents();
    const interval = setInterval(fetchAccidents, 4000);
    return () => clearInterval(interval);
  }, []);

  const triggerAccidentSimulation = async () => {
    setSimulating(true);
    try {
      const res = await fetch('/api/simulate-incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'accident', lane: selectedLane }),
      });
      if (res.ok) {
        setMsg(`🚨 Crash incident simulated on ${selectedLane} approach!`);
        setTimeout(() => setMsg(''), 4000);
        fetchAccidents();
      }
    } catch (e) {
      setMsg(`Simulation failed: ${e.message}`);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto text-slate-200 pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0a101f]/90 border border-cyan-500/15 rounded-2xl shadow-lg backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500/20 to-orange-600/30 border border-rose-500/30 flex items-center justify-center text-rose-400 shadow-inner">
            <span className="material-symbols-outlined text-[22px]">car_crash</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[16px] font-headline font-bold text-slate-100 uppercase tracking-wide">
                Kinematic Collision & Accident Monitoring
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
                {incidents.length} Collisions Recorded
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Kinematic Physics Invariants &bull; 2-Phase Post-Impact Dwell &bull; Zero Hallucination Standard
            </p>
          </div>
        </div>

        {/* Model Transparency Tag */}
        <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-[10.5px] font-mono flex items-center gap-2">
          <span className="text-slate-400">DETECTION MODE:</span>
          <span className="text-amber-400 font-bold">Kinematic Collision Invariants Active</span>
          <span className="text-slate-400">(Visual weights unconfigured fallback)</span>
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-[12px] font-mono font-semibold">
          {msg}
        </div>
      )}

      {/* Main Grid: Telemetry Meters & Event Records */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Physics Vector Monitors (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-rose-400 text-[18px]">
                  speed
                </span>
                <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
                  Collision Physics Verification Vectors
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400">3-Tier Fusion</span>
            </div>

            {/* Vector Meters */}
            <div className="space-y-3 font-mono text-[11px]">
              {/* Vector 1: Deceleration Anomaly */}
              <div className="p-3 rounded-xl bg-[#0a101f]/80 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-bold">Vector 1: Deceleration Spike Anomaly</span>
                  <span className="text-rose-400 font-bold">Threshold: ≥ 5.8 m/s² (18 px/s²)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="w-[78%] h-full bg-gradient-to-r from-amber-500 to-rose-500 rounded-full"></div>
                </div>
                <div className="text-[10px] text-slate-400 font-sans">
                  Detects anomalous velocity drop over adjacent frames (indicating physical collision or emergency braking).
                </div>
              </div>

              {/* Vector 2: Spatial IoU Overlap */}
              <div className="p-3 rounded-xl bg-[#0a101f]/80 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-bold">Vector 2: Bounding Box Spatial IoU Overlap</span>
                  <span className="text-amber-400 font-bold">Threshold: ≥ 0.18 IoU</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="w-[62%] h-full bg-gradient-to-r from-cyan-500 to-amber-500 rounded-full"></div>
                </div>
                <div className="text-[10px] text-slate-400 font-sans">
                  Quantifies trajectory intersection and spatial bounding volume intersection between adjacent vehicle targets.
                </div>
              </div>

              {/* Vector 3: Post-Impact Dwell Timer */}
              <div className="p-3 rounded-xl bg-[#0a101f]/80 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-bold">Vector 3: Post-Impact Stationary Dwell</span>
                  <span className="text-emerald-400 font-bold">Threshold: ≥ 15.0s</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="w-[85%] h-full bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full"></div>
                </div>
                <div className="text-[10px] text-slate-400 font-sans">
                  Prevents false positives from brief close calls by verifying vehicle remains immobilized after deceleration spike.
                </div>
              </div>
            </div>

            {/* Simulation Trigger */}
            <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-slate-400 uppercase font-bold">Approach:</span>
                <select
                  value={selectedLane}
                  onChange={(e) => setSelectedLane(e.target.value)}
                  className="px-2.5 py-1 rounded-lg bg-black/60 border border-slate-700 text-cyan-300 text-[11px] font-mono font-bold outline-none"
                >
                  <option value="North">North Approach</option>
                  <option value="South">South Approach</option>
                  <option value="East">East Approach</option>
                  <option value="West">West Approach</option>
                </select>
              </div>

              <button
                onClick={triggerAccidentSimulation}
                disabled={simulating}
                className="px-3.5 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-[11px] font-mono font-bold transition-colors flex items-center gap-1.5"
              >
                <span>💥</span>
                {simulating ? 'Injecting...' : 'Inject Test Collision'}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Collision Incident Records (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-cyan-500/10">
              <span className="text-[12px] font-bold text-slate-200 uppercase font-mono">
                Captured Collision Incidents ({incidents.length})
              </span>
              <span className="text-[10px] font-mono text-slate-400">SQLite Synced</span>
            </div>

            <div className="max-h-[500px] overflow-y-auto custom-scrollbar space-y-2.5">
              {loading && incidents.length === 0 ? (
                <div className="text-center py-12 text-slate-500 font-mono text-[11px]">
                  Loading accident telemetry records...
                </div>
              ) : incidents.length === 0 ? (
                <div className="text-center py-12 text-slate-500 text-[12px] space-y-1">
                  <div className="text-[32px]">🛡️</div>
                  <div className="font-semibold text-slate-400">Zero Active Collisions</div>
                  <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                    No collisions detected. You can inject a test accident scenario using the controls on the left.
                  </p>
                </div>
              ) : (
                incidents.map((acc) => (
                  <div
                    key={acc.id}
                    className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-2 font-mono text-[11px]"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-rose-400 font-bold">[{acc.id}]</span>
                        <span className="px-1.5 py-0.5 rounded text-[8.5px] bg-rose-500/20 text-rose-300 border border-rose-500/40 uppercase font-bold">
                          {acc.severity || 'critical'}
                        </span>
                      </div>
                      <span className="text-slate-400 text-[10px]">
                        {new Date(acc.timestamp * 1000).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="text-slate-200 font-sans text-[12px] leading-relaxed">
                      {acc.description}
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800/80 text-[10px] text-slate-400">
                      <div>APPROACH: <span className="text-slate-200 font-bold">{acc.lane || 'North'}</span></div>
                      <div>STATUS: <span className="text-cyan-300 font-bold uppercase">{acc.status || 'new'}</span></div>
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
