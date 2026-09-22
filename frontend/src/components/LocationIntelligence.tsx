import React, { useEffect, useState } from 'react';
import { useProject } from '../context/ProjectContext';
import api from '../api';
import { Info, Users, Droplets, MapPin } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const LocationIntelligence: React.FC = () => {
  const { activeProject } = useProject();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchIntelligence = async () => {
    if (!activeProject) return;
    setLoading(true);
    try {
      const res = await api.get(`/projects/${activeProject.id}/enrichment`);
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntelligence();
    const interval = setInterval(() => {
      if (data && data.job_status !== 'COMPLETED' && data.job_status !== 'FAILED' && data.job_status !== 'PARTIAL') {
        fetchIntelligence();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [activeProject, data?.job_status]);

  if (!activeProject) return <div className="card">Select a project to view location intelligence.</div>;
  if (loading && !data) return <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}><div className="loading-spinner"></div></div>;

  const renderStatus = () => {
    if (!data) return null;
    if (data.job_status === 'PENDING' || data.job_status === 'RUNNING') {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--warning-orange)', marginBottom: '16px' }}>
          <div className="loading-spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
          Fetching government datasets...
        </div>
      );
    }
    if (data.job_status === 'PARTIAL') {
      return <div style={{ color: 'var(--warning-orange)', marginBottom: '16px' }}>Enrichment completed with partial failures. Check source status below.</div>;
    }
    if (data.job_status === 'FAILED') {
      return <div style={{ color: 'var(--danger-red)', marginBottom: '16px' }}>Location enrichment failed.</div>;
    }
    return null;
  };

  return (
    <div style={{ marginTop: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3>Location Intelligence Profile</h3>
        <button className="btn-secondary" onClick={fetchIntelligence} style={{ fontSize: '12px', padding: '4px 8px' }}>
          Refresh
        </button>
      </div>

      {renderStatus()}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
        
        {/* Dam Profile */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <Info size={18} color="var(--water-blue)" />
            <h4 style={{ margin: 0 }}>Primary Dam Profile</h4>
          </div>
          {data?.selected_dam ? (
            <div>
              <h5 style={{ margin: '0 0 8px 0', fontSize: '16px', color: 'var(--deep-navy)' }}>{data.selected_dam.dam_name}</h5>
              <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: 'var(--text-muted)' }}>{data.selected_dam.operator}</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '13px' }}>
                <div><span style={{ color: 'var(--text-muted)' }}>River:</span> {data.selected_dam.river}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Basin:</span> {data.selected_dam.river_basin}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Type:</span> {data.selected_dam.dam_type}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Completed:</span> {data.selected_dam.year_completed}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Height:</span> {data.selected_dam.dam_height_m}m</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Capacity:</span> {data.selected_dam.gross_storage_capacity_mcm} MCM</div>
              </div>

              <div style={{ marginTop: '20px', fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px dashed var(--border-color)', paddingTop: '12px' }}>
                Source: {data.selected_dam.source_name} | ID: {data.selected_dam.source_record_id}
                <br/>Retrieved: {new Date(data.selected_dam.retrieved_at).toLocaleString()}
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No dam data available for this location.</div>
          )}
        </div>

        {/* Population Exposure */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <Users size={18} color="var(--warning-orange)" />
            <h4 style={{ margin: 0 }}>Population Exposure</h4>
          </div>
          {data?.population ? (
            <div>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Within 5km</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{data.population.population_5km?.toLocaleString()}</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Within 10km</div>
                  <div style={{ fontSize: '16px', fontWeight: 500 }}>{data.population.population_10km?.toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Within 25km</div>
                  <div style={{ fontSize: '16px', fontWeight: 500 }}>{data.population.population_25km?.toLocaleString()}</div>
                </div>
              </div>
              <div style={{ marginTop: '20px', fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px dashed var(--border-color)', paddingTop: '12px' }}>
                Source: {data.population.source_name}
                <br/>Methodology: {data.population.methodology}
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No population data available.</div>
          )}
        </div>

        {/* Dynamic Water Status */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <Droplets size={18} color="var(--success-green)" />
            <h4 style={{ margin: 0 }}>Live Reservoir Status</h4>
          </div>
          {data?.water_snapshot ? (
            <div>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Current Level</div>
                <div style={{ fontSize: '24px', fontWeight: 600, color: 'var(--water-blue)' }}>{data.water_snapshot.current_water_level_m} m</div>
              </div>
              
              {data.water_snapshot.storage_percentage && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                    <span>Storage Capacity</span>
                    <span>{data.water_snapshot.storage_percentage}%</span>
                  </div>
                  <div style={{ height: '6px', backgroundColor: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(data.water_snapshot.storage_percentage, 100)}%`, height: '100%', backgroundColor: data.water_snapshot.storage_percentage > 85 ? 'var(--danger-red)' : 'var(--water-blue)' }}></div>
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '13px' }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Inflow:</span> {data.water_snapshot.inflow_cumec} cumecs</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Outflow:</span> {data.water_snapshot.outflow_cumec} cumecs</div>
              </div>

              <div style={{ marginTop: '20px', fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px dashed var(--border-color)', paddingTop: '12px' }}>
                Source: {data.water_snapshot.source_name}
                <br/>Observed: {new Date(data.water_snapshot.observation_date).toLocaleString()}
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Real-time telemetry unavailable.</div>
          )}
        </div>
      </div>
      
      {/* Map visualization of the candidates/radii */}
      {activeProject.latitude && activeProject.longitude && (
        <div className="card" style={{ marginTop: '24px', padding: '0', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid var(--border-color)' }}>
            <h4 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}><MapPin size={18} /> Location Context</h4>
          </div>
          <div style={{ height: '350px', width: '100%' }}>
            <MapContainer center={[activeProject.latitude, activeProject.longitude]} zoom={11} style={{ height: '100%', width: '100%' }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Marker position={[activeProject.latitude, activeProject.longitude]}>
                <Popup>Project Area</Popup>
              </Marker>
              
              {/* Population Radii */}
              <Circle center={[activeProject.latitude, activeProject.longitude]} radius={5000} pathOptions={{ color: 'var(--warning-orange)', weight: 1, fillOpacity: 0.1 }} />
              <Circle center={[activeProject.latitude, activeProject.longitude]} radius={10000} pathOptions={{ color: 'var(--warning-orange)', weight: 1, fillOpacity: 0.05 }} />
            </MapContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default LocationIntelligence;
