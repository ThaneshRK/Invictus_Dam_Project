import React from 'react';
import { BarChart2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import EmptyState from './ui/EmptyState';

const Comparison: React.FC = () => {
  // Using dummy data structurally similar to what the API will return
  const data = [
    { metric: 'Max Depth (m)', SPH: 14.2, Delft3D: 14.5 },
    { metric: 'Flood Area (km²)', SPH: 24.1, Delft3D: 25.0 },
    { metric: 'Peak Velocity (m/s)', SPH: 5.8, Delft3D: 5.5 },
  ];

  const hasData = false; // Toggle to false to show the realistic EmptyState initially

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2>Cross-Model Validation (SPH vs Delft3D)</h2>
        <p style={{ color: 'var(--text-muted)' }}>Analytically compare the spatial output rasters of different numerical solvers.</p>
      </div>

      {!hasData ? (
        <EmptyState 
          title="Insufficient Results" 
          message="To compare models, you must first run both an SPH simulation and a Delft3D simulation for the exact same Scenario ID."
          action={<button className="btn-secondary">Go to Simulations</button>}
        />
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', marginBottom: '24px' }}>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>Intersection over Union (IoU)</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--deep-navy)', marginTop: '8px' }}>86.4%</div>
              <div style={{ fontSize: '12px', color: 'var(--success-green)', marginTop: '4px' }}>High Spatial Agreement</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>Depth Root Mean Square Error</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--deep-navy)', marginTop: '8px' }}>0.42m</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>Depth Mean Absolute Error</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--deep-navy)', marginTop: '8px' }}>0.28m</div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <BarChart2 size={18} /> Value Discrepancy Breakdown
            </h3>
            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                  <XAxis dataKey="metric" axisLine={false} tickLine={false} />
                  <YAxis axisLine={false} tickLine={false} />
                  <Tooltip cursor={{fill: '#f8fafc'}} />
                  <Legend />
                  <Bar dataKey="SPH" fill="var(--water-blue)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Delft3D" fill="var(--deep-navy)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Comparison;
