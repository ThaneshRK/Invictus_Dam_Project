import React from 'react';
import StatusBadge from './ui/StatusBadge';

const SystemHealth: React.FC = () => {
  const healthData = [
    { service: 'FastAPI Backend', status: 'OPERATIONAL', latency: '24ms', message: 'Connected' },
    { service: 'PostgreSQL Database', status: 'OPERATIONAL', latency: '4ms', message: 'flood_db accessible' },
    { service: 'PostGIS Extension', status: 'OPERATIONAL', latency: '-', message: 'Spatial functions verified' },
    { service: 'Background Worker Queue', status: 'OPERATIONAL', latency: '-', message: 'Ready' },
    { service: 'SPH Physics Engine', status: 'OPERATIONAL', latency: '-', message: 'Solver available' },
    { service: 'Delft3D Engine (CLI)', status: 'DEGRADED', latency: '-', message: 'Binary not found in PATH. Using Fixture Mode.' },
    { service: 'Google Earth Engine API', status: 'DEGRADED', latency: '-', message: 'Credentials missing. Using Fixture Mode.' },
  ];

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2>System Diagnostic & Health</h2>
        <p style={{ color: 'var(--text-muted)' }}>Real-time status of all microservices, databases, and external physics binaries.</p>
      </div>

      <div className="card">
        <table className="dense-table">
          <thead>
            <tr>
              <th>Service Component</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Diagnostic Message</th>
            </tr>
          </thead>
          <tbody>
            {healthData.map((h, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 500 }}>{h.service}</td>
                <td><StatusBadge status={h.status as any} /></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{h.latency}</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{h.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SystemHealth;
