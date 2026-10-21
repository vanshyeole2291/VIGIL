import React, { useState, useEffect } from 'react';

export default function EvidenceDatabaseView() {
  const [evidenceList, setEvidenceList] = useState([]);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const fetchEvidence = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/evidence');
      if (res.ok) {
        const data = await res.json();
        setEvidenceList(data || []);
      }
    } catch (e) {
      console.error('Failed to fetch evidence list', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, []);

  const handleCopySha = (sha, id) => {
    if (!sha) return;
    navigator.clipboard.writeText(sha);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredEvidence = evidenceList.filter((item) => {
    const matchesSearch =
      (item.incident_id || '').toLowerCase().includes(search.toLowerCase()) ||
      (item.cctv_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (item.camera_id || '').toLowerCase().includes(search.toLowerCase()) ||
      (item.lane || '').toLowerCase().includes(search.toLowerCase()) ||
      (item.checksum_sha256 || '').toLowerCase().includes(search.toLowerCase());
    const matchesType = typeFilter === 'all' || item.file_type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* 1. Header Toolbar */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-slate-800 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400">
              Chain of Custody & Forensic Store
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Evidence Database
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Immutable forensic snapshots and accident video clips with SHA-256 cryptographic integrity hashes.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchEvidence}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-colors"
          >
            <span className="material-symbols-outlined text-base">refresh</span>
            <span>Reload Store</span>
          </button>
        </div>
      </section>

      {/* 2. Filter & Search Controls */}
      <div className="p-4 rounded-xl bg-[#0D1424] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <span className="material-symbols-outlined absolute left-3 top-2.5 text-slate-400 text-base">search</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by CCTV, ID, Lane, SHA-256..."
            className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          {['all', 'snapshot', 'video/mp4'].map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all ${
                typeFilter === t
                  ? 'bg-amber-950/70 text-amber-300 border border-amber-500/40'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
              }`}
            >
              {t === 'video/mp4' ? 'Video Proof' : t}
            </button>
          ))}
          <span className="text-xs font-mono text-slate-400 ml-2">
            {filteredEvidence.length} Evidence Records
          </span>
        </div>
      </div>

      {/* 3. Evidence Cards Grid */}
      {filteredEvidence.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-[#0D1424] border border-slate-800">
          <span className="material-symbols-outlined text-5xl text-slate-600 block mb-2">folder_off</span>
          <h3 className="text-slate-200 font-bold text-sm">No Forensic Evidence Files Found</h3>
          <p className="text-slate-500 text-xs font-mono mt-1">
            Evidence packages are generated automatically upon confirmed accident detections or camera events.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEvidence.map((item) => {
            const previewImg = item.thumbnail_b64 || item.snapshot_b64;
            const cctvLabel = item.cctv_name || item.camera_id || (item.file_path ? item.file_path.split('/').pop().split('\\').pop() : 'CCTV');
            const isVideo = item.file_type === 'video/mp4' || (item.file_path && item.file_path.endsWith('.mp4'));

            return (
              <div
                key={item.id}
                className="p-4 rounded-xl bg-[#0D1424] border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-all shadow-md group"
              >
                <div>
                  {/* Header: CCTV Source & Type Badge */}
                  <div className="flex items-center justify-between mb-2.5">
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-slate-900 border border-slate-700 text-cyan-300 font-mono text-[11px] font-bold truncate max-w-[170px]" title={cctvLabel}>
                      <span className="material-symbols-outlined text-xs text-cyan-400">videocam</span>
                      <span className="truncate">{cctvLabel}</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold bg-amber-950/80 text-amber-300 border border-amber-500/30">
                      {item.incident_type ? `🚨 ${item.incident_type.toUpperCase()}` : isVideo ? '🎥 VIDEO PROOF' : '📸 SNAPSHOT'}
                    </span>
                  </div>

                  {/* Incident ID & Date */}
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
                    <span className="text-slate-300 font-semibold">{item.incident_id || item.id}</span>
                    <span>{item.created_at ? new Date(item.created_at * 1000).toLocaleString() : 'Recent'}</span>
                  </div>

                  {/* Visual Thumbnail Snapshot */}
                  <div
                    onClick={() => setSelectedItem(item)}
                    className="cursor-pointer rounded-xl overflow-hidden border border-slate-800 h-36 bg-black mb-3 group/thumb relative shadow-inner"
                  >
                    {previewImg ? (
                      <img
                        src={`data:image/jpeg;base64,${previewImg}`}
                        alt="Evidence Forensic Preview"
                        className="w-full h-full object-cover group-hover/thumb:scale-105 transition-all duration-300"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-900/90 text-slate-500 font-mono text-xs">
                        <span className="material-symbols-outlined text-3xl mb-1 text-slate-600">center_focus_strong</span>
                        <span>[Forensic Telemetry File]</span>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover/thumb:opacity-100 flex items-center justify-center text-white text-xs font-semibold transition-opacity gap-1.5">
                      <span className="material-symbols-outlined text-base">{isVideo ? 'play_circle' : 'zoom_in'}</span>
                      <span>{isVideo ? 'Play Proof Video' : 'Enlarge Snapshot'}</span>
                    </div>
                    {isVideo && (
                      <div className="absolute bottom-2 left-2 px-1.5 py-0.5 rounded bg-black/80 border border-white/20 text-[10px] font-mono text-amber-300 flex items-center gap-1">
                        <span className="material-symbols-outlined text-xs text-amber-400">videocam</span>
                        <span>{item.duration_sec ? `${Math.round(item.duration_sec)}s Clip` : 'MP4 Clip'}</span>
                      </div>
                    )}
                  </div>

                  {/* SHA-256 Checksum Pill */}
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[10px] mb-3">
                    <div className="flex items-center justify-between text-slate-400 mb-1">
                      <span className="font-bold text-cyan-400">SHA-256 HASH:</span>
                      <button
                        onClick={() => handleCopySha(item.checksum_sha256, item.id)}
                        className="text-slate-400 hover:text-white flex items-center gap-0.5"
                        title="Copy SHA-256 Checksum"
                      >
                        <span className="material-symbols-outlined text-xs">
                          {copiedId === item.id ? 'check' : 'content_copy'}
                        </span>
                        <span>{copiedId === item.id ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <div className="text-slate-300 truncate" title={item.checksum_sha256}>
                      {item.checksum_sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
                  <a
                    href={`/api/evidence/${item.id}/download`}
                    download
                    className="flex-1 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                  >
                    <span className="material-symbols-outlined text-sm">download</span>
                    <span>Download</span>
                  </a>
                  <button
                    onClick={() => setSelectedItem(item)}
                    className="px-3.5 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/40 text-xs font-semibold flex items-center gap-1 transition-all"
                  >
                    <span className="material-symbols-outlined text-xs">{isVideo ? 'play_arrow' : 'visibility'}</span>
                    <span>{isVideo ? 'Play' : 'Preview'}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 4. Inspection Modal with Inline Video Player & Snapshot */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-[#0D1424] border border-slate-800 rounded-2xl max-w-2xl w-full p-5 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>Forensic Evidence Proof · {selectedItem.id}</span>
                </h3>
                <span className="text-xs font-mono text-cyan-300">
                  {selectedItem.cctv_name || selectedItem.camera_id || 'CCTV Stream'} · Incident: {selectedItem.incident_id || selectedItem.id}
                </span>
              </div>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            {/* Media Player: MP4 Video Playback or High-Res Snapshot */}
            {selectedItem.file_type === 'video/mp4' || (selectedItem.file_path && selectedItem.file_path.endsWith('.mp4')) ? (
              <div className="rounded-xl overflow-hidden border border-slate-700 bg-black relative">
                <video
                  controls
                  autoPlay
                  src={`/api/evidence/file/${(selectedItem.file_path || '').split('/').pop().split('\\').pop()}`}
                  poster={selectedItem.thumbnail_b64 || selectedItem.snapshot_b64 ? `data:image/jpeg;base64,${selectedItem.thumbnail_b64 || selectedItem.snapshot_b64}` : undefined}
                  className="w-full max-h-[380px] object-contain"
                >
                  Your browser does not support the video tag.
                </video>
              </div>
            ) : (selectedItem.thumbnail_b64 || selectedItem.snapshot_b64) ? (
              <div className="rounded-xl overflow-hidden border border-slate-700 bg-black">
                <img
                  src={`data:image/jpeg;base64,${selectedItem.thumbnail_b64 || selectedItem.snapshot_b64}`}
                  alt="Full Evidence Frame"
                  className="w-full object-contain max-h-[380px]"
                />
              </div>
            ) : null}

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
              <span className="text-cyan-400 font-bold block mb-1">SHA-256 Checksum:</span>
              <p className="text-slate-300 break-all">{selectedItem.checksum_sha256}</p>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <a
                href={`/api/evidence/${selectedItem.id}/download`}
                download
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs inline-flex items-center gap-1.5 transition-colors"
              >
                <span className="material-symbols-outlined text-sm">download</span>
                Download File
              </a>
              <button
                onClick={() => setSelectedItem(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
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
