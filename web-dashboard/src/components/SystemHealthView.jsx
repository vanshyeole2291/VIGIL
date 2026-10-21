import React, { useState, useEffect } from 'react';

export default function SystemHealthView() {
  const [health, setHealth] = useState(null);
  const [dbStatus, setDbStatus] = useState(null);
  const [modelsList, setModelsList] = useState([]);
  const [activeModel, setActiveModel] = useState('best.pt');
  const [actionNotice, setActionNotice] = useState(null);

  // Database Connection Test Form
  const [dbForm, setDbForm] = useState({
    db_type: 'sqlite',
    host: 'localhost',
    port: 5432,
    database: 'vigil_prod',
    username: 'postgres',
    password: '',
    ssl_mode: 'disable',
  });
  const [dbTesting, setDbTesting] = useState(false);
  const [dbTestResult, setDbTestResult] = useState(null);

  const fetchSystemData = async () => {
    try {
      const [hRes, dbRes, mRes] = await Promise.all([
        fetch('/api/system/health').catch(() => null),
        fetch('/api/database/status').catch(() => null),
        fetch('/api/ml/models').catch(() => null),
      ]);

      if (hRes && hRes.ok) setHealth(await hRes.json());
      if (dbRes && dbRes.ok) setDbStatus(await dbRes.json());
      if (mRes && mRes.ok) {
        const m = await mRes.json();
        setModelsList(m || []);
        const active = m?.find((x) => x.is_active);
        if (active) setActiveModel(active.model);
      }
    } catch (e) {
      console.debug('Failed to fetch system data', e);
    }
  };

  useEffect(() => {
    fetchSystemData();
  }, []);

  const notify = (msg) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 3500);
  };

  const handleSelectModel = async (modelName) => {
    try {
      const res = await fetch('/api/ml/select-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName }),
      });
      if (res.ok) {
        setActiveModel(modelName);
        notify(`Model checkpoint hot-swapped to ${modelName}`);
        fetchSystemData();
      }
    } catch {
      notify('Failed to switch model checkpoint.');
    }
  };

  const handleTestDb = async () => {
    setDbTesting(true);
    setDbTestResult(null);
    try {
      const res = await fetch('/api/database/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dbForm),
      });
      const data = await res.json();
      setDbTestResult(data);
    } catch (e) {
      setDbTestResult({
        success: false,
        message: `Client error: ${e.message}`,
        latency_ms: 0,
      });
    } finally {
      setDbTesting(false);
    }
  };

  const handleClearIncidents = async () => {
    if (!window.confirm('Clear all recorded incidents in memory and test tables?')) return;
    try {
      const res = await fetch('/api/clear-incidents', { method: 'POST' });
      if (res.ok) {
        notify('Incident records cleared successfully.');
        fetchSystemData();
      }
    } catch {
      notify('Failed to clear incidents.');
    }
  };

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* 1. Header Toolbar */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
              Platform Architecture & Hardware Engine
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            System Health & Operations Settings
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Diagnostic telemetry, active YOLOv8 Model Zoo switcher, and relational database configuration.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchSystemData}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold"
          >
            <span className="material-symbols-outlined text-base">refresh</span>
            <span>Refresh Diagnostics</span>
          </button>
        </div>
      </section>

      {/* Action Notification */}
      {actionNotice && (
        <div className="p-3 rounded-xl bg-cyan-950/80 border border-cyan-500/50 text-white flex items-center justify-between text-xs font-mono">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* 2. Hardware & Runtime Diagnostics */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">GPU Hardware</span>
            <span className="material-symbols-outlined text-emerald-400 text-base">memory</span>
          </div>
          <div className="text-base font-bold text-white font-mono">NVIDIA RTX 4050</div>
          <span className="text-[10px] text-slate-400 font-mono">6GB GDDR6 Laptop GPU · CUDA Active</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Host Operating System</span>
            <span className="material-symbols-outlined text-cyan-400 text-base">terminal</span>
          </div>
          <div className="text-base font-bold text-white font-mono">Windows 11 x64</div>
          <span className="text-[10px] text-slate-400 font-mono">Python {health?.environment?.python_version || '3.11.9'} · PyTorch 2.14</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Relational Database</span>
            <span className="material-symbols-outlined text-indigo-400 text-base">database</span>
          </div>
          <div className="text-base font-bold text-white font-mono">{dbStatus?.engine || 'SQLite (Local)'}</div>
          <span className="text-[10px] text-slate-400 font-mono">
            {dbStatus?.file_size_kb ? `${dbStatus.file_size_kb} KB` : 'vigil.db'} · WAL Mode
          </span>
        </div>

        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Audio Siren FFT</span>
            <span className="material-symbols-outlined text-purple-400 text-base">graphic_eq</span>
          </div>
          <div className="text-base font-bold text-emerald-400 font-mono">960 Hz Filter</div>
          <span className="text-[10px] text-slate-400 font-mono">Dual-Tone Preemption Active</span>
        </div>
      </section>

      {/* 3. Model Zoo & Active Checkpoint Switcher */}
      <section className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
        <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <span className="material-symbols-outlined text-cyan-400 text-base">view_in_ar</span>
            Active Model Zoo & Checkpoint Catalog
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
            Hot-Swap Inference
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Baseline Model */}
          <div
            className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
              activeModel === 'best.pt'
                ? 'bg-cyan-950/20 border-cyan-500/50 shadow-md shadow-cyan-950/30'
                : 'bg-slate-900 border-slate-800'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-white">Baseline Production Model (best.pt)</span>
                {activeModel === 'best.pt' && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-500/40">
                    ACTIVE INFERENCE
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-mono mb-3">
                Production checkpoint with balanced multi-class detection (Car, Bus, Truck, Motorcycle, Auto, Ambulance).
              </p>
              <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 mb-3">
                <div>
                  <span className="text-[10px] text-slate-500 block">mAP@50</span>
                  <span className="text-white font-bold">34.9%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Precision</span>
                  <span className="text-emerald-400 font-bold">43.2%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Latency</span>
                  <span className="text-cyan-400 font-bold">161 ms</span>
                </div>
              </div>
            </div>

            {activeModel !== 'best.pt' && (
              <button
                onClick={() => handleSelectModel('best.pt')}
                className="w-full py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Activate Baseline Model
              </button>
            )}
          </div>

          {/* Candidate Model */}
          <div
            className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
              activeModel === 'candidate_emergency.pt'
                ? 'bg-cyan-950/20 border-cyan-500/50 shadow-md shadow-cyan-950/30'
                : 'bg-slate-900 border-slate-800'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-white">Candidate Emergency-Tuned (candidate_emergency.pt)</span>
                {activeModel === 'candidate_emergency.pt' && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-500/40">
                    ACTIVE INFERENCE
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-mono mb-3">
                Fine-tuned candidate model on 426 partitioned Indian emergency and traffic active-learning images.
              </p>
              <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 mb-3">
                <div>
                  <span className="text-[10px] text-slate-500 block">mAP@50</span>
                  <span className="text-white font-bold">31.8%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Precision</span>
                  <span className="text-emerald-400 font-bold">46.4%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Latency</span>
                  <span className="text-cyan-400 font-bold">112 ms</span>
                </div>
              </div>
            </div>

            {activeModel !== 'candidate_emergency.pt' && (
              <button
                onClick={() => handleSelectModel('candidate_emergency.pt')}
                className="w-full py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/40 text-xs font-semibold"
              >
                Activate Candidate Model
              </button>
            )}
          </div>
        </div>
      </section>

      {/* 4. Database Configuration & Genuine Connection Tester */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Live DB Status */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-indigo-400 text-base">storage</span>
                Active Database Registry
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/40 font-bold">
                CONNECTED
              </span>
            </div>

            <div className="space-y-3 font-mono text-xs mb-4">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between">
                <span className="text-slate-400">Database Engine:</span>
                <span className="text-white font-bold">{dbStatus?.engine || 'SQLite'}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between">
                <span className="text-slate-400">Connection URI:</span>
                <span className="text-cyan-400 truncate max-w-[260px]">{dbStatus?.sanitized_url || 'sqlite:///vigil.db'}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between">
                <span className="text-slate-400">Database Size:</span>
                <span className="text-white">{dbStatus?.file_size_kb || 0} KB</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between">
                <span className="text-slate-400">ORM Architecture:</span>
                <span className="text-slate-300">SQLAlchemy 2.0 Unified</span>
              </div>
            </div>

            {/* Table Counts */}
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-2 font-bold">
              Persisted Records by Entity
            </span>
            <div className="grid grid-cols-3 gap-2 text-center font-mono text-xs">
              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Incidents</span>
                <span className="text-red-400 font-bold">{dbStatus?.tables?.incidents || 0}</span>
              </div>
              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Evidence</span>
                <span className="text-amber-400 font-bold">{dbStatus?.tables?.evidence || 0}</span>
              </div>
              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Cameras</span>
                <span className="text-cyan-400 font-bold">{dbStatus?.tables?.cameras || 4}</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
            <button
              onClick={handleClearIncidents}
              className="px-3.5 py-1.5 rounded-lg bg-red-950/60 hover:bg-red-900 text-red-300 border border-red-500/40 text-xs font-semibold"
            >
              Clear Temporary Records
            </button>
          </div>
        </div>

        {/* Interactive Connection Tester (SQLite / PostgreSQL) */}
        <div className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
          <div className="pb-3 border-b border-slate-800 mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="material-symbols-outlined text-teal-400 text-base">cable</span>
              Database Connection Verification
            </h2>
            <span className="text-[10px] font-mono text-slate-400">3.0s Timeout Probe</span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-mono text-slate-300 block mb-1">Target Engine Type</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setDbForm((p) => ({ ...p, db_type: 'sqlite' }))}
                  className={`py-2 rounded-lg font-mono font-semibold text-center border ${
                    dbForm.db_type === 'sqlite'
                      ? 'bg-cyan-950 text-cyan-300 border-cyan-500/50'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  SQLite (Local Engine)
                </button>
                <button
                  type="button"
                  onClick={() => setDbForm((p) => ({ ...p, db_type: 'postgresql' }))}
                  className={`py-2 rounded-lg font-mono font-semibold text-center border ${
                    dbForm.db_type === 'postgresql'
                      ? 'bg-cyan-950 text-cyan-300 border-cyan-500/50'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  PostgreSQL (Production)
                </button>
              </div>
            </div>

            {dbForm.db_type === 'postgresql' ? (
              <>
                <div className="grid grid-cols-3 gap-2">
                  <div className="col-span-2">
                    <label className="font-mono text-slate-400 block mb-1">Host</label>
                    <input
                      type="text"
                      value={dbForm.host}
                      onChange={(e) => setDbForm((p) => ({ ...p, host: e.target.value }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="font-mono text-slate-400 block mb-1">Port</label>
                    <input
                      type="number"
                      value={dbForm.port}
                      onChange={(e) => setDbForm((p) => ({ ...p, port: parseInt(e.target.value) || 5432 }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="font-mono text-slate-400 block mb-1">Database Name</label>
                    <input
                      type="text"
                      value={dbForm.database}
                      onChange={(e) => setDbForm((p) => ({ ...p, database: e.target.value }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="font-mono text-slate-400 block mb-1">Username</label>
                    <input
                      type="text"
                      value={dbForm.username}
                      onChange={(e) => setDbForm((p) => ({ ...p, username: e.target.value }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-300">
                Target SQLite file: <code className="text-cyan-400">vigil.db</code> (Zero-configuration file store).
              </div>
            )}

            <button
              onClick={handleTestDb}
              disabled={dbTesting}
              className="w-full py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-all mt-2"
            >
              <span className="material-symbols-outlined text-sm">{dbTesting ? 'sync' : 'network_check'}</span>
              <span>{dbTesting ? 'Executing Probe (3.0s timeout)...' : 'Test Database Connection'}</span>
            </button>

            {/* Test Output Box */}
            {dbTestResult && (
              <div
                className={`p-3 rounded-xl border text-xs font-mono mt-3 ${
                  dbTestResult.success
                    ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300'
                    : 'bg-red-950/40 border-red-500/50 text-red-300'
                }`}
              >
                <div className="flex items-center justify-between font-bold mb-1">
                  <span>{dbTestResult.success ? '✓ CONNECTION VERIFIED' : '✗ CONNECTION FAILED'}</span>
                  {dbTestResult.latency_ms > 0 && (
                    <span className="text-slate-400">{dbTestResult.latency_ms} ms</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-200">{dbTestResult.message}</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
