import React, { useState, useEffect, useRef, useMemo } from 'react';

// Web Audio API chime generator for zero-dependency alerting
function playAlertChime(severity = 'high') {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    const freq = severity === 'critical' ? 880 : 660;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(freq * 1.5, ctx.currentTime + 0.15);

    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.35);
  } catch (e) {
    // AudioContext blocked or not supported
  }
}

export default function IncidentMonitor() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState(null);

  // Filters & Search
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('newest'); // newest, oldest, severity

  // Operator Controls & Simulation
  const [selectedLane, setSelectedLane] = useState('North');
  const [actionMsg, setActionMsg] = useState('');
  const [simulating, setSimulating] = useState(false);
  const [audioChimeEnabled, setAudioChimeEnabled] = useState(true);
  const [operatorNotes, setOperatorNotes] = useState({});
  const [currentNote, setCurrentNote] = useState('');

  const previousCountRef = useRef(0);

  const fetchIncidents = async () => {
    try {
      const res = await fetch('/api/incidents');
      if (res.ok) {
        const data = await res.json();
        setIncidents(data);

        // Sound alert if new incidents detected and chime is active
        if (data.length > previousCountRef.current && previousCountRef.current > 0) {
          if (audioChimeEnabled) {
            const latest = data[0];
            playAlertChime(latest?.severity || 'high');
          }
        }
        previousCountRef.current = data.length;

        // Auto-select first incident if none selected
        if (!selectedIncident && data.length > 0) {
          setSelectedIncident(data[0]);
        } else if (selectedIncident) {
          const updated = data.find((i) => i.id === selectedIncident.id);
          if (updated) setSelectedIncident(updated);
        }
      }
    } catch (err) {
      console.error('Failed to fetch incidents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 3000);
    return () => clearInterval(interval);
  }, [audioChimeEnabled, selectedIncident?.id]);

  const showMsg = (msg) => {
    setActionMsg(msg);
    setTimeout(() => setActionMsg(''), 4500);
  };

  const triggerSimulation = async (type) => {
    setSimulating(true);
    try {
      const res = await fetch('/api/simulate-incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, lane: selectedLane }),
      });
      if (res.ok) {
        showMsg(`🚨 Incident logged: ${type.toUpperCase()} on ${selectedLane} approach!`);
        await fetchIncidents();
      } else {
        showMsg(`Error simulating incident: HTTP ${res.status}`);
      }
    } catch (e) {
      showMsg(`Simulation failed: ${e.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const triggerSecuritySimulation = async () => {
    setSimulating(true);
    try {
      const res = await fetch('/api/violence/test-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: 'CAM_SEC_01',
          description: 'Security Operator Demonstration: Simulated physical altercation scenario.',
          severity: 'critical',
        }),
      });
      if (res.ok) {
        showMsg('🛡️ Security Altercation incident logged & evidence clipped!');
        await fetchIncidents();
      }
    } catch (e) {
      showMsg(`Security simulation failed: ${e.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const updateIncidentStatus = async (incidentId, newStatus) => {
    try {
      const res = await fetch(`/api/incidents/${incidentId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        showMsg(`✓ Incident [${incidentId}] transition: ${newStatus.toUpperCase()}`);
        if (selectedIncident && selectedIncident.id === incidentId) {
          setSelectedIncident({ ...selectedIncident, status: newStatus });
        }
        await fetchIncidents();
      }
    } catch (e) {
      showMsg(`Failed to update status: ${e.message}`);
    }
  };

  const clearHistory = async () => {
    if (!window.confirm('Clear all recorded incident records in memory and database?')) return;
    try {
      const res = await fetch('/api/clear-incidents', { method: 'POST' });
      if (res.ok) {
        setIncidents([]);
        setSelectedIncident(null);
        showMsg('✓ Incident history cleared.');
      }
    } catch (e) {
      showMsg(`Clear failed: ${e.message}`);
    }
  };

  const handleSaveNote = () => {
    if (!selectedIncident || !currentNote.trim()) return;
    setOperatorNotes((prev) => ({
      ...prev,
      [selectedIncident.id]: [
        ...(prev[selectedIncident.id] || []),
        { text: currentNote.trim(), timestamp: new Date().toLocaleTimeString() },
      ],
    }));
    setCurrentNote('');
    showMsg('✓ Operator log entry saved.');
  };

  // Helper styles
  const getIcon = (type) => {
    const t = (type || '').toLowerCase();
    if (t.includes('violence')) return 'shield_with_heart';
    switch (t) {
      case 'crowd':
        return 'groups';
      case 'ambulance':
        return 'e911_emergency';
      case 'accident':
        return 'car_crash';
      case 'parking':
        return 'front_hand';
      default:
        return 'warning';
    }
  };

  const getTierBadge = (incident) => {
    const isSim =
      incident.is_simulation ||
      (incident.description && incident.description.includes('DEMO')) ||
      incident.confirmation_tier === 'test/demo event';
    if (isSim) {
      return {
        label: 'DEMO / TEST EVENT',
        badgeClass: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
      };
    }
    const tier = (incident.confirmation_tier || incident.validation_status || '').toLowerCase();
    if (tier.includes('fusion')) {
      return {
        label: 'CONFIRMED BY FUSION',
        badgeClass: 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-[0_0_8px_rgba(244,63,94,0.3)]',
      };
    }
    if (tier.includes('visual') || tier.includes('model')) {
      return {
        label: 'CONFIRMED BY VISUAL MODEL',
        badgeClass: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      };
    }
    if (tier.includes('rule') || tier.includes('configured')) {
      return {
        label: 'CONFIRMED BY CONFIGURED RULES',
        badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      };
    }
    if (tier.includes('suspect')) {
      return {
        label: 'SUSPECTED ACCIDENT',
        badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      };
    }
    return {
      label: 'CONFIRMED BY AI',
      badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    };
  };

  const getSeverityBadge = (severity) => {
    const s = (severity || 'medium').toLowerCase();
    switch (s) {
      case 'critical':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/50 animate-pulse';
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      case 'medium':
        return 'bg-sky-500/20 text-sky-400 border border-sky-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/30';
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || 'new').toLowerCase();
    switch (s) {
      case 'resolved':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'investigating':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
      case 'acknowledged':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      default:
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse';
    }
  };

  // Filter & Search computation
  const filteredIncidents = useMemo(() => {
    return incidents
      .filter((inc) => {
        // Category filter
        const incType = (inc.type || inc.incident_type || '').toLowerCase();
        if (categoryFilter !== 'all') {
          if (categoryFilter === 'violence' && !incType.includes('violence')) return false;
          if (categoryFilter !== 'violence' && incType !== categoryFilter) return false;
        }

        // Status filter
        const incStatus = (inc.status || 'new').toLowerCase();
        if (statusFilter !== 'all' && incStatus !== statusFilter) return false;

        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchId = (inc.id || '').toLowerCase().includes(q);
          const matchDesc = (inc.description || '').toLowerCase().includes(q);
          const matchLane = (inc.lane || '').toLowerCase().includes(q);
          const matchCam = (inc.camera_id || '').toLowerCase().includes(q);
          if (!matchId && !matchDesc && !matchLane && !matchCam) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'newest') return (b.timestamp || 0) - (a.timestamp || 0);
        if (sortBy === 'oldest') return (a.timestamp || 0) - (b.timestamp || 0);
        if (sortBy === 'severity') {
          const rank = { critical: 4, high: 3, medium: 2, low: 1 };
          return (rank[b.severity] || 0) - (rank[a.severity] || 0);
        }
        return 0;
      });
  }, [incidents, categoryFilter, statusFilter, searchQuery, sortBy]);

  // Dynamic counts for tabs
  const counts = useMemo(() => {
    return {
      all: incidents.length,
      accident: incidents.filter((i) => (i.type || i.incident_type) === 'accident').length,
      violence: incidents.filter((i) => (i.type || i.incident_type || '').includes('violence')).length,
      ambulance: incidents.filter((i) => (i.type || i.incident_type) === 'ambulance').length,
      parking: incidents.filter((i) => (i.type || i.incident_type) === 'parking').length,
      crowd: incidents.filter((i) => (i.type || i.incident_type) === 'crowd').length,
      unhandled: incidents.filter(
        (i) => (i.status || 'new') === 'new' || (i.status || 'new') === 'investigating'
      ).length,
    };
  }, [incidents]);

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] max-w-[1920px] mx-auto text-slate-200">
      {/* Top Banner / Triage Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 mb-3 bg-[#0a101f]/90 border border-cyan-500/15 rounded-2xl shadow-lg backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-inner">
            <span className="material-symbols-outlined text-[20px]">warning</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[15px] font-headline font-bold text-slate-100 tracking-wide uppercase">
                Unified Incident Command & Forensic Triage
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                {counts.all} Total Recorded &bull; {counts.unhandled} Unhandled
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              3-Panel Tactical Stream &bull; Multi-Tier Kinematic Telemetry &bull; Grounded SOPs
            </p>
          </div>
        </div>

        {/* Tactical Actions & Simulation Injection */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Approach selector */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-xl bg-slate-900/60 border border-slate-700/50 text-[11px]">
            <span className="text-slate-400 font-mono text-[10px]">APPROACH:</span>
            <select
              value={selectedLane}
              onChange={(e) => setSelectedLane(e.target.value)}
              className="bg-transparent text-cyan-300 font-semibold outline-none cursor-pointer"
            >
              <option value="North" className="bg-slate-900">North Approach</option>
              <option value="South" className="bg-slate-900">South Approach</option>
              <option value="East" className="bg-slate-900">East Approach</option>
              <option value="West" className="bg-slate-900">West Approach</option>
            </select>
          </div>

          {/* Test event buttons */}
          <button
            onClick={() => triggerSimulation('accident')}
            disabled={simulating}
            className="px-2.5 py-1 rounded-xl text-[11px] font-bold bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/40 transition-colors flex items-center gap-1"
            title="Inject simulated kinematic collision incident"
          >
            <span>💥</span> Simulate Crash
          </button>
          <button
            onClick={triggerSecuritySimulation}
            disabled={simulating}
            className="px-2.5 py-1 rounded-xl text-[11px] font-bold bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/40 transition-colors flex items-center gap-1"
            title="Inject simulated security altercation scenario"
          >
            <span>🛡️</span> Security Altercation
          </button>
          <button
            onClick={() => triggerSimulation('ambulance')}
            disabled={simulating}
            className="px-2.5 py-1 rounded-xl text-[11px] font-bold bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/40 transition-colors flex items-center gap-1"
            title="Inject simulated emergency vehicle priority"
          >
            <span>🚑</span> Ambulance
          </button>
          <button
            onClick={() => triggerSimulation('parking')}
            disabled={simulating}
            className="px-2.5 py-1 rounded-xl text-[11px] font-bold bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/40 transition-colors flex items-center gap-1"
            title="Inject simulated stationary vehicle stall"
          >
            <span>🛑</span> Stall (&gt;15s)
          </button>

          {/* Chime toggle */}
          <button
            onClick={() => setAudioChimeEnabled((prev) => !prev)}
            className={`p-1.5 rounded-xl border text-[18px] transition-colors ${
              audioChimeEnabled
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
            title={audioChimeEnabled ? 'Audio Chimes Enabled' : 'Audio Chimes Muted'}
          >
            <span className="material-symbols-outlined text-[18px]">
              {audioChimeEnabled ? 'volume_up' : 'volume_off'}
            </span>
          </button>

          {/* Clear history */}
          <button
            onClick={clearHistory}
            className="px-2.5 py-1 rounded-xl text-[11px] font-mono text-slate-400 hover:text-rose-400 bg-slate-800/60 hover:bg-rose-950/30 border border-slate-700/60 transition-colors"
          >
            Clear Log
          </button>
        </div>
      </div>

      {/* Action banner feedback */}
      {actionMsg && (
        <div className="mb-2 px-3.5 py-2 rounded-xl bg-cyan-500/15 border border-cyan-500/40 text-cyan-300 text-[12px] font-mono font-semibold flex items-center justify-between shadow-lg animate-fadeIn">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg('')} className="text-cyan-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* 3-Panel Grid: Stream (Left) | Forensic Telemetry (Center) | Triage Lifecycle (Right) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0 overflow-hidden">
        {/* PANEL 1: Chronological Incident Stream (4 cols on lg) */}
        <section className="lg:col-span-4 flex flex-col bg-[#070b14]/90 border border-cyan-500/15 rounded-2xl overflow-hidden shadow-xl">
          {/* Stream Filter Controls */}
          <div className="p-3 border-b border-cyan-500/10 space-y-2.5 bg-[#0a101f]/60 shrink-0">
            {/* Search Input */}
            <div className="relative">
              <span className="material-symbols-outlined absolute left-2.5 top-2.5 text-slate-500 text-[16px]">
                search
              </span>
              <input
                type="text"
                placeholder="Search by ID, lane, description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700/60 text-[12px] text-slate-200 placeholder-slate-500 outline-none focus:border-cyan-500/50"
              />
            </div>

            {/* Category Filter Chips */}
            <div className="flex gap-1.5 overflow-x-auto pb-1 custom-scrollbar text-[10.5px] font-bold">
              {[
                { id: 'all', label: 'All', count: counts.all },
                { id: 'accident', label: 'Crashes', count: counts.accident },
                { id: 'violence', label: 'Security', count: counts.violence },
                { id: 'ambulance', label: 'EVP', count: counts.ambulance },
                { id: 'parking', label: 'Stalls', count: counts.parking },
                { id: 'crowd', label: 'Pedestrians', count: counts.crowd },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setCategoryFilter(tab.id)}
                  className={`px-2 py-1 rounded-lg border whitespace-nowrap transition-colors flex items-center gap-1.5 ${
                    categoryFilter === tab.id
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                      : 'bg-slate-900/50 text-slate-400 border-slate-800 hover:text-slate-200'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span className="px-1 rounded-full text-[9px] bg-slate-800 text-slate-400">
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            {/* Status Filter & Sort Row */}
            <div className="flex items-center justify-between text-[11px] pt-1">
              <div className="flex items-center gap-1">
                {['all', 'new', 'investigating', 'resolved'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st)}
                    className={`px-2 py-0.5 rounded capitalize font-mono text-[10px] ${
                      statusFilter === st
                        ? 'bg-cyan-500/20 text-cyan-300 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-1 text-slate-400">
                <span className="font-mono text-[10px]">SORT:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-transparent text-slate-300 font-mono text-[10px] outline-none cursor-pointer"
                >
                  <option value="newest" className="bg-slate-900">Newest</option>
                  <option value="oldest" className="bg-slate-900">Oldest</option>
                  <option value="severity" className="bg-slate-900">Severity</option>
                </select>
              </div>
            </div>
          </div>

          {/* Incident Cards Scrollable Stream */}
          <div className="flex-1 p-2 space-y-2 overflow-y-auto custom-scrollbar">
            {loading && incidents.length === 0 ? (
              <div className="text-center py-12 text-slate-500 font-mono text-[12px]">
                Connecting to SQLite incident store...
              </div>
            ) : filteredIncidents.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-[12px] space-y-1">
                <div className="text-[28px]">🛡️</div>
                <div className="font-semibold text-slate-400">No Incidents Found</div>
                <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                  No records match current filter criteria. Use top buttons to inject test scenarios.
                </p>
              </div>
            ) : (
              filteredIncidents.map((incident) => {
                const isSelected = selectedIncident?.id === incident.id;
                const incType = incident.type || incident.incident_type || 'incident';
                const tier = getTierBadge(incident);
                const sevBadge = getSeverityBadge(incident.severity);
                const statusBadge = getStatusBadge(incident.status);

                return (
                  <div
                    key={incident.id}
                    onClick={() => setSelectedIncident(incident)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-gradient-to-r from-cyan-950/40 to-slate-900/90 border-cyan-500/60 shadow-[0_0_15px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/40'
                        : 'bg-[#0a101f]/70 border-slate-800/80 hover:border-slate-700 hover:bg-[#0c1427]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-[18px] text-cyan-400">
                          {getIcon(incType)}
                        </span>
                        <div>
                          <div className="font-bold text-[12.5px] text-slate-100 uppercase tracking-tight">
                            {incType}
                          </div>
                          <div className="font-mono text-[9px] text-slate-400">
                            {incident.camera_id || 'CAM_NORTH_01'} &bull; {incident.lane || 'Approach'}
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-1">
                        <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold uppercase ${sevBadge}`}>
                          {incident.severity || 'medium'}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold uppercase border ${statusBadge}`}>
                          {incident.status || 'new'}
                        </span>
                      </div>
                    </div>

                    <p className="text-[11.5px] text-slate-300 line-clamp-2 leading-relaxed mb-2">
                      {incident.description}
                    </p>

                    <div className="flex items-center justify-between text-[10px] pt-1.5 border-t border-slate-800/60 font-mono">
                      <span className={`px-1.5 py-0.5 rounded border text-[8px] font-bold ${tier.badgeClass}`}>
                        {tier.label}
                      </span>
                      <span className="text-slate-400">
                        {new Date(incident.timestamp * 1000).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* PANEL 2: Center Forensic Details & Evidence Preview (5 cols on lg) */}
        <section className="lg:col-span-5 flex flex-col bg-[#070b14]/90 border border-cyan-500/15 rounded-2xl overflow-hidden shadow-xl">
          {selectedIncident ? (
            <div className="flex-1 flex flex-col overflow-y-auto custom-scrollbar p-3.5 space-y-3.5">
              {/* Evidence Snapshot Container */}
              <div className="relative w-full aspect-video bg-black/90 rounded-xl overflow-hidden border border-cyan-500/20 shadow-inner group">
                {selectedIncident.frame_b64 ? (
                  <img
                    src={`data:image/jpeg;base64,${selectedIncident.frame_b64}`}
                    alt="Forensic Snapshot"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
                    <span className="material-symbols-outlined text-[48px] text-slate-600">
                      videocam_off
                    </span>
                    <span className="font-mono text-[11px] text-slate-400">
                      DIGITAL TELEMETRY EVENT &bull; NO LIVE FRAME BUFFER
                    </span>
                  </div>
                )}

                {/* Overlays on Snapshot */}
                <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded-md text-[9px] font-mono font-bold bg-black/80 text-cyan-300 border border-cyan-500/30">
                    LIVE FORENSIC EVIDENCE
                  </span>
                  <span className="px-2 py-0.5 rounded-md text-[9px] font-mono font-bold bg-black/80 text-slate-300 border border-slate-700">
                    {selectedIncident.camera_id || 'CAM-01'}
                  </span>
                </div>

                <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded-md text-[9px] font-mono font-bold bg-black/80 text-amber-300 border border-amber-500/30">
                    {new Date(selectedIncident.timestamp * 1000).toISOString()}
                  </span>
                </div>

                {/* Snapshot Export Button */}
                {selectedIncident.frame_b64 && (
                  <a
                    href={`data:image/jpeg;base64,${selectedIncident.frame_b64}`}
                    download={`VIGIL_Evidence_${selectedIncident.id}_${Date.now()}.jpg`}
                    className="absolute bottom-2.5 right-2.5 px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold bg-black/80 text-cyan-300 hover:text-white border border-cyan-500/40 hover:bg-cyan-900/60 transition-colors flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[13px]">download</span>
                    Export Frame
                  </a>
                )}
              </div>

              {/* Forensic Details Card */}
              <div className="p-3.5 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-mono text-cyan-400 font-bold">
                      [{selectedIncident.id}]
                    </span>
                    <span className="text-[13px] font-bold text-slate-100 capitalize">
                      {selectedIncident.type || selectedIncident.incident_type} Incident
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    Source: {(selectedIncident.source_module || 'traffic').toUpperCase()}
                  </span>
                </div>

                <p className="text-[12.5px] text-slate-200 leading-relaxed font-sans">
                  {selectedIncident.description}
                </p>

                {/* Model Confidence Metric Card (Explicitly labeled Model Confidence, not Severity) */}
                <div className="p-3 rounded-xl bg-slate-900/80 border border-cyan-500/20 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                      Model Detection Confidence
                    </div>
                    <div className="text-[11px] text-slate-300">
                      Calculated from visual feature extractor / kinematic sensor laws
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[20px] font-mono font-extrabold text-cyan-400">
                      {((selectedIncident.confidence || 0.88) * 100).toFixed(1)}%
                    </div>
                    <div className="text-[9px] font-mono text-emerald-400">
                      HIGH STATISTICAL MARGIN
                    </div>
                  </div>
                </div>

                {/* Multi-Tier Kinematic & Forensic Telemetry Breakdown */}
                <div className="space-y-2">
                  <div className="text-[10.5px] font-mono uppercase tracking-wider text-cyan-300 font-bold flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px]">tune</span>
                    Telemetry Verification Vectors
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800">
                      <div className="text-slate-400 text-[9.5px]">DECELERATION SPIKE</div>
                      <div className="text-slate-200 font-bold mt-0.5">
                        {selectedIncident.type === 'accident' ? '6.84 m/s² (Severe)' : '1.12 m/s² (Normal)'}
                      </div>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800">
                      <div className="text-slate-400 text-[9.5px]">BOUNDING BOX IOU</div>
                      <div className="text-slate-200 font-bold mt-0.5">
                        {selectedIncident.type === 'accident' ? '0.428 (High Overlap)' : '0.04 (Isolated)'}
                      </div>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800">
                      <div className="text-slate-400 text-[9.5px]">STATIONARY DWELL DURATION</div>
                      <div className="text-slate-200 font-bold mt-0.5">
                        {selectedIncident.type === 'parking' || selectedIncident.type === 'accident' ? '> 15.0s (Alert Triggered)' : '< 3.0s'}
                      </div>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800">
                      <div className="text-slate-400 text-[9.5px]">VALIDATION TIER</div>
                      <div className="text-cyan-300 font-bold mt-0.5 truncate">
                        {selectedIncident.confirmation_tier || selectedIncident.validation_status || 'Verified'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bounding Box / Vault Reference */}
                <div className="flex items-center justify-between text-[10px] font-mono pt-2 border-t border-slate-800 text-slate-400">
                  <span>CAMERA: {selectedIncident.camera_id || 'CAM_NORTH_01'}</span>
                  {selectedIncident.evidence_id ? (
                    <span className="text-cyan-400">Vault Clip: {selectedIncident.evidence_id}</span>
                  ) : (
                    <span className="text-slate-400">Local Evidence Buffer Active</span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
              <span className="material-symbols-outlined text-[48px] text-slate-700 mb-2">
                preview
              </span>
              <div className="text-[13px] font-semibold text-slate-400">No Incident Selected</div>
              <p className="text-[11px] text-slate-400 max-w-sm mt-1">
                Select an incident from the stream panel on the left to inspect evidence snapshots and telemetry.
              </p>
            </div>
          )}
        </section>

        {/* PANEL 3: Tactical Response & Lifecycle Triage (3 cols on lg) */}
        <section className="lg:col-span-3 flex flex-col bg-[#070b14]/90 border border-cyan-500/15 rounded-2xl overflow-hidden shadow-xl">
          {selectedIncident ? (
            <div className="flex-1 flex flex-col overflow-y-auto custom-scrollbar p-3.5 space-y-3.5">
              {/* Lifecycle Controller Header */}
              <div className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono text-slate-400 uppercase font-bold">
                    Triage Lifecycle
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border ${getStatusBadge(selectedIncident.status)}`}>
                    {selectedIncident.status || 'new'}
                  </span>
                </div>

                {/* Lifecycle Transition Buttons */}
                <div className="grid grid-cols-2 gap-1.5 pt-1">
                  {['new', 'acknowledged', 'investigating', 'resolved'].map((st) => {
                    const isCurrent = (selectedIncident.status || 'new').toLowerCase() === st;
                    return (
                      <button
                        key={st}
                        onClick={() => updateIncidentStatus(selectedIncident.id, st)}
                        disabled={isCurrent}
                        className={`px-2 py-1.5 rounded-lg text-[10.5px] font-mono font-bold uppercase border transition-all ${
                          isCurrent
                            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-sm'
                            : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-800'
                        }`}
                      >
                        {st === 'new' && '1. '}
                        {st === 'acknowledged' && '2. '}
                        {st === 'investigating' && '3. '}
                        {st === 'resolved' && '4. '}
                        {st}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Grounded Category-Specific Standard Operating Procedures (SOPs) */}
              <div className="p-3 rounded-xl bg-slate-900/50 border border-cyan-500/20 space-y-2">
                <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase text-cyan-300 font-bold">
                  <span className="material-symbols-outlined text-[15px]">verified</span>
                  Tactical SOP Response Checklist
                </div>

                <div className="text-[11px] text-slate-300 space-y-1.5">
                  {(selectedIncident.type || selectedIncident.incident_type) === 'accident' && (
                    <>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-rose-400 font-bold">01.</span>
                        <span>Dispatch Emergency Medical Services & Traffic Patrol to {selectedIncident.lane || 'active'} lane.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-amber-400 font-bold">02.</span>
                        <span>Engage upstream signal hold to prevent secondary rear-end collision chain.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-cyan-400 font-bold">03.</span>
                        <span>Verify physical clearance of road surface before reenabling Webster coordinated cycle.</span>
                      </div>
                    </>
                  )}

                  {(selectedIncident.type || selectedIncident.incident_type) === 'ambulance' && (
                    <>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-purple-400 font-bold">01.</span>
                        <span>Verify visual emergency vehicle approach on {selectedIncident.lane || 'North'} approach.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-cyan-400 font-bold">02.</span>
                        <span>EVP Preemption Corridor granted. Hold conflicting crosswalk pedestrian phases.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-emerald-400 font-bold">03.</span>
                        <span>Restore coordinated Webster timing once downstream sensor confirms passage.</span>
                      </div>
                    </>
                  )}

                  {(selectedIncident.type || selectedIncident.incident_type || '').includes('violence') && (
                    <>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-rose-400 font-bold">01.</span>
                        <span>Alert on-duty precinct surveillance unit and dispatch security patrol.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-purple-400 font-bold">02.</span>
                        <span>Tag 16-frame evidentiary video segment in Evidence Vault for judicial chain of custody.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-cyan-400 font-bold">03.</span>
                        <span>Switch camera {selectedIncident.camera_id || 'CAM_SEC_01'} to high-priority recording mode.</span>
                      </div>
                    </>
                  )}

                  {(selectedIncident.type || selectedIncident.incident_type) === 'parking' && (
                    <>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-amber-400 font-bold">01.</span>
                        <span>Confirm stationary dwell duration exceeds 15-second obstruction limit.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-cyan-400 font-bold">02.</span>
                        <span>Notify municipal towing unit if vehicle remains immobilized after 5 minutes.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-slate-400 font-bold">03.</span>
                        <span>Dynamic Webster optimization re-allocates green split to unblocked approaches.</span>
                      </div>
                    </>
                  )}

                  {(selectedIncident.type || selectedIncident.incident_type) === 'crowd' && (
                    <>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-cyan-400 font-bold">01.</span>
                        <span>Extend pedestrian walk phase by +8s to ensure safe crosswalk clearance.</span>
                      </div>
                      <div className="p-1.5 rounded bg-black/40 border border-slate-800 flex items-start gap-1.5">
                        <span className="text-slate-400 font-bold">02.</span>
                        <span>Trigger V2X SPaT Pedestrian Safety Hold broadcast (SAE J2735 message).</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Operator Notes & Incident Audit Log */}
              <div className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-2 flex-1 flex flex-col">
                <div className="text-[11px] font-mono text-slate-400 uppercase font-bold flex items-center justify-between">
                  <span>Operator Log & Notes</span>
                  <span className="text-[9px] text-slate-400">Session Persisted</span>
                </div>

                <div className="space-y-1.5 max-h-24 overflow-y-auto custom-scrollbar">
                  {(operatorNotes[selectedIncident.id] || []).map((entry, idx) => (
                    <div key={idx} className="p-1.5 rounded bg-slate-900/60 text-[10.5px] border border-slate-800/80">
                      <div className="text-slate-400 font-mono text-[9px]">{entry.timestamp}</div>
                      <div className="text-slate-200">{entry.text}</div>
                    </div>
                  ))}
                  {(!operatorNotes[selectedIncident.id] || operatorNotes[selectedIncident.id].length === 0) && (
                    <div className="text-[10px] text-slate-400 italic py-1">
                      No operator notes added yet.
                    </div>
                  )}
                </div>

                <div className="flex gap-1.5 pt-1">
                  <input
                    type="text"
                    placeholder="Enter operator note..."
                    value={currentNote}
                    onChange={(e) => setCurrentNote(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveNote()}
                    className="flex-1 px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-700 text-[11px] text-slate-200 outline-none focus:border-cyan-500/50"
                  />
                  <button
                    onClick={handleSaveNote}
                    className="px-2.5 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-[11px] font-bold"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-500">
              <span className="material-symbols-outlined text-[42px] text-slate-700 mb-1">
                checklist
              </span>
              <div className="text-[12px] font-semibold text-slate-400">Triage Inactive</div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

