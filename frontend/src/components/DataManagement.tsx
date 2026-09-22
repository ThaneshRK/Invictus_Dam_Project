import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle2 } from 'lucide-react';
import api from '../api';
import { useProject } from '../context/ProjectContext';
import StatusBadge from './ui/StatusBadge';

const DataManagement: React.FC = () => {
  const { activeProject } = useProject();
  const [loading, setLoading] = useState(false);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [govDatasets, setGovDatasets] = useState<any[]>([]);
  const [govDams, setGovDams] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [datasetType, setDatasetType] = useState('ELEVATION');
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDatasets = async () => {
    if (!activeProject) return;
    try {
      const res = await api.get(`/projects/${activeProject.id}/datasets`);
      setDatasets(res.data);
    } catch (e) {
      console.error("Failed to fetch datasets", e);
    }
  };

  const fetchGovData = async () => {
    try {
      const resDs = await api.get('/government/datasets');
      setGovDatasets(resDs.data.datasets || []);
      const resDams = await api.get('/government/dams?limit=10');
      setGovDams(resDams.data.dams || []);
    } catch (e) {
      console.error("Failed to fetch gov data", e);
    }
  };

  useEffect(() => {
    fetchDatasets();
    fetchGovData();
  }, [activeProject]);

  const handleUpload = async () => {
    if (!activeProject) return alert("Select a project first");
    if (!name || !file) return alert("Name and File are required");

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("dataset_type", datasetType);
      formData.append("file", file);

      await api.post(`/projects/${activeProject.id}/datasets`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("Dataset uploaded and validated successfully.");
      setName('');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      fetchDatasets();
    } catch (e) {
      console.error(e);
      alert("Upload failed.");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2>GIS Data Ingestion & Validation</h2>
        <p style={{ color: 'var(--text-muted)' }}>Upload and standardize Raster (DEM) and Vector (Dam/River) datasets.</p>
        {!activeProject && <p style={{ color: 'var(--warning-yellow)' }}>Please create or select a project in the Dashboard to upload datasets.</p>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>Upload New Dataset</h3>
          <div className="form-group">
            <label className="form-label">Dataset Name</label>
            <input className="form-input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. SRTM 30m" />
          </div>
          <div className="form-group" style={{ marginTop: '12px' }}>
            <label className="form-label">Dataset Type</label>
            <select className="form-select" value={datasetType} onChange={e => setDatasetType(e.target.value)}>
              <option value="ELEVATION">Digital Elevation Model (Raster)</option>
              <option value="INFRASTRUCTURE">Dam Infrastructure (Vector)</option>
              <option value="LAND_COVER">Land Cover (Raster/Vector)</option>
              <option value="HYDROLOGY">River Geometry (Vector)</option>
            </select>
          </div>
          
          <div style={{ 
            border: '2px dashed var(--border-color)', 
            borderRadius: '6px', 
            padding: '20px', 
            textAlign: 'center',
            backgroundColor: '#f8fafc',
            marginTop: '16px',
            marginBottom: '16px'
          }}>
            <input type="file" ref={fileInputRef} onChange={e => setFile(e.target.files?.[0] || null)} style={{ marginBottom: '8px' }} />
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Max size 500MB. Supported: .tif, .geojson, .zip</div>
          </div>
          
          <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={handleUpload} disabled={loading}>
            {loading ? "Validating..." : "Upload & Validate"}
          </button>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>Current Project Datasets</h3>
          <table className="dense-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Resolution</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {datasets.length === 0 ? (
                <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No datasets found for this project.</td></tr>
              ) : datasets.map(d => (
                <tr key={d.id}>
                  <td style={{ fontWeight: 500 }}>{d.name}</td>
                  <td>{d.dataset_type}</td>
                  <td>{d.resolution ? `${d.resolution}m` : 'N/A'}</td>
                  <td><StatusBadge status="COMPLETED" /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--success-green)' }}>
            <CheckCircle2 size={16} /> All CRS automatically normalized to Project EPSG:32643
          </div>
        </div>
      </div>

      <div style={{ marginTop: '32px' }}>
        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>India-Wide Government Data (Global)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div>
              <h4 style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--text-muted)' }}>Registered Datasets</h4>
              <table className="dense-table">
                <thead>
                  <tr>
                    <th>Source File</th>
                    <th>Classification</th>
                    <th>Status</th>
                    <th>Features</th>
                  </tr>
                </thead>
                <tbody>
                  {govDatasets.length === 0 ? (
                    <tr><td colSpan={4} style={{ textAlign: 'center' }}>No government datasets loaded.</td></tr>
                  ) : govDatasets.map(d => (
                    <tr key={d.id}>
                      <td>{d.source_filename}</td>
                      <td>{d.classification}</td>
                      <td><StatusBadge status={d.ingestion_status === 'INGESTED' ? 'COMPLETED' : d.ingestion_status || 'PENDING'} /></td>
                      <td>{d.feature_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            <div>
              <h4 style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--text-muted)' }}>Sample Dams (Readiness)</h4>
              <table className="dense-table">
                <thead>
                  <tr>
                    <th>Dam Name</th>
                    <th>State</th>
                    <th>Type</th>
                    <th>Readiness</th>
                  </tr>
                </thead>
                <tbody>
                  {govDams.length === 0 ? (
                    <tr><td colSpan={4} style={{ textAlign: 'center' }}>No government dams loaded.</td></tr>
                  ) : govDams.map(d => (
                    <tr key={d.id}>
                      <td>{d.name}</td>
                      <td>{d.state}</td>
                      <td>{d.type}</td>
                      <td>
                        <span style={{ 
                          padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
                          backgroundColor: d.readiness === 'AVAILABLE' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                          color: d.readiness === 'AVAILABLE' ? 'var(--success-green)' : 'var(--danger-red)'
                        }}>
                          {d.readiness}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataManagement;
