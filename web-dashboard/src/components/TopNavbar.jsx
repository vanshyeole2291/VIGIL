import React, { useState, useEffect } from 'react';

const VIEW_TITLES = {
  'main-command-hub': { title: 'Command Hub', icon: 'dashboard' },
  'dashboard': { title: 'Command Hub', icon: 'dashboard' },
  '4-way-ai-perception': { title: 'Traffic Perception & ATSC', icon: 'traffic' },
  'security-surveillance': { title: 'AI Violence & CCTV Security', icon: 'security' },
  'incidents': { title: 'Unified Incident Feed', icon: 'warning' },
  'evidence-vault': { title: 'Forensic Evidence Vault', icon: 'videocam' },
  'camera-network': { title: 'Camera Network & Feeds', icon: 'linked_camera' },
  'system-health': { title: 'System Health & Diagnostics', icon: 'health_and_safety' },
};

export default function TopNavbar({
  selectedIntersection,
  setSelectedIntersection,
  emergencyActive,
  onToggleSidebar,
  onToggleCollapse,
  sidebarCollapsed = false,
  currentView = 'main-command-hub',
}) {
  const [utcTime, setUtcTime] = useState('');
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState("assets/videos/north.mp4");

  useEffect(() => {
    fetch('/api/videos')
      .then(r => r.json())
      .then(data => setVideos(data || []))
      .catch(console.error);
  }, []);

  const handleVideoChange = (e) => {
    const path = e.target.value;
    setSelectedVideo(path);
    fetch('/api/load-videos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ v_north: path })
    }).catch(console.error);
  };

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toTimeString().split(' ')[0] + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const currentViewInfo = VIEW_TITLES[currentView] || { title: 'Dashboard', icon: 'traffic' };

  return (
    <header
      className={`fixed top-0 left-0 ${
        sidebarCollapsed ? 'lg:left-16' : 'lg:left-64'
      } right-0 h-16 bg-surface-container-lowest/70 backdrop-blur-2xl z-40 flex items-center justify-between px-3 sm:px-space-md lg:px-space-lg border-b border-white/5 shadow-lg transition-all duration-300`}
    >
      {/* Left: Sidebar Toggle + Active View Breadcrumb & Intersection Selector */}
      <div className="flex items-center gap-2 sm:gap-space-sm min-w-0">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-1.5 rounded-lg bg-surface-container/50 text-on-surface hover:bg-surface-container hover:shadow-md transition-all shrink-0 border border-white/5"
        >
          <span className="material-symbols-outlined text-[20px]">menu</span>
        </button>

        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-1.5 rounded-lg bg-surface-container/50 text-on-surface hover:bg-surface-container hover:shadow-md transition-all shrink-0 border border-white/5"
          >
            <span className="material-symbols-outlined text-[20px]">
              {sidebarCollapsed ? 'menu_open' : 'view_sidebar'}
            </span>
          </button>
        )}

        <div className="hidden md:flex items-center gap-2 bg-surface-container/40 px-3 py-1.5 rounded-xl border border-white/5 shrink-0 shadow-inner">
          <span className="material-symbols-outlined text-primary text-[18px]">
            {currentViewInfo.icon}
          </span>
          <span className="font-headline text-[12px] font-bold tracking-wider uppercase text-on-surface whitespace-nowrap">
            {currentViewInfo.title}
          </span>
        </div>

        <div className="relative flex items-center bg-surface-container/40 border border-white/5 px-3 sm:px-space-md py-1.5 rounded-xl cursor-pointer hover:bg-surface-container hover:border-primary/30 transition-all shrink-0 shadow-sm group">
          <span className="material-symbols-outlined text-primary text-[17px] mr-2 shrink-0 group-hover:scale-110 transition-transform">traffic</span>
          <div className="flex flex-col">
            <span className="font-mono text-[8px] uppercase tracking-wider text-on-surface-variant font-medium leading-none mb-0.5">
              JUNCTION
            </span>
            <select
              value={selectedIntersection}
              onChange={(e) => setSelectedIntersection(e.target.value)}
              className="bg-transparent text-on-surface text-[12px] font-semibold cursor-pointer outline-none appearance-none pr-5 leading-tight"
            >
              <option value="j04">Junction 04: Grand Ave & 5th St</option>
              <option value="j05">Junction 05: Metro Blvd & 8th St</option>
              <option value="j02">Junction 02: Riverside & King Way</option>
              <option value="j07">Junction 07: Central Square Cross</option>
            </select>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant text-[15px] absolute right-2 pointer-events-none group-hover:text-primary transition-colors">
            expand_more
          </span>
        </div>
        <div className="relative flex items-center bg-surface-container/40 border border-white/5 px-3 sm:px-space-md py-1.5 rounded-xl cursor-pointer hover:bg-surface-container hover:border-primary/30 transition-all shrink-0 shadow-sm group">
          <span className="material-symbols-outlined text-primary text-[17px] mr-2 shrink-0 group-hover:scale-110 transition-transform">videocam</span>
          <div className="flex flex-col">
            <span className="font-mono text-[8px] uppercase tracking-wider text-on-surface-variant font-medium leading-none mb-0.5">
              PRESENTATION VIDEO
            </span>
            <select
              value={selectedVideo}
              onChange={handleVideoChange}
              className="bg-transparent text-on-surface text-[12px] font-semibold cursor-pointer outline-none appearance-none pr-5 leading-tight"
            >
              {videos.map(v => (
                <option key={v.path} value={v.path}>{v.filename}</option>
              ))}
            </select>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant text-[15px] absolute right-2 pointer-events-none group-hover:text-primary transition-colors">
            expand_more
          </span>
        </div>

      </div>

      {/* Right: Clock & Status */}
      <div className="flex items-center gap-3 sm:gap-space-md shrink-0">
        {emergencyActive && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-error/10 text-error border border-error/30 animate-pulse shadow-glow">
            <span className="material-symbols-outlined text-[16px]">e911_emergency</span>
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider">
              EMERGENCY ACTIVE
            </span>
          </div>
        )}
        <div className="flex items-center gap-1.5 bg-surface-container/40 px-3 py-1.5 rounded-xl border border-white/5 shadow-inner">
          <span className="material-symbols-outlined text-primary/70 text-[15px]">schedule</span>
          <div className="font-mono text-[11px] text-on-surface font-semibold tracking-wide">
            {utcTime}
          </div>
        </div>
      </div>
    </header>
  );
}
