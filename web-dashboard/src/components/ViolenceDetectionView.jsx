import React from 'react';

export default function ViolenceDetectionView() {
  const roadmapMilestones = [
    {
      phase: 'Phase 2.1',
      title: 'Temporal Video Action Recognition Architecture',
      desc: 'Dual-stream 3D CNN / MobileNetV2-LSTM neural network architecture operating on 16-frame sliding temporal buffers.',
      status: 'In Research',
      badge: 'border-purple-500/40 text-purple-400 bg-purple-950/60',
    },
    {
      phase: 'Phase 2.2',
      title: 'Action Dataset Curation & Benchmark',
      desc: 'Dataset collection and annotation covering public space altercations, assaults, crowd panic, and normal pedestrian motion.',
      status: 'Dataset Curation',
      badge: 'border-blue-500/40 text-blue-400 bg-blue-950/60',
    },
    {
      phase: 'Phase 2.3',
      title: 'Forensic Pre-Roll & Incident Dispatch',
      desc: 'Circular RAM buffer preserving 30 seconds of pre-incident forensic context upon verified physical security alerts.',
      status: 'Planned',
      badge: 'border-slate-500/40 text-slate-400 bg-slate-900',
    },
    {
      phase: 'Phase 2.4',
      title: 'Unified Control Room Integration',
      desc: 'Seamless dispatch integration alongside Module 1 traffic ATSC in the VIGIL operations command hub.',
      status: 'Scheduled',
      badge: 'border-slate-500/40 text-slate-400 bg-slate-900',
    },
  ];

  return (
    <div className="flex flex-col w-full gap-5 max-w-7xl mx-auto pb-12">
      {/* 1. Header Banner */}
      <section className="bg-[#0D1424] rounded-2xl p-5 border border-purple-500/30 shadow-lg shadow-purple-950/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
              Module 2 · Physical Security Intelligence
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Violence Detection & Security Surveillance
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Automated physical altercation, weapon hazard, and crowd panic recognition for public transit hubs and security corridors.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 rounded-xl bg-purple-950/90 text-purple-300 border border-purple-500/50 text-xs font-mono font-bold uppercase tracking-wider">
            Coming Soon · Module 2
          </span>
        </div>
      </section>

      {/* 2. Notice Card on Scope */}
      <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 text-slate-300 text-xs font-mono flex items-start gap-3">
        <span className="material-symbols-outlined text-purple-400 text-xl shrink-0 mt-0.5">info</span>
        <div>
          <strong className="text-purple-300 block mb-0.5">Module Scope Notice:</strong>
          VIGIL Module 1 is currently in production focus, delivering Indian traffic density monitoring, Webster ATSC signal preemption, and accident detection.
          Module 2 (Violence Detection) is under active research and scheduled for delivery in the next release cycle.
        </div>
      </div>

      {/* 3. Planned Architecture & Pipeline Flowchart */}
      <section className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
        <h2 className="text-sm font-bold text-white flex items-center gap-2 pb-3 border-b border-slate-800 mb-5">
          <span className="material-symbols-outlined text-purple-400 text-base">account_tree</span>
          Module 2 Action Recognition Architecture
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-mono text-purple-400 font-bold block mb-1">STAGE 1</span>
              <h3 className="text-xs font-bold text-white mb-2">Temporal Sampling</h3>
              <p className="text-[11px] text-slate-400 font-mono">
                16-frame sliding video window sampled at uniform 40ms intervals from high-risk CCTV nodes.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-slate-800 text-[10px] text-slate-500 font-mono">
              Temporal Window: 640ms
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 font-bold block mb-1">STAGE 2</span>
              <h3 className="text-xs font-bold text-white mb-2">Kinematic Feature Fusion</h3>
              <p className="text-[11px] text-slate-400 font-mono">
                Dense optical flow vectors combined with spatial CNN embeddings to capture rapid limb acceleration.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-slate-800 text-[10px] text-slate-500 font-mono">
              Features: Spatial + Motion
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-mono text-indigo-400 font-bold block mb-1">STAGE 3</span>
              <h3 className="text-xs font-bold text-white mb-2">Multi-Head Classifier</h3>
              <p className="text-[11px] text-slate-400 font-mono">
                Recurrent neural net classifying sequences into Normal, Fight / Assault, and Crowd Panic events.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-slate-800 text-[10px] text-slate-500 font-mono">
              Softmax Probability Output
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-mono text-emerald-400 font-bold block mb-1">STAGE 4</span>
              <h3 className="text-xs font-bold text-white mb-2">Forensic Lock & Alert</h3>
              <p className="text-[11px] text-slate-400 font-mono">
                Pre-roll recording locked to SQLite store with SHA-256 seal and automated security dispatch.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-slate-800 text-[10px] text-slate-500 font-mono">
              Tamper-Evident SHA-256
            </div>
          </div>
        </div>
      </section>

      {/* 4. Development Roadmap */}
      <section className="p-5 rounded-2xl bg-[#0D1424] border border-slate-800">
        <h2 className="text-sm font-bold text-white flex items-center gap-2 pb-3 border-b border-slate-800 mb-4">
          <span className="material-symbols-outlined text-purple-400 text-base">route</span>
          Module 2 Implementation Roadmap
        </h2>

        <div className="space-y-3">
          {roadmapMilestones.map((m) => (
            <div
              key={m.phase}
              className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[11px] font-mono font-bold text-purple-400">{m.phase}</span>
                  <span className="text-xs font-bold text-white">{m.title}</span>
                </div>
                <p className="text-xs text-slate-400">{m.desc}</p>
              </div>
              <span className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold border shrink-0 ${m.badge}`}>
                {m.status}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
