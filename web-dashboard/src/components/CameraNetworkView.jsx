import React, { useState, useEffect } from 'react';

export default function CameraNetworkView() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCam, setNewCam] = useState({
    id: '',
    name: '',
    location: '',
    stream_url: 'assets/videos/north.mp4',
    camera_type: 'traffic'
  });

  const fetchCameras = async () => {
    try {
      const res = await fetch('/api/cameras');
      if (res.ok) {
        const data = await res.json();
        setCameras(data || []);
      }
    } catch (e) {
      console.error('Failed to load cameras', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const handleCreateCamera = async (e) => {
    e.preventDefault();
    if (!newCam.id || !newCam.name) return;
    try {
      const res = await fetch('/api/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCam)
      });
      if (res.ok) {
        setShowAddModal(false);
        setNewCam({ id: '', name: '', location: '', stream_url: 'assets/videos/north.mp4', camera_type: 'traffic' });
        await fetchCameras();
      }
    } catch (e) {
      console.error('Failed to create camera', e);
    }
  };

  const handleToggleStatus = async (cam) => {
    const nextStatus = cam.status === 'online' ? 'offline' : 'online';
    try {
      const res = await fetch(`/api/cameras/${cam.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
      });
      if (res.ok) {
        await fetchCameras();
      }
    } catch (e) {
      console.error('Failed to update status', e);
    }
  };

  const filteredCameras = cameras.filter((c) => {
    if (filter === 'all') return true;
    return c.camera_type === filter;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-surface-container border border-outline-variant/30 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[24px]">linked_camera</span>
          </div>
          <div>
            <h1 className="text-xl font-headline font-bold text-on-surface">
              Camera Network Management
            </h1>
            <p className="text-xs text-on-surface-variant font-mono">
              Multi-Quadrant Traffic Detection Nodes & Autonomous Security CCTV Feeds
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-surface-container-high p-1 rounded-xl border border-outline-variant/30 font-mono text-xs">
            {['all', 'traffic', 'security'].map((t) => (
              <button
                key={t}
                onClick={() => setFilter(t)}
                className={`px-3 py-1 rounded-lg uppercase font-bold transition-all ${
                  filter === t
                    ? 'bg-primary text-on-primary shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="py-2 px-3.5 rounded-xl bg-primary hover:bg-primary/90 text-on-primary font-mono font-bold text-xs uppercase flex items-center gap-1.5 shadow-md shadow-primary/20 transition-all"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Add Camera
          </button>
        </div>
      </div>

      {/* Camera Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredCameras.map((cam) => {
          const isOnline = cam.status === 'online';
          return (
            <div
              key={cam.id}
              className="p-5 rounded-2xl bg-surface-container border border-outline-variant/30 space-y-4 hover:border-primary/40 transition-all shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-surface-container-high text-primary border border-outline-variant/30">
                    {cam.id}
                  </span>
                  <h3 className="font-headline font-bold text-sm text-on-surface mt-1.5">
                    {cam.name}
                  </h3>
                  <p className="text-xs text-on-surface-variant font-mono">{cam.location}</p>
                </div>

                <span
                  className={`px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase flex items-center gap-1.5 ${
                    isOnline
                      ? 'bg-secondary/15 text-secondary border border-secondary/30'
                      : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-secondary animate-pulse' : 'bg-rose-500'}`}
                  ></span>
                  {cam.status}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-surface-container-lowest font-mono text-xs space-y-1 text-on-surface-variant">
                <div className="flex justify-between">
                  <span>Type:</span>
                  <span className="text-on-surface font-bold uppercase">{cam.camera_type}</span>
                </div>
                <div className="flex justify-between">
                  <span>Stream URL:</span>
                  <span className="text-on-surface truncate max-w-[180px]">{cam.stream_url}</span>
                </div>
                <div className="flex justify-between">
                  <span>Registered:</span>
                  <span>{new Date(cam.created_at * 1000).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => handleToggleStatus(cam)}
                  className="flex-1 py-1.5 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-mono font-bold text-xs uppercase transition-all"
                >
                  {isOnline ? 'Disable Stream' : 'Enable Stream'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Camera Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fadeIn">
          <form
            onSubmit={handleCreateCamera}
            className="w-full max-w-md bg-surface-container rounded-2xl border border-outline-variant/40 shadow-2xl p-6 space-y-4"
          >
            <div className="flex items-center justify-between border-b border-outline-variant/20 pb-3">
              <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
                Register New Camera Feed
              </h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-on-surface-variant hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-on-surface-variant mb-1">Camera ID (e.g. CAM_PLAZA_01)</label>
                <input
                  type="text"
                  required
                  value={newCam.id}
                  onChange={(e) => setNewCam({ ...newCam, id: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/40 text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-on-surface-variant mb-1">Camera Name</label>
                <input
                  type="text"
                  required
                  value={newCam.name}
                  onChange={(e) => setNewCam({ ...newCam, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/40 text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-on-surface-variant mb-1">Location Description</label>
                <input
                  type="text"
                  required
                  value={newCam.location}
                  onChange={(e) => setNewCam({ ...newCam, location: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/40 text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-on-surface-variant mb-1">Stream Source (RTSP / Video File)</label>
                <input
                  type="text"
                  required
                  value={newCam.stream_url}
                  onChange={(e) => setNewCam({ ...newCam, stream_url: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/40 text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-on-surface-variant mb-1">System Module</label>
                <select
                  value={newCam.camera_type}
                  onChange={(e) => setNewCam({ ...newCam, camera_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/40 text-on-surface focus:outline-none focus:border-primary"
                >
                  <option value="traffic">Traffic Management (Module 1)</option>
                  <option value="security">Security Surveillance (Module 2)</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-outline-variant/20">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="py-2 px-4 rounded-xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-mono font-bold text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="py-2 px-5 rounded-xl bg-primary hover:bg-primary/90 text-on-primary font-mono font-bold text-xs uppercase"
              >
                Save Camera
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
