import React, { useState, useEffect } from 'react';

const VIEW_TITLES = {
  'command-center': { title: 'Command Center', subtitle: 'Integrated Operations, Emergency Preemption & Incident Triage', icon: 'dashboard', tag: 'OVERVIEW' },
  'main-command-hub': { title: 'Command Center', subtitle: 'Integrated Operations, Emergency Preemption & Incident Triage', icon: 'dashboard', tag: 'OVERVIEW' },
  'single-camera': { title: 'Single Camera Workspace', subtitle: 'Dedicated Video Source Perception & Forensic Analysis', icon: 'videocam', tag: 'SINGLE CAM' },
  'four-way': { title: 'Four-Way Intersection Workspace', subtitle: 'Adaptive Webster ATSC & Directional Demand Perception', icon: 'grid_view', tag: '4-WAY ATSC' },
  '4-way-ai-perception': { title: 'Four-Way Intersection Workspace', subtitle: 'Adaptive Webster ATSC & Directional Demand Perception', icon: 'grid_view', tag: '4-WAY ATSC' },
  'ip-webcam': { title: 'IP Webcam Input', subtitle: 'Network Camera Diagnostics, Authentication & Live Perception', icon: 'linked_camera', tag: 'IP WEBCAM' },
  'accidents': { title: 'Accident & Incident Feed', subtitle: 'Persistent Forensic Accident Triage & Investigation Log', icon: 'car_crash', tag: 'ACCIDENTS' },
  'evidence': { title: 'Evidence Database', subtitle: 'Forensic Video Clips, Snapshots & SHA-256 Checksums', icon: 'folder_data', tag: 'EVIDENCE' },
  'analytics': { title: 'Traffic Analytics', subtitle: 'Historical Density Trends, PCU Demand & Vehicle Distributions', icon: 'monitoring', tag: 'ANALYTICS' },
  'violence-coming-soon': { title: 'Violence Detection — Module 2', subtitle: 'CCTV Threat Detection & Action Recognition (Coming Soon)', icon: 'shield', tag: 'COMING SOON' },
  'system-health': { title: 'System Health & Settings', subtitle: 'Hardware Diagnostics, Model Zoo & Relational Database Store', icon: 'settings', tag: 'SETTINGS' },
};

export default function TopNavbar({
  emergencyActive,
  onToggleSidebar,
  sidebarCollapsed = false,
  currentView = 'command-center',
  isConnected = false,
  uptime = '',
}) {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const currentViewInfo = VIEW_TITLES[currentView] || {
    title: 'VIGIL Operations Hub',
    subtitle: 'Traffic & Incident Management',
    icon: 'traffic',
    tag: 'SYSTEM',
  };

  return (
    <header
      className={`fixed top-0 left-0 ${
        sidebarCollapsed ? 'lg:left-16' : 'lg:left-64'
      } right-0 h-16 bg-[#0B101D]/95 backdrop-blur-md z-40 flex items-center justify-between px-4 sm:px-6 border-b border-slate-800 shadow-md transition-all duration-300`}
    >
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition-colors"
          title="Open Menu"
        >
          <span className="material-symbols-outlined text-[20px]">menu</span>
        </button>

        <div className="flex items-center gap-2.5 truncate">
          <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-500/30 flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-cyan-400 text-[20px]">
              {currentViewInfo.icon}
            </span>
          </div>
          <div className="truncate">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white tracking-tight truncate">
                {currentViewInfo.title}
              </span>
              <span className="hidden sm:inline-block font-mono text-[9px] px-1.5 py-0.5 rounded font-bold bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                {currentViewInfo.tag}
              </span>
            </div>
            <span className="hidden md:block text-[11px] text-slate-400 truncate">
              {currentViewInfo.subtitle}
            </span>
          </div>
        </div>
      </div>

      {/* Right: Actions, Emergency & Clock */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {emergencyActive && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-950/70 text-red-300 border border-red-500/60 animate-pulse text-xs font-bold shadow-md shadow-red-950">
            <span>🚑</span>
            <span className="hidden sm:inline">EMERGENCY CORRIDOR ACTIVE</span>
            <span className="sm:hidden">EVP</span>
          </div>
        )}

        {/* Backend Online & WS Status */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 font-mono">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></span>
          <span>{isConnected ? 'Backend Active' : 'Connecting...'}</span>
          {uptime ? <span className="text-[10px] text-slate-500">({uptime})</span> : null}
        </div>

        {/* Real-time Clock */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 font-mono">
          <span className="material-symbols-outlined text-[15px] text-slate-400">schedule</span>
          <span>{timeStr}</span>
        </div>
      </div>
    </header>
  );
}
