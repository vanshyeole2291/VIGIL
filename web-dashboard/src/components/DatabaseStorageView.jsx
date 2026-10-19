import React, { useState, useEffect } from 'react';

export default function DatabaseStorageView() {
  const [dbStatus, setDbStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // PostgreSQL Test Connection Form State
  const [pgConfig, setPgConfig] = useState({
    host: 'localhost',
    port: 5432,
    database: 'vigil_production',
    username: 'vigil_admin',
    password: '',
    ssl_mode: 'disable',
  });

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const fetchDatabaseStatus = async () => {
    try {
      const res = await fetch('/api/database/status');
      if (res.ok) {
        const data = await res.json();
        setDbStatus(data);
      }
    } catch (e) {
      console.error('Failed to fetch DB status', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDatabaseStatus();
    const interval = setInterval(fetchDatabaseStatus, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleTestConnection = async (e) => {
    e.preventDefault();
    setTesting(true);
    setTestResult(null);

    try {
      const res = await fetch('/api/database/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...pgConfig,
          port: parseInt(pgConfig.port, 10) || 5432,
        }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err) {
      setTestResult({
        success: false,
        message: 'Network request error testing connection: ' + err.message,
      });
    } finally {
      setTesting(false);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto text-slate-200 pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0a101f]/90 border border-cyan-500/15 rounded-2xl shadow-lg backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-inner">
            <span className="material-symbols-outlined text-[22px]">database</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[16px] font-headline font-bold text-slate-100 uppercase tracking-wide">
                Database & Storage Infrastructure
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                ACTIVE ENGINE: {dbStatus?.engine?.toUpperCase() || 'SQLITE'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              SQLite v3 (WAL Mode Local) &bull; PostgreSQL Regional Deployment Ready &bull; Schema {dbStatus?.schema_version || 'v2.0'}
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            setRefreshing(true);
            fetchDatabaseStatus();
          }}
          disabled={refreshing}
          className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-cyan-500/40 text-[11px] font-mono text-cyan-300 flex items-center gap-1.5 transition-colors"
        >
          <span className={`material-symbols-outlined text-[15px] ${refreshing ? 'animate-spin' : ''}`}>
            refresh
          </span>
          Refresh Telemetry
        </button>
      </div>

      {/* Main Grid: Active SQLite Status (Left) & PostgreSQL Deployment Configuration (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Active Local Database Engine Card (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-cyan-400 text-[18px]">
                  storage
                </span>
                <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
                  Active Engine: SQLite v3 (WAL Concurrency)
                </span>
              </div>
              <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                STATUS: {dbStatus?.status?.toUpperCase() || 'HEALTHY'}
              </span>
            </div>

            {/* Storage Metric Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 font-mono text-[11px]">
              <div className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800">
                <div className="text-slate-400 text-[9.5px] uppercase">Database File</div>
                <div className="text-cyan-300 font-bold mt-1 truncate">
                  {dbStatus?.path || 'vigil.db'}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800">
                <div className="text-slate-400 text-[9.5px] uppercase">File On Disk</div>
                <div className="text-slate-200 font-bold mt-1">
                  {formatBytes(dbStatus?.size_bytes)}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800">
                <div className="text-slate-400 text-[9.5px] uppercase">Write Mode</div>
                <div className="text-emerald-400 font-bold mt-1 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  {dbStatus?.wal_mode ? 'WAL Mode (Active)' : 'Normal'}
                </div>
              </div>
            </div>

            {/* Record Counts Table */}
            <div className="space-y-2">
              <div className="text-[11px] font-mono uppercase text-slate-400 tracking-wider font-bold flex items-center justify-between">
                <span>Entity Table Audit</span>
                <span className="text-[10px] text-cyan-400">Auto-Synchronized</span>
              </div>

              <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-[#0a101f]/60 overflow-hidden font-mono text-[11.5px]">
                <div className="flex items-center justify-between p-2.5 px-3.5 hover:bg-slate-900/40">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="material-symbols-outlined text-[16px] text-rose-400">warning</span>
                    <span>Incidents (`incidents`)</span>
                  </div>
                  <span className="font-bold text-cyan-300">
                    {dbStatus?.counts?.incidents ?? '0'} records
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 px-3.5 hover:bg-slate-900/40">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="material-symbols-outlined text-[16px] text-amber-400">notifications_active</span>
                    <span>System Alerts (`alerts`)</span>
                  </div>
                  <span className="font-bold text-cyan-300">
                    {dbStatus?.counts?.alerts ?? '0'} records
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 px-3.5 hover:bg-slate-900/40">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="material-symbols-outlined text-[16px] text-blue-400">linked_camera</span>
                    <span>Surveillance Cameras (`cameras`)</span>
                  </div>
                  <span className="font-bold text-cyan-300">
                    {dbStatus?.counts?.cameras ?? '0'} records
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 px-3.5 hover:bg-slate-900/40">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="material-symbols-outlined text-[16px] text-purple-400">videocam</span>
                    <span>Forensic Evidence Vault (`evidence`)</span>
                  </div>
                  <span className="font-bold text-cyan-300">
                    {dbStatus?.counts?.evidence ?? '0'} records
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 px-3.5 hover:bg-slate-900/40">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="material-symbols-outlined text-[16px] text-emerald-400">manage_accounts</span>
                    <span>System Users & Operators (`users`)</span>
                  </div>
                  <span className="font-bold text-cyan-300">
                    {dbStatus?.counts?.users ?? '0'} records
                  </span>
                </div>
              </div>
            </div>

            {/* Architecture Info Callout */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-cyan-500/20 text-[11px] text-slate-300 leading-relaxed font-sans">
              <div className="font-bold text-cyan-300 mb-1 flex items-center gap-1 font-mono text-[10.5px]">
                <span className="material-symbols-outlined text-[14px]">info</span>
                Zero Data Overwrite / Non-Destructive Storage Architecture
              </div>
              VIGIL initializes SQLite with Write-Ahead Logging (WAL) enabled at startup.
              This permits concurrent reads from WebSockets and API workers while OpenCV video loops write detection frames and telemetry observations.
            </div>
          </div>
        </div>

        {/* PostgreSQL Deployment & Connection Tester Card (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-purple-400 text-[18px]">
                  cloud_sync
                </span>
                <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
                  PostgreSQL Production Deployment Testing
                </span>
              </div>
              <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                ENTERPRISE / REGIONAL
              </span>
            </div>

            <p className="text-[11.5px] text-slate-400 font-sans leading-relaxed">
              For enterprise deployments across regional traffic networks, VIGIL seamlessly connects to PostgreSQL.
              Use this safe, non-destructive test panel (`SELECT 1`, 3s timeout) to verify connectivity before migrating.
            </p>

            {/* Configuration Form */}
            <form onSubmit={handleTestConnection} className="space-y-3 font-mono text-[11px]">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <div className="sm:col-span-2 space-y-1">
                  <label className="text-slate-400 text-[10px] uppercase font-bold">Host / Endpoint</label>
                  <input
                    type="text"
                    value={pgConfig.host}
                    onChange={(e) => setPgConfig({ ...pgConfig, host: e.target.value })}
                    placeholder="localhost or postgres.cluster.internal"
                    required
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700 text-slate-200 outline-none focus:border-cyan-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[10px] uppercase font-bold">Port</label>
                  <input
                    type="number"
                    value={pgConfig.port}
                    onChange={(e) => setPgConfig({ ...pgConfig, port: e.target.value })}
                    required
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700 text-slate-200 outline-none focus:border-cyan-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[10px] uppercase font-bold">Database Name</label>
                  <input
                    type="text"
                    value={pgConfig.database}
                    onChange={(e) => setPgConfig({ ...pgConfig, database: e.target.value })}
                    required
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700 text-slate-200 outline-none focus:border-cyan-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[10px] uppercase font-bold">SSL Mode</label>
                  <select
                    value={pgConfig.ssl_mode}
                    onChange={(e) => setPgConfig({ ...pgConfig, ssl_mode: e.target.value })}
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700 text-slate-200 outline-none focus:border-cyan-500/50 cursor-pointer"
                  >
                    <option value="disable">disable (Local / Dev)</option>
                    <option value="require">require (Cloud / Production)</option>
                    <option value="verify-ca">verify-ca (Strict TLS)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[10px] uppercase font-bold">Username</label>
                  <input
                    type="text"
                    value={pgConfig.username}
                    onChange={(e) => setPgConfig({ ...pgConfig, username: e.target.value })}
                    required
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700 text-slate-200 outline-none focus:border-cyan-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[10px] uppercase font-bold">Password</label>
                  <input
                    type="password"
                    value={pgConfig.password}
                    onChange={(e) => setPgConfig({ ...pgConfig, password: e.target.value })}
                    placeholder="••••••••"
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700 text-slate-200 outline-none focus:border-cyan-500/50"
                  />
                </div>
              </div>

              <div className="pt-1 flex items-center justify-between gap-3">
                <span className="text-[9.5px] text-slate-500 font-sans">
                  🔒 Zero credentials logged or stored in history. Non-destructive connection ping only.
                </span>
                <button
                  type="submit"
                  disabled={testing}
                  className="px-4 py-2 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 text-[11px] font-bold font-mono transition-colors flex items-center gap-1.5 shrink-0"
                >
                  <span className={`material-symbols-outlined text-[16px] ${testing ? 'animate-spin' : ''}`}>
                    {testing ? 'hourglass_top' : 'bolt'}
                  </span>
                  {testing ? 'Testing...' : 'Test Connection'}
                </button>
              </div>
            </form>

            {/* Test Results Banner */}
            {testResult && (
              <div
                className={`p-3 rounded-xl border font-mono text-[11px] space-y-1 ${
                  testResult.success
                    ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                    : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
                }`}
              >
                <div className="font-bold flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">
                    {testResult.success ? 'check_circle' : 'cancel'}
                  </span>
                  <span>
                    {testResult.success
                      ? `Connection Successful (${testResult.latency_ms} ms)`
                      : 'Connection Failed'}
                  </span>
                </div>
                <div className="text-[10px] text-slate-300 font-sans leading-relaxed">
                  {testResult.message}
                </div>
              </div>
            )}

            {/* Deployment Activation Instructions */}
            <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1.5">
              <div className="text-slate-300 font-bold uppercase text-[10px]">
                Regional Production Activation Guide:
              </div>
              <p className="text-[10.5px] text-slate-400 font-sans">
                To activate PostgreSQL as the primary persistence engine, set the environment variable in your production configuration and restart the VIGIL backend:
              </p>
              <div className="p-2 rounded bg-black/60 border border-slate-800 text-cyan-300 text-[10px] break-all select-all">
                DATABASE_URL=postgresql://{pgConfig.username || 'user'}:password@{pgConfig.host || 'localhost'}:{pgConfig.port || '5432'}/{pgConfig.database || 'vigil'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
