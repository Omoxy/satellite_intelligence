import React from 'react';
import { jsPDF } from 'jspdf';
import { AnalysisRun } from '../../types';
import { Download, FileText, Code, X } from 'lucide-react';

interface ExportModalProps {
  analysis: AnalysisRun;
  onClose: () => void;
}

export const ExportModal: React.FC<ExportModalProps> = ({ analysis, onClose }) => {
  const generatePdf = () => {
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });

    let y = 18;

    // Header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.setTextColor(27, 67, 50); // Forest Green
    doc.text('SATELLITE INTELLIGENCE EXPLORER', 14, y);
    y += 6;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    doc.text('Earth Observation Analysis & Anomaly Assessment Dossier', 14, y);
    y += 10;

    // Horizontal Rule
    doc.setDrawColor(200, 200, 200);
    doc.line(14, y, 196, y);
    y += 8;

    // Metadata Section
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(13, 27, 42);
    doc.text('1. STUDY AREA & TEMPORAL CONTEXT', 14, y);
    y += 6;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(40, 40, 40);
    doc.text(`Study Area: ${analysis.aoi.name} (${analysis.aoi.area_sq_km.toFixed(2)} km²)`, 14, y);
    y += 5;
    doc.text(`Centroid: ${analysis.aoi.centroid.lat.toFixed(4)}°N, ${analysis.aoi.centroid.lng.toFixed(4)}°E`, 14, y);
    y += 5;
    doc.text(`Temporal Window: ${analysis.start_date} (T1) to ${analysis.end_date} (T2)`, 14, y);
    y += 5;
    doc.text(`Data Source: Sentinel-2 MSI Level-2A (${analysis.data_source})`, 14, y);
    y += 5;
    doc.text(`Cloud Cover Contamination: ${analysis.cloud_cover_pct}%`, 14, y);
    y += 9;

    // Zonal Statistics Table
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(13, 27, 42);
    doc.text('2. SPECTRAL INDICATOR SUMMARY', 14, y);
    y += 6;

    // Table Header
    doc.setFillColor(240, 245, 242);
    doc.rect(14, y, 182, 6, 'F');
    doc.setFontSize(8);
    doc.setTextColor(20, 20, 20);
    doc.text('INDICATOR', 18, y + 4.5);
    doc.text('MEAN', 60, y + 4.5);
    doc.text('MIN', 88, y + 4.5);
    doc.text('MAX', 116, y + 4.5);
    doc.text('STD DEV', 144, y + 4.5);
    doc.text('VALID PIXELS', 170, y + 4.5);
    y += 7;

    // Table Rows
    doc.setFont('helvetica', 'normal');
    Object.entries(analysis.indicators).forEach(([ind, s]) => {
      doc.text(ind.toUpperCase(), 18, y + 4);
      doc.text(s.mean !== null ? s.mean.toFixed(3) : 'N/A', 60, y + 4);
      doc.text(s.min !== null ? s.min.toFixed(3) : 'N/A', 88, y + 4);
      doc.text(s.max !== null ? s.max.toFixed(3) : 'N/A', 116, y + 4);
      doc.text(s.std !== null ? s.std.toFixed(3) : 'N/A', 144, y + 4);
      doc.text(s.pixel_count !== null ? s.pixel_count.toLocaleString() : 'N/A', 170, y + 4);
      y += 6;
    });
    y += 6;

    // Change Detection & Anomaly
    if (analysis.change_detection.length > 0) {
      const chg = analysis.change_detection[0];
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.setTextColor(13, 27, 42);
      doc.text('3. MULTI-TEMPORAL CHANGE & ANOMALY ASSESSMENT', 14, y);
      y += 6;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(40, 40, 40);
      doc.text(`Change Indicator: ${chg.indicator.toUpperCase()} (T1 Mean: ${chg.period1_mean?.toFixed(3)} -> T2 Mean: ${chg.period2_mean?.toFixed(3)})`, 14, y);
      y += 5;
      doc.text(`Net Absolute Shift: ${chg.absolute_change !== null ? (chg.absolute_change > 0 ? '+' : '') + chg.absolute_change.toFixed(3) : 'N/A'}`, 14, y);
      y += 5;
      doc.text(`Class Distribution: ${chg.increase_pct}% Gain | ${chg.stable_pct}% Stable | ${chg.decrease_pct}% Reduction`, 14, y);
      y += 7;
    }

    if (analysis.anomalies.length > 0) {
      const anom = analysis.anomalies[0];
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.text(`Anomaly Classification: ${anom.classification.toUpperCase()} (Deviation: ${anom.deviation?.toFixed(2)} sigma)`, 14, y);
      y += 5;
      doc.setFont('helvetica', 'normal');
      doc.text(`Scientific Assessment: ${anom.description}`, 14, y, { maxWidth: 180 });
      y += 14;
    }

    // Scientific Methodology & Limitations
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(13, 27, 42);
    doc.text('4. METHODOLOGY & SCIENTIFIC DISCLOSURES', 14, y);
    y += 6;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(70, 70, 70);
    const disclosures = [
      'NDVI = (NIR - Red) / (NIR + Red) per Rouse et al. (1974).',
      'NDMI = (NIR - SWIR) / (NIR + SWIR) per Gao (1996) canopy liquid water index.',
      'NDWI = (Green - NIR) / (Green + NIR) per McFeeters (1996) open water mapping.',
      'NDBI = (SWIR - NIR) / (SWIR + NIR) per Zha et al. (2003) built-up surface proxy.',
      analysis.data_source?.toLowerCase().includes('live')
        ? `Data Provenance: LIVE Sentinel-2 MSI Level-2A via Copernicus Data Space Ecosystem (${analysis.data_source}).`
        : `Demonstration Mode Disclosure: Data generated via deterministic physically-constrained synthesis (${analysis.data_source}).`,
      'Cautionary Remote Sensing Principle: Satellite spectral indices represent radiative surface proxies; they do not establish unverified agronomic ground truth.',
    ];
    disclosures.forEach((d) => {
      doc.text(`* ${d}`, 16, y, { maxWidth: 178 });
      y += 5;
    });

    // Save PDF
    const filename = `satellite_report_${analysis.aoi.name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_${analysis.end_date}.pdf`;
    doc.save(filename);
  };

  const downloadJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(analysis, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute(
      'download',
      `satellite_analysis_${analysis.aoi.name.toLowerCase()}_${analysis.id.slice(0, 8)}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000,
    }}>
      <div style={{
        background: 'var(--color-bg-sidebar)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        width: '520px',
        maxWidth: '90vw',
        padding: '24px',
        boxShadow: 'var(--shadow-lg)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-accent)', fontWeight: 700 }}>
            <FileText size={18} />
            <span style={{ fontFamily: 'var(--font-serif)', fontSize: '1.1rem' }}>Export Analysis Dossier</span>
          </div>
          <button className="btn btn-outline" style={{ padding: '4px' }} onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
          Export the complete Earth Observation assessment for <strong>{analysis.aoi.name}</strong> ({analysis.start_date} to {analysis.end_date}) formatted for stakeholder briefing, GIS records, or automated ingest.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <button
            type="button"
            className="btn btn-primary"
            style={{ padding: '12px', flexDirection: 'column', gap: '6px' }}
            onClick={generatePdf}
          >
            <Download size={18} />
            <span style={{ fontWeight: 600 }}>Download PDF Dossier</span>
            <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>Publication-grade report</span>
          </button>

          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '12px', flexDirection: 'column', gap: '6px' }}
            onClick={downloadJson}
          >
            <Code size={18} />
            <span style={{ fontWeight: 600 }}>Export Raw JSON</span>
            <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>Zonal stats & metadata</span>
          </button>
        </div>
      </div>
    </div>
  );
};
