import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: string;
  trendUp?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, icon, trend, trendUp }) => {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
          {title}
        </span>
        {icon && <span style={{ color: 'var(--water-blue)' }}>{icon}</span>}
      </div>
      <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--deep-navy)' }}>
        {value}
      </div>
      {trend && (
        <div style={{ fontSize: '12px', color: trendUp ? 'var(--success-green)' : 'var(--emergency-red)', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
          {trendUp ? '↑' : '↓'} {trend}
        </div>
      )}
    </div>
  );
};

export default KPICard;
