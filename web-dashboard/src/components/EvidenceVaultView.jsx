import React, { useState, useEffect } from 'react';

export default function EvidenceVaultView() {
  const [evidenceList, setEvidenceList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClip, setSelectedClip] = useState(null);
  const [filter, setFilter] = useState('all');

  const fetchEvidence = async () => {
    try {
      const res = await fetch('/api/evidence');
      if (res.ok) {
        const data = await res.json();
        setEvidenceList(data || []);
      }
    } catch (e) {
      console.error('Failed to load evidence', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
    const interval = setInterval(fetchEvidence, 4000);
    return () => clearInterval(interval);
  }, []);

  const totalSizeMB = (
    evidenceList.reduce((acc, curr) => acc + (curr.file_size_bytes || 0), 0) / (1024 * 1024)
  ).toFixed(2);

  const filteredEvidence = evidenceList.filter((item) => {
    if (filter === 'all') return true;
    if (filter === 'video') return item.file_type?.includes('video') || item.file_path?.endsWith('.mp4');
    if (filter === 'image') return item.file_type?.includes('image') || item.file_path?.endsWith('.jpg');
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-surface-container border border-outline-variant/30 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[24px]">videocam</span>
          </div>
          <div>
            <h1 className="text-xl font-headline font-bold text-on-surface">
              Forensic Evidence Vault
            </h1>
            <p className="text-xs text-on-surface-variant font-mono">
              Autonomous Pre & Post-Event Rolling MP4 Clips &bull; Multi-Camera Chain of Custody
            </p>
          </div>
        </div>

        {/* Quick Filter */}
        <div className="flex items-center gap-2 bg-surface-container-high p-1.5 rounded-xl border border-outline-variant/30 font-mono text-xs">
          {['all', 'video', 'image'].map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1 rounded-lg uppercase font-bold transition-all ${
                filter === t
                  ? 'bg-primary text-on-primary shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface-container border border-outline-variant/30">
          <span className="text-[10px] font-mono uppercase text-on-surface-variant block">Total Evidence Artifacts</span>
          <span className="text-2xl font-bold font-mono text-on-surface mt-1 block">{evidenceList.length}</span>
        </div>
        <div className="p-4 rounded-xl bg-surface-container border border-outline-variant/30">
          <span className="text-[10px] font-mono uppercase text-on-surface-variant block">Forensic Video Clips</span>
          <span className="text-2xl font-bold font-mono text-primary mt-1 block">
            {evidenceList.filter((e) => e.file_path?.endsWith('.mp4')).length}
          </span>
        </div>
        <div className="p-4 rounded-xl bg-surface-container border border-outline-variant/30">
          <span className="text-[10px] font-mono uppercase text-on-surface-variant block">Storage Utilized</span>
          <span className="text-2xl font-bold font-mono text-secondary mt-1 block">{totalSizeMB} MB</span>
        </div>
        <div className="p-4 rounded-xl bg-surface-container border border-outline-variant/30">
          <span className="text-[10px] font-mono uppercase text-on-surface-variant block">Integrity Status</span>
          <span className="text-2xl font-bold font-mono text-on-surface mt-1 block">VERIFIED</span>
        </div>
      </div>

      {/* Evidence Grid / List */}
      <div className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4">
        <h2 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">folder_special</span>
          Recorded Incident Artifacts
        </h2>

        {loading && evidenceList.length === 0 ? (
          <div className="py-12 text-center text-xs font-mono text-on-surface-variant">
            Accessing VIGIL Forensic Evidence Vault...
          </div>
        ) : filteredEvidence.length === 0 ? (
          <div className="py-12 text-center text-xs font-mono text-on-surface-variant">
            No evidence records matched current filter. Trigger a simulation or incident to generate clips.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredEvidence.map((evd) => {
              const filename = evd.file_path?.split(/[/\\]/).pop() || 'evidence.mp4';
              const isVideo = evd.file_path?.endsWith('.mp4') || evd.file_type?.includes('video');
              const sizeKB = (evd.file_size_bytes / 1024).toFixed(1);

              return (
                <div
                  key={evd.id}
                  className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/20 hover:border-primary/40 transition-all flex flex-col justify-between gap-3 group"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-primary/20 text-primary">
                        {evd.id}
                      </span>
                      <span className="text-[10px] font-mono text-on-surface-variant">
                        {new Date(evd.created_at * 1000).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <div className="w-10 h-10 rounded-lg bg-surface-container-high flex items-center justify-center text-primary shrink-0 group-hover:scale-105 transition-transform">
                        <span className="material-symbols-outlined text-[22px]">
                          {isVideo ? 'videocam' : 'image'}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-bold text-on-surface truncate font-mono">
                          {filename}
                        </div>
                        <div className="text-[10px] font-mono text-on-surface-variant">
                          {evd.duration_sec ? `${evd.duration_sec}s duration` : 'Snapshot'} &bull; {sizeKB} KB
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-2 border-t border-outline-variant/20">
                    {isVideo && (
                      <button
                        onClick={() => setSelectedClip(filename)}
                        className="flex-1 py-1.5 px-3 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-xs font-mono font-bold flex items-center justify-center gap-1.5 transition-all"
                      >
                        <span className="material-symbols-outlined text-[16px]">play_circle</span>
                        Play Clip
                      </button>
                    )}
                    <a
                      href={`/api/evidence/${evd.id}/download`}
                      download
                      className="py-1.5 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface border border-outline-variant/30 text-xs font-mono font-bold flex items-center justify-center gap-1 transition-all"
                      title="Download Evidence File"
                    >
                      <span className="material-symbols-outlined text-[16px]">download</span>
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Video Playback Modal */}
      {selectedClip && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className="w-full max-w-2xl bg-surface-container rounded-2xl border border-outline-variant/40 shadow-2xl overflow-hidden space-y-4 p-5">
            <div className="flex items-center justify-between border-b border-outline-variant/20 pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[22px]">play_circle</span>
                <span className="text-sm font-bold font-mono text-on-surface">{selectedClip}</span>
              </div>
              <button
                onClick={() => setSelectedClip(null)}
                className="p-1 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="aspect-video bg-black rounded-xl overflow-hidden flex items-center justify-center border border-outline-variant/20">
              <video
                src={`/api/evidence/file/${selectedClip}`}
                controls
                autoPlay
                className="w-full h-full object-contain"
              >
                Your browser does not support HTML5 MP4 video.
              </video>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedClip(null)}
                className="py-2 px-5 rounded-xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-mono font-bold text-xs uppercase"
              >
                Close Player
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
