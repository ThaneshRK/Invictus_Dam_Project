import React, { useEffect, useState } from 'react';
import api from '../api';
import { useProject } from '../context/ProjectContext';
import StatusBadge from './ui/StatusBadge';
import EmptyState from './ui/EmptyState';
import SimulationProgress from './ui/SimulationProgress';
import { PlayCircle, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SimulationJobs: React.FC = () => {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  const [jobs, setJobs] = useState<any[]>([]);
  const [scenarioNames, setScenarioNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchJobs = async () => {
      if (!activeProject) {
        if (isMounted) setLoading(false);
        return;
      }
      try {
        const res = await api.get(`/projects/${activeProject.id}/simulations`);
        if (!isMounted) return;
        setJobs(res.data);
        
        // Fetch missing scenario names asynchronously
        const missingIds = res.data
          .map((j: any) => j.scenario_id)
          .filter((id: string) => id && !scenarioNames[id]);
          
        if (missingIds.length > 0) {
          const newNames = { ...scenarioNames };
          await Promise.all(
            missingIds.map(async (id: string) => {
              try {
                const scenRes = await api.get(`/scenarios/${id}`);
                newNames[id] = scenRes.data.name;
              } catch {
                newNames[id] = id.split('-')[0] + '...';
              }
            })
          );
          if (isMounted) setScenarioNames(newNames);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    
    fetchJobs();
    const interval = setInterval(fetchJobs, 2000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeProject]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>Simulation Jobs</h2>
        <button className="btn-primary" onClick={() => navigate('/scenarios')}>
          <PlayCircle size={16} /> Run New Simulation
        </button>
      </div>

      <div className="card">
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading simulation history...</div>
        ) : jobs.length === 0 ? (
          <EmptyState 
            title="No Simulations Found" 
            message="You haven't run any hydraulic simulations for this project yet." 
            action={<button className="btn-secondary">Configure Scenario</button>}
          />
        ) : (
          <table className="dense-table">
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Scenario</th>
                <th>Engine</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '13px' }}>{job.id.split('-')[0]}...</td>
                  <td>{scenarioNames[job.scenario_id] || job.scenario_id?.split('-')[0] + '...'}</td>
                  <td style={{ fontWeight: 600 }}>{job.engine}</td>
                  <td><StatusBadge status={job.status} /></td>
                  <td style={{ minWidth: '150px' }}>
                    <SimulationProgress 
                      progress={job.status === 'COMPLETED' ? 100 : (job.progress || 0)} 
                      status={job.status} 
                    />
                  </td>
                  <td>
                    <button 
                      className="btn-secondary" 
                      style={{ padding: '6px 12px', fontSize: '12px' }} 
                      disabled={job.status !== 'COMPLETED'}
                      onClick={() => navigate('/map')}
                    >
                      <Eye size={14} /> View Map
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default SimulationJobs;
