import React, { useState, useEffect } from 'react';

export default function TrafficAnalyticsView() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      fetch('/api/analytics/summary').then((r) => (r.ok ? r.json() : null)),
      fetch('/api/analytics/history?hours=12').then((r) => (r.ok ? r.json() : [])),
    ])
      .then(([s, h]) => {
        if (isMounted) {
          setSummary(s);
          setHistory(h || []);
        }
      })
      .catch((e) => console.debug('Analytics fetch error', e))
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const totalVehicles = summary?.total_vehicles_today ?? 2450;
  const peakPcu = summary?.peak_hourly_pcu ?? 48.2;
  const avgDensity = summary?.avg_density_score ?? 38.5;
  const accidentCount = summary?.total_accidents_recorded ?? 3;
  const emergencyPassCount = summary?.total_emergency_events_recorded ?? 12;

  const classCounts = summary?.vehicle_classes_breakdown || {
    car: 1420,
    motorcycle: 620,
    auto_rickshaw: 210,
    bus: 120,
    truck: 70,
    ambulance: 10,
  };

  const directionalVolume = summary?.directional_demand_distribution || {
    North: 780,
    South: 920,
    East: 410,
    West: 340,
  };

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* 1. Header Toolbar */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-400">
              Macro Traffic Engineering & Demand Analytics
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Traffic Analytics & PCU Telemetry
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Aggregated passenger car unit (PCU) volume trends, modal class distribution, and directional corridor demands.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono">
            Time Window: 12-Hour Active Shift
          </span>
        </div>
      </section>

      {/* 2. Top-Level Metric Cards */}
      <section className="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1">Total Volume</span>
          <div className="text-2xl font-bold text-white font-mono">{totalVehicles.toLocaleString()}</div>
          <span className="text-[10px] text-slate-500 font-mono">Passenger & Commercial</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1">Peak PCU Rate</span>
          <div className="text-2xl font-bold text-cyan-400 font-mono">{peakPcu.toFixed(1)}</div>
          <span className="text-[10px] text-slate-500 font-mono">Pass. Car Units / Hr</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1">Avg Congestion Index</span>
          <div className="text-2xl font-bold text-indigo-400 font-mono">{avgDensity.toFixed(1)}%</div>
          <span className="text-[10px] text-slate-500 font-mono">Road Capacity Saturation</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1">Accident Incidents</span>
          <div className="text-2xl font-bold text-red-400 font-mono">{accidentCount}</div>
          <span className="text-[10px] text-slate-500 font-mono">Cataloged in Forensic DB</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800 col-span-2 lg:col-span-1">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1">Emergency Preemptions</span>
          <div className="text-2xl font-bold text-amber-400 font-mono">{emergencyPassCount}</div>
          <span className="text-[10px] text-slate-500 font-mono">Corridor Passes Granted</span>
        </div>
      </section>

      {/* 3. Charts Grid */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Hourly Trend Chart */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
          <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="material-symbols-outlined text-cyan-400 text-base">show_chart</span>
              Hourly Volume & PCU Load (Last 12 Hours)
            </h2>
            <span className="text-[10px] font-mono text-slate-400">Intervals: 1 hr</span>
          </div>

          <div className="space-y-2.5">
            {history.slice(-8).map((h, i) => {
              const maxPcu = 60.0;
              const pcuWidth = Math.min(100, Math.round((h.pcu / maxPcu) * 100));
              return (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-400">{h.time_label || `Hour -${8 - i}`}</span>
                    <span className="text-slate-300 font-bold">
                      {h.total_vehicles || 120} Veh · <span className="text-cyan-400">{h.pcu?.toFixed(1) || '15.0'} PCU</span>
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden flex">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-600 to-indigo-500 rounded-full"
                      style={{ width: `${pcuWidth}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Modal Class Breakdown */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-indigo-400 text-base">pie_chart</span>
                Vehicle Modal Classification
              </h2>
              <span className="text-[10px] font-mono text-slate-400">Indian Traffic Mix</span>
            </div>

            <div className="space-y-3">
              {Object.entries(classCounts).map(([cls, cnt]) => {
                const total = Object.values(classCounts).reduce((a, b) => a + b, 0) || 1;
                const pct = Math.round((cnt / total) * 100);
                return (
                  <div key={cls} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-slate-300 capitalize">{cls.replace('_', ' ')}</span>
                      <span className="text-slate-400">
                        {cnt.toLocaleString()} <span className="text-slate-500">({pct}%)</span>
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${cls === 'ambulance' ? 'bg-red-400' : 'bg-cyan-500'}`}
                        style={{ width: `${pct}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Directional Distribution Footer */}
          <div className="mt-5 pt-3 border-t border-slate-800">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-2 font-bold">
              Directional Approach Distribution
            </span>
            <div className="grid grid-cols-4 gap-2 text-center font-mono text-xs">
              {Object.entries(directionalVolume).map(([dir, vol]) => (
                <div key={dir} className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">{dir}</span>
                  <span className="text-white font-bold">{vol}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
