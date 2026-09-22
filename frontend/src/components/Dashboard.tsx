import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import KPICard from './ui/KPICard';
import { Activity, Droplets, Map, Server, Waves, FileText, Plus, Search } from 'lucide-react';
import api from '../api';
import { useProject } from '../context/ProjectContext';
import LocationIntelligence from './LocationIntelligence';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix leaflet icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

function MapController({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    if (!isNaN(center[0]) && !isNaN(center[1])) {
      map.setView(center, map.getZoom() > 8 ? map.getZoom() : 9);
    }
  }, [center, map]);
  return null;
}

function LocationMarker({ position, setPosition }: { position: [number, number], setPosition: (p: [number, number]) => void }) {
  useMapEvents({
    click(e) {
      setPosition([e.latlng.lat, e.latlng.lng]);
    },
  });
  return (isNaN(position[0]) || isNaN(position[1])) ? null : <Marker position={position} />;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { projects, activeProject, setActiveProject, createProject, loading, error } = useProject();
  const [newProjectName, setNewProjectName] = useState('');
  const [newLat, setNewLat] = useState<number>(11.80);
  const [newLng, setNewLng] = useState<number>(77.80);
  const [latStr, setLatStr] = useState<string>('11.80');
  const [lngStr, setLngStr] = useState<string>('77.80');
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [stats, setStats] = useState({
    simulations: 0,
    completed: 0,
    health: 'Checking...'
  });

  useEffect(() => {
    // Fetch stats (simulations) in a real app
    const fetchStats = async () => {
      try {
        const res = await api.get('/simulations');
        setStats(s => ({ ...s, simulations: res.data.length, health: 'ONLINE' }));
      } catch (err) {
        setStats(s => ({ ...s, health: 'API UNAVAILABLE' }));
      }
    };
    fetchStats();
  }, []);

  const updateCoords = (latVal: number, lngVal: number) => {
    setNewLat(latVal);
    setNewLng(lngVal);
    setLatStr(Math.abs(latVal).toFixed(4));
    setLngStr(Math.abs(lngVal).toFixed(4));
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      if (data && data.length > 0) {
        const result = data[0];
        const parsedLat = parseFloat(result.lat);
        const parsedLng = parseFloat(result.lon);
        updateCoords(parsedLat, parsedLng);
      } else {
        alert('Location not found. Please try a different search query.');
      }
    } catch (e) {
      console.error("Search failed", e);
      alert('Search request failed. Please check internet connection.');
    } finally {
      setSearching(false);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName) return;
    try {
      await createProject(newProjectName, "Created from dashboard", newLat, newLng);
      setNewProjectName('');
      setShowCreate(false);
    } catch (e) {
      alert("Failed to create project");
    }
  };

  const validLat = isNaN(newLat) ? 20.5937 : newLat;
  const validLng = isNaN(newLng) ? 78.9629 : newLng;

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h1>Flood Simulation Command Center</h1>
        <p style={{ color: 'var(--text-muted)' }}>Monitor terrain, hydrological conditions, simulations, and flood impacts in real-time.</p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '24px',
        marginBottom: '32px'
      }}>
        <KPICard title="Active Projects" value={loading ? '...' : projects.length} icon={<FileText />} />
        <KPICard title="Running Simulations" value={stats.simulations} icon={<Activity />} />
        <KPICard title="Completed Simulations" value={stats.completed} icon={<Waves />} />
        <KPICard title="System Status" value={stats.health} icon={<Server />} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginBottom: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <h3>Your Projects</h3>
            <button className="btn-secondary" style={{ fontSize: '13px', padding: '4px 10px' }} onClick={() => setShowCreate(!showCreate)}>
              <Plus size={14} style={{ marginRight: '4px' }} /> New Project
            </button>
          </div>
          
          {showCreate && (
            <div style={{ marginBottom: '24px', padding: '16px', border: '1px solid var(--border-color)', borderRadius: '8px', backgroundColor: 'var(--bg-card)' }}>
              <h4 style={{ marginBottom: '12px' }}>Project Details & Mini Map Location</h4>
              
              <div style={{ marginBottom: '12px' }}>
                <input 
                  type="text" 
                  className="form-input" 
                  style={{ width: '100%' }}
                  placeholder="Project Name (e.g., Mettur Dam)" 
                  value={newProjectName} 
                  onChange={e => setNewProjectName(e.target.value)}
                />
              </div>

              {/* Location Search Up */}
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input 
                  type="text" 
                  className="form-input" 
                  style={{ flex: 1 }}
                  placeholder="Search location (e.g. Mettur Dam, Narmada, Tehri)..." 
                  value={searchQuery} 
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleSearch())}
                />
                <button 
                  type="button" 
                  className="btn-secondary" 
                  onClick={handleSearch} 
                  disabled={searching}
                  style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Search size={14} />
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>

              {/* User-friendly Latitude and Longitude with direction (N/S, E/W) */}
              <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Lat:</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    style={{ width: '100px' }}
                    placeholder="11.80" 
                    value={latStr} 
                    onChange={e => {
                      setLatStr(e.target.value);
                      const parsed = parseFloat(e.target.value);
                      if (!isNaN(parsed)) {
                        const isN = newLat >= 0;
                        setNewLat(isN ? Math.abs(parsed) : -Math.abs(parsed));
                      }
                    }}
                  />
                  <select 
                    className="form-input" 
                    value={newLat >= 0 ? 'N' : 'S'}
                    onChange={e => {
                      const isN = e.target.value === 'N';
                      const absVal = Math.abs(newLat);
                      setNewLat(isN ? absVal : -absVal);
                    }}
                    style={{ width: '56px', padding: '0 4px' }}
                  >
                    <option value="N">N</option>
                    <option value="S">S</option>
                  </select>
                </div>

                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Lng:</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    style={{ width: '100px' }}
                    placeholder="77.80" 
                    value={lngStr} 
                    onChange={e => {
                      setLngStr(e.target.value);
                      const parsed = parseFloat(e.target.value);
                      if (!isNaN(parsed)) {
                        const isE = newLng >= 0;
                        setNewLng(isE ? Math.abs(parsed) : -Math.abs(parsed));
                      }
                    }}
                  />
                  <select 
                    className="form-input" 
                    value={newLng >= 0 ? 'E' : 'W'}
                    onChange={e => {
                      const isE = e.target.value === 'E';
                      const absVal = Math.abs(newLng);
                      setNewLng(isE ? absVal : -absVal);
                    }}
                    style={{ width: '56px', padding: '0 4px' }}
                  >
                    <option value="E">E</option>
                    <option value="W">W</option>
                  </select>
                </div>
              </div>

              {/* Mini Map */}
              <div style={{ height: '220px', width: '100%', marginBottom: '12px', borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                <MapContainer center={[validLat, validLng]} zoom={8} style={{ height: '100%', width: '100%' }}>
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <MapController center={[validLat, validLng]} />
                  <LocationMarker position={[validLat, validLng]} setPosition={(p) => updateCoords(p[0], p[1])} />
                </MapContainer>
              </div>

              <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={handleCreateProject}>
                Create Project
              </button>
            </div>
          )}

          {error && <div style={{ color: 'var(--danger-red)', marginBottom: '16px' }}>{error}</div>}
          
          <table className="dense-table">
            <thead>
              <tr>
                <th>Project Name</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {projects.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No projects found. Create one to get started.</td>
                </tr>
              ) : (
                projects.map(p => (
                  <tr key={p.id} style={{ backgroundColor: activeProject?.id === p.id ? 'var(--hover-bg)' : 'transparent' }}>
                    <td style={{ fontWeight: 500 }}>
                      {p.name} {activeProject?.id === p.id && <span style={{ fontSize: '10px', backgroundColor: 'var(--water-blue)', color: '#fff', padding: '2px 6px', borderRadius: '10px', marginLeft: '8px' }}>ACTIVE</span>}
                    </td>
                    <td>{new Date(p.created_at).toLocaleDateString()}</td>
                    <td>
                      <button 
                        className="btn-secondary" 
                        style={{ padding: '2px 8px', fontSize: '12px' }}
                        onClick={() => setActiveProject(p)}
                        disabled={activeProject?.id === p.id}
                      >
                        {activeProject?.id === p.id ? 'Selected' : 'Select'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Quick Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '20px' }}>
            <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => navigate('/map')}>
              <Map size={18} /> Open Interactive Map
            </button>
            <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => navigate('/scenarios')}>
              <Droplets size={18} /> New Scenario
            </button>
          </div>
        </div>
      </div>

      <LocationIntelligence />
    </div>
  );
};

export default Dashboard;
