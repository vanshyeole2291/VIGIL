import React from 'react';

export default function MainCommandHubView({
  onSelectIntersection,
  onSwitchView,
  metrics,
  signals,
  emergencyActive,
  onTriggerEmergency,
}) {
  const handleInspect = (junctionId) => {
    if (onSelectIntersection) onSelectIntersection(junctionId);
    if (onSwitchView) onSwitchView('4-way-ai-perception');
  };

  const currentLane = signals?.current_lane || 'North';
  const emSource = signals?.emergency_source || '';
  const emLane = signals?.emergency_lane || currentLane;
  const websterCycle = signals?.webster_cycle_length ? Number(signals.webster_cycle_length).toFixed(1) : '68.4';
  const criticalFlow = signals?.critical_flow_ratio ? Number(signals.critical_flow_ratio).toFixed(2) : '0.54';
  const totalCycles = signals?.total_cycles || 0;
  const laneSplits = signals?.lane_green_splits || { North: 22.0, South: 18.0, East: 14.2, West: 14.2 };

  const lanes = ['North', 'South', 'East', 'West'];

  const junctions = [
    { id: 'j04', name: 'Grand Ave & 5th St', status: 'Normal', congestion: '32%', alert: emergencyActive },
    { id: 'j05', name: 'Metro Blvd & 8th St', status: 'Heavy Flow', congestion: '78%', alert: false },
    { id: 'j02', name: 'Riverside & King Way', status: 'Moderate', congestion: '45%', alert: false },
    { id: 'j07', name: 'Central Square Cross', status: 'Light', congestion: '12%', alert: false },
  ];

  return (
    <div className="flex flex-col w-full pb-space-xl gap-space-lg">
      
      {/* 1. Global System Telemetry Header with Emergency Preemption Source Pill */}
      <section className="bg-surface-container-low/70 backdrop-blur-2xl rounded-2xl p-space-md border border-white/5 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-space-md transition-all">
        <div className="flex flex-col">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse shadow-glow-success"></span>
            <span className="font-mono text-[11px] text-secondary font-bold uppercase tracking-widest">
              System Online
            </span>
            <span className="text-outline/40 font-mono text-[10px]">/</span>

            {/* Emergency Preemption Authority Badge */}
            {emergencyActive ? (
              emSource === 'visual' ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-error/20 text-error border border-error/50 animate-pulse shadow-glow">
                  <span className="material-symbols-outlined text-[16px]">visibility</span>
                  <span className="font-mono text-[11px] font-extrabold uppercase tracking-wider">
                    VISUAL PREEMPTION — PRIMARY (YOLOv8)
                  </span>
                  <span className="bg-error text-on-error font-mono text-[10px] px-1.5 py-0.2 rounded font-bold ml-1">
                    {emLane.toUpperCase()} APPROACH
                  </span>
                </div>
              ) : emSource === 'audio' ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/50 animate-pulse shadow-glow">
                  <span className="material-symbols-outlined text-[16px]">volume_up</span>
                  <span className="font-mono text-[11px] font-extrabold uppercase tracking-wider">
                    ACOUSTIC SIREN FFT — SECONDARY FALLBACK
                  </span>
                  <span className="bg-amber-500 text-black font-mono text-[10px] px-1.5 py-0.2 rounded font-bold ml-1">
                    {emLane.toUpperCase()} APPROACH
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-primary/20 text-primary border border-primary/50 animate-pulse shadow-glow">
                  <span className="material-symbols-outlined text-[16px]">e911_emergency</span>
                  <span className="font-mono text-[11px] font-extrabold uppercase tracking-wider">
                    MANUAL OVERRIDE PREEMPTION ACTIVE
                  </span>
                  <span className="bg-primary text-on-primary font-mono text-[10px] px-1.5 py-0.2 rounded font-bold ml-1">
                    {emLane.toUpperCase()}
                  </span>
                </div>
              )
            ) : (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-secondary/10 text-secondary border border-secondary/30">
                <span className="material-symbols-outlined text-[15px]">traffic</span>
                <span className="font-mono text-[10px] font-bold uppercase tracking-wider">
                  NORMAL ATSC WEBSTER AUTOMATION
                </span>
              </div>
            )}
          </div>

          <h2 className="font-headline text-[22px] text-on-surface font-bold tracking-tight">
            City-Wide AI Traffic Command Hub
          </h2>
          <p className="text-[13px] text-on-surface-variant mt-1 max-w-xl leading-relaxed">
            Multi-junction perception engine with kinematic vehicle tracking, automated Webster ATSC signal cycle optimization, and Code-3 emergency vehicle preemption (EVP).
          </p>
        </div>

        <div className="flex flex-wrap gap-space-sm w-full md:w-auto">
          <div className="bg-surface-container/50 border border-white/5 p-3 rounded-xl flex flex-col min-w-[120px] shadow-inner flex-1 md:flex-auto">
            <span className="text-[10px] uppercase font-mono text-on-surface-variant font-bold mb-1">Active Targets</span>
            <span className="text-[24px] font-headline font-black text-on-surface">
              {metrics?.active_targets_count !== undefined ? metrics.active_targets_count : 24}
            </span>
            <span className="text-[9px] text-secondary font-mono">Real-time tracked</span>
          </div>
          <div className="bg-surface-container/50 border border-white/5 p-3 rounded-xl flex flex-col min-w-[120px] shadow-inner flex-1 md:flex-auto">
            <span className="text-[10px] uppercase font-mono text-on-surface-variant font-bold mb-1">Webster Cycle (C₀)</span>
            <span className="text-[24px] font-headline font-black text-primary">
              {websterCycle}<span className="text-[14px] text-on-surface-variant">s</span>
            </span>
            <span className="text-[9px] text-primary font-mono">Y = {criticalFlow} (Flow Ratio)</span>
          </div>
          <div className="bg-surface-container/50 border border-white/5 p-3 rounded-xl flex flex-col min-w-[120px] shadow-inner flex-1 md:flex-auto">
            <span className="text-[10px] uppercase font-mono text-on-surface-variant font-bold mb-1">Completed Cycles</span>
            <span className="text-[24px] font-headline font-black text-on-surface">
              {totalCycles}
            </span>
            <span className="text-[9px] text-secondary font-mono">Adaptive ATSC</span>
          </div>
        </div>
      </section>

      {/* 2. Live 4-Way Approach Signal Status & Real-Time Countdowns */}
      <section className="bg-surface-container-low/60 backdrop-blur-xl rounded-2xl p-space-md border border-white/5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">traffic</span>
            <h3 className="font-headline text-[15px] text-on-surface font-bold uppercase tracking-wider">
              Live Approach Signals & Real-Time Countdown Matrix
            </h3>
          </div>
          <span className="font-mono text-[10px] text-on-surface-variant">
            Current Green Corridor: <strong className="text-secondary">{currentLane.toUpperCase()}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
          {lanes.map((lane) => {
            const laneSig = signals?.signals?.[lane] || {};
            const state = laneSig.state || (lane === currentLane ? 'green' : 'red');
            const timeLeft = laneSig.time_left !== undefined ? laneSig.time_left : (state === 'green' ? 14.5 : 0.0);
            const split = laneSplits[lane] ? Number(laneSplits[lane]).toFixed(1) : '18.0';
            const isGreen = state === 'green';
            const isYellow = state === 'yellow';
            const isRed = state === 'red';
            const isTargetEmergency = emergencyActive && emLane.toLowerCase() === lane.toLowerCase();

            return (
              <div
                key={lane}
                className={`p-4 rounded-xl border flex flex-col justify-between transition-all duration-300 ${
                  isTargetEmergency
                    ? 'bg-error/15 border-error/50 shadow-glow animate-pulse'
                    : isGreen
                    ? 'bg-secondary/10 border-secondary/40 shadow-glow-success'
                    : 'bg-surface-container/50 border-white/5'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-headline text-[15px] font-bold text-on-surface flex items-center gap-1.5">
                      <span>{lane} Approach</span>
                      {isTargetEmergency && (
                        <span className="bg-error text-on-error font-mono text-[9px] px-1.5 py-0.5 rounded font-extrabold">
                          EVP PRIORITY
                        </span>
                      )}
                    </span>
                    <span className="font-mono text-[10px] text-on-surface-variant font-bold">
                      Split: {split}s
                    </span>
                  </div>

                  {/* Signal Light Visualizer */}
                  <div className="flex items-center justify-between bg-black/40 p-3 rounded-xl border border-white/5 my-2">
                    <div className="flex items-center gap-2">
                      {/* Red Lamp */}
                      <span
                        className={`w-4 h-4 rounded-full transition-all duration-300 ${
                          isRed
                            ? 'bg-red-500 shadow-[0_0_12px_#ef4444]'
                            : 'bg-red-950/40 opacity-40'
                        }`}
                      ></span>
                      {/* Yellow Lamp */}
                      <span
                        className={`w-4 h-4 rounded-full transition-all duration-300 ${
                          isYellow
                            ? 'bg-amber-400 shadow-[0_0_12px_#fbbf24]'
                            : 'bg-amber-950/40 opacity-40'
                        }`}
                      ></span>
                      {/* Green Lamp */}
                      <span
                        className={`w-4 h-4 rounded-full transition-all duration-300 ${
                          isGreen
                            ? 'bg-emerald-400 shadow-[0_0_12px_#34d399] animate-pulse'
                            : 'bg-emerald-950/40 opacity-40'
                        }`}
                      ></span>
                    </div>

                    {/* Countdown Display */}
                    <div className="flex flex-col items-end">
                      <span className="font-mono text-[9px] uppercase tracking-wider text-on-surface-variant">
                        {isGreen ? 'GREEN REMAINING' : isYellow ? 'YELLOW CLEARANCE' : 'QUEUE HOLD'}
                      </span>
                      <span
                        className={`font-mono text-[22px] font-black leading-none ${
                          isGreen ? 'text-secondary' : isYellow ? 'text-amber-400' : 'text-on-surface-variant'
                        }`}
                      >
                        {isGreen || isYellow ? `${timeLeft.toFixed(1)}s` : 'RED'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Priority Preemption Action Button */}
                <button
                  onClick={() => onTriggerEmergency && onTriggerEmergency(lane)}
                  className={`mt-3 w-full py-2 rounded-lg font-mono text-[11px] font-bold flex items-center justify-center gap-1.5 transition-all ${
                    isTargetEmergency
                      ? 'bg-error text-on-error cursor-default'
                      : 'bg-surface-container-high hover:bg-error/20 text-on-surface hover:text-error border border-white/5 hover:border-error/30'
                  }`}
                >
                  <span className="material-symbols-outlined text-[16px]">e911_emergency</span>
                  <span>{isTargetEmergency ? 'Corridor Cleared' : `Grant Priority (${lane})`}</span>
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* 3. Webster ATSC Math Engine & Telemetry Card */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-space-md">
        <div className="bg-surface-container-low/60 backdrop-blur-xl rounded-2xl p-space-md border border-white/5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-primary text-[20px]">functions</span>
              <h4 className="font-headline text-[14px] text-on-surface font-bold uppercase tracking-wider">
                Webster Optimum Cycle Length
              </h4>
            </div>
            <p className="text-[11px] text-on-surface-variant font-mono">
              F.V. Webster Minimum Delay Formulation:
            </p>
            <div className="my-3 p-3 rounded-xl bg-surface-container/60 border border-white/5 text-center font-mono">
              <span className="text-[15px] font-bold text-primary tracking-wide block">
                C₀ = (1.5L + 5) / (1 - Y)
              </span>
              <span className="text-[10px] text-on-surface-variant mt-1 block">
                L = Lost Time (12.0s) • Y = Critical Flow Ratio ({criticalFlow})
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono py-1 border-b border-white/5">
              <span className="text-on-surface-variant">Optimum Cycle (C₀):</span>
              <span className="text-secondary font-bold">{websterCycle} seconds</span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono py-1 border-b border-white/5">
              <span className="text-on-surface-variant">Min/Max Bounds:</span>
              <span className="text-on-surface">30.0s — 120.0s</span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono py-1">
              <span className="text-on-surface-variant">Yellow Clearance:</span>
              <span className="text-amber-400 font-bold">3.0s Mandatory</span>
            </div>
          </div>
        </div>

        <div className="bg-surface-container-low/60 backdrop-blur-xl rounded-2xl p-space-md border border-white/5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-secondary text-[20px]">pie_chart</span>
              <h4 className="font-headline text-[14px] text-on-surface font-bold uppercase tracking-wider">
                Dynamic Green Split Allocation
              </h4>
            </div>
            <p className="text-[11px] text-on-surface-variant font-mono">
              Effective green proportional to approach saturation flow (gᵢ = (yᵢ / Y) × (C₀ - L)):
            </p>
            <div className="flex flex-col gap-2 mt-3 font-mono text-[11px]">
              {lanes.map((lane) => {
                const split = laneSplits[lane] ? Number(laneSplits[lane]) : 18.0;
                const total = Object.values(laneSplits).reduce((a, b) => a + Number(b), 0) || 72.4;
                const pct = Math.round((split / total) * 100);
                return (
                  <div key={lane} className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <span className="text-on-surface font-semibold">{lane} Approach</span>
                      <span className="text-on-surface-variant">{split.toFixed(1)}s ({pct}%)</span>
                    </div>
                    <div className="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${pct}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="bg-surface-container-low/60 backdrop-blur-xl rounded-2xl p-space-md border border-white/5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-primary text-[20px]">bolt</span>
              <h4 className="font-headline text-[14px] text-on-surface font-bold uppercase tracking-wider">
                Emergency Priority Invariants
              </h4>
            </div>
            <div className="flex flex-col gap-2.5 font-mono text-[11px] mt-2">
              <div className="p-2.5 rounded-lg bg-surface-container/50 border border-white/5">
                <span className="text-primary font-bold block mb-0.5">Priority 1: Visual Detection</span>
                <span className="text-on-surface-variant text-[10px]">
                  YOLOv8 bounding-box detection triggers immediate corridor lock; visual evidence overrides audio.
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-surface-container/50 border border-white/5">
                <span className="text-amber-400 font-bold block mb-0.5">Priority 2: Acoustic Siren FFT</span>
                <span className="text-on-surface-variant text-[10px]">
                  Secondary fallback for blind corners; cannot disrupt an active visual corridor.
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-surface-container/50 border border-white/5">
                <span className="text-secondary font-bold block mb-0.5">Anti-Starvation Timer</span>
                <span className="text-on-surface-variant text-[10px]">
                  Maximum 25.0s hold limit ensures cross-traffic does not starve indefinitely.
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Active Intersections Grid */}
      <section className="flex flex-col gap-space-md">
        <div className="flex items-center gap-space-xs px-2">
          <span className="material-symbols-outlined text-primary text-[22px]">device_hub</span>
          <h3 className="font-headline text-[16px] text-on-surface font-bold uppercase tracking-wider">
            Connected Intersections
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-md">
          {junctions.map((j) => (
            <div key={j.id} className="group bg-surface-container-low/60 backdrop-blur-xl rounded-2xl p-space-md shadow-lg hover:shadow-xl hover:bg-surface-container/80 border border-white/5 hover:border-primary/30 transition-all duration-300 flex flex-col justify-between h-[200px]">
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] bg-primary/10 text-primary px-2 py-1 rounded-md font-bold border border-primary/20 group-hover:bg-primary group-hover:text-on-primary transition-colors">
                      {j.id.toUpperCase()}
                    </span>
                  </div>
                  {j.alert && (
                    <span className="bg-error/15 text-error text-[9px] font-mono px-2 py-1 rounded font-bold uppercase border border-error/30 animate-pulse shadow-glow">
                      Emergency
                    </span>
                  )}
                </div>
                
                <h4 className="font-headline text-[15px] text-on-surface font-bold truncate leading-tight mb-1">
                  {j.name}
                </h4>
                
                <div className="flex items-center gap-2 mt-4">
                  <div className="flex-1 bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${parseInt(j.congestion) > 70 ? 'bg-error' : parseInt(j.congestion) > 40 ? 'bg-tertiary' : 'bg-secondary'}`} 
                      style={{ width: j.congestion }}
                    ></div>
                  </div>
                  <span className="font-mono text-[10px] text-on-surface-variant font-bold w-8 text-right">
                    {j.congestion}
                  </span>
                </div>
              </div>

              <button
                onClick={() => handleInspect(j.id)}
                className="w-full bg-surface-container/50 hover:bg-primary/20 text-on-surface hover:text-primary py-2.5 rounded-xl text-[12px] font-bold flex items-center justify-center gap-1.5 transition-all border border-white/5 hover:border-primary/30 group-hover:shadow-glow mt-4"
              >
                <span className="material-symbols-outlined text-[18px]">visibility</span>
                <span>Enter AI View</span>
              </button>
            </div>
          ))}
        </div>
      </section>

    </div>
  );
}
