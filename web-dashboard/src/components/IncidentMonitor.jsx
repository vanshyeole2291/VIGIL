import { useState, useEffect } from 'react';

export default function IncidentMonitor() {
    const [incidents, setIncidents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // all, accident, ambulance, crowd, parking, violence
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [selectedLane, setSelectedLane] = useState('North');
    const [actionMsg, setActionMsg] = useState('');
    const [simulating, setSimulating] = useState(false);

    const fetchIncidents = async () => {
        try {
            const res = await fetch('/api/incidents');
            if (res.ok) {
                const data = await res.json();
                setIncidents(data);
            }
        } catch (err) {
            console.error("Failed to fetch incidents", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchIncidents();
        const interval = setInterval(fetchIncidents, 2500);
        return () => clearInterval(interval);
    }, []);

    const showMsg = (msg) => {
        setActionMsg(msg);
        setTimeout(() => setActionMsg(''), 4000);
    };

    const triggerSimulation = async (type) => {
        setSimulating(true);
        try {
            const res = await fetch('/api/simulate-incident', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, lane: selectedLane })
            });
            if (res.ok) {
                const data = await res.json();
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
                    severity: 'critical'
                })
            });
            if (res.ok) {
                showMsg('🛡️ Security Altercation incident logged & MP4 evidence clipped!');
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
                body: JSON.stringify({ status: newStatus })
            });
            if (res.ok) {
                showMsg(`✓ Incident ${incidentId} marked as ${newStatus.toUpperCase()}`);
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
        if (!window.confirm("Clear all recorded incident evidence logs in memory and database?")) return;
        try {
            const res = await fetch('/api/clear-incidents', { method: 'POST' });
            if (res.ok) {
                setIncidents([]);
                showMsg('✓ Incident history cleared.');
            }
        } catch (e) {
            showMsg(`Clear failed: ${e.message}`);
        }
    };

    const getTypeColor = (type) => {
        const t = (type || '').toLowerCase();
        if (t.includes('violence')) return '#f43f5e';
        switch (t) {
            case 'crowd': return 'var(--blue)';
            case 'ambulance': return 'var(--purple)';
            case 'accident': return 'var(--red)';
            case 'parking': return 'var(--orange)';
            default: return 'var(--text-muted)';
        }
    };

    const getIcon = (type) => {
        const t = (type || '').toLowerCase();
        if (t.includes('violence')) return '🛡️';
        switch (t) {
            case 'crowd': return '👥';
            case 'ambulance': return '🚑';
            case 'accident': return '💥';
            case 'parking': return '🛑';
            default: return '⚠️';
        }
    };

    const getMethodology = (type) => {
        const t = (type || '').toLowerCase();
        if (t.includes('violence')) return '16-Frame Temporal Sequence & MobileNetV2-BiLSTM Graph';
        switch (t) {
            case 'accident': return 'Kinematic IoU Overlap & Two-Phase Dwell Impact';
            case 'ambulance': return 'Optical HSV Multi-Spectral & Acoustic FFT Preemption';
            case 'parking': return 'Stationary Dwell Delay Threshold (>15s)';
            case 'crowd': return 'Crosswalk Radar & Pedestrian Safety Hold';
            default: return 'Autonomous Computer Vision Anomaly Detection';
        }
    };

    const counts = {
        all: incidents.length,
        accident: incidents.filter(i => (i.type || i.incident_type) === 'accident').length,
        ambulance: incidents.filter(i => (i.type || i.incident_type) === 'ambulance').length,
        parking: incidents.filter(i => (i.type || i.incident_type) === 'parking').length,
        crowd: incidents.filter(i => (i.type || i.incident_type) === 'crowd').length,
        violence: incidents.filter(i => (i.type || i.incident_type || '').includes('violence')).length,
    };

    const filtered = incidents.filter(inc => {
        if (filter === 'all') return true;
        const incType = (inc.type || inc.incident_type || '').toLowerCase();
        if (filter === 'violence') return incType.includes('violence');
        return incType === filter;
    });

    return (
        <div style={{ padding: '20px 24px', flex: 1, overflowY: 'auto' }}>
            {/* Header with Title and Filters */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                        width: '36px', height: '36px', borderRadius: '10px',
                        background: 'rgba(244, 63, 94, 0.2)', border: '1px solid var(--red)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px'
                    }}>
                        🚨
                    </div>
                    <div>
                        <h2 style={{ fontSize: '18px', fontWeight: '800', color: '#fff', margin: 0, letterSpacing: '-0.3px' }}>
                            VIGIL Unified Incident Command & Forensic Archive
                        </h2>
                        <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
                            Traffic Kinematic Collision Analysis &bull; AI Security Altercation Detection &bull; SQLite Persistence
                        </p>
                    </div>
                </div>

                {/* Filter Tabs with Dynamic Counts */}
                <div style={{ display: 'flex', gap: '6px', background: 'rgba(15, 23, 42, 0.6)', padding: '3px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)', flexWrap: 'wrap' }}>
                    {[
                        { id: 'all', label: 'All', icon: '📋', count: counts.all },
                        { id: 'accident', label: 'Accidents', icon: '💥', count: counts.accident },
                        { id: 'violence', label: 'Security Altercations', icon: '🛡️', count: counts.violence },
                        { id: 'ambulance', label: 'Ambulances', icon: '🚑', count: counts.ambulance },
                        { id: 'parking', label: 'Stalls (>15s)', icon: '🛑', count: counts.parking },
                        { id: 'crowd', label: 'Pedestrians', icon: '👥', count: counts.crowd },
                    ].map(f => (
                        <button
                            key={f.id}
                            onClick={() => setFilter(f.id)}
                            style={{
                                background: filter === f.id ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                                color: filter === f.id ? '#38bdf8' : 'var(--text-muted)',
                                border: filter === f.id ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid transparent',
                                padding: '6px 10px', borderRadius: '6px',
                                fontSize: '11px', fontWeight: '700', cursor: 'pointer',
                                display: 'flex', alignItems: 'center', gap: '5px'
                            }}>
                            <span>{f.icon}</span> {f.label}
                            <span style={{
                                background: filter === f.id ? 'rgba(56, 189, 248, 0.3)' : 'rgba(255,255,255,0.06)',
                                padding: '1px 5px', borderRadius: '10px', fontSize: '10px',
                                color: filter === f.id ? '#fff' : 'var(--text-dim)'
                            }}>
                                {f.count}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Interactive Simulation & Testing Action Bar */}
            <div className="glass-panel" style={{ padding: '12px 16px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', fontWeight: '800', color: 'var(--blue)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        🧪 Simulation & Test Injection:
                    </span>
                    <select
                        value={selectedLane}
                        onChange={(e) => setSelectedLane(e.target.value)}
                        style={{
                            background: '#0a0f1d', color: '#fff', border: '1px solid rgba(255,255,255,0.15)',
                            padding: '4px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: '700'
                        }}>
                        <option value="North">North Approach</option>
                        <option value="South">South Approach</option>
                        <option value="East">East Approach</option>
                        <option value="West">West Approach</option>
                    </select>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                        onClick={() => triggerSimulation('accident')}
                        disabled={simulating}
                        className="tactical-btn"
                        style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid var(--red)', color: '#f43f5e', fontSize: '11px', padding: '6px 10px' }}>
                        💥 Simulate Crash
                    </button>
                    <button
                        onClick={triggerSecuritySimulation}
                        disabled={simulating}
                        className="tactical-btn"
                        style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#f87171', fontSize: '11px', padding: '6px 10px' }}>
                        🛡️ Simulate Security Altercation
                    </button>
                    <button
                        onClick={() => triggerSimulation('ambulance')}
                        disabled={simulating}
                        className="tactical-btn"
                        style={{ background: 'rgba(168, 85, 247, 0.15)', border: '1px solid var(--purple)', color: '#c084fc', fontSize: '11px', padding: '6px 10px' }}>
                        🚑 Test Ambulance Priority
                    </button>
                    <button
                        onClick={() => triggerSimulation('parking')}
                        disabled={simulating}
                        className="tactical-btn"
                        style={{ background: 'rgba(249, 115, 22, 0.15)', border: '1px solid var(--orange)', color: '#fb923c', fontSize: '11px', padding: '6px 10px' }}>
                        🛑 Test Vehicle Stall
                    </button>
                    <button
                        onClick={() => triggerSimulation('crowd')}
                        disabled={simulating}
                        className="tactical-btn"
                        style={{ background: 'rgba(56, 189, 248, 0.15)', border: '1px solid var(--blue)', color: '#38bdf8', fontSize: '11px', padding: '6px 10px' }}>
                        👥 Test Pedestrian Conflict
                    </button>
                    <button
                        onClick={clearHistory}
                        className="tactical-btn"
                        style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontSize: '11px', padding: '6px 10px' }}>
                        🗑️ Clear Log
                    </button>
                </div>
            </div>

            {/* Action Feedback Banner */}
            {actionMsg && (
                <div style={{
                    marginBottom: '16px',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: '700',
                    background: 'rgba(56, 189, 248, 0.15)',
                    border: '1px solid rgba(56, 189, 248, 0.5)',
                    color: '#38bdf8',
                    animation: 'fadeIn 0.2s ease'
                }}>
                    {actionMsg}
                </div>
            )}

            {/* Main Content Area */}
            {loading && incidents.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '60px' }}>
                    Loading incident repository from SQLite...
                </div>
            ) : filtered.length === 0 ? (
                <div className="glass-panel" style={{ textAlign: 'center', padding: '50px 24px', borderRadius: '16px' }}>
                    <div style={{ fontSize: '42px', marginBottom: '12px' }}>🛡️</div>
                    <h3 style={{ color: 'var(--green)', fontSize: '16px', fontWeight: '700', marginBottom: '6px' }}>
                        No {filter !== 'all' ? filter.toUpperCase() : ''} Incidents Currently Filtered
                    </h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '12px', maxWidth: '480px', margin: '0 auto 16px auto' }}>
                        No anomalies matching this filter. You can inject on-demand test scenarios above to immediately verify incident capture and evidence logging.
                    </p>
                </div>
            ) : (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
                    gap: '16px'
                }}>
                    {filtered.map((incident, idx) => {
                        const incType = incident.type || incident.incident_type || 'incident';
                        const incId = incident.id || `INC_${idx}`;
                        const statusVal = incident.status || 'new';

                        return (
                            <div
                                key={idx}
                                onClick={() => setSelectedIncident(incident)}
                                style={{
                                    background: '#090e1a',
                                    borderRadius: '10px',
                                    border: '1px solid rgba(255, 255, 255, 0.08)',
                                    overflow: 'hidden',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
                                    cursor: 'pointer',
                                    transition: 'transform 0.15s ease, border-color 0.15s ease'
                                }}
                                onMouseEnter={e => {
                                    e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                }}
                                onMouseLeave={e => {
                                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                                    e.currentTarget.style.transform = 'translateY(0)';
                                }}
                            >
                                {/* Snapshot Image Container */}
                                <div style={{ position: 'relative', width: '100%', height: '215px', background: '#020617', overflow: 'hidden' }}>
                                    {incident.frame_b64 ? (
                                        <img
                                            src={`data:image/jpeg;base64,${incident.frame_b64}`}
                                            alt="Incident Snapshot"
                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        />
                                    ) : (
                                        <div style={{
                                            display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center',
                                            flexDirection: 'column', color: '#64748b', background: '#040814'
                                        }}>
                                            <span style={{ fontSize: '38px', marginBottom: '6px' }}>{getIcon(incType)}</span>
                                            <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '700' }}>
                                                {incType.toUpperCase()} EVENT
                                            </span>
                                            {incident.evidence_id && (
                                                <span style={{ fontSize: '10px', color: '#38bdf8', marginTop: '4px' }}>
                                                    📹 MP4 Clip Available in Vault
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {/* Module Tag Overlay */}
                                    <div style={{
                                        position: 'absolute', top: '10px', left: '10px',
                                        background: incident.source_module === 'security' ? 'rgba(239, 68, 68, 0.85)' : 'rgba(59, 130, 246, 0.85)',
                                        color: '#fff', fontSize: '9px', fontWeight: '800', textTransform: 'uppercase',
                                        padding: '2px 8px', borderRadius: '4px', letterSpacing: '0.5px'
                                    }}>
                                        {incident.source_module || 'traffic'}
                                    </div>

                                    {/* Severity Tag */}
                                    <div style={{
                                        position: 'absolute', top: '10px', right: '10px',
                                        background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,255,255,0.2)',
                                        color: incident.severity === 'critical' ? '#f43f5e' : '#fbbf24',
                                        fontSize: '9px', fontWeight: '800', textTransform: 'uppercase',
                                        padding: '2px 6px', borderRadius: '4px'
                                    }}>
                                        {incident.severity || 'high'}
                                    </div>
                                </div>

                                {/* Card Footer Info Block */}
                                <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '8px', background: '#090e1a' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <span style={{
                                            fontSize: '11px',
                                            color: '#94a3b8',
                                            fontFamily: 'JetBrains Mono, monospace',
                                            fontWeight: '500'
                                        }}>
                                            {new Date(incident.timestamp * 1000).toLocaleTimeString()} &bull; {incId}
                                        </span>

                                        <span style={{
                                            background: statusVal === 'resolved' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                                            border: statusVal === 'resolved' ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(245, 158, 11, 0.4)',
                                            padding: '2px 8px',
                                            borderRadius: '6px',
                                            fontSize: '10px',
                                            fontWeight: '800',
                                            color: statusVal === 'resolved' ? '#10b981' : '#f59e0b',
                                            textTransform: 'uppercase'
                                        }}>
                                            {statusVal}
                                        </span>
                                    </div>

                                    <div style={{
                                        fontSize: '13px',
                                        color: '#f8fafc',
                                        fontWeight: '500',
                                        lineHeight: 1.45,
                                        wordBreak: 'break-word',
                                        overflowWrap: 'break-word'
                                    }}>
                                        {incident.description || 'Automatic anomaly alert captured.'}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* High-Resolution Inspection Modal */}
            {selectedIncident && (
                <div style={{
                    position: 'fixed', inset: 0, zIndex: 1000,
                    background: 'rgba(0, 0, 0, 0.88)', backdropFilter: 'blur(12px)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px'
                }}>
                    <div className="glass-panel" style={{
                        maxWidth: '880px', width: '100%',
                        background: '#090e1a', borderRadius: '16px', overflow: 'hidden',
                        border: '1px solid rgba(56, 189, 248, 0.4)',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)'
                    }}>
                        {/* Modal Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '20px' }}>{getIcon(selectedIncident.type || selectedIncident.incident_type)}</span>
                                <div>
                                    <span style={{ fontWeight: '800', fontSize: '14px', textTransform: 'uppercase', color: getTypeColor(selectedIncident.type || selectedIncident.incident_type) }}>
                                        {selectedIncident.type || selectedIncident.incident_type} Incident Details
                                    </span>
                                    <span className="mono" style={{ fontSize: '11px', color: 'var(--text-dim)', marginLeft: '10px' }}>
                                        [{selectedIncident.id || `INC_${Math.floor(selectedIncident.timestamp % 10000)}`}]
                                    </span>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedIncident(null)}
                                className="tactical-btn"
                                style={{ padding: '4px 10px', fontSize: '12px' }}
                            >
                                ✕ Close
                            </button>
                        </div>

                        {/* Modal Snapshot View */}
                        <div style={{ padding: '16px', background: '#000', maxHeight: '550px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                            {selectedIncident.frame_b64 ? (
                                <img
                                    src={`data:image/jpeg;base64,${selectedIncident.frame_b64}`}
                                    alt="Enlarged Incident Snapshot"
                                    style={{ maxWidth: '100%', maxHeight: '480px', objectFit: 'contain', borderRadius: '8px' }}
                                />
                            ) : (
                                <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                                    <div style={{ fontSize: '40px', marginBottom: '10px' }}>{getIcon(selectedIncident.type || selectedIncident.incident_type)}</div>
                                    <p style={{ margin: 0, fontSize: '13px' }}>Digital event telemetry captured with automated evidence record.</p>
                                    {selectedIncident.evidence_id && (
                                        <p style={{ fontSize: '11px', color: '#38bdf8', marginTop: '6px' }}>
                                            Evidence File: {selectedIncident.evidence_id} (Stored in Evidence Vault)
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Modal Footer with Triage Controls */}
                        <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                            <div>
                                <div style={{ fontSize: '13px', fontWeight: '700', color: '#fff', marginBottom: '4px' }}>
                                    {selectedIncident.description}
                                </div>
                                <div className="mono" style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                                    Module: {selectedIncident.source_module?.toUpperCase() || 'TRAFFIC'} &bull; Status: {selectedIncident.status?.toUpperCase() || 'NEW'} &bull; Timestamp: {new Date(selectedIncident.timestamp * 1000).toISOString()}
                                </div>
                            </div>

                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <button
                                    onClick={() => updateIncidentStatus(selectedIncident.id, 'acknowledged')}
                                    className="tactical-btn"
                                    style={{ padding: '6px 12px', fontSize: '11px', background: 'rgba(245, 158, 11, 0.2)', border: '1px solid #f59e0b', color: '#fbbf24' }}
                                >
                                    ✓ Acknowledge
                                </button>
                                <button
                                    onClick={() => updateIncidentStatus(selectedIncident.id, 'resolved')}
                                    className="tactical-btn"
                                    style={{ padding: '6px 12px', fontSize: '11px', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#34d399' }}
                                >
                                    ✓ Resolve
                                </button>
                                {selectedIncident.frame_b64 && (
                                    <a
                                        href={`data:image/jpeg;base64,${selectedIncident.frame_b64}`}
                                        download={`incident_evidence_${selectedIncident.type}_${Date.now()}.jpg`}
                                        className="tactical-btn tactical-btn-primary"
                                        style={{ textDecoration: 'none', padding: '6px 12px', fontSize: '11px' }}
                                    >
                                        💾 Export Snapshot
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
