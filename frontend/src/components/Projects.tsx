import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderGit2, Plus, Play } from 'lucide-react';
import { useProject } from '../context/ProjectContext';

const Projects: React.FC = () => {
  const navigate = useNavigate();
  const { projects, activeProject, setActiveProject, fetchProjects } = useProject();

  useEffect(() => {
    fetchProjects();
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2>Project Configurations</h2>
          <p style={{ color: 'var(--text-muted)' }}>Manage geographical study areas and hydrological scenarios.</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/projects/new')}>
          <Plus size={16} /> Create New Project
        </button>
      </div>

      <div className="card">
        <table className="dense-table">
          <thead>
            <tr>
              <th>Project Name</th>
              <th>Description</th>
              <th>CRS</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                  No projects found. Create one to get started.
                </td>
              </tr>
            ) : projects.map(p => (
              <tr key={p.id} style={{ backgroundColor: activeProject?.id === p.id ? '#f8fafc' : 'transparent' }}>
                <td style={{ fontWeight: 600, color: 'var(--deep-navy)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FolderGit2 size={16} color="var(--water-blue)" /> {p.name}
                  {activeProject?.id === p.id && <span style={{ fontSize: '10px', backgroundColor: 'var(--success-green)', color: 'white', padding: '2px 6px', borderRadius: '12px' }}>ACTIVE</span>}
                </td>
                <td>{p.description || "N/A"}</td>
                <td><span style={{ fontSize: '12px', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>{p.crs}</span></td>
                <td><span style={{ color: 'var(--success-green)' }}>Ready</span></td>
                <td>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={() => { setActiveProject(p); navigate('/scenarios'); }}>
                      <Play size={14} /> Select & Run
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
};

export default Projects;
