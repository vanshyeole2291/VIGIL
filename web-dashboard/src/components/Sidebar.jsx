import React from 'react';

export default function Sidebar({
  currentView,
  setCurrentView,
  mobileOpen,
  onClose,
  collapsed = false,
  onToggleCollapse,
}) {
  const navItems = [
    {
      id: 'command-center',
      label: 'Command Center',
      icon: 'dashboard',
      tag: 'OVERVIEW',
      badgeColor: 'border-cyan-500/30 text-cyan-400 bg-cyan-950/40',
    },
    {
      id: 'single-camera',
      label: 'Single Camera',
      icon: 'videocam',
      tag: 'FEED 1',
      badgeColor: 'border-blue-500/30 text-blue-400 bg-blue-950/40',
    },
    {
      id: 'four-way',
      label: 'Four-Way Intersection',
      icon: 'grid_view',
      tag: '4-WAY',
      badgeColor: 'border-emerald-500/30 text-emerald-400 bg-emerald-950/40',
    },
    {
      id: 'ip-webcam',
      label: 'IP Webcam',
      icon: 'linked_camera',
      tag: 'RTSP/IP',
      badgeColor: 'border-teal-500/30 text-teal-400 bg-teal-950/40',
    },
    {
      id: 'accidents',
      label: 'Accident & Incident Feed',
      icon: 'car_crash',
      tag: 'INCIDENTS',
      badgeColor: 'border-red-500/30 text-red-400 bg-red-950/40',
    },
    {
      id: 'evidence',
      label: 'Evidence Database',
      icon: 'folder_data',
      tag: 'SHA-256',
      badgeColor: 'border-amber-500/30 text-amber-400 bg-amber-950/40',
    },
    {
      id: 'analytics',
      label: 'Traffic Analytics',
      icon: 'monitoring',
      tag: 'PCU/FPS',
      badgeColor: 'border-indigo-500/30 text-indigo-400 bg-indigo-950/40',
    },
    {
      id: 'violence-coming-soon',
      label: 'Violence Detection',
      icon: 'shield',
      tag: 'MODULE 2',
      badgeText: 'Soon',
      badgeColor: 'border-purple-500/30 text-purple-400 bg-purple-950/40',
    },
    {
      id: 'system-health',
      label: 'System Health & Settings',
      icon: 'settings',
      tag: 'HARDWARE',
      badgeColor: 'border-slate-500/30 text-slate-400 bg-slate-900/60',
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-full ${
          collapsed ? 'lg:w-16' : 'lg:w-64'
        } w-64 bg-[#0B101D] z-50 flex flex-col border-r border-slate-800 shadow-2xl transition-all duration-300 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Top Brand Header */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800 bg-[#090D18]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-600 to-blue-700 border border-cyan-400/30 flex items-center justify-center shrink-0 shadow-lg shadow-cyan-900/30">
              <span className="material-symbols-outlined text-white text-[20px]">traffic</span>
            </div>
            {!collapsed && (
              <div className="truncate">
                <div className="flex items-center gap-1.5">
                  <span className="font-extrabold text-[15px] text-white tracking-wider block font-headline">
                    VIGIL
                  </span>
                  <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-bold">
                    v2.0
                  </span>
                </div>
                <span className="font-mono text-[9px] text-slate-400 block tracking-wider font-semibold">
                  INDIAN ITMS & ROAD SAFETY
                </span>
              </div>
            )}
          </div>

          {!collapsed ? (
            <div className="flex items-center gap-1.5 shrink-0">
              <div className="flex items-center gap-1.5 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-500/30">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="font-mono text-[9px] text-emerald-400 font-bold uppercase tracking-wider">LIVE</span>
              </div>
              {onToggleCollapse && (
                <button
                  onClick={onToggleCollapse}
                  className="hidden lg:flex p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-1"
                  title="Collapse Menu"
                >
                  <span className="material-symbols-outlined text-[18px]">chevron_left</span>
                </button>
              )}
            </div>
          ) : (
            onToggleCollapse && (
              <button
                onClick={onToggleCollapse}
                className="hidden lg:flex p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors mx-auto"
                title="Expand Menu"
              >
                <span className="material-symbols-outlined text-[18px]">chevron_right</span>
              </button>
            )
          )}
        </div>

        {/* Operational Context Chip */}
        {!collapsed && (
          <div className="px-4 py-2.5 bg-[#0D1424] border-b border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400">
              <span className="font-mono text-[9px] uppercase tracking-wider font-semibold">URBAN CORRIDOR</span>
              <span className="font-mono text-[9px] text-cyan-400 bg-cyan-950/50 px-1.5 py-0.2 rounded font-semibold border border-cyan-800/50">
                ATSC ACTIVE
              </span>
            </div>
            <div className="mt-1 flex items-center justify-between">
              <span className="text-[11px] text-slate-300 font-medium">Junction 04 — Quad Array</span>
              <span className="font-mono text-[10px] text-emerald-400 font-bold">4 Feeds Sync</span>
            </div>
          </div>
        )}

        {/* Navigation Items List */}
        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-1">
          {navItems.map((item) => {
            const isActive = currentView === item.id || (item.id === 'command-center' && currentView === 'main-command-hub');
            return (
              <button
                key={item.id}
                onClick={() => {
                  setCurrentView(item.id);
                  if (onClose) onClose();
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                  isActive
                    ? 'bg-cyan-950/50 text-cyan-300 border border-cyan-500/40 font-semibold shadow-inner shadow-cyan-950'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
                title={collapsed ? item.label : undefined}
              >
                <span
                  className={`material-symbols-outlined text-[20px] shrink-0 ${
                    isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300'
                  }`}
                >
                  {item.icon}
                </span>

                {!collapsed && (
                  <div className="flex-1 flex items-center justify-between truncate min-w-0">
                    <span className="text-[13px] truncate">{item.label}</span>
                    {item.badgeText ? (
                      <span className="ml-1.5 text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-500/40 uppercase font-bold">
                        {item.badgeText}
                      </span>
                    ) : item.tag ? (
                      <span className={`ml-1.5 text-[9px] font-mono px-1.5 py-0.2 rounded border font-semibold ${item.badgeColor}`}>
                        {item.tag}
                      </span>
                    ) : null}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer Hardware & Engine Info */}
        {!collapsed && (
          <div className="p-3 border-t border-slate-800 bg-[#090D18]">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="text-[10px] font-mono font-bold text-slate-300">GPU ACCELERATED</span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono flex justify-between">
              <span>RTX 4050 6GB</span>
              <span className="text-cyan-400">YOLOv8 v12</span>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
