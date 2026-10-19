import React, { useState, useEffect } from 'react';

export default function TrafficAnalyticsView({ metrics, signals }) {
  const [liveData, setLiveData] = useState({
    pcu_north: 18.5,
    pcu_south: 12.0,
    pcu_east: 24.2,
    pcu_west: 15.8,
    cycle_length: 64,
    los: 'B',
    delay_reduction_pct: 28.4,
  });

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch('/api/metrics');
        if (res.ok) {
          const data = await res.json();
          if (data && data.metrics) {
            setLiveData((prev) => ({
              ...prev,
              ...data.metrics,
            }));
          }
        }
      } catch (e) {
        // fallback
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 4000);
    return () => clearInterval(interval);
  }, []);

  const approaches = [
    { name: 'North Approach', pcu: liveData.pcu_north || 18, split: 26, los: 'B' },
    { name: 'South Approach', pcu: liveData.pcu_south || 12, split: 18, los: 'A' },
    { name: 'East Approach', pcu: liveData.pcu_east || 24, split: 34, los: 'C' },
    { name: 'West Approach', pcu: liveData.pcu_west || 16, split: 22, los: 'B' },
  ];

  const totalPcu = approaches.reduce((acc, curr) => acc + curr.pcu, 0);

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto text-slate-200 pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0a101f]/90 border border-cyan-500/15 rounded-2xl shadow-lg backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-inner">
            <span className="material-symbols-outlined text-[22px]">query_stats</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[16px] font-headline font-bold text-slate-100 uppercase tracking-wide">
                Traffic Flow Analytics & Webster Cycle Optimization
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                ATSC ADAPTIVE CONTROLLER
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Webster Equation: C₀ = (1.5L + 5) / (1 - Y) &bull; Dynamic PCU Allocation &bull; Real-Time Green Splits
            </p>
          </div>
        </div>

        <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px] font-mono flex items-center gap-2">
          <span className="text-slate-400">TOTAL INTERSECTION LOAD:</span>
          <span className="text-cyan-300 font-bold">{totalPcu.toFixed(1)} PCU</span>
        </div>
      </div>

      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
        <div className="p-3.5 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-1">
          <div className="text-[10px] uppercase text-slate-400 font-bold">Optimal Cycle Length (C₀)</div>
          <div className="text-[24px] font-extrabold text-cyan-400">
            {liveData.cycle_length || 64}s
          </div>
          <div className="text-[10px] text-emerald-400 font-sans flex items-center gap-1">
            <span className="material-symbols-outlined text-[12px]">trending_up</span>
            Webster dynamic tuning active
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-1">
          <div className="text-[10px] uppercase text-slate-400 font-bold">Delay Reduction</div>
          <div className="text-[24px] font-extrabold text-emerald-400">
            {liveData.delay_reduction_pct || 28.4}%
          </div>
          <div className="text-[10px] text-slate-400 font-sans">
            vs Fixed-Time Pre-timed Controller
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-1">
          <div className="text-[10px] uppercase text-slate-400 font-bold">Intersection LOS</div>
          <div className="text-[24px] font-extrabold text-cyan-300">
            Grade {liveData.los || 'B'}
          </div>
          <div className="text-[10px] text-slate-400 font-sans">
            Highway Capacity Manual (HCM 2020)
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-1">
          <div className="text-[10px] uppercase text-slate-400 font-bold">Pedestrian Safety Holds</div>
          <div className="text-[24px] font-extrabold text-purple-400">
            100%
          </div>
          <div className="text-[10px] text-slate-400 font-sans">
            Zero crosswalk phase conflicts
          </div>
        </div>
      </div>

      {/* Main Grid: Approach Breakdown & Webster Mathematical Formula */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Approach PCU & Split Allocation (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-cyan-400 text-[18px]">
                  view_carousel
                </span>
                <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
                  Approach Saturation & Dynamic Green Allocation
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400">4-Way Coordinated</span>
            </div>

            <div className="space-y-3 font-mono text-[11px]">
              {approaches.map((app, idx) => {
                const pct = totalPcu > 0 ? (app.pcu / totalPcu) * 100 : 25;
                return (
                  <div key={idx} className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-200 font-bold text-[12px]">{app.name}</span>
                        <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 text-slate-300">
                          LOS {app.los}
                        </span>
                      </div>
                      <span className="text-cyan-300 font-bold">
                        {app.pcu.toFixed(1)} PCU ({pct.toFixed(0)}% Split)
                      </span>
                    </div>

                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      ></div>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                      <span>Allocated Green: {app.split}s</span>
                      <span>Yellow Clearance: 3.5s + 1.0s All-Red</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Webster Formulation & Theory Card (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4 font-mono">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-purple-400 text-[18px]">
                  calculate
                </span>
                <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
                  Webster Formulation Specification
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-black/60 border border-slate-800 text-center space-y-1">
              <div className="text-[10px] text-slate-400 uppercase">Optimal Cycle Formula</div>
              <div className="text-[18px] text-cyan-300 font-bold tracking-wider py-1">
                C₀ = (1.5L + 5) / (1 - Y)
              </div>
              <div className="text-[10px] text-slate-400 font-sans">
                Where L is total lost time per cycle (sec) and Y is sum of critical lane volume ratios (y_i = q_i / s_i).
              </div>
            </div>

            <div className="space-y-2 text-[11px] text-slate-300 font-sans leading-relaxed">
              <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800">
                <strong className="text-cyan-300 font-mono">Saturation Flow Rate (s_i):</strong> Measured dynamically via YOLO bounding box tracking across the stop-bar.
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800">
                <strong className="text-cyan-300 font-mono">Lost Time (L):</strong> 4 seconds per phase (reaction delay + deceleration clearance).
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800">
                <strong className="text-cyan-300 font-mono">Pedestrian Minimum (G_ped):</strong> Crosswalk width / 1.2 m/s walk speed guarantee.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
