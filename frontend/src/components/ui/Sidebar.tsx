import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderGit2, 
  Database, 
  Layers, 
  Activity, 
  Map as MapIcon, 
  BarChart2, 
  ShieldAlert, 
  FileOutput, 
  Settings, 
  Radio,
  Cuboid
} from 'lucide-react';

const Sidebar: React.FC = () => {
  const navGroups = [
    {
      title: "OVERVIEW",
      items: [{ name: "Dashboard", path: "/", icon: <LayoutDashboard size={18} /> }]
    },
    {
      title: "MODELING",
      items: [
        { name: "Projects", path: "/projects", icon: <FolderGit2 size={18} /> },
        { name: "Datasets", path: "/data", icon: <Database size={18} /> },
        { name: "Scenarios", path: "/scenarios", icon: <Layers size={18} /> },
        { name: "Simulations", path: "/jobs", icon: <Activity size={18} /> },
        { name: "3D Asset Alignment", path: "/assets/align", icon: <Cuboid size={18} /> }
      ]
    },
    {
      title: "ANALYSIS",
      items: [
        { name: "Flood Map", path: "/map", icon: <MapIcon size={18} /> },
        { name: "3D Simulation", path: "/map3d", icon: <Cuboid size={18} /> },
        { name: "SPH vs Delft3D", path: "/comparison", icon: <BarChart2 size={18} /> },
        { name: "HADR Impact", path: "/hadr", icon: <ShieldAlert size={18} /> }
      ]
    },
    {
      title: "OUTPUTS",
      items: [
        { name: "Exports & Reports", path: "/exports", icon: <FileOutput size={18} /> },
        { name: "Satellite", path: "/satellite", icon: <Radio size={18} /> }
      ]
    },
    {
      title: "SYSTEM",
      items: [
        { name: "System Health", path: "/health", icon: <Settings size={18} /> }
      ]
    }
  ];

  return (
    <aside style={{
      width: '260px',
      backgroundColor: 'var(--deep-navy)',
      color: 'white',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      borderRight: '1px solid var(--border-color)',
      overflowY: 'auto'
    }}>
      <div style={{ padding: '24px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <h1 style={{ color: 'white', fontSize: '18px', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Activity color="var(--flood-cyan)" />
          Flood HADR
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px' }}>Simulation Command Center</p>
      </div>

      <nav style={{ padding: '20px 0', flex: 1 }}>
        {navGroups.map((group, idx) => (
          <div key={idx} style={{ marginBottom: '24px' }}>
            <h3 style={{ 
              fontSize: '11px', 
              color: 'var(--text-muted)', 
              padding: '0 20px',
              marginBottom: '8px',
              fontWeight: 600,
              letterSpacing: '0.5px'
            }}>
              {group.title}
            </h3>
            <ul style={{ listStyle: 'none' }}>
              {group.items.map(item => (
                <li key={item.path}>
                  <NavLink 
                    to={item.path}
                    style={({isActive}) => ({
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '10px 20px',
                      color: isActive ? 'white' : '#A0ABBA',
                      backgroundColor: isActive ? 'rgba(255,255,255,0.05)' : 'transparent',
                      borderLeft: isActive ? '3px solid var(--flood-cyan)' : '3px solid transparent',
                      textDecoration: 'none',
                      fontSize: '14px',
                      transition: 'all 0.2s ease'
                    })}
                  >
                    {item.icon}
                    {item.name}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
