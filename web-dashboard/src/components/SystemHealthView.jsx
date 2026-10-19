import React, { useState, useEffect } from 'react';

export default function SystemHealthView() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/system/health');
      if (res.ok) {
        const data = await res.json();
        setHealthData(data);
      }
    } catch (e) {
      console.error('Failed to load system health', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-surface-container border border-outline-variant/30 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[24px]">health_and_safety</span>
          </div>
          <div>
            <h1 className="text-xl font-headline font-bold text-on-surface">
              System Health & Diagnostics
            </h1>
            <p className="text-xs text-on-surface-variant font-mono">
              VIGIL Multi-Modal Runtime &bull; SQLite Persistence &bull; Edge Inference Telemetry
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-container-high border border-outline-variant/30 font-mono text-xs">
          <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse"></span>
          <span className="text-on-surface font-bold uppercase">
            STATUS: {healthData?.status || 'MONITORING'}
          </span>
        </div>
      </div>

      {/* Diagnostics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* 1. Database Health */}
        <div className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">database</span>
              <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
                Database Engine
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-secondary/15 text-secondary">
              {healthData?.database?.status || 'CONNECTED'}
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs text-on-surface-variant">
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Database Provider:</span>
              <span className="text-on-surface font-bold">{healthData?.database?.type || 'SQLite'}</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Path:</span>
              <span className="text-on-surface truncate max-w-[150px]">{healthData?.database?.database_path || 'vigil.db'}</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Persisted Incidents:</span>
              <span className="text-on-surface font-bold">{healthData?.database?.total_incidents || 0}</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Active Alerts:</span>
              <span className="text-on-surface font-bold">{healthData?.database?.total_alerts || 0}</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Registered Cameras:</span>
              <span className="text-on-surface font-bold">{healthData?.database?.total_cameras || 0}</span>
            </div>
          </div>
        </div>

        {/* 2. Traffic Perception (Module 1) */}
        <div className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">traffic</span>
              <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
                Module 1: Traffic AI
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-secondary/15 text-secondary">
              OPERATIONAL
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs text-on-surface-variant">
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Model Architecture:</span>
              <span className="text-on-surface font-bold">YOLOv8 CSPDarknet</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>PCU Standard:</span>
              <span className="text-on-surface font-bold">IRC:106 Indian Highway</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Signal Optimization:</span>
              <span className="text-on-surface font-bold">Webster Delay Formula</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Collision Verification:</span>
              <span className="text-on-surface font-bold">Kinematic Two-Phase IoU</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>YOLO Checkpoints:</span>
              <span className="text-on-surface font-bold">
                {healthData?.modules?.module_1_traffic?.yolo_models_detected?.length || 0} Found
              </span>
            </div>
          </div>
        </div>

        {/* 3. Security Surveillance (Module 2) */}
        <div className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">security</span>
              <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
                Module 2: Security AI
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400">
              {healthData?.modules?.module_2_security?.status || 'MODEL_NOT_CONFIGURED'}
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs text-on-surface-variant">
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Classifier Graph:</span>
              <span className="text-on-surface font-bold">MobileNetV2 + BiLSTM</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Input Shape:</span>
              <span className="text-on-surface font-bold">(1, 3, 16, 224, 224)</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Compute Device:</span>
              <span className="text-on-surface font-bold uppercase">
                {healthData?.modules?.module_2_security?.device || 'CPU'}
              </span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Integrity Policy:</span>
              <span className="text-secondary font-bold">Zero Mock Predictions</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-surface-container-low">
              <span>Evidence Clipping:</span>
              <span className="text-secondary font-bold">Active (10s Circular)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
