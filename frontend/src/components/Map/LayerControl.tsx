import React, { useState } from 'react';
import { Layers, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react';

interface LayerControlProps {
  activeLayer: string;
  onLayerChange: (layer: string) => void;
  opacity: number;
  onOpacityChange: (opacity: number) => void;
  isVisible: boolean;
  onToggleVisibility: () => void;
  availableLayers: string[];
  hasChangeLayer: boolean;
}

const LEGEND_CONFIGS: Record<string, { label: string; min: string; max: string; gradient: string }> = {
  ndvi: {
    label: 'NDVI (Vegetation Index)',
    min: '-0.2 (Bare/Water)',
    max: '+0.9 (Dense Canopy)',
    gradient: 'linear-gradient(to right, #a50026, #f46d43, #fee08b, #d9ef8b, #66bd63, #006837)',
  },
  ndmi: {
    label: 'NDMI (Moisture Index)',
    min: '-0.4 (Dry Stress)',
    max: '+0.6 (High Moisture)',
    gradient: 'linear-gradient(to right, #8c510a, #dfc27d, #f6e8c3, #c7eae5, #5ab4ac, #003c30)',
  },
  ndwi: {
    label: 'NDWI (Water Index)',
    min: '-0.5 (Terrestrial)',
    max: '+0.5 (Open Water)',
    gradient: 'linear-gradient(to right, #8c510a, #d8b365, #f6e8c3, #baefbc, #4487b0, #08306b)',
  },
  ndbi: {
    label: 'NDBI (Built-up Index)',
    min: '-0.3 (Vegetated)',
    max: '+0.4 (Built-up / Urban)',
    gradient: 'linear-gradient(to right, #006837, #a6d96a, #fee08b, #f46d43, #800000)',
  },
  change: {
    label: 'Multi-Temporal Change (Δ NDVI)',
    min: '-0.3 (Reduction)',
    max: '+0.3 (Vigour Gain)',
    gradient: 'linear-gradient(to right, #b2182b, #ef8a62, #fddbc7, #ffffff, #d1e5f0, #67a9cf, #2166ac)',
  },
};

export const LayerControl: React.FC<LayerControlProps> = ({
  activeLayer,
  onLayerChange,
  opacity,
  onOpacityChange,
  isVisible,
  onToggleVisibility,
  availableLayers,
  hasChangeLayer,
}) => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
  const currentLegend = LEGEND_CONFIGS[activeLayer];

  if (isCollapsed) {
    return (
      <div
        className="map-status-strip"
        onClick={() => setIsCollapsed(false)}
        title="Click to expand raster window settings"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={13} color="var(--color-accent)" />
          <span className="status-strip-title">RASTER: {activeLayer.toUpperCase()}</span>
          <span className="status-strip-meta">{isVisible ? `${Math.round(opacity * 100)}%` : 'OFF'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '2px 5px', fontSize: '0.68rem', lineHeight: 1 }}
            onClick={(e) => {
              e.stopPropagation();
              onToggleVisibility();
            }}
            title={isVisible ? 'Hide raster overlay' : 'Show raster overlay'}
          >
            {isVisible ? <Eye size={11} /> : <EyeOff size={11} color="var(--color-danger)" />}
          </button>
          <ChevronUp size={13} color="var(--color-accent)" />
        </div>
      </div>
    );
  }

  return (
    <div className="map-card" style={{ width: '260px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--color-accent)', fontSize: '0.78rem' }}>
          <Layers size={13} />
          <span>Active Raster Window</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '2px 6px', fontSize: '0.7rem' }}
            onClick={onToggleVisibility}
            title={isVisible ? 'Hide raster layer' : 'Show raster layer'}
          >
            {isVisible ? <Eye size={12} /> : <EyeOff size={12} color="var(--color-danger)" />}
          </button>
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '2px 6px', fontSize: '0.7rem' }}
            onClick={() => setIsCollapsed(true)}
            title="Collapse to compact status strip"
          >
            <ChevronDown size={12} />
          </button>
        </div>
      </div>

      <div className="form-group" style={{ marginBottom: '8px' }}>
        <select
          className="form-select"
          style={{ padding: '4px 8px', fontSize: '0.76rem' }}
          value={activeLayer}
          onChange={(e) => onLayerChange(e.target.value)}
        >
          {availableLayers.map((ind) => (
            <option key={ind} value={ind}>
              {ind.toUpperCase()} Layer
            </option>
          ))}
          {hasChangeLayer && <option value="change">Change Detection (Δ NDVI)</option>}
        </select>
      </div>

      {isVisible && (
        <div style={{ marginTop: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
            <span>Opacity</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>{Math.round(opacity * 100)}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={opacity}
            onChange={(e) => onOpacityChange(parseFloat(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--color-accent)', cursor: 'pointer' }}
          />
        </div>
      )}

      {isVisible && currentLegend && (
        <div className="legend-container">
          <div className="legend-bar" style={{ background: currentLegend.gradient }} />
          <div className="legend-labels">
            <span>{currentLegend.min}</span>
            <span>{currentLegend.max}</span>
          </div>
        </div>
      )}

      {/* Non-intrusive technical raster metadata note */}
      <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--color-border-subtle)', display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)' }}>
        <span>CRS: EPSG:4326</span>
        <span>Res: 10m Ground</span>
      </div>
    </div>
  );
};
