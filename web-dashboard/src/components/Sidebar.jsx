import React, { useState, useEffect } from 'react';

export default function Sidebar({
  currentView,
  setCurrentView,
  mobileOpen,
  onClose,
  collapsed = false,
  onToggleCollapse,
}) {
  const [activeIncidentCount, setActiveIncidentCount] = useState(0);

  useEffect(() => {
    const fetchIncidentCount = async () => {
      try {
        const res = await fetch('/api/incidents');
        if (res.ok) {
          const data = await res.json();
          const unhandled = (data || []).filter(
            (i) => (i.status || 'new') === 'new' || (i.status || 'new') === 'investigating'
          ).length;
          setActiveIncidentCount(unhandled);
        }
      } catch (e) {
        // quiet fallback
      }
    };
    fetchIncidentCount();
    const interval = setInterval(fetchIncidentCount, 5000);
    return () => clearInterval(interval);
  }, []);

  const navGroups = [
    {
      group: 'OVERVIEW',
      items: [
        { id: 'main-command-hub', label: 'Command Hub', icon: 'dashboard' },
      ],
    },
    {
      group: 'LIVE TRAFFIC',
      items: [
        { id: '4-way-ai-perception', label: 'Four-Way Intersection', icon: 'traffic' },
        { id: 'camera-network', label: 'Camera Network', icon: 'linked_camera' },
      ],
    },
    {
      group: 'SAFETY & INTELLIGENCE',
      items: [
        {
          id: 'incidents',
          label: 'Incident Feed',
          icon: 'warning',
          badge: activeIncidentCount > 0 ? activeIncidentCount : null,
          badgeColor: 'bg-rose-500/20 text-rose-400 border border-rose-500/40',
        },
        { id: 'emergency-response', label: 'Emergency Response', icon: 'e911_emergency' },
        { id: 'accident-monitoring', label: 'Accident Monitoring', icon: 'car_crash' },
        { id: 'security-surveillance', label: 'Surveillance Security', icon: 'shield_with_heart' },
      ],
    },
    {
      group: 'ANALYTICS',
      items: [
        { id: 'traffic-analytics', label: 'Traffic Analytics', icon: 'query_stats' },
        { id: 'model-performance', label: 'Model Performance', icon: 'analytics' },
        { id: 'evidence-vault', label: 'Forensic Evidence', icon: 'videocam' },
      ],
    },
    {
      group: 'SYSTEM',
      items: [
        { id: 'data-sources', label: 'Data Sources', icon: 'hub' },
        { id: 'database-storage', label: 'Database & Storage', icon: 'database' },
        { id: 'system-health', label: 'System Health', icon: 'health_and_safety' },
        { id: 'settings', label: 'Settings', icon: 'settings' },
      ],
    },
  ];

  return (
    <>
      {mobileOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 lg:hidden"
        />
      )}
      <aside
        className={`fixed left-0 top-0 h-full ${
          collapsed ? 'lg:w-16' : 'lg:w-64'
        } w-64 bg-[#070b14]/95 backdrop-blur-2xl z-50 flex flex-col border-r border-cyan-500/10 shadow-[0_4px_24px_rgba(0,0,0,0.6)] transition-all duration-300 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-cyan-500/10 bg-[#0a101f]/70 overflow-hidden shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/30 flex items-center justify-center shadow-inner shrink-0">
              <span className="material-symbols-outlined text-cyan-400 text-[20px]">shield</span>
            </div>
            {!collapsed && (
              <div className="truncate">
                <div className="flex items-center gap-1.5">
                  <span className="font-headline text-[15px] font-extrabold tracking-wider uppercase text-cyan-400 block leading-none truncate">
                    VIGIL
                  </span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-300 font-mono border border-cyan-500/20 font-bold">
                    v2.0
                  </span>
                </div>
                <span className="font-mono text-[9px] text-slate-400 block mt-1 tracking-tight truncate">
                  AI TRAFFIC & SURVEILLANCE
                </span>
              </div>
            )}
          </div>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex p-1 rounded-md text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors ml-1"
              title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            >
              <span className="material-symbols-outlined text-[18px]">
                {collapsed ? 'chevron_right' : 'chevron_left'}
              </span>
            </button>
          )}
        </div>

        {/* Navigation items grouped */}
        <nav className="flex-1 px-2.5 py-3 space-y-4 overflow-y-auto custom-scrollbar">
          {navGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1">
              {!collapsed && (
                <div className="px-3 pt-2 pb-1 text-[10px] font-mono font-bold tracking-wider text-slate-400 uppercase">
                  {group.group}
                </div>
              )}
              {group.items.map((item) => {
                const isActive = currentView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setCurrentView(item.id)}
                    title={collapsed ? item.label : undefined}
                    className={`group w-full flex items-center ${
                      collapsed ? 'justify-center px-2 py-2.5' : 'justify-between px-3 py-2'
                    } rounded-xl text-left transition-all duration-200 border ${
                      isActive
                        ? 'bg-cyan-500/15 text-cyan-300 font-semibold shadow-[0_0_12px_rgba(6,182,212,0.15)] border-cyan-500/30'
                        : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span
                        className={`material-symbols-outlined text-[19px] shrink-0 transition-transform ${
                          isActive ? 'text-cyan-400 scale-105' : 'text-slate-400 group-hover:text-cyan-400'
                        }`}
                      >
                        {item.icon}
                      </span>
                      {!collapsed && (
                        <span className="text-[13px] truncate tracking-tight">{item.label}</span>
                      )}
                    </div>
                    {!collapsed && item.badge !== undefined && item.badge !== null && (
                      <span
                        className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full ${item.badgeColor}`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer Status Pill */}
        {!collapsed && (
          <div className="p-3 border-t border-cyan-500/10 bg-[#0a101f]/40 shrink-0">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                SOC ONLINE
              </span>
              <span className="text-slate-400">J04 ACTIVE</span>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

