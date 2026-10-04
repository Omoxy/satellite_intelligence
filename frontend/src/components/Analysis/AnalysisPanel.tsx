import React, { useState } from 'react';
import { Play, MapPin, Calendar, CheckSquare, Square, AlertCircle, PlusCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { AOI } from '../../types';

interface AnalysisPanelProps {
  areas: AOI[];
  selectedAoi: AOI | null;
  onSelectAoi: (aoi: AOI) => void;
  startDate: string;
  endDate: string;
  onStartDateChange: (d: string) => void;
  onEndDateChange: (d: string) => void;
  selectedIndicators: string[];
  onToggleIndicator: (ind: string) => void;
  onRunAnalysis: () => void;
  isAnalyzing: boolean;
  onCreateCustomAoi?: (name: string, geometry: any) => Promise<void>;
  isDrawingMode?: boolean;
  onStartDrawingAoi?: () => void;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  areas,
  selectedAoi,
  onSelectAoi,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  selectedIndicators,
  onToggleIndicator,
  onRunAnalysis,
  isAnalyzing,
  onCreateCustomAoi,
}) => {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showCustomAoiForm, setShowCustomAoiForm] = useState<boolean>(false);

  // Custom AOI form fields
  const [customName, setCustomName] = useState<string>('Custom Plot AOI');
  const [customWest, setCustomWest] = useState<string>('36.81');
  const [customSouth, setCustomSouth] = useState<string>('-1.28');
  const [customEast, setCustomEast] = useState<string>('36.84');
  const [customNorth, setCustomNorth] = useState<string>('-1.24');
  const [isSubmittingAoi, setIsSubmittingAoi] = useState<boolean>(false);

  const handleValidateAndRun = () => {
    setErrorMsg(null);
    if (!selectedAoi) {
      setErrorMsg('Please select an Area of Interest first.');
      return;
    }
    if (selectedIndicators.length === 0) {
      setErrorMsg('Select at least one spectral indicator to compute.');
      return;
    }
    if (startDate >= endDate) {
      setErrorMsg('Start date must precede the end date.');
      return;
    }
    onRunAnalysis();
  };

  const handleCreateCustom = async () => {
    setErrorMsg(null);
    const w = parseFloat(customWest);
    const s = parseFloat(customSouth);
    const e = parseFloat(customEast);
    const n = parseFloat(customNorth);

    if (isNaN(w) || isNaN(s) || isNaN(e) || isNaN(n)) {
      setErrorMsg('Bounding coordinates must be valid numbers in decimal degrees.');
      return;
    }
    if (w >= e || s >= n) {
      setErrorMsg('Invalid bounds: West must be < East and South must be < North.');
      return;
    }
    if (!customName.trim()) {
      setErrorMsg('Please provide a name for this custom AOI.');
      return;
    }

    const geometry = {
      type: 'Polygon',
      coordinates: [
        [
          [w, s],
          [e, s],
          [e, n],
          [w, n],
          [w, s],
        ],
      ],
    };

    if (onCreateCustomAoi) {
      try {
        setIsSubmittingAoi(true);
        await onCreateCustomAoi(customName.trim(), geometry);
        setShowCustomAoiForm(false);
      } catch (err: any) {
        setErrorMsg(err.message || 'Failed to create custom Area of Interest.');
      } finally {
        setIsSubmittingAoi(false);
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* AOI Selector */}
      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '5px', margin: 0 }}>
            <MapPin size={13} color="var(--color-accent)" />
            <span>Study Area (Kenya AOI)</span>
          </label>
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '2px 8px', fontSize: '0.68rem', gap: '4px' }}
            onClick={() => setShowCustomAoiForm(!showCustomAoiForm)}
            disabled={isAnalyzing}
          >
            <PlusCircle size={12} />
            <span>{showCustomAoiForm ? 'Cancel' : 'New AOI'}</span>
            {showCustomAoiForm ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>

        <select
          className="form-select"
          value={selectedAoi?.id || ''}
          onChange={(e) => {
            const chosen = areas.find((a) => a.id === e.target.value);
            if (chosen) onSelectAoi(chosen);
          }}
          disabled={isAnalyzing}
        >
          {areas.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.area_sq_km.toFixed(1)} km²) {a.is_predefined ? '★' : ''}
            </option>
          ))}
        </select>

        {selectedAoi && (
          <div style={{ marginTop: '8px', fontSize: '0.72rem', color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)' }}>
            <div>Centroid: {selectedAoi.centroid.lat.toFixed(4)}°N, {selectedAoi.centroid.lng.toFixed(4)}°E</div>
            <div>BBox: [{selectedAoi.bbox.west.toFixed(2)}, {selectedAoi.bbox.south.toFixed(2)}] to [{selectedAoi.bbox.east.toFixed(2)}, {selectedAoi.bbox.north.toFixed(2)}]</div>
          </div>
        )}
      </div>

      {/* Custom AOI Form */}
      {showCustomAoiForm && (
        <div style={{ padding: '10px', background: 'rgba(15, 29, 44, 0.7)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--color-accent)' }}>Define Custom Area of Interest</div>
          <div>
            <label style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)' }}>AOI Name</label>
            <input
              type="text"
              className="form-input"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="e.g. Nairobi Sub-basin"
              style={{ fontSize: '0.76rem', padding: '4px 8px' }}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            <div>
              <label style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)' }}>West (Lon)</label>
              <input
                type="text"
                className="form-input"
                value={customWest}
                onChange={(e) => setCustomWest(e.target.value)}
                style={{ fontSize: '0.74rem', padding: '4px 6px' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)' }}>South (Lat)</label>
              <input
                type="text"
                className="form-input"
                value={customSouth}
                onChange={(e) => setCustomSouth(e.target.value)}
                style={{ fontSize: '0.74rem', padding: '4px 6px' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)' }}>East (Lon)</label>
              <input
                type="text"
                className="form-input"
                value={customEast}
                onChange={(e) => setCustomEast(e.target.value)}
                style={{ fontSize: '0.74rem', padding: '4px 6px' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)' }}>North (Lat)</label>
              <input
                type="text"
                className="form-input"
                value={customNorth}
                onChange={(e) => setCustomNorth(e.target.value)}
                style={{ fontSize: '0.74rem', padding: '4px 6px' }}
              />
            </div>
          </div>
          <button
            type="button"
            className="btn btn-accent"
            style={{ padding: '6px 10px', fontSize: '0.76rem', marginTop: '4px' }}
            onClick={handleCreateCustom}
            disabled={isSubmittingAoi}
          >
            {isSubmittingAoi ? 'Registering & Validating...' : 'Register & Select AOI'}
          </button>
        </div>
      )}

      {/* Observation Temporal Range */}
      <div className="form-group">
        <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <Calendar size={13} color="var(--color-accent)" />
          <span>Observation Timeframe</span>
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-dim)' }}>Baseline (T1)</span>
            <input
              type="date"
              className="form-input"
              value={startDate}
              onChange={(e) => onStartDateChange(e.target.value)}
              disabled={isAnalyzing}
            />
          </div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-dim)' }}>Analysis (T2)</span>
            <input
              type="date"
              className="form-input"
              value={endDate}
              onChange={(e) => onEndDateChange(e.target.value)}
              disabled={isAnalyzing}
            />
          </div>
        </div>
      </div>

      {/* Indicators Checklist */}
      <div className="form-group">
        <label className="form-label">Spectral Indicators</label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {[
            { id: 'ndvi', label: 'NDVI (Vegetation)' },
            { id: 'ndmi', label: 'NDMI (Moisture)' },
            { id: 'ndwi', label: 'NDWI (Water)' },
            { id: 'ndbi', label: 'NDBI (Built-up)' },
          ].map((item) => {
            const isChecked = selectedIndicators.includes(item.id);
            return (
              <button
                key={item.id}
                type="button"
                className="btn btn-outline"
                style={{
                  justifyContent: 'flex-start',
                  padding: '7px 9px',
                  fontSize: '0.76rem',
                  borderColor: isChecked ? 'var(--color-accent)' : 'var(--color-border)',
                  background: isChecked ? 'rgba(244, 162, 97, 0.08)' : 'transparent',
                }}
                onClick={() => onToggleIndicator(item.id)}
                disabled={isAnalyzing}
              >
                {isChecked ? <CheckSquare size={14} color="var(--color-accent)" /> : <Square size={14} />}
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {errorMsg && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-danger)', fontSize: '0.78rem' }}>
          <AlertCircle size={14} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Run Analysis Button */}
      <button
        type="button"
        className="btn btn-accent"
        style={{ width: '100%', padding: '10px 14px', fontSize: '0.88rem' }}
        onClick={handleValidateAndRun}
        disabled={isAnalyzing}
      >
        <Play size={16} fill="currentColor" />
        <span>{isAnalyzing ? 'Processing Analysis...' : 'Execute EO Analysis'}</span>
      </button>

      {/* Real Processing Loading State */}
      {isAnalyzing && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px', background: 'rgba(27, 67, 50, 0.25)', border: '1px solid var(--color-primary-light)', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', color: '#d8f3dc' }}>
          <div className="spinner" style={{ width: '16px', height: '16px', border: '2px solid rgba(216, 243, 220, 0.2)', borderTopColor: '#d8f3dc', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          <span>Loading GeoTIFF raster, clipping to AOI with Rasterio, and computing spectral indices...</span>
        </div>
      )}
    </div>
  );
};
