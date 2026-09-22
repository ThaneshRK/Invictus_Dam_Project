import React from 'react';
import { MapContainer, TileLayer, Polygon, LayersControl, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Layers } from 'lucide-react';
import { useProject } from '../context/ProjectContext';

function ChangeView({ center, zoom }: { center: [number, number], zoom: number }) {
  const map = useMap();
  map.setView(center, zoom);
  return null;
}

const MapViewer: React.FC = () => {
  const { BaseLayer, Overlay } = LayersControl;
  const { activeProject } = useProject();

  const lat = activeProject?.latitude || 9.84;
  const lng = activeProject?.longitude || 76.97;

  // Mock bounds centered around project (4 points for a complete polygon)
  const bounds = [
    [lat - 0.04, lng - 0.07], // Bottom-Left
    [lat + 0.01, lng - 0.07], // Top-Left
    [lat + 0.01, lng + 0.01], // Top-Right
    [lat - 0.04, lng + 0.01]  // Bottom-Right
  ];
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2>Interactive Flood Map Viewer</h2>
      </div>
      
      <div style={{ display: 'flex', gap: '20px', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: 1, borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)', position: 'relative' }}>
          <MapContainer center={[lat, lng]} zoom={13} style={{ height: '100%', width: '100%' }}>
            <ChangeView center={[lat, lng]} zoom={13} />
            <LayersControl position="topright">
              <BaseLayer checked name="OpenStreetMap">
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; OpenStreetMap contributors'
                />
              </BaseLayer>
              <BaseLayer name="Satellite">
                <TileLayer
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  attribution='Tiles &copy; Esri'
                />
              </BaseLayer>
              <Overlay checked name="Flood Extent (Simulation)">
                <Polygon positions={bounds as any} pathOptions={{ color: 'var(--flood-cyan)', fillOpacity: 0.4, weight: 2 }} />
              </Overlay>
            </LayersControl>
          </MapContainer>
        </div>

        <div style={{ width: '300px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
          <div className="card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px' }}>
              <Layers size={18} /> Layer Control
            </h3>
            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                <input type="checkbox" defaultChecked /> Flood Extent (Max Depth)
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                <input type="checkbox" /> Affected Infrastructure
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                <input type="checkbox" /> Digital Elevation Model
              </label>
            </div>
          </div>
          
          <div className="card">
            <h3 style={{ fontSize: '15px' }}>Depth Legend</h3>
            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><div style={{ width: '16px', height: '16px', background: '#e0f3db' }}></div> 0 - 0.5 m</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><div style={{ width: '16px', height: '16px', background: '#a8ddb5' }}></div> 0.5 - 1.0 m</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><div style={{ width: '16px', height: '16px', background: '#4eb3d3' }}></div> 1.0 - 2.0 m</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><div style={{ width: '16px', height: '16px', background: '#2b8cbe' }}></div> 2.0 - 5.0 m</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><div style={{ width: '16px', height: '16px', background: '#0868ac' }}></div> &gt; 5.0 m</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapViewer;
