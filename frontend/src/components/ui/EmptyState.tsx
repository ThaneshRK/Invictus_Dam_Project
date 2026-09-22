import React from 'react';
import { AlertCircle } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  message: string;
  action?: React.ReactNode;
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, message, action }) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 20px',
      backgroundColor: 'var(--surface-color)',
      borderRadius: '8px',
      border: '1px dashed var(--border-color)',
      textAlign: 'center'
    }}>
      <AlertCircle size={48} color="var(--text-muted)" style={{ opacity: 0.5, marginBottom: '16px' }} />
      <h3 style={{ fontSize: '18px', color: 'var(--deep-navy)', marginBottom: '8px' }}>{title}</h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '14px', maxWidth: '400px', marginBottom: action ? '24px' : '0' }}>
        {message}
      </p>
      {action}
    </div>
  );
};

export default EmptyState;
