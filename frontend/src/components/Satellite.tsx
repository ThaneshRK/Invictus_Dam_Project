import React, { useState } from 'react';
import axios from 'axios';
import { Radio, CloudRain } from 'lucide-react';
import EmptyState from './ui/EmptyState';

const Satellite: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchSatelliteData = async () => {
    setLoading(true);
    try {
      const res = await axios.post('http://localhost:8000/api/v1/satellite/extract', {
        bounds: [[9.8, 76.9], [9.9, 77.0]],
        start_date: "2023-08-01",
        end_date: "2023-08-15"
      });
      setData(res.data);
    } catch (err) {
      alert("Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Earth Observation (GEE Integration)</h2>
          <p style={{ color: 'var(--text-muted)' }}>Monitor real-world validation using Sentinel-1 SAR observations.</p>
        </div>
        <button className="btn-primary" onClick={fetchSatelliteData} disabled={loading}>
          <Radio size={16} /> {loading ? "Querying..." : "Query Earth Engine"}
        </button>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ fontSize: '15px' }}>Sentinel-1 SAR Detection</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Synthetic Aperture Radar penetrates cloud cover to detect surface water changes. We use Google Earth Engine to extract the `VV` polarization mask.
            </p>
          </div>
          <div style={{ padding: '16px', backgroundColor: '#f8fafc', borderRadius: '8px', minWidth: '250px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '8px' }}>CURRENT SENSOR STATUS</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--deep-navy)', fontWeight: 500, fontSize: '14px' }}>
              <CloudRain size={16} color="var(--water-blue)" /> Earth Engine API Available
            </div>
          </div>
        </div>
      </div>

      {!data ? (
        <EmptyState 
          title="No Satellite Imagery Queried" 
          message="Select a date range and region to query the Sentinel-1 collection. Note: If GEE credentials are not configured, the system will return a static test fixture."
          action={<button className="btn-secondary" onClick={fetchSatelliteData}>Run Extraction Job</button>}
        />
      ) : (
        <div className="card">
          <h3 style={{ color: 'var(--success-green)' }}>Extraction Complete</h3>
          <pre style={{ backgroundColor: '#1e293b', color: '#e2e8f0', padding: '16px', borderRadius: '4px', overflowX: 'auto', marginTop: '16px' }}>
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default Satellite;
