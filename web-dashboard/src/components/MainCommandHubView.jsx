import React, { useState, useEffect } from 'react';

export default function MainCommandHubView({
  onSwitchView,
  metrics = {},
  signals = {},
  emergencyActive = false,
  onTriggerEmergency,
}) {
  const [healthData, setHealthData] = useState(null);
  const [accidents, setAccidents] = useState([]);
  const [fourWayState, setFourWayState] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);

  const currentLane = signals.current_lane || fourWayState?.intersection?.active_green || 'North';
  const timeLeft = Math.max(0, Math.round(signals.time_left ?? fourWayState?.intersection?.time_remaining ?? 15));
  const totalVehicles = metrics.total_vehicles ?? 16;
  const totalPcu = typeof metrics.total_pcu === 'number' ? metrics.total_pcu.toFixed(1) : '22.0';

  useEffect(() => {
    let isMounted = true;

    const fetchDashboardData = async () => {
      try {
        const [healthRes, accRes, fourRes] = await Promise.all([
          fetch('/api/system/health').catch(() => null),
          fetch('/api/accidents?limit=5').catch(() => null),
          fetch('/api/four-way/state').catch(() => null),
        ]);

        if (healthRes && healthRes.ok && isMounted) {
          const h = await healthRes.json();
          setHealthData(h);
        }
        if (accRes && accRes.ok && isMounted) {
          const a = await accRes.json();
          setAccidents(a || []);
        }
        if (fourRes && fourRes.ok && isMounted) {
          const f = await fourRes.json();
          setFourWayState(f);
        }
      } catch (err) {
        console.debug('Dashboard data fetch error', err);
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const triggerAction = (msg) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 3500);
  };

  const handleAmbulance = async (lane) => {
    if (onTriggerEmergency) {
      onTriggerEmergency(lane);
      triggerAction(`🚑 Emergency Vehicle Priority preemption commanded for ${lane} approach!`);
    }
  };

  const handleClearEmergency = async () => {
    try {
      await fetch('/api/clear-emergency', { method: 'POST' });
      triggerAction('✓ Emergency hold cleared. Returning to Webster adaptive cycles.');
    } catch {
      triggerAction('Failed to clear emergency.');
    }
  };

  const laneData = [
    { name: 'North', count: fourWayState?.directions?.North?.total_vehicles ?? 4, pcu: fourWayState?.directions?.North?.pcu ?? 5.5, signal: fourWayState?.directions?.North?.signal_state || (currentLane === 'North' ? 'GREEN' : 'RED') },
    { name: 'South', count: fourWayState?.directions?.South?.total_vehicles ?? 5, pcu: fourWayState?.directions?.South?.pcu ?? 7.0, signal: fourWayState?.directions?.South?.signal_state || (currentLane === 'South' ? 'GREEN' : 'RED') },
    { name: 'East',  count: fourWayState?.directions?.East?.total_vehicles ?? 4,  pcu: fourWayState?.directions?.East?.pcu ?? 5.5,  signal: fourWayState?.directions?.East?.signal_state || (currentLane === 'East' ? 'GREEN' : 'RED') },
    { name: 'West',  count: fourWayState?.directions?.West?.total_vehicles ?? 3,  pcu: fourWayState?.directions?.West?.pcu ?? 4.0,  signal: fourWayState?.directions?.West?.signal_state || (currentLane === 'West' ? 'GREEN' : 'RED') },
  ];

  const activeAccidentsCount = accidents.filter((a) => a.status === 'new').length;

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* Action Notification Banner */}
      {actionNotice && (
        <div className="p-3 rounded-xl bg-cyan-950/80 border border-cyan-500/50 text-white flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2 font-mono text-xs font-bold text-cyan-300">
            <span className="material-symbols-outlined text-base">info</span>
            <span>{actionNotice}</span>
          </div>
          <button onClick={() => setActionNotice(null)} className="text-slate-400 hover:text-white">
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      )}

      {/* 1. Header Overview Banner */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
              System Online · Intelligent Traffic Management
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            VIGIL Operations Command Center
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Real-time Indian traffic density monitoring, Webster ATSC signal optimization, and persistent forensic accident triage.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => onSwitchView('single-camera')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all"
          >
            <span className="material-symbols-outlined text-base text-cyan-400">videocam</span>
            <span>Single Cam</span>
          </button>

          <button
            onClick={() => onSwitchView('four-way')}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/40 text-xs font-semibold shadow-sm transition-all"
          >
            <span className="material-symbols-outlined text-base">grid_view</span>
            <span>4-Way ATSC</span>
          </button>

          <button
            onClick={() => onSwitchView('ip-webcam')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all"
          >
            <span className="material-symbols-outlined text-base text-teal-400">linked_camera</span>
            <span>IP Webcam</span>
          </button>
        </div>
      </section>

      {/* 2. Key Operational Telemetry KPI Cards */}
      <section className="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* Backend & DB Health */}
        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">System State</span>
            <span className="material-symbols-outlined text-emerald-400 text-base">check_circle</span>
          </div>
          <div className="text-xl font-bold text-white">
            {healthData ? (healthData.status === 'healthy' ? 'OPTIMAL' : 'DEGRADED') : 'ONLINE'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1 flex justify-between">
            <span>DB: {healthData?.database?.type || 'SQLite'}</span>
            <span className="text-emerald-400">Synced</span>
          </div>
        </div>

        {/* Configured Camera Count */}
        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Cameras Configured</span>
            <span className="material-symbols-outlined text-cyan-400 text-base">video_camera_front</span>
          </div>
          <div className="text-xl font-bold text-white">
            {healthData?.database?.total_cameras ?? 4} <span className="text-xs font-normal text-slate-400">Sources</span>
          </div>
          <div className="text-[10px] text-cyan-400 font-mono mt-1">
            4-Way Junction Array
          </div>
        </div>

        {/* Active Accident Incidents */}
        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Active Accidents</span>
            <span className="material-symbols-outlined text-red-400 text-base">car_crash</span>
          </div>
          <div className="text-xl font-bold text-red-400">
            {activeAccidentsCount} <span className="text-xs font-normal text-slate-400">Unresolved</span>
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">
            {accidents.length} total logged in DB
          </div>
        </div>

        {/* Emergency Vehicle Priority Status */}
        <div className={`p-4 rounded-xl border flex flex-col justify-between ${emergencyActive ? 'bg-red-950/40 border-red-500/60' : 'bg-[#0D1424] border-slate-800'}`}>
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Emergency Preemption</span>
            <span className={`material-symbols-outlined text-base ${emergencyActive ? 'text-red-400 animate-pulse' : 'text-amber-400'}`}>emergency</span>
          </div>
          <div className={`text-xl font-bold ${emergencyActive ? 'text-red-400' : 'text-slate-300'}`}>
            {emergencyActive ? 'PREEMPTED' : 'STANDBY'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">
            {emergencyActive ? `Priority Corridor on ${currentLane}` : 'No active preemption'}
          </div>
        </div>

        {/* Total Intersection Demand */}
        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-mono uppercase tracking-wider">Intersection Demand</span>
            <span className="material-symbols-outlined text-indigo-400 text-base">speed</span>
          </div>
          <div className="text-xl font-bold text-white">
            {totalPcu} <span className="text-xs font-normal text-slate-400">PCU</span>
          </div>
          <div className="text-[10px] text-indigo-400 font-mono mt-1">
            {totalVehicles} Vehicles Tracked
          </div>
        </div>
      </section>

      {/* 3. Central Operational Section: Intersection Visualizer + Directional Congestion */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Active Signal & Webster Controller Status */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-cyan-400 text-base">traffic</span>
                Signal Controller Status
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
                {fourWayState?.intersection?.mode || 'Adaptive Webster ATSC'}
              </span>
            </div>

            {/* Signal Phase Display */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900 border border-slate-800 mb-4">
              <div>
                <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Current Green Phase</span>
                <span className="text-2xl font-black text-emerald-400 font-headline">
                  {currentLane.toUpperCase()} APPROACH
                </span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Next Scheduled: <strong className="text-slate-300">{fourWayState?.intersection?.next_direction || 'South'}</strong>
                </span>
              </div>
              <div className="text-right">
                <span className="text-3xl font-black font-mono text-white block">
                  {timeLeft}s
                </span>
                <span className="text-[10px] font-mono text-slate-500 uppercase">Remaining</span>
              </div>
            </div>

            {/* ATSC Decision Reason */}
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 mb-4 text-xs text-slate-300 font-mono">
              <span className="text-cyan-400 font-bold block mb-1">DECISION LOGIC:</span>
              {fourWayState?.intersection?.decision_reason || `Phase allocated to ${currentLane} based on Webster saturation flow calculations and PCU queue load.`}
            </div>
          </div>

          {/* Quick Preemption Actions */}
          <div className="pt-3 border-t border-slate-800">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-2 font-semibold">
              Operator Priority Override
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleAmbulance(currentLane)}
                className="px-3 py-2 rounded-lg bg-red-950/60 hover:bg-red-900/60 text-red-300 border border-red-500/40 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
              >
                <span>🚑</span> Trigger EVP
              </button>
              <button
                onClick={handleClearEmergency}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
              >
                <span className="material-symbols-outlined text-sm">restart_alt</span> Reset ATSC
              </button>
            </div>
          </div>
        </div>

        {/* Right: Approach Breakdown (2 Columns) */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="material-symbols-outlined text-indigo-400 text-base">alt_route</span>
              Directional Congestion & Signal Phase
            </h2>
            <span className="text-xs text-slate-400">Junction 04 Corridors</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {laneData.map((lane) => {
              const isGreen = lane.signal === 'GREEN' || currentLane === lane.name;
              return (
                <div
                  key={lane.name}
                  className={`p-4 rounded-xl border transition-all ${
                    isGreen
                      ? 'bg-emerald-950/20 border-emerald-500/50 shadow-sm shadow-emerald-950'
                      : 'bg-slate-900 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-bold text-white">{lane.name} Approach</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                        isGreen
                          ? 'bg-emerald-950 text-emerald-400 border-emerald-500/50'
                          : 'bg-red-950 text-red-400 border-red-500/50'
                      }`}
                    >
                      {isGreen ? 'GREEN PHASE' : 'RED PHASE'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-400 font-mono block">Vehicles</span>
                      <span className="text-base font-bold text-white">{lane.count}</span>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-400 font-mono block">PCU Demand</span>
                      <span className="text-base font-bold text-cyan-400">{lane.pcu.toFixed(1)}</span>
                    </div>
                  </div>

                  {/* Congestion Bar */}
                  <div className="mt-3">
                    <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
                      <span>Density Index</span>
                      <span className="text-slate-300 font-bold">{Math.round((lane.pcu / 15.0) * 100)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          (lane.pcu / 15.0) > 0.7 ? 'bg-red-400' : (lane.pcu / 15.0) > 0.4 ? 'bg-amber-400' : 'bg-cyan-400'
                        }`}
                        style={{ width: `${Math.min(100, (lane.pcu / 15.0) * 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. Recent Persistent Accident Incidents */}
      <section className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-red-400 text-base">warning</span>
            <h2 className="text-sm font-bold text-white">Recent Accident & Collision Feed</h2>
          </div>
          <button
            onClick={() => onSwitchView('accidents')}
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
          >
            <span>Full Accident Triage</span>
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </button>
        </div>

        {accidents.length === 0 ? (
          <div className="p-8 text-center text-slate-500 font-mono text-xs">
            <span className="material-symbols-outlined text-3xl text-slate-600 block mb-2">verified_user</span>
            No unresolved accident incidents recorded in database. Roadways clear.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {accidents.slice(0, 3).map((inc) => (
              <div key={inc.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-500/40 font-bold uppercase">
                      {inc.incident_type || 'ACCIDENT'}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      {inc.time_str || new Date(inc.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 font-medium line-clamp-2 mb-2">
                    {inc.description}
                  </p>

                  <div className="text-[11px] text-slate-400 flex items-center gap-2">
                    <span>Approach: <strong className="text-slate-300">{inc.lane || 'North'}</strong></span>
                    <span>·</span>
                    <span>Status: <strong className={inc.status === 'resolved' ? 'text-emerald-400' : 'text-amber-400'}>{inc.status}</strong></span>
                  </div>
                </div>

                {inc.snapshot_b64 && (
                  <div className="mt-3 rounded-lg overflow-hidden border border-slate-800 h-24 bg-black">
                    <img
                      src={`data:image/jpeg;base64,${inc.snapshot_b64}`}
                      alt="Incident Snapshot"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
