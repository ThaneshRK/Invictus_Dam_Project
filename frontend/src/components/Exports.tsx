import React, { useState } from 'react';
import { FileOutput } from 'lucide-react';
import axios from 'axios';
import EmptyState from './ui/EmptyState';

const Exports: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      await axios.post('http://localhost:8000/api/v1/exports', {
        result_id: "Idukki_SPH_Run1_MaxDepth",
        format: "GeoJSON"
      });
      alert("Export job queued successfully!");
    } catch (err) {
      alert("Failed to queue export job.");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2>GIS Export Center</h2>
        <p style={{ color: 'var(--text-muted)' }}>Generate interoperable geospatial files (SHP, KML, GeoJSON) from PostgreSQL/PostGIS result data.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>Generate New Export</h3>
          <div className="form-group">
            <label className="form-label">Simulation Result</label>
            <select className="form-select">
              <option>Idukki_SPH_Run1_MaxDepth</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Target Format</label>
            <select className="form-select">
              <option>ESRI Shapefile (.shp)</option>
              <option>GeoJSON (.geojson)</option>
              <option>Keyhole Markup Language (.kml)</option>
              <option>GeoTIFF (.tif)</option>
            </select>
          </div>
          <button className="btn-primary" onClick={handleExport} disabled={loading}>
            <FileOutput size={16} /> {loading ? "Queueing..." : "Request Generation Job"}
          </button>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>Available Downloads</h3>
          <EmptyState 
            title="No Exports Ready" 
            message="You have not requested any GIS exports yet." 
          />
        </div>
      </div>
    </div>
  );
};

export default Exports;
