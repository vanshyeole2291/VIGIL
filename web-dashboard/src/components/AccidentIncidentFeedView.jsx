import React, { useState, useEffect, useMemo } from 'react';

export default function AccidentIncidentFeedView() {
  const [incidents, setIncidents] = useState([]);
  const [activeTab, setActiveTab] = useState('all'); // all, accident, ambulance, new, resolved
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [noteText, setNoteText] = useState('');
  const [actionNotice, setActionNotice] = useState(null);

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      // Fetch unified incidents covering both accidents and ambulances
      const res = await fetch('/api/incidents?limit=60');
      if (res.ok) {
        const data = await res.json();
        // Exclude legacy routine queue/crowd alerts: strictly keep accident and ambulance
        const filtered = (data || []).filter(
          (item) => item.type === 'accident' || item.type === 'ambulance' || item.incident_type === 'accident' || item.incident_type === 'ambulance'
        );
        setIncidents(filtered);
      }
    } catch (e) {
      console.error('Failed to fetch incidents', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 3000);
    return () => clearInterval(interval);
  }, []);

  const notify = (msg) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 3500);
  };

  const handleUpdateStatus = async (id, newStatus) => {
    try {
      const res = await fetch(`/api/incidents/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        notify(`Incident ${id} updated to ${newStatus.toUpperCase()}`);
        fetchIncidents();
        if (selectedIncident && selectedIncident.id === id) {
          setSelectedIncident((prev) => ({ ...prev, status: newStatus }));
        }
      }
    } catch {
      notify('Failed to update incident status.');
    }
  };

  const handleAddNote = async (id) => {
    if (!noteText.trim()) return;
    try {
      const res = await fetch(`/api/accidents/${id}/note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: noteText.trim() }),
      });
      if (res.ok) {
        notify('Investigation note saved to database.');
        setNoteText('');
        fetchIncidents();
        if (selectedIncident && selectedIncident.id === id) {
          const updatedNotes = selectedIncident.notes
            ? `${selectedIncident.notes} | ${noteText.trim()}`
            : noteText.trim();
          setSelectedIncident((prev) => ({ ...prev, notes: updatedNotes }));
        }
      }
    } catch {
      notify('Failed to save note.');
    }
  };

  const handleSimulateCollision = async () => {
    try {
      const res = await fetch('/api/accidents/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lane: 'West' }),
      });
      if (res.ok) {
        notify('⚠️ Collision Anomaly generated and committed to persistent database with snapshot evidence.');
        fetchIncidents();
      }
    } catch {
      notify('Failed to trigger collision simulation.');
    }
  };

  // Filtered and Searched list
  const displayedIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      // Tab filter
      const type = (inc.type || inc.incident_type || '').toLowerCase();
      const status = (inc.status || 'new').toLowerCase();
      if (activeTab === 'accident' && type !== 'accident') return false;
      if (activeTab === 'ambulance' && type !== 'ambulance') return false;
      if (activeTab === 'new' && status !== 'new') return false;
      if (activeTab === 'resolved' && status !== 'resolved') return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const cctv = (inc.cctv_name || inc.camera_id || '').toLowerCase();
        const desc = (inc.description || '').toLowerCase();
        const id = (inc.id || '').toLowerCase();
        const lane = (inc.lane || '').toLowerCase();
        return cctv.includes(q) || desc.includes(q) || id.includes(q) || lane.includes(q);
      }
      return true;
    });
  }, [incidents, activeTab, searchQuery]);

  // Statistics Summary
  const stats = useMemo(() => {
    const total = incidents.length;
    const accidentsCount = incidents.filter((i) => (i.type || i.incident_type) === 'accident').length;
    const ambulanceCount = incidents.filter((i) => (i.type || i.incident_type) === 'ambulance').length;
    const pendingAction = incidents.filter((i) => (i.status || 'new') === 'new').length;
    return { total, accidentsCount, ambulanceCount, pendingAction };
  }, [incidents]);

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-16">
      {/* 1. Header & Live Metric KPI Ribbon */}
      <section className="bg-gradient-to-r from-[#0D1424] via-[#111C33] to-[#0D1424] rounded-2xl p-6 border border-slate-800 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-red-400">
              VIGIL FORENSIC INCIDENT & ACCIDENT DISPATCH
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <span>Accident & Incident Feed</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-cyan-300 font-mono font-normal">
              Live Edge Perception
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Real-time catalog of verified vehicle collisions and emergency ambulance corridors. Non-hazard traffic queues and routine crawls are filtered out.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleSimulateCollision}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-red-950/90 to-red-900/90 hover:from-red-900 hover:to-red-800 text-red-200 border border-red-500/60 text-xs font-bold shadow-lg shadow-red-950/50 transition-all hover:scale-[1.02] active:scale-[0.98]"
            title="Generate a real test collision anomaly to verify database persistence and evidence capture"
          >
            <span className="material-symbols-outlined text-base text-red-400">emergency_share</span>
            <span>Simulate Collision (Demo)</span>
          </button>

          <button
            onClick={fetchIncidents}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition-all"
            title="Refresh Incidents"
          >
            <span className={`material-symbols-outlined text-lg ${loading ? 'animate-spin' : ''}`}>refresh</span>
          </button>
        </div>
      </section>

      {/* 2. Tactical Metrics Counters */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800/80 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase text-slate-400">Total Cataloged</div>
            <div className="text-2xl font-bold font-mono text-white mt-0.5">{stats.total}</div>
          </div>
          <span className="material-symbols-outlined text-3xl text-slate-600">database</span>
        </div>

        <div className="p-4 rounded-xl bg-red-950/20 border border-red-500/30 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase text-red-400">Verified Accidents</div>
            <div className="text-2xl font-bold font-mono text-red-300 mt-0.5">{stats.accidentsCount}</div>
          </div>
          <span className="material-symbols-outlined text-3xl text-red-500">car_crash</span>
        </div>

        <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/30 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase text-cyan-400">Emergency Vehicles</div>
            <div className="text-2xl font-bold font-mono text-cyan-300 mt-0.5">{stats.ambulanceCount}</div>
          </div>
          <span className="material-symbols-outlined text-3xl text-cyan-400">ambulance</span>
        </div>

        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase text-amber-400">Pending Triage</div>
            <div className="text-2xl font-bold font-mono text-amber-300 mt-0.5">{stats.pendingAction}</div>
          </div>
          <span className="material-symbols-outlined text-3xl text-amber-400">warning</span>
        </div>
      </section>

      {/* Feedback Banner */}
      {actionNotice && (
        <div className="p-3.5 rounded-xl bg-cyan-950/90 border border-cyan-500/60 text-white flex items-center justify-between text-xs font-mono shadow-lg animate-fadeIn">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-cyan-400 text-sm">info</span>
            <span>{actionNotice}</span>
          </div>
          <button onClick={() => setActionNotice(null)} className="text-slate-400 hover:text-white text-sm font-bold">✕</button>
        </div>
      )}

      {/* 3. Search and Filter Navigation */}
      <section className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { id: 'all', label: 'All Incidents', icon: 'view_list' },
            { id: 'accident', label: 'Accidents Only', icon: 'car_crash' },
            { id: 'ambulance', label: 'Ambulance Priority', icon: 'ambulance' },
            { id: 'new', label: 'New / Alerting', icon: 'notifications_active' },
            { id: 'resolved', label: 'Resolved', icon: 'check_circle' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-slate-800 text-cyan-300 border border-cyan-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <span className="material-symbols-outlined text-sm">{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative w-full sm:w-64">
          <span className="material-symbols-outlined absolute left-2.5 top-2 text-slate-500 text-sm">search</span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search CCTV name, ID..."
            className="w-full bg-[#0D1424] border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-2 text-slate-400 hover:text-white text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </section>

      {/* 4. Incident Cards Feed */}
      {displayedIncidents.length === 0 ? (
        <div className="p-16 text-center rounded-2xl bg-[#0D1424]/90 border border-slate-800/80 shadow-md">
          <span className="material-symbols-outlined text-5xl text-slate-600 block mb-3">verified</span>
          <h3 className="text-slate-200 font-bold text-base">No Incidents in Selected Filter</h3>
          <p className="text-slate-500 text-xs font-mono mt-1 max-w-md mx-auto">
            {searchQuery
              ? `No incidents matching search query "${searchQuery}".`
              : 'All monitored intersections are operating normally with zero active collisions or emergency overrides.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedIncidents.map((inc) => {
            const isAccident = (inc.type || inc.incident_type) === 'accident';
            const isAmbulance = (inc.type || inc.incident_type) === 'ambulance';
            const isNew = inc.status === 'new' || !inc.status;
            const isAck = inc.status === 'acknowledged';
            const isResolved = inc.status === 'resolved';

            // Snapshot resolution
            const snapshot = inc.frame_b64 || inc.snapshot_b64;

            // CCTV display name: direct CCTV filename
            const cctvDisplay = inc.cctv_name || (inc.camera_id ? (inc.camera_id.startsWith('CCTV:') ? inc.camera_id : `CCTV: ${inc.camera_id}`) : 'CCTV: Camera Stream');

            // Formatted time
            const timeStr = inc.timestamp
              ? new Date(inc.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
              : 'Just now';

            return (
              <div
                key={inc.id}
                className={`group rounded-2xl border flex flex-col justify-between overflow-hidden transition-all duration-200 hover:translate-y-[-2px] ${
                  isAccident
                    ? isNew
                      ? 'bg-gradient-to-b from-red-950/30 to-[#0D1424] border-red-500/60 shadow-lg shadow-red-950/30'
                      : 'bg-[#0D1424] border-red-900/40'
                    : isAmbulance
                    ? 'bg-gradient-to-b from-cyan-950/30 to-[#0D1424] border-cyan-500/60 shadow-lg shadow-cyan-950/20'
                    : 'bg-[#0D1424] border-slate-800'
                }`}
              >
                {/* Header Strip with CCTV Name */}
                <div className="p-4 pb-3">
                  <div className="flex items-center justify-between mb-2.5">
                    {/* CCTV Name Badge */}
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-700 text-cyan-300 font-mono text-[11px] font-bold shadow-sm">
                      <span className="material-symbols-outlined text-xs text-cyan-400">videocam</span>
                      <span className="truncate max-w-[170px]" title={cctvDisplay}>{cctvDisplay}</span>
                    </div>

                    {/* Incident Type & Status */}
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase border ${
                          isAccident
                            ? 'bg-red-950 text-red-300 border-red-500/50 animate-pulse'
                            : 'bg-cyan-950 text-cyan-300 border-cyan-500/50'
                        }`}
                      >
                        {isAccident ? '🚨 ACCIDENT' : '🚑 AMBULANCE'}
                      </span>
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold uppercase ${
                          isNew
                            ? 'bg-amber-950/80 text-amber-300 border border-amber-500/40'
                            : isAck
                            ? 'bg-blue-950/80 text-blue-300 border border-blue-500/40'
                            : 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40'
                        }`}
                      >
                        {inc.status || 'NEW'}
                      </span>
                    </div>
                  </div>

                  {/* Incident Snapshot Image Preview */}
                  <div
                    onClick={() => setSelectedIncident(inc)}
                    className="cursor-pointer relative rounded-xl overflow-hidden border border-slate-800 h-36 bg-black group mb-3 shadow-inner"
                  >
                    {snapshot ? (
                      <img
                        src={`data:image/jpeg;base64,${snapshot}`}
                        alt="Incident Snapshot"
                        className="w-full h-full object-cover group-hover:scale-105 transition-all duration-300"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-900/80 text-slate-500 font-mono text-xs">
                        <span className="material-symbols-outlined text-3xl mb-1 text-slate-600">center_focus_weak</span>
                        <span>[Snapshot Processing]</span>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 flex items-center justify-center text-white text-xs font-semibold transition-opacity">
                      <span className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-black/70 backdrop-blur-sm border border-white/20">
                        <span className="material-symbols-outlined text-sm text-cyan-400">zoom_in</span> Inspect Evidence
                      </span>
                    </div>
                    {/* Time watermark */}
                    <div className="absolute bottom-1.5 right-2 px-1.5 py-0.5 rounded bg-black/70 backdrop-blur-sm text-[9px] font-mono text-slate-300 border border-white/10">
                      {timeStr}
                    </div>
                  </div>

                  {/* Incident Description */}
                  <p className="text-xs font-medium text-slate-200 line-clamp-2 mb-2.5">
                    {inc.description}
                  </p>

                  {/* Metadata Telemetry Badges */}
                  <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono text-slate-400 mb-2">
                    <div className="bg-slate-900/80 px-2 py-1 rounded border border-slate-800/80 truncate">
                      ID: <strong className="text-slate-200 font-bold">{inc.id}</strong>
                    </div>
                    <div className="bg-slate-900/80 px-2 py-1 rounded border border-slate-800/80 truncate">
                      Confidence: <strong className="text-emerald-400 font-bold">{((inc.confidence || 0.88) * 100).toFixed(0)}%</strong>
                    </div>
                    <div className="bg-slate-900/80 px-2 py-1 rounded border border-slate-800/80 truncate col-span-2">
                      Approach: <strong className="text-cyan-300 font-bold">{inc.lane || 'Corridor'}</strong>
                    </div>
                  </div>

                  {/* Notes summary */}
                  {inc.notes && (
                    <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-[10px] font-mono text-slate-300 mb-1">
                      <strong className="text-cyan-400">NOTES:</strong> {inc.notes}
                    </div>
                  )}
                </div>

                {/* Triage Action Footer */}
                <div className="p-3 bg-slate-900/60 border-t border-slate-800/80 flex items-center gap-2">
                  {isNew && (
                    <button
                      onClick={() => handleUpdateStatus(inc.id, 'acknowledged')}
                      className="flex-1 py-1.5 rounded-lg bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-500/40 text-xs font-semibold transition-colors"
                    >
                      Acknowledge
                    </button>
                  )}
                  {!isResolved && (
                    <button
                      onClick={() => handleUpdateStatus(inc.id, 'resolved')}
                      className="flex-1 py-1.5 rounded-lg bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/40 text-xs font-semibold transition-colors"
                    >
                      Resolve
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setSelectedIncident(inc);
                      setNoteText('');
                    }}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
                    title="Add Investigation Notes"
                  >
                    <span className="material-symbols-outlined text-sm">edit_note</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. Forensic Evidence Inspection Modal */}
      {selectedIncident && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#0D1424] border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[92vh] overflow-y-auto p-6 shadow-2xl animate-scaleUp">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-300">
                    ID: {selectedIncident.id}
                  </span>
                  <span
                    className={`text-xs font-mono font-bold px-2 py-0.5 rounded uppercase border ${
                      (selectedIncident.type || selectedIncident.incident_type) === 'accident'
                        ? 'bg-red-950 text-red-300 border-red-500/50'
                        : 'bg-cyan-950 text-cyan-300 border-cyan-500/50'
                    }`}
                  >
                    {(selectedIncident.type || selectedIncident.incident_type) === 'accident' ? '🚨 ACCIDENT' : '🚑 AMBULANCE'}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mt-1">
                  Forensic Incident Inspection
                </h3>
                <div className="text-xs font-mono text-cyan-400 mt-0.5">
                  📹 {selectedIncident.cctv_name || selectedIncident.camera_id || 'CCTV Feed'}
                </div>
              </div>
              <button
                onClick={() => setSelectedIncident(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 text-base"
              >
                ✕
              </button>
            </div>

            {/* High-Resolution Snapshot Evidence Frame */}
            {(selectedIncident.frame_b64 || selectedIncident.snapshot_b64) && (
              <div className="rounded-xl overflow-hidden border border-slate-700 mb-4 bg-black shadow-lg">
                <img
                  src={`data:image/jpeg;base64,${selectedIncident.frame_b64 || selectedIncident.snapshot_b64}`}
                  alt="Forensic Evidence Frame"
                  className="w-full object-contain max-h-[360px]"
                />
              </div>
            )}

            {/* Description & Technical Telemetry */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-xs mb-4">
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block font-bold mb-1">
                Forensic Incident Telemetry:
              </span>
              <p className="text-slate-200 text-sm leading-relaxed mb-3">{selectedIncident.description}</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[10px] font-mono text-slate-400 pt-2 border-t border-slate-800">
                <div>Source: <span className="text-slate-200">{selectedIncident.cctv_name || selectedIncident.camera_id}</span></div>
                <div>Approach: <span className="text-slate-200">{selectedIncident.lane || 'Approach'}</span></div>
                <div>Status: <span className="text-amber-400 font-bold">{(selectedIncident.status || 'NEW').toUpperCase()}</span></div>
              </div>
            </div>

            {/* Investigation Notes Form (Persisted to Database) */}
            <div className="mb-5">
              <label className="text-xs font-mono text-slate-300 block mb-1.5 font-bold">
                Operator Investigation Notes (Persisted to Database)
              </label>
              {selectedIncident.notes && (
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300 mb-2.5">
                  <span className="text-cyan-400 font-bold block mb-1">LOGGED NOTES:</span>
                  {selectedIncident.notes}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Enter observation (e.g. Cleared by emergency responder, lane unobstructed)..."
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
                <button
                  onClick={() => handleAddNote(selectedIncident.id)}
                  className="px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shrink-0 transition-colors"
                >
                  Save Note
                </button>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="pt-3 border-t border-slate-800 flex justify-between items-center">
              <div className="flex gap-2">
                {selectedIncident.status !== 'resolved' && (
                  <button
                    onClick={() => {
                      handleUpdateStatus(selectedIncident.id, 'resolved');
                      setSelectedIncident(null);
                    }}
                    className="px-3.5 py-2 rounded-xl bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/40 text-xs font-semibold"
                  >
                    Mark Resolved
                  </button>
                )}
              </div>
              <button
                onClick={() => setSelectedIncident(null)}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
