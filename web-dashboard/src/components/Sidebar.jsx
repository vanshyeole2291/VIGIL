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
    { id: 'main-command-hub', label: 'Command Hub', icon: 'dashboard' },
    { id: '4-way-ai-perception', label: 'Traffic Perception', icon: 'traffic' },
    { id: 'model-performance', label: 'Model Performance', icon: 'analytics' },
    { id: 'security-surveillance', label: 'Violence & Security', icon: 'security' },
    { id: 'incidents', label: 'Incident Archive', icon: 'warning' },
    { id: 'evidence-vault', label: 'Evidence Vault', icon: 'videocam' },
    { id: 'camera-network', label: 'Camera Network', icon: 'linked_camera' },
    { id: 'system-health', label: 'System Health', icon: 'health_and_safety' },
  ];

  return (
    <>
      {mobileOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
        />
      )}
      <aside
        className={`fixed left-0 top-0 h-full ${collapsed ? 'lg:w-16' : 'lg:w-64'
          } w-64 bg-surface-container-lowest/95 backdrop-blur-xl z-50 flex flex-col border-r border-outline-variant/30 shadow-[0_1px_8px_rgba(0,0,0,0.3)] transition-all duration-300 ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          }`}
      >
        <div className="h-16 px-space-md flex items-center justify-between border-b border-outline-variant/20 bg-surface-container-low/60 overflow-hidden">
          <div className="flex items-center gap-space-sm min-w-0">
            <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center shadow-inner shrink-0">
              <span className="material-symbols-outlined text-primary text-[20px]">shield</span>
            </div>
            {!collapsed && (
              <div className="truncate">
                <span className="font-headline text-[15px] font-extrabold tracking-wider uppercase text-primary block leading-none truncate">
                  VIGIL
                </span>
                <span className="font-mono text-[9px] text-on-surface-variant block mt-1 tracking-tight truncate">
                  AI SURVEILLANCE & SAFETY
                </span>
              </div>
            )}
          </div>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex p-1 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors ml-1"
            >
              <span className="material-symbols-outlined text-[18px]">
                {collapsed ? 'chevron_right' : 'chevron_left'}
              </span>
            </button>
          )}
        </div>

        <nav className="flex-1 px-space-sm py-space-md space-y-2 overflow-y-auto mt-4">
          {navItems.map((item) => {
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                title={collapsed ? item.label : undefined}
                className={`group w-full flex items-center ${collapsed ? 'justify-center px-2 py-3' : 'justify-start gap-3 px-4 py-3'
                  } rounded-xl text-left transition-all duration-300 ease-out border border-transparent ${isActive
                    ? 'bg-primary/10 text-primary font-semibold shadow-glow border-primary/20 backdrop-blur-md'
                    : 'text-on-surface-variant hover:bg-surface-container-high/50 hover:text-on-surface hover:shadow-lg'
                  }`}
              >
                <span className={`material-symbols-outlined text-[20px] transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`}>{item.icon}</span>
                {!collapsed && <span className="text-[14px]">{item.label}</span>}
              </button>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
