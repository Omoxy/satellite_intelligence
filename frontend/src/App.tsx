import React, { useState, useEffect } from 'react';
import { api } from './api/client';
import { AOI, AnalysisRun, LocationInspection } from './types';
import { MapView } from './components/Map/MapView';
import { LayerControl } from './components/Map/LayerControl';
import { AnalysisPanel } from './components/Analysis/AnalysisPanel';
import { ResultsView } from './components/Analysis/ResultsView';
import { TemporalChart } from './components/Analysis/TemporalChart';
import { LocationInspector } from './components/Inspector/LocationInspector';
import { ExportModal } from './components/Export/ExportModal';
import {
  Satellite,
  BarChart2,
  Crosshair,
  Sliders,
  Download,
  AlertCircle,
  Info,
} from 'lucide-react';

export const App: React.FC = () => {
  // State management
  const [areas, setAreas] = useState<AOI[]>([]);
  const [selectedAoi, setSelectedAoi] = useState<AOI | null>(null);
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2024-03-15');
  const [selectedIndicators, setSelectedIndicators] = useState<string[]>([
    'ndvi',
    'ndmi',
    'ndwi',
    'ndbi',
  ]);

  const [activeTab, setActiveTab] = useState<'config' | 'results' | 'inspector'>('config');
  const [analysis, setAnalysis] = useState<AnalysisRun | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);

  const [activeLayer, setActiveLayer] = useState<string>('ndvi');
  const [overlayOpacity, setOverlayOpacity] = useState<number>(0.75);
  const [isOverlayVisible, setIsOverlayVisible] = useState<boolean>(true);

  const [locationInspection, setLocationInspection] = useState<LocationInspection | null>(null);
  const [isInspecting, setIsInspecting] = useState<boolean>(false);
  const [isExportOpen, setIsExportOpen] = useState<boolean>(false);
  const [systemError, setSystemError] = useState<string | null>(null);
  const [systemDataMode, setSystemDataMode] = useState<string>('demo');

  // Initialise: Load study areas and execute default analysis on Nairobi
  useEffect(() => {
    async function init() {
      try {
        api.getHealth().then((h) => {
          if (h?.data_mode) setSystemDataMode(h.data_mode);
        }).catch(() => {});

        const loadedAreas = await api.getAreas();
        setAreas(loadedAreas);

        if (loadedAreas.length > 0) {
          const defaultAoi = loadedAreas[0];
          setSelectedAoi(defaultAoi);

          // Auto-run baseline analysis on default study area
          executeAnalysis(defaultAoi.id, startDate, endDate, selectedIndicators);
        }
      } catch (err: any) {
        setSystemError('Failed to connect to satellite backend. Verify FastAPI service is online.');
      }
    }
    init();
  }, []);

  // Execute Analysis with genuine backend processing
  const executeAnalysis = async (
    aoiId: string,
    start: string,
    end: string,
    indicators: string[]
  ) => {
    setIsAnalyzing(true);
    setSystemError(null);

    try {
      const result = await api.runAnalysis(aoiId, start, end, indicators);
      setAnalysis(result);
      setActiveTab('results');

      // Sync active overlay
      if (!result.indicators[activeLayer]) {
        setActiveLayer(Object.keys(result.indicators)[0] || 'ndvi');
      }
    } catch (err: any) {
      setSystemError(err.message || 'Analysis run failed. Please check AOI validity.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCreateCustomAoi = async (name: string, geometry: any) => {
    try {
      const newArea = await api.createArea(name, geometry);
      setAreas((prev) => [newArea, ...prev]);
      setSelectedAoi(newArea);
      await executeAnalysis(newArea.id, startDate, endDate, selectedIndicators);
    } catch (err: any) {
      setSystemError(err.message || 'Failed to create and register custom AOI.');
      throw err;
    }
  };

  const handleToggleIndicator = (ind: string) => {
    if (selectedIndicators.includes(ind)) {
      if (selectedIndicators.length > 1) {
        setSelectedIndicators(selectedIndicators.filter((i) => i !== ind));
      }
    } else {
      setSelectedIndicators([...selectedIndicators, ind]);
    }
  };

  const handleMapClick = async (lat: number, lng: number) => {
    setIsInspecting(true);
    setActiveTab('inspector');
    try {
      const loc = await api.inspectLocation(lat, lng, analysis?.id);
      setLocationInspection(loc);
    } catch (err: any) {
      console.error('Probe failed:', err);
    } finally {
      setIsInspecting(false);
    }
  };

  // Determine active raster overlay URL
  let activeOverlayUrl: string | null = null;
  if (isOverlayVisible && analysis) {
    if (activeLayer === 'change' && analysis.change_detection[0]) {
      activeOverlayUrl = analysis.change_detection[0].change_overlay;
    } else if (analysis.indicators[activeLayer]) {
      activeOverlayUrl = analysis.indicators[activeLayer].raster_overlay;
    }
  }

  const isLive = Boolean(analysis ? analysis.data_source.toLowerCase().includes('live') : systemDataMode === 'live');

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand">
          <Satellite size={22} className="brand-icon" />
          <span className="brand-title">SATELLITE INTELLIGENCE EXPLORER</span>
          <span className="brand-subtitle">
            {isLive ? 'LIVE SENTINEL-2 EARTH OBSERVATION WORKSTATION' : 'SENTINEL-2-STYLE DEMONSTRATION WORKSTATION'}
          </span>
        </div>

        <div className="header-status">
          <div
            className={`status-badge ${isLive ? 'live' : 'demo'}`}
            title={isLive ? 'Operating with LIVE Sentinel-2 MSI Level-2A imagery via Copernicus Data Space Ecosystem' : 'Operating with deterministic physical synthesis and genuine Rasterio GeoTIFF processing'}
          >
            <span className={`status-dot ${isLive ? 'live' : ''}`} />
            <span>{isLive ? 'LIVE SENTINEL-2 (CDSE)' : 'DEMO MODE (SYNTHESIS)'}</span>
          </div>

          {analysis && (
            <button
              className="btn btn-outline"
              style={{ padding: '5px 10px', fontSize: '0.78rem' }}
              onClick={() => setIsExportOpen(true)}
            >
              <Download size={14} />
              <span>Export Report</span>
            </button>
          )}
        </div>
      </header>

      {/* Prominent Data Transparency Banner */}
      <div className={`demo-banner ${isLive ? 'live' : ''}`}>
        <span className={`demo-banner-tag ${isLive ? 'live' : ''}`}>
          {isLive ? 'LIVE SATELLITE DATA' : 'DEMONSTRATION DATA'}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Info size={14} style={{ flexShrink: 0 }} />
          <span>
            {isLive ? (
              <>
                Operational mode: Active analysis is derived directly from live Copernicus Sentinel-2 MSI Level-2A imagery acquired via Copernicus Data Space Ecosystem (CDSE). Surface reflectance bands (B02, B03, B04, B08, B11) are processed in real time through the Rasterio NumPy pipeline.
              </>
            ) : (
              <>
                This project uses deterministic synthetic reflectance data to demonstrate the Earth-observation processing pipeline.
                The remote-sensing calculations are real, but the demonstration raster values are not measurements from current satellite acquisitions.
              </>
            )}
          </span>
        </span>
      </div>

      {/* Main Workspace (Split View) */}
      <div className="workspace">
        {/* Left: Map Viewport */}
        <div className="map-viewport">
          <MapView
            selectedAoi={selectedAoi}
            activeOverlayUrl={activeOverlayUrl}
            overlayOpacity={overlayOpacity}
            locationInspection={locationInspection}
            onMapClick={handleMapClick}
          />

          {/* Floating Map Layer Controls */}
          {analysis && (
            <div className="map-floating-overlay">
              <LayerControl
                activeLayer={activeLayer}
                onLayerChange={setActiveLayer}
                opacity={overlayOpacity}
                onOpacityChange={setOverlayOpacity}
                isVisible={isOverlayVisible}
                onToggleVisibility={() => setIsOverlayVisible(!isOverlayVisible)}
                availableLayers={Object.keys(analysis.indicators)}
                hasChangeLayer={analysis.change_detection.length > 0}
              />
            </div>
          )}
        </div>

        {/* Right: Technical Analytics Sidebar */}
        <aside className="sidebar-panel">
          {/* Navigation Tabs */}
          <div className="panel-tabs">
            <button
              className={`panel-tab ${activeTab === 'config' ? 'active' : ''}`}
              onClick={() => setActiveTab('config')}
            >
              <Sliders size={14} />
              <span>AOI & Params</span>
            </button>
            <button
              className={`panel-tab ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => setActiveTab('results')}
              disabled={!analysis}
            >
              <BarChart2 size={14} />
              <span>Analysis Results</span>
            </button>
            <button
              className={`panel-tab ${activeTab === 'inspector' ? 'active' : ''}`}
              onClick={() => setActiveTab('inspector')}
            >
              <Crosshair size={14} />
              <span>Inspector</span>
            </button>
          </div>

          {/* Tab Content */}
          <div className="panel-content">
            {systemError && (
              <div
                style={{
                  padding: '10px 12px',
                  background: 'rgba(231, 111, 81, 0.15)',
                  border: '1px solid #e76f51',
                  borderRadius: 'var(--radius-sm)',
                  color: '#e76f51',
                  fontSize: '0.78rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '14px',
                }}
              >
                <AlertCircle size={16} />
                <span>{systemError}</span>
              </div>
            )}

            {activeTab === 'config' && (
              <AnalysisPanel
                areas={areas}
                selectedAoi={selectedAoi}
                onSelectAoi={setSelectedAoi}
                startDate={startDate}
                endDate={endDate}
                onStartDateChange={setStartDate}
                onEndDateChange={setEndDate}
                selectedIndicators={selectedIndicators}
                onToggleIndicator={handleToggleIndicator}
                onRunAnalysis={() => {
                  if (selectedAoi) {
                    executeAnalysis(selectedAoi.id, startDate, endDate, selectedIndicators);
                  }
                }}
                isAnalyzing={isAnalyzing}
                onCreateCustomAoi={handleCreateCustomAoi}
              />
            )}

            {activeTab === 'results' && analysis && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <ResultsView analysis={analysis} />
                <TemporalChart timeseries={analysis.timeseries} />
              </div>
            )}

            {activeTab === 'inspector' && (
              <LocationInspector
                inspection={locationInspection}
                isLoading={isInspecting}
              />
            )}
          </div>
        </aside>
      </div>

      {/* Export Report Modal */}
      {isExportOpen && analysis && (
        <ExportModal analysis={analysis} onClose={() => setIsExportOpen(false)} />
      )}
    </div>
  );
};
