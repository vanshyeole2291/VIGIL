import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import TopNavbar from './components/TopNavbar';
import MainCommandHubView from './components/MainCommandHubView';
import FourWayPerceptionView from './components/FourWayPerceptionView';
import IncidentMonitor from './components/IncidentMonitor';
import SecuritySurveillanceView from './components/SecuritySurveillanceView';
import EvidenceVaultView from './components/EvidenceVaultView';
import CameraNetworkView from './components/CameraNetworkView';
import SystemHealthView from './components/SystemHealthView';
import ModelPerformanceView from './components/ModelPerformanceView';
import EmergencyResponseView from './components/EmergencyResponseView';
import AccidentMonitoringView from './components/AccidentMonitoringView';
import TrafficAnalyticsView from './components/TrafficAnalyticsView';
import DataSourcesView from './components/DataSourcesView';
import DatabaseStorageView from './components/DatabaseStorageView';
import SettingsView from './components/SettingsView';

function App() {
  const [currentView, setCurrentView] = useState('main-command-hub');
  const [selectedIntersection, setSelectedIntersection] = useState('j04');
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
      await fetch('/api/emergency', {
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
    <div className="bg-surface font-body text-on-surface min-h-screen selection:bg-primary-container selection:text-on-primary-container">
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
          selectedIntersection={selectedIntersection}
          setSelectedIntersection={setSelectedIntersection}
          emergencyActive={isEmergency}
          onToggleSidebar={() => setMobileSidebarOpen((prev) => !prev)}
          onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
          sidebarCollapsed={sidebarCollapsed}
          currentView={currentView}
        />

        {/* Main View Port */}
        <main className="w-full pt-16 pb-24 bg-surface px-3 sm:px-gutter flex-1 overflow-y-auto">
          <div className="pt-space-md">
            {currentView === 'incidents' && (
              <IncidentMonitor />
            )}

            {(currentView === 'main-command-hub' || currentView === 'dashboard') && (
              <MainCommandHubView
                onSelectIntersection={(jId) => setSelectedIntersection(jId)}
                onSwitchView={(viewId) => setCurrentView(viewId)}
                metrics={state.metrics}
                signals={state.signals}
                emergencyActive={isEmergency}
                onTriggerEmergency={handleTriggerEmergency}
              />
            )}

            {currentView === '4-way-ai-perception' && (
              <FourWayPerceptionView
                selectedIntersection={selectedIntersection}
                onSwitchView={(viewId) => setCurrentView(viewId)}
                signals={state.signals}
                emergencyActive={isEmergency}
              />
            )}

            {currentView === 'emergency-response' && (
              <EmergencyResponseView
                signals={state.signals}
                emergencyActive={isEmergency}
                onTriggerEmergency={handleTriggerEmergency}
              />
            )}

            {currentView === 'accident-monitoring' && (
              <AccidentMonitoringView />
            )}

            {currentView === 'traffic-analytics' && (
              <TrafficAnalyticsView
                metrics={state.metrics}
                signals={state.signals}
              />
            )}

            {currentView === 'model-performance' && (
              <ModelPerformanceView />
            )}

            {currentView === 'security-surveillance' && (
              <SecuritySurveillanceView />
            )}

            {currentView === 'evidence-vault' && (
              <EvidenceVaultView />
            )}

            {currentView === 'camera-network' && (
              <CameraNetworkView />
            )}

            {currentView === 'data-sources' && (
              <DataSourcesView />
            )}

            {currentView === 'database-storage' && (
              <DatabaseStorageView />
            )}

            {currentView === 'system-health' && (
              <SystemHealthView />
            )}

            {currentView === 'settings' && (
              <SettingsView />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
