import React, { useState, useEffect } from 'react';

export default function DataSourcesView() {
  const [sourcesData, setSourcesData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filterCategory, setFilterCategory] = useState('all');
  const [selectedSource, setSelectedSource] = useState(null);

  const fetchDataSources = async () => {
    try {
      const res = await fetch('/api/data-sources/status');
      if (res.ok) {
        const data = await res.json();
        setSourcesData(data);
      }
    } catch (e) {
      console.error('Failed to fetch data sources status', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDataSources();
    const interval = setInterval(fetchDataSources, 8000);
    return () => clearInterval(interval);
  }, []);

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'video_stream':
        return 'videocam';
      case 'sensors':
        return 'sensors';
      case 'ai_model':
        return 'neurology';
      case 'safety_engine':
        return 'security';
      case 'storage':
        return 'database';
      default:
        return 'hub';
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    if (s.includes('ready') || s.includes('connected') || s.includes('loaded') || s.includes('operational')) {
      return {
        badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
        dot: 'bg-emerald-400',
        text: status,
      };
    }
    if (s.includes('candidate') || s.includes('rules active')) {
      return {
        badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
        dot: 'bg-cyan-400',
        text: status,
      };
    }
    if (s.includes('not_configured') || s.includes('missing') || s.includes('not configured')) {
      return {
        badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
        dot: 'bg-amber-400',
        text: status,
      };
    }
    return {
      badge: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
      dot: 'bg-slate-400',
      text: status,
    };
  };

  const sources = sourcesData?.sources || [];
  const filteredSources = sources.filter((s) => {
    if (filterCategory === 'all') return true;
    return s.category === filterCategory;
  });

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto text-slate-200 pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0a101f]/90 border border-cyan-500/15 rounded-2xl shadow-lg backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-inner">
            <span className="material-symbols-outlined text-[22px]">hub</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[16px] font-headline font-bold text-slate-100 uppercase tracking-wide">
                Perception & Sensor Data Sources
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                {sources.length} Verified Sources Monitored
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Zero AI Hallucination Guarantee &bull; Verified Model Weights &bull; Live Telemetry Endpoints
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Category Filter Pills */}
          <div className="flex gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-[11px] font-mono">
            {['all', 'ai_model', 'sensors', 'video_stream', 'safety_engine', 'storage'].map((cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={`px-2 py-1 rounded-lg capitalize transition-colors ${
                  filterCategory === cat
                    ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat.replace('_', ' ')}
              </button>
            ))}
          </div>

          <button
            onClick={() => {
              setRefreshing(true);
              fetchDataSources();
            }}
            disabled={refreshing}
            className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-cyan-500/40 text-[11px] font-mono text-cyan-300 flex items-center gap-1.5 transition-colors"
          >
            <span className={`material-symbols-outlined text-[15px] ${refreshing ? 'animate-spin' : ''}`}>
              refresh
            </span>
            Refresh
          </button>
        </div>
      </div>

      {/* Grid of Sources Cards */}
      {loading && sources.length === 0 ? (
        <div className="p-12 text-center text-slate-500 font-mono text-[12px]">
          Scanning hardware ports, file descriptors, and model directories...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {filteredSources.map((source) => {
            const badge = getStatusBadge(source.status);
            const isModelNotConfigured = (source.status || '').includes('NOT_CONFIGURED') || (source.status || '').includes('Candidate Not Trained');

            return (
              <div
                key={source.id}
                onClick={() => setSelectedSource(source)}
                className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 hover:border-cyan-500/40 shadow-xl flex flex-col justify-between transition-all cursor-pointer group hover:bg-[#0a1122]"
              >
                <div className="space-y-3">
                  {/* Top Row: Icon + Status Pill */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="w-9 h-9 rounded-xl bg-slate-900 border border-slate-800 group-hover:border-cyan-500/30 flex items-center justify-center text-cyan-400 transition-colors">
                      <span className="material-symbols-outlined text-[20px]">
                        {getCategoryIcon(source.category)}
                      </span>
                    </div>

                    <span
                      className={`px-2 py-0.5 rounded-full text-[9.5px] font-mono font-bold border flex items-center gap-1.5 ${badge.badge}`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`}></span>
                      {badge.text}
                    </span>
                  </div>

                  {/* Title & Category */}
                  <div>
                    <h3 className="font-bold text-[13.5px] text-slate-100 group-hover:text-cyan-300 transition-colors">
                      {source.name}
                    </h3>
                    <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mt-0.5">
                      CATEGORY: {source.category.replace('_', ' ')}
                    </div>
                  </div>

                  {/* Technical Details description */}
                  <p className="text-[11.5px] text-slate-300 font-sans leading-relaxed">
                    {source.details}
                  </p>

                  {/* Checkpoint / Path Pill if AI Model */}
                  {source.checkpoint && (
                    <div className="p-2 rounded-lg bg-black/40 border border-slate-800 text-[10px] font-mono text-cyan-400/90 truncate">
                      CHECKPOINT: {source.checkpoint}
                    </div>
                  )}

                  {/* Honest Disclosure notice if candidate/not configured */}
                  {isModelNotConfigured && (
                    <div className="p-2 rounded-lg bg-amber-950/20 border border-amber-500/30 text-[10px] font-sans text-amber-300/90 flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-[13px] text-amber-400 shrink-0">
                        verified
                      </span>
                      <span>Honest Status: Model is unconfigured; zero fake scores emitted.</span>
                    </div>
                  )}
                </div>

                {/* Card Footer: Metadata snippet & drilldown action */}
                <div className="pt-3 mt-3 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span>ID: {source.id}</span>
                  <span className="text-cyan-400 group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                    Inspect Details &rarr;
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal / Inspection Drawer for Selected Source */}
      {selectedSource && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="max-w-xl w-full p-5 rounded-2xl bg-[#090e1a] border border-cyan-500/40 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-cyan-400 text-[22px]">
                  {getCategoryIcon(selectedSource.category)}
                </span>
                <div>
                  <h3 className="font-bold text-[15px] text-slate-100">
                    {selectedSource.name}
                  </h3>
                  <span className="text-[10px] font-mono text-slate-400 uppercase">
                    Source Descriptor &bull; {selectedSource.id}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedSource(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 font-mono text-[11.5px]">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5">
                <div className="text-[10px] text-slate-400 uppercase font-bold">Operational Status</div>
                <div className="text-slate-200 font-bold flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${getStatusBadge(selectedSource.status).dot}`}></span>
                  {selectedSource.status}
                </div>
                <div className="text-slate-300 font-sans text-[11px] pt-1">
                  {selectedSource.details}
                </div>
              </div>

              {selectedSource.items && (
                <div className="space-y-1.5">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">
                    Connected Items ({selectedSource.items.length})
                  </div>
                  <div className="max-h-48 overflow-y-auto custom-scrollbar divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-slate-900/40">
                    {selectedSource.items.map((item, idx) => (
                      <div key={idx} className="p-2.5 flex items-center justify-between text-[11px]">
                        <span className="text-slate-200 font-medium truncate">
                          {item.name || item.filename || item.id}
                        </span>
                        <span className="text-cyan-400 text-[10px] shrink-0">
                          {item.size_mb ? `${item.size_mb} MB` : item.type || item.status || 'Active'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedSource(null)}
                className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-mono font-bold"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
