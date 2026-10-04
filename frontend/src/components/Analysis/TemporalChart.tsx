import React, { useState } from 'react';
import { TimeseriesPoint } from '../../types';
import { Activity } from 'lucide-react';

interface TemporalChartProps {
  timeseries: Record<string, TimeseriesPoint[]>;
}

export const TemporalChart: React.FC<TemporalChartProps> = ({ timeseries }) => {
  const availableIndicators = Object.keys(timeseries);
  const [selectedInd, setSelectedInd] = useState<string>(availableIndicators[0] || 'ndvi');
  const [hoveredPoint, setHoveredPoint] = useState<TimeseriesPoint | null>(null);

  const points = timeseries[selectedInd] || [];

  if (points.length === 0) {
    return <div style={{ fontSize: '0.78rem', color: 'var(--color-text-dim)', textAlign: 'center', padding: '16px' }}>No temporal observations recorded.</div>;
  }

  // Dimensions for SVG rendering
  const width = 390;
  const height = 150;
  const padding = { top: 15, right: 15, bottom: 25, left: 35 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  // Domain scaling
  const allValues = points.flatMap((p) => [p.min, p.mean, p.max].filter((v): v is number => v !== null));
  const minVal = Math.min(...allValues, -0.2);
  const maxVal = Math.max(...allValues, 0.8);
  const valRange = maxVal - minVal || 1;

  const getY = (val: number | null) => {
    if (val === null) return chartH;
    const norm = (val - minVal) / valRange;
    return chartH - norm * chartH;
  };

  const getX = (index: number) => {
    if (points.length <= 1) return chartW / 2;
    return (index / (points.length - 1)) * chartW;
  };

  // Build SVG path for the mean line
  const linePoints = points.map((p, i) => `${getX(i)},${getY(p.mean)}`);
  const pathD = `M ${linePoints.join(' L ')}`;

  // Build area ribbon between min and max
  const topPoints = points.map((p, i) => `${getX(i)},${getY(p.max)}`);
  const bottomPoints = [...points].reverse().map((p, i) => `${getX(points.length - 1 - i)},${getY(p.min)}`);
  const areaD = `M ${topPoints.join(' L ')} L ${bottomPoints.join(' L ')} Z`;

  return (
    <div style={{ background: '#09131e', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-accent)' }}>
          <Activity size={14} />
          <span>Multi-Temporal Trajectory</span>
        </div>
        <select
          className="form-select"
          style={{ width: 'auto', padding: '2px 8px', fontSize: '0.72rem', textTransform: 'uppercase' }}
          value={selectedInd}
          onChange={(e) => setSelectedInd(e.target.value)}
        >
          {availableIndicators.map((ind) => (
            <option key={ind} value={ind}>
              {ind.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      <svg width={width} height={height} style={{ overflow: 'visible', width: '100%' }} viewBox={`0 0 ${width} ${height}`}>
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Horizontal gridlines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = chartH * ratio;
            const labelVal = maxVal - ratio * valRange;
            return (
              <g key={ratio}>
                <line x1={0} y1={y} x2={chartW} y2={y} stroke="#1f364d" strokeDasharray="3,3" />
                <text x={-6} y={y + 3} fill="#64748b" fontSize="8" textAnchor="end" fontFamily="var(--font-mono)">
                  {labelVal.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Uncertainty Envelope (Min-Max) */}
          <path d={areaD} fill="rgba(42, 157, 143, 0.12)" stroke="none" />

          {/* Mean Trajectory Line */}
          <path d={pathD} fill="none" stroke="#2A9D8F" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

          {/* Observation Dots */}
          {points.map((p, i) => {
            const cx = getX(i);
            const cy = getY(p.mean);
            const qualityColors = {
              good: '#2A9D8F',
              partial: '#E9C46A',
              poor: '#E76F51',
            };
            return (
              <circle
                key={p.date}
                cx={cx}
                cy={cy}
                r={hoveredPoint?.date === p.date ? 5 : 3.5}
                fill={qualityColors[p.data_quality]}
                stroke="#09131e"
                strokeWidth="1.5"
                style={{ cursor: 'pointer', transition: 'r 0.15s' }}
                onMouseEnter={() => setHoveredPoint(p)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
            );
          })}

          {/* X Axis Date Labels */}
          {points.length > 0 && (
            <>
              <text x={0} y={chartH + 16} fill="#64748b" fontSize="8" fontFamily="var(--font-mono)">
                {points[0].date}
              </text>
              <text x={chartW} y={chartH + 16} fill="#64748b" fontSize="8" textAnchor="end" fontFamily="var(--font-mono)">
                {points[points.length - 1].date}
              </text>
            </>
          )}
        </g>
      </svg>

      {/* Observation Tooltip */}
      {hoveredPoint && (
        <div style={{ marginTop: '8px', padding: '6px 8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '4px', fontSize: '0.72rem', display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)' }}>
          <span>{hoveredPoint.date}</span>
          <span>Mean: <strong>{hoveredPoint.mean?.toFixed(3)}</strong></span>
          <span>[{hoveredPoint.min?.toFixed(2)} - {hoveredPoint.max?.toFixed(2)}]</span>
          <span style={{ color: hoveredPoint.data_quality === 'good' ? '#2A9D8F' : '#E9C46A' }}>
            QA: {hoveredPoint.data_quality}
          </span>
        </div>
      )}
    </div>
  );
};
