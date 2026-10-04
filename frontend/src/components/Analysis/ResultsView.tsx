import React, { useState } from 'react';
import { AnalysisRun } from '../../types';
import { TrendingUp, AlertTriangle, Layers, Info, Eye, EyeOff } from 'lucide-react';

interface ResultsViewProps {
  analysis: AnalysisRun;
  activeLayer?: string;
  onLayerChange?: (layer: string) => void;
  overlayOpacity?: number;
  onOpacityChange?: (opacity: number) => void;
  isOverlayVisible?: boolean;
  onToggleVisibility?: () => void;
}

export const ResultsView: React.FC<ResultsViewProps> = ({
  analysis,
  activeLayer,
  onLayerChange,
  overlayOpacity,
  isOverlayVisible = true,
  onToggleVisibility,
}) => {
  const [selectedIndicatorTab, setSelectedIndicatorTab] = useState<string>(
    activeLayer || Object.keys(analysis.indicators)[0] || 'ndvi'
  );

  const currentStats = analysis.indicators[selectedIndicatorTab];
  const primaryAnomaly = analysis.anomalies[0];
  const primaryChange = analysis.change_detection[0];

  const handleSelectTab = (ind: string) => {
    setSelectedIndicatorTab(ind);
    if (onLayerChange) {
      onLayerChange(ind);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Indicator Tabs with Layer Visibility status */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Indicators
          </span>
          {onToggleVisibility && overlayOpacity !== undefined && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.72rem', color: 'var(--color-text-dim)' }}>
              <span>Map Layer: {Math.round(overlayOpacity * 100)}%</span>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '2px 5px', fontSize: '0.68rem', lineHeight: 1 }}
                onClick={onToggleVisibility}
                title={isOverlayVisible ? 'Hide raster overlay on map' : 'Show raster overlay on map'}
              >
                {isOverlayVisible ? <Eye size={12} color="var(--color-accent)" /> : <EyeOff size={12} color="var(--color-danger)" />}
              </button>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--color-border)', paddingBottom: '6px' }}>
          {Object.keys(analysis.indicators).map((ind) => (
            <button
              key={ind}
              className={`btn ${selectedIndicatorTab === ind ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '4px 10px', fontSize: '0.75rem', textTransform: 'uppercase' }}
              onClick={() => handleSelectTab(ind)}
            >
              {ind}
            </button>
          ))}
          {analysis.change_detection.length > 0 && (
            <button
              className={`btn ${selectedIndicatorTab === 'change' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '4px 10px', fontSize: '0.75rem', textTransform: 'uppercase' }}
              onClick={() => handleSelectTab('change')}
            >
              Δ Change
            </button>
          )}
        </div>
      </div>

      {/* Zonal Statistics Grid */}
      {currentStats && (
        <div>
          <div className="form-label" style={{ marginBottom: '8px' }}>
            Zonal Statistics ({selectedIndicatorTab.toUpperCase()})
          </div>
          <div className="metric-grid">
            <div className="metric-card">
              <div className="metric-label">Spatial Mean</div>
              <div className="metric-value">
                {currentStats.mean !== null ? currentStats.mean.toFixed(3) : 'N/A'}
              </div>
              <div className="metric-sub">Area-weighted average</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Std Deviation</div>
              <div className="metric-value">
                {currentStats.std !== null ? currentStats.std.toFixed(3) : 'N/A'}
              </div>
              <div className="metric-sub">Spatial variance</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Minimum</div>
              <div className="metric-value">
                {currentStats.min !== null ? currentStats.min.toFixed(3) : 'N/A'}
              </div>
              <div className="metric-sub">Lowest valid pixel</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Maximum</div>
              <div className="metric-value">
                {currentStats.max !== null ? currentStats.max.toFixed(3) : 'N/A'}
              </div>
              <div className="metric-sub">Peak reflectance</div>
            </div>
          </div>

          {/* Histogram Visualisation */}
          {currentStats.histogram && currentStats.histogram.counts.length > 0 && (
            <div style={{ background: '#09131e', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)', marginTop: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--color-text-dim)', marginBottom: '6px' }}>
                <span>Pixel Distribution Histogram</span>
                <span>{currentStats.pixel_count?.toLocaleString()} pixels</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end', height: '48px', gap: '2px' }}>
                {(() => {
                  const maxCount = Math.max(...currentStats.histogram.counts, 1);
                  return currentStats.histogram.counts.map((count, i) => {
                    const heightPct = Math.round((count / maxCount) * 100);
                    return (
                      <div
                        key={i}
                        title={`Bin ${i + 1}: ${count} pixels`}
                        style={{
                          flex: 1,
                          height: `${Math.max(heightPct, 4)}%`,
                          background: 'var(--color-primary-light)',
                          borderRadius: '1px',
                          transition: 'height 0.2s',
                        }}
                      />
                    );
                  });
                })()}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Multi-Temporal Change Detection */}
      {primaryChange && (
        <div style={{ background: '#09131e', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-accent)', marginBottom: '8px' }}>
            <TrendingUp size={14} />
            <span>Multi-Temporal Change (Δ {primaryChange.indicator.toUpperCase()})</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', fontSize: '0.75rem', textAlign: 'center' }}>
            <div style={{ padding: '6px', background: 'rgba(33, 102, 172, 0.1)', border: '1px solid #2166ac', borderRadius: '4px' }}>
              <div style={{ color: '#67a9cf', fontWeight: 700 }}>{primaryChange.increase_pct}%</div>
              <div style={{ color: 'var(--color-text-dim)', fontSize: '0.68rem' }}>Gain</div>
            </div>
            <div style={{ padding: '6px', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--color-border)', borderRadius: '4px' }}>
              <div style={{ color: '#fff', fontWeight: 700 }}>{primaryChange.stable_pct}%</div>
              <div style={{ color: 'var(--color-text-dim)', fontSize: '0.68rem' }}>Stable</div>
            </div>
            <div style={{ padding: '6px', background: 'rgba(178, 24, 43, 0.1)', border: '1px solid #b2182b', borderRadius: '4px' }}>
              <div style={{ color: '#ef8a62', fontWeight: 700 }}>{primaryChange.decrease_pct}%</div>
              <div style={{ color: 'var(--color-text-dim)', fontSize: '0.68rem' }}>Reduction</div>
            </div>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--color-text-muted)', marginTop: '8px' }}>
            Net change: <strong>{primaryChange.absolute_change !== null ? (primaryChange.absolute_change > 0 ? '+' : '') + primaryChange.absolute_change.toFixed(3) : 'N/A'}</strong> (T1: {primaryChange.period1_mean?.toFixed(3)} → T2: {primaryChange.period2_mean?.toFixed(3)})
          </div>
        </div>
      )}

      {/* Historical Anomaly Assessment */}
      {primaryAnomaly && (
        <div style={{ background: '#09131e', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-accent)' }}>
              <AlertTriangle size={14} />
              <span>Statistical Anomaly Status</span>
            </div>
            <span className={`status-badge badge-${primaryAnomaly.classification}`}>
              {primaryAnomaly.classification.toUpperCase()}
            </span>
          </div>
          <p style={{ fontSize: '0.76rem', color: 'var(--color-text-main)', lineHeight: 1.4 }}>
            {primaryAnomaly.description}
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '0.7rem', color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)' }}>
            <span>Baseline: {primaryAnomaly.baseline_value?.toFixed(3)}</span>
            <span>Current: {primaryAnomaly.current_value?.toFixed(3)}</span>
            <span>Deviation: {primaryAnomaly.deviation?.toFixed(2)}σ</span>
          </div>
        </div>
      )}

      {/* Rule-Based Land-Cover Distribution */}
      {analysis.classification && analysis.classification.length > 0 && (
        <div style={{ background: '#09131e', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-accent)', marginBottom: '8px' }}>
            <Layers size={14} />
            <span>Rule-Based Land Cover Distribution</span>
          </div>
          <div style={{ display: 'flex', height: '14px', borderRadius: '3px', overflow: 'hidden', marginBottom: '8px' }}>
            {analysis.classification.map((c) => {
              const colors: Record<string, string> = {
                Vegetation: '#1B4332',
                Cropland: '#E9C46A',
                'Built-up': '#E76F51',
                'Bare land': '#D4A373',
                Water: '#457B9D',
              };
              return (
                <div
                  key={c.class_name}
                  title={`${c.class_name}: ${c.area_pct}%`}
                  style={{
                    width: `${c.area_pct || 0}%`,
                    backgroundColor: colors[c.class_name] || '#6c757d',
                  }}
                />
              );
            })}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px', fontSize: '0.72rem' }}>
            {analysis.classification.map((c) => (
              <div key={c.class_name} style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-muted)' }}>
                <span>{c.class_name}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#fff' }}>{c.area_pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Quality & Limitations Notice */}
      {(() => {
        const isLive = Boolean(analysis.data_source && analysis.data_source.toLowerCase().includes('live'));
        return (
          <div style={{
            background: isLive ? 'rgba(74, 222, 128, 0.05)' : 'rgba(216, 243, 220, 0.05)',
            border: `1px solid ${isLive ? 'rgba(74, 222, 128, 0.25)' : 'rgba(216, 243, 220, 0.15)'}`,
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', color: isLive ? '#4ade80' : 'var(--color-surface-pale)', fontWeight: 600 }}>
                <Info size={13} />
                <span>Data Provenance & Scientific Quality</span>
              </div>
              <span style={{
                fontSize: '0.65rem',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                backgroundColor: isLive ? 'rgba(74, 222, 128, 0.15)' : 'rgba(244, 162, 97, 0.15)',
                color: isLive ? '#4ade80' : 'var(--color-accent)',
                border: `1px solid ${isLive ? 'rgba(74, 222, 128, 0.3)' : 'rgba(244, 162, 97, 0.3)'}`
              }}>
                {isLive ? 'LIVE SENTINEL-2 / CDSE' : 'DEMO MODE (SYNTHESIS)'}
              </span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-dim)', lineHeight: 1.4 }}>
              {isLive ? (
                <>
                  <strong>Source:</strong> LIVE Sentinel-2 MSI Level-2A Surface Reflectance (Copernicus Data Space Ecosystem / Sentinel Hub API).
                  {' '}Data source: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-surface-pale)' }}>{analysis.data_source}</span>.
                  {' '}Cloud cover: {analysis.cloud_cover_pct !== null ? `${analysis.cloud_cover_pct}%` : 'N/A'} (masked via QA band). Remotely sensed indices represent environmental proxies; ground validation is mandatory for agronomic action.
                </>
              ) : (
                <>
                  <strong>Source:</strong> Sentinel-2 MSI Level-2A Surface Reflectance (Demonstration Synthesis Mode).
                  {' '}Data source: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-dim)' }}>{analysis.data_source}</span>.
                  {' '}Cloud cover: {analysis.cloud_cover_pct !== null ? `${analysis.cloud_cover_pct}%` : '0%'} (masked via QA band). Remotely sensed indices represent environmental proxies; ground validation is mandatory for agronomic action.
                </>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
};
