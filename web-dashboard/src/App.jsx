import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import TopNavbar from './components/TopNavbar';
import MainCommandHubView from './components/MainCommandHubView';
import SingleCameraView from './components/SingleCameraView';
import FourWayPerceptionView from './components/FourWayPerceptionView';
import IPWebcamView from './components/IPWebcamView';
import AccidentIncidentFeedView from './components/AccidentIncidentFeedView';
import EvidenceDatabaseView from './components/EvidenceDatabaseView';
import TrafficAnalyticsView from './components/TrafficAnalyticsView';
import ViolenceDetectionView from './components/ViolenceDetectionView';
import SystemHealthView from './components/SystemHealthView';

function App() {
  const [currentView, setCurrentView] = useState('command-center');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const startTime = useRef(Date.now());
  const [uptime, setUptime] = useState('00:00');

  useEffect(() => {
    const t = setInterval(() => {
      const sec = Math.floor((Date.now() - startTime.current) / 1000);
      setUptime(
        String(Math.floor(sec / 60)).padStart(2, '0') + ':' + String(sec % 60).padStart(2, '0')
      );
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const [state, setState] = useState({
    metrics: {},
    signals: {},
    alerts: [],
    chart: {},
    active_targets: [],
    audio_siren: {},
    v2x_spat: {},
    green_wave: {},
    pedestrian_safety: {},
    bev_radar: {},
    frame_b64: null,
  });

  const [isConnected, setIsConnected] = useState(false);
  const [activePopup, setActivePopup] = useState(null);
  const seenIncidentIds = useRef(new Set());
  const popupTimer = useRef(null);

  // Poll for real-time critical incidents to surface on-screen alert popup
  useEffect(() => {
    let isMounted = true;
    const checkLatestIncident = async () => {
      try {
        const res = await fetch('/api/incidents');
        if (!res.ok) return;
        const list = await res.json();
        if (Array.isArray(list) && list.length > 0 && isMounted) {
          const latest = list[0];
          // On initialization, mark existing history so only fresh events trigger popups
          if (seenIncidentIds.current.size === 0) {
            list.forEach((item) => seenIncidentIds.current.add(item.id));
            return;
          }
          if (!seenIncidentIds.current.has(latest.id)) {
            seenIncidentIds.current.add(latest.id);
            setActivePopup((prev) => {
              const isPrevAccident = prev && (prev.type === 'accident' || prev.incident_type === 'accident');
              const isLatestAccident = latest.type === 'accident' || latest.incident_type === 'accident';
              if (isPrevAccident && !isLatestAccident) {
                return prev; // Accident alert maintains absolute top screen priority
              }
              return latest;
            });
            if (popupTimer.current) clearTimeout(popupTimer.current);
            popupTimer.current = setTimeout(() => {
              if (isMounted) setActivePopup(null);
            }, 9000);
          }
        }
      } catch (e) {
        // silent catch
      }
    };

    checkLatestIncident();
    const interval = setInterval(checkLatestIncident, 2500);
    return () => {
      isMounted = false;
      clearInterval(interval);
      if (popupTimer.current) clearTimeout(popupTimer.current);
    };
  }, []);

  // WebSocket Live Connection to Backend
  useEffect(() => {
    let ws;
    let wsRetries = 0;

    function connectWS() {
      const loc = window.location;
      const host = loc.hostname || 'localhost';
      const port = loc.port ? loc.port : '8000';
      const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${proto}//${host}:${port}/ws`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setIsConnected(true);
          wsRetries = 0;
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setState((prev) => ({
              ...prev,
              ...data,
              metrics: data.metrics || prev.metrics,
              signals: data.signals || prev.signals,
              alerts: data.alerts || prev.alerts,
              chart: data.chart || prev.chart,
              active_targets: data.active_targets || prev.active_targets,
              audio_siren: data.audio_siren || prev.audio_siren,
              v2x_spat: data.v2x_spat || prev.v2x_spat,
              green_wave: data.green_wave || prev.green_wave,
              pedestrian_safety: data.pedestrian_safety || prev.pedestrian_safety,
              bev_radar: data.bev_radar || prev.bev_radar,
            }));
          } catch (e) {
            console.error('Failed to parse WebSocket message', e);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          const delay = Math.min(10000, 1000 * Math.pow(1.5, wsRetries++));
          setTimeout(connectWS, delay);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        console.error('WebSocket connection error:', e);
      }
    }

    connectWS();
    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleTriggerEmergency = async (lane) => {
    try {
      await fetch('/api/trigger-emergency', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lane: lane || 'North' }),
      });
    } catch (e) {
      console.warn('API trigger emergency failed:', e);
    }
  };

  const isEmergency = state.signals?.emergency_active || false;

  return (
    <div className="bg-[#080B14] font-body text-slate-100 min-h-screen selection:bg-cyan-500/30 selection:text-cyan-300">
      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        currentView={currentView}
        setCurrentView={(view) => {
          setCurrentView(view);
          setMobileSidebarOpen(false);
        }}
        mobileOpen={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
      />

      {/* 2. Responsive Content Container with dynamic sidebar offset */}
      <div
        className={`${
          sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'
        } flex flex-col min-h-screen w-full transition-all duration-300`}
      >
        {/* Unified Top Navigation & Status Bar */}
        <TopNavbar
          emergencyActive={isEmergency}
          onToggleSidebar={() => setMobileSidebarOpen((prev) => !prev)}
          onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
          sidebarCollapsed={sidebarCollapsed}
          currentView={currentView}
          isConnected={isConnected}
          uptime={uptime}
        />

        {/* Main View Port */}
        <main className="w-full pt-20 pb-12 bg-[#080B14] px-4 sm:px-6 flex-1 overflow-y-auto">
          {/* View 1: Command Center */}
          {(currentView === 'command-center' || currentView === 'main-command-hub' || currentView === 'dashboard') && (
            <MainCommandHubView
              onSwitchView={(viewId) => setCurrentView(viewId)}
              metrics={state.metrics}
              signals={state.signals}
              emergencyActive={isEmergency}
              onTriggerEmergency={handleTriggerEmergency}
            />
          )}

          {/* View 2: Single Camera */}
          {currentView === 'single-camera' && (
            <SingleCameraView />
          )}

          {/* View 3: Four-Way Intersection */}
          {(currentView === 'four-way' || currentView === '4-way-ai-perception') && (
            <FourWayPerceptionView
              onSwitchView={(viewId) => setCurrentView(viewId)}
            />
          )}

          {/* View 4: IP Webcam */}
          {currentView === 'ip-webcam' && (
            <IPWebcamView />
          )}

          {/* View 5: Accident & Incident Feed */}
          {(currentView === 'accidents' || currentView === 'incidents') && (
            <AccidentIncidentFeedView />
          )}

          {/* View 6: Evidence Database */}
          {currentView === 'evidence' && (
            <EvidenceDatabaseView />
          )}

          {/* View 7: Traffic Analytics */}
          {currentView === 'analytics' && (
            <TrafficAnalyticsView />
          )}

          {/* View 8: Violence Detection — Coming Soon */}
          {currentView === 'violence-coming-soon' && (
            <ViolenceDetectionView />
          )}

          {/* View 9: System Health & Settings */}
          {currentView === 'system-health' && (
            <SystemHealthView />
          )}
        </main>
      </div>

      {/* 3. Sleek Compact Top Incident Alert Notification */}
      {activePopup && (
        <div className={`fixed top-3 right-5 z-50 max-w-sm sm:max-w-md w-full bg-[#0D1424]/95 border ${
          activePopup.type === 'accident' || activePopup.incident_type === 'accident' ? 'border-red-500/90 shadow-red-950/70' : 'border-cyan-500/80 shadow-cyan-950/50'
        } rounded-xl shadow-xl p-2.5 animate-in fade-in slide-in-from-top-3 duration-200 backdrop-blur-md flex items-center justify-between gap-3`}>
          <div className="flex items-center gap-2.5 min-w-0">
            <span className={`w-2.5 h-2.5 rounded-full ${activePopup.type === 'accident' || activePopup.incident_type === 'accident' ? 'bg-red-400' : 'bg-cyan-400'} animate-ping shrink-0`}></span>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 leading-tight">
                <span className={`text-[10px] font-mono font-bold uppercase tracking-wide shrink-0 ${
                  activePopup.type === 'accident' || activePopup.incident_type === 'accident' ? 'text-red-400 font-extrabold' : 'text-cyan-400 font-bold'
                }`}>
                  {activePopup.type === 'accident' || activePopup.incident_type === 'accident' ? '🚨 Collision / Accident' : '🚑 Ambulance'}
                </span>
                <span className="text-slate-600">·</span>
                <span className="text-[10px] font-mono text-cyan-300 font-semibold truncate max-w-[130px]" title={activePopup.cctv_name || activePopup.camera_id}>
                  {activePopup.cctv_name || (activePopup.camera_id ? (activePopup.camera_id.startsWith('CCTV:') ? activePopup.camera_id : `CCTV: ${activePopup.camera_id}`) : 'CCTV')}
                </span>
              </div>
              <p className="text-[11px] text-slate-200 font-medium truncate mt-0.5">
                {activePopup.description?.replace(/^CCTV:\s*[^—–-]+\s*[—–-]\s*/, '') || activePopup.description}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => {
                setCurrentView('accidents');
                setActivePopup(null);
              }}
              className="px-2.5 py-1 rounded-lg bg-red-950 hover:bg-red-900 border border-red-500/60 text-red-200 text-[11px] font-semibold transition-colors"
            >
              View
            </button>
            <button
              onClick={() => setActivePopup(null)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              title="Dismiss"
            >
              <span className="material-symbols-outlined text-sm block">close</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
