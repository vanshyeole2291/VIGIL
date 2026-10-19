import React, { useState, useEffect } from 'react';

// Web Audio API chime test
function playTestChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.15);

    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.35);
  } catch (e) {
    console.error('Audio test error', e);
  }
}

export default function SettingsView() {
  const [settings, setSettings] = useState({
    audioAlerts: true,
    refreshInterval: 3000,
    density: 'comfortable',
    themeAccents: 'cyan',
    autoAcknowledgeLowSeverity: false,
    saveSnapshotsLocally: true,
  });

  const [savedMsg, setSavedMsg] = useState('');

  useEffect(() => {
    try {
      const stored = localStorage.getItem('vigil_settings');
      if (stored) {
        setSettings(JSON.parse(stored));
      }
    } catch (e) {
      // ignore
    }
  }, []);

  const updateSetting = (key, val) => {
    const next = { ...settings, [key]: val };
    setSettings(next);
    localStorage.setItem('vigil_settings', JSON.stringify(next));
    setSavedMsg('Settings persisted in browser local storage');
    setTimeout(() => setSavedMsg(''), 3000);
  };

  return (
    <div className="space-y-4 max-w-[1200px] mx-auto text-slate-200 pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#0a101f]/90 border border-cyan-500/15 rounded-2xl shadow-lg backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-inner">
            <span className="material-symbols-outlined text-[22px]">settings</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[16px] font-headline font-bold text-slate-100 uppercase tracking-wide">
                System Preferences & Operator Settings
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                LOCAL PERSISTENCE
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Configure Audio Alerting &bull; Telemetry Refresh Rates &bull; Command Center Density
            </p>
          </div>
        </div>

        {savedMsg && (
          <div className="px-3 py-1 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 text-[11px] font-mono">
            {savedMsg}
          </div>
        )}
      </div>

      {/* Settings Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Section 1: Audio & Alert Notifications */}
        <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-cyan-500/10">
            <span className="material-symbols-outlined text-cyan-400 text-[20px]">
              notifications_active
            </span>
            <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
              Auditory Alerts & Sound Synthesis
            </span>
          </div>

          <div className="space-y-3 font-mono text-[11.5px]">
            <div className="flex items-center justify-between p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800">
              <div>
                <div className="text-slate-200 font-bold">Audio Incident Chimes</div>
                <div className="text-[10px] text-slate-400 font-sans mt-0.5">
                  Play Web Audio API chime tone when high/critical incidents are detected
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.audioAlerts}
                onChange={(e) => updateSetting('audioAlerts', e.target.checked)}
                className="w-4 h-4 rounded text-cyan-500 cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800">
              <div>
                <div className="text-slate-200 font-bold">Test Synthesized Chime</div>
                <div className="text-[10px] text-slate-400 font-sans mt-0.5">
                  Plays tone through local speaker (no external files required)
                </div>
              </div>
              <button
                onClick={playTestChime}
                className="px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-[11px] font-bold flex items-center gap-1.5 transition-colors"
              >
                <span className="material-symbols-outlined text-[15px]">volume_up</span>
                Test Sound
              </button>
            </div>
          </div>
        </div>

        {/* Section 2: Telemetry Refresh Rates */}
        <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-cyan-500/10">
            <span className="material-symbols-outlined text-cyan-400 text-[20px]">
              sync
            </span>
            <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
              Data Polling & Refresh Frequency
            </span>
          </div>

          <div className="space-y-3 font-mono text-[11.5px]">
            <div className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-200 font-bold">Incident Archive Refresh</span>
                <span className="text-cyan-300 font-bold">{settings.refreshInterval / 1000}s</span>
              </div>
              <div className="text-[10px] text-slate-400 font-sans">
                Controls background polling rate for REST endpoints. (WebSockets update in real-time).
              </div>
              <div className="grid grid-cols-3 gap-2 pt-1">
                {[1500, 3000, 5000].map((ms) => (
                  <button
                    key={ms}
                    onClick={() => updateSetting('refreshInterval', ms)}
                    className={`py-1.5 rounded-lg border text-center transition-colors ${
                      settings.refreshInterval === ms
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 font-bold'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {ms / 1000}s ({ms === 1500 ? 'Fast' : ms === 3000 ? 'Balanced' : 'Eco'})
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Interface Display Density */}
        <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-cyan-500/10">
            <span className="material-symbols-outlined text-cyan-400 text-[20px]">
              density_medium
            </span>
            <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
              Command Center Density
            </span>
          </div>

          <div className="space-y-3 font-mono text-[11.5px]">
            <div className="p-3 rounded-xl bg-[#0a101f]/70 border border-slate-800 space-y-2">
              <div className="text-slate-200 font-bold">Layout Density Mode</div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                {['comfortable', 'compact'].map((mode) => (
                  <button
                    key={mode}
                    onClick={() => updateSetting('density', mode)}
                    className={`py-2 rounded-xl border capitalize text-center transition-colors ${
                      settings.density === mode
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 font-bold'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {mode} {mode === 'comfortable' ? '(Standard)' : '(High Information)'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Operator & System Info */}
        <div className="p-4 rounded-2xl bg-[#070b14]/90 border border-cyan-500/15 shadow-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-cyan-500/10">
            <span className="material-symbols-outlined text-cyan-400 text-[20px]">
              badge
            </span>
            <span className="text-[13px] font-bold text-slate-100 uppercase tracking-wide">
              Active Operator Station
            </span>
          </div>

          <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-[#0a101f]/70 font-mono text-[11px]">
            <div className="flex items-center justify-between p-2.5 px-3">
              <span className="text-slate-400">OPERATOR ID</span>
              <span className="text-slate-200 font-bold">OP_DESK_PRIMARY</span>
            </div>
            <div className="flex items-center justify-between p-2.5 px-3">
              <span className="text-slate-400">ASSIGNED INTERSECTION</span>
              <span className="text-cyan-300 font-bold">Junction 04 (Grand Ave & 5th)</span>
            </div>
            <div className="flex items-center justify-between p-2.5 px-3">
              <span className="text-slate-400">SECURITY ROLE</span>
              <span className="text-emerald-400 font-bold">SOC_COMMANDER</span>
            </div>
            <div className="flex items-center justify-between p-2.5 px-3">
              <span className="text-slate-400">CLIENT RUNTIME</span>
              <span className="text-slate-200 font-bold">Vite 7 + React 19 Engine</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
