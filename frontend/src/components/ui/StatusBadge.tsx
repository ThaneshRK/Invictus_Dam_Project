import React from 'react';

interface StatusBadgeProps {
  status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'QUEUED' | 'OPERATIONAL' | 'DEGRADED';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getStyles = () => {
    switch (status) {
      case 'COMPLETED':
      case 'OPERATIONAL':
        return { bg: '#E3FCEF', color: '#006644' };
      case 'RUNNING':
        return { bg: '#DEEBFF', color: '#0747A6' };
      case 'FAILED':
      case 'DEGRADED':
        return { bg: '#FFEBE6', color: '#BF2600' };
      case 'QUEUED':
        return { bg: '#EAEAEC', color: '#42526E' };
      default:
        return { bg: '#EAEAEC', color: '#42526E' };
    }
  };

  const { bg, color } = getStyles();

  return (
    <span style={{
      backgroundColor: bg,
      color: color,
      padding: '4px 8px',
      borderRadius: '4px',
      fontSize: '12px',
      fontWeight: 700,
      letterSpacing: '0.5px'
    }}>
      {status}
    </span>
  );
};

export default StatusBadge;
