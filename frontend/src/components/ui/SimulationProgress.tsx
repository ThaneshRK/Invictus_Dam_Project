import React from 'react';

interface SimulationProgressProps {
  progress: number;
  status: string;
  eta?: string;
  elapsed?: string;
}

const SimulationProgress: React.FC<SimulationProgressProps> = ({ progress, status, eta, elapsed }) => {
  const isComplete = progress >= 100 || status === 'COMPLETED';
  const isFailed = status === 'FAILED';
  const isCancelled = status === 'CANCELLED';
  const isRunning = status === 'RUNNING' || status === 'PREPARING' || status === 'QUEUED';

  let color = 'var(--water-blue)';
  if (isComplete) color = 'var(--success-green)';
  else if (isFailed) color = 'var(--danger-red)';
  else if (isCancelled) color = '#8c8c8c';

  const rawPercent = isComplete ? 100 : (progress || 0);
  const displayPercent = isComplete ? 100 : Math.min(Math.max(Math.round(rawPercent), isRunning ? 1 : 0), 100);
  const barWidth = isComplete ? 100 : (isFailed || isCancelled) ? Math.min(rawPercent, 100) : Math.min(Math.max(rawPercent, isRunning ? 6 : 0), 100);

  return (
    <div style={{ width: '100%', marginBottom: '6px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px', color: 'var(--text-muted)', fontWeight: 500 }}>
        <span>Progress</span>
        <span style={{ color: color, fontWeight: 700 }}>{displayPercent}%</span>
      </div>
      <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
        <div style={{ 
          width: `${barWidth}%`, 
          height: '100%', 
          backgroundColor: color, 
          borderRadius: '4px',
          transition: 'width 0.4s ease-in-out'
        }} />
      </div>
      {(eta || elapsed) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginTop: '6px', color: 'var(--text-muted)' }}>
          {elapsed && <span>Elapsed: {elapsed}</span>}
          {eta && <span>ETA: {eta}</span>}
        </div>
      )}
    </div>
  );
};

export default SimulationProgress;
