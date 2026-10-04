import { Crosshair, Clock } from 'lucide-react';
import { LocationInspection } from '../../types';

interface LocationInspectorProps {
  inspection: LocationInspection | null;
  isLoading: boolean;
}

export const LocationInspector: React.FC<LocationInspectorProps> = ({
  inspection,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-dim)', fontSize: '0.8rem' }}>
        <div className="spinner" style={{ margin: '0 auto 8px' }} />
        Probing coordinate pixel values & historical baseline...
      </div>
    );
  }

  if (!inspection) {
    return (
      <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--color-text-dim)', fontSize: '0.8rem' }}>
        <Crosshair size={28} style={{ margin: '0 auto 10px', opacity: 0.5, color: 'var(--color-accent)' }} />
        <p style={{ fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '4px' }}>
          Interactive Location Inspector
        </p>
        <p style={{ fontSize: '0.74rem' }}>
          Click anywhere on the map or active AOI to probe spectral reflectance, historical baseline deviation, and surface interpretation.
        </p>
      </div>
    );
  }

  const { lat, lng, indicators, historical_comparison, anomaly_status, interpretation } = inspection;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Coordinates Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', paddingBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Crosshair size={14} color="var(--color-accent)" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 600 }}>
            {lat.toFixed(5)}°N, {lng.toFixed(5)}°E
          </span>
        </div>
        <span className={`status-badge badge-${anomaly_status.toLowerCase()}`}>
          {anomaly_status}
        </span>
      </div>

      {/* Spectral Indices Grid */}
      <div>
        <div className="form-label" style={{ marginBottom: '6px' }}>Probed Spectral Values</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
          {[
            { label: 'NDVI', val: indicators.ndvi },
            { label: 'NDMI', val: indicators.ndmi },
            { label: 'NDWI', val: indicators.ndwi },
            { label: 'NDBI', val: indicators.ndbi },
          ].map((item) => (
            <div key={item.label} style={{ background: '#09131e', padding: '8px 4px', textAlign: 'center', borderRadius: '4px', border: '1px solid var(--color-border-subtle)' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)' }}>{item.label}</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: item.val !== null ? '#fff' : 'var(--color-text-dim)' }}>
                {item.val !== null ? item.val.toFixed(3) : 'NaN'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Historical Baseline Comparison */}
      <div style={{ background: '#09131e', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', color: 'var(--color-accent)', fontWeight: 600, marginBottom: '6px' }}>
          <Clock size={13} />
          <span>Historical Baseline Context</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.74rem' }}>
          <div>
            <span style={{ color: 'var(--color-text-dim)' }}>Historical Mean:</span>{' '}
            <strong style={{ fontFamily: 'var(--font-mono)' }}>{historical_comparison.baseline_mean_ndvi.toFixed(3)}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--color-text-dim)' }}>Z-Score:</span>{' '}
            <strong style={{ fontFamily: 'var(--font-mono)' }}>{historical_comparison.z_score.toFixed(2)}σ</strong>
          </div>
        </div>
        <div style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)', marginTop: '4px' }}>
          Grounded on {historical_comparison.historical_samples_count} multi-season observations.
        </div>
      </div>

      {/* Biophysical Interpretation */}
      <div style={{ background: 'rgba(244, 162, 97, 0.05)', border: '1px solid rgba(244, 162, 97, 0.2)', padding: '10px 12px', borderRadius: 'var(--radius-sm)' }}>
        <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--color-accent)', marginBottom: '4px' }}>
          Scientific Interpretation
        </div>
        <p style={{ fontSize: '0.76rem', color: 'var(--color-text-main)', lineHeight: 1.4 }}>
          {interpretation}
        </p>
      </div>
    </div>
  );
};
