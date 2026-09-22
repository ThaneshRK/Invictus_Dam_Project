import React from 'react';
import { Bell, User } from 'lucide-react';
import { useProject } from '../../context/ProjectContext';

const Header: React.FC = () => {
  const { activeProject } = useProject();
  
  return (
    <header style={{
      height: '60px',
      backgroundColor: 'var(--surface-color)',
      borderBottom: '1px solid var(--border-color)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-muted)' }}>
          Active Project: <strong style={{ color: 'var(--deep-navy)' }}>{activeProject ? activeProject.name : 'No Project Selected'}</strong>
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--success-green)' }}></div>
          <span>API Online</span>
        </div>
        
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
          <Bell size={20} />
        </button>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
          <User size={20} />
        </button>
      </div>
    </header>
  );
};

export default Header;
