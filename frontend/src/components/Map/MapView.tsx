import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { AOI, LocationInspection } from '../../types';

interface MapViewProps {
  selectedAoi: AOI | null;
  activeOverlayUrl: string | null;
  overlayOpacity: number;
  locationInspection: LocationInspection | null;
  onMapClick: (lat: number, lng: number) => void;
  isDrawingMode?: boolean;
  drawnPoints?: [number, number][];
  onAddDrawnPoint?: (lat: number, lng: number) => void;
  onFinishDrawing?: () => void;
  onCancelDrawing?: () => void;
}

export const MapView: React.FC<MapViewProps> = ({
  selectedAoi,
  activeOverlayUrl,
  overlayOpacity,
  locationInspection,
  onMapClick,
  isDrawingMode = false,
  drawnPoints = [],
  onAddDrawnPoint,
  onFinishDrawing,
  onCancelDrawing,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const aoiLayerRef = useRef<L.GeoJSON | null>(null);
  const imageOverlayRef = useRef<L.ImageOverlay | null>(null);
  const probeMarkerRef = useRef<L.Marker | null>(null);
  const drawLayerGroupRef = useRef<L.LayerGroup | null>(null);

  // Initialise Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Default center on Kenya
    const map = L.map(mapContainerRef.current, {
      center: [-0.0236, 37.9062],
      zoom: 7,
      minZoom: 3,
      maxZoom: 18,
      zoomControl: true,
    });

    const cartoApiKey = import.meta.env.VITE_CARTO_API_KEY?.trim();
    const cartoDark = cartoApiKey
      ? L.tileLayer(
          `https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${encodeURIComponent(cartoApiKey)}`,
          {
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attribution/">CARTO</a>',
            maxZoom: 20,
          }
        )
      : null;
    const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    });

    const baseLayers: Record<string, L.Layer> = {
      'OpenStreetMap Standard': osm,
    };
    if (cartoDark) {
      baseLayers['CartoDB Dark Matter'] = cartoDark;
    }
    L.control.layers(baseLayers, {}, { position: 'topright' }).addTo(map);

    if (cartoDark) {
      cartoDark.addTo(map);
    } else {
      osm.addTo(map);
    }

    drawLayerGroupRef.current = L.layerGroup().addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Handle map clicks (either location probe or AOI vertex placement)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const handleClick = (e: L.LeafletMouseEvent) => {
      if (isDrawingMode && onAddDrawnPoint) {
        onAddDrawnPoint(e.latlng.lat, e.latlng.lng);
      } else {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    };

    map.off('click');
    map.on('click', handleClick);

    if (mapContainerRef.current) {
      mapContainerRef.current.style.cursor = isDrawingMode ? 'crosshair' : '';
    }

    return () => {
      map.off('click', handleClick);
    };
  }, [isDrawingMode, onAddDrawnPoint, onMapClick]);

  // Sync AOI Geometry & Bounds (clean GIS vector outline, solid crisp stroke without dashed box appearance)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (aoiLayerRef.current) {
      map.removeLayer(aoiLayerRef.current);
      aoiLayerRef.current = null;
    }

    if (selectedAoi && selectedAoi.geometry) {
      const geoLayer = L.geoJSON(selectedAoi.geometry, {
        style: {
          color: '#F4A261', // Gold accent
          weight: 2,
          opacity: 0.95,
          fillColor: '#1B4332',
          fillOpacity: 0.12,
        },
        onEachFeature: (_feature, layer) => {
          layer.bindTooltip(
            `<div style="font-family: var(--font-mono); font-size: 0.72rem; padding: 2px 4px;">
              <strong>${selectedAoi.name}</strong> (${selectedAoi.area_sq_km.toFixed(1)} km²)
            </div>`,
            { sticky: true, className: 'aoi-map-tooltip' }
          );
        },
      }).addTo(map);

      aoiLayerRef.current = geoLayer;
      const bounds = geoLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
      }
    }
  }, [selectedAoi]);

  // Sync Interactive Drawn Points
  useEffect(() => {
    const drawGroup = drawLayerGroupRef.current;
    if (!drawGroup) return;

    drawGroup.clearLayers();

    if (!isDrawingMode || drawnPoints.length === 0) return;

    // Render vertex circles
    drawnPoints.forEach(([lat, lng], idx) => {
      const marker = L.circleMarker([lat, lng], {
        radius: 5,
        color: '#F4A261',
        weight: 2,
        fillColor: '#0D1B2A',
        fillOpacity: 0.9,
      });
      drawGroup.addLayer(marker);

      if (idx === 0) {
        marker.bindTooltip('Start Point (click to close)', { permanent: true, direction: 'top' });
        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          if (drawnPoints.length >= 3 && onFinishDrawing) {
            onFinishDrawing();
          }
        });
      }
    });

    // Render connection line or polygon preview
    if (drawnPoints.length >= 2) {
      const latlngs = drawnPoints.map(([lat, lng]) => [lat, lng] as [number, number]);
      if (drawnPoints.length >= 3) {
        const poly = L.polygon(latlngs, {
          color: '#F4A261',
          weight: 2,
          opacity: 0.9,
          fillColor: '#2D6A4F',
          fillOpacity: 0.15,
          dashArray: '3, 5',
        });
        drawGroup.addLayer(poly);
      } else {
        const line = L.polyline(latlngs, {
          color: '#F4A261',
          weight: 2,
          opacity: 0.9,
          dashArray: '3, 5',
        });
        drawGroup.addLayer(line);
      }
    }
  }, [isDrawingMode, drawnPoints, onFinishDrawing]);

  // Sync Raster Image Overlay
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (imageOverlayRef.current) {
      map.removeLayer(imageOverlayRef.current);
      imageOverlayRef.current = null;
    }

    if (activeOverlayUrl && selectedAoi) {
      const { south, west, north, east } = selectedAoi.bbox;
      const bounds = L.latLngBounds([south, west], [north, east]);

      const overlay = L.imageOverlay(activeOverlayUrl, bounds, {
        opacity: overlayOpacity,
        interactive: false,
      }).addTo(map);

      imageOverlayRef.current = overlay;
    }
  }, [activeOverlayUrl, selectedAoi]);

  // Sync Image Overlay Opacity
  useEffect(() => {
    if (imageOverlayRef.current) {
      imageOverlayRef.current.setOpacity(overlayOpacity);
    }
  }, [overlayOpacity]);

  // Sync Probed Marker Pin
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (probeMarkerRef.current) {
      map.removeLayer(probeMarkerRef.current);
      probeMarkerRef.current = null;
    }

    if (locationInspection && !isDrawingMode) {
      const { lat, lng, indicators, anomaly_status } = locationInspection;

      const customIcon = L.divIcon({
        className: 'probe-pin',
        html: `<div style="
          width: 14px;
          height: 14px;
          background: #F4A261;
          border: 2px solid #0D1B2A;
          border-radius: 50%;
          box-shadow: 0 0 10px rgba(244, 162, 97, 0.9);
        "></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
      marker
        .bindPopup(
          `<div style="font-family: var(--font-mono); font-size: 0.75rem; color: #0D1B2A;">
            <strong>Location Probe</strong><br/>
            Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}<br/>
            NDVI: ${indicators.ndvi !== null ? indicators.ndvi.toFixed(3) : 'N/A'}<br/>
            Status: <strong>${anomaly_status}</strong>
          </div>`
        )
        .openPopup();

      probeMarkerRef.current = marker;
    }
  }, [locationInspection, isDrawingMode]);

  return (
    <div ref={mapContainerRef} className="map-viewport" id="map-container">
      {/* Onscreen Drawing Guide when in drawing mode */}
      {isDrawingMode && (
        <div className="drawing-status-banner">
          <span style={{ fontWeight: 600 }}>AOI Drawing Mode:</span> Click on the map to place vertices ({drawnPoints.length} added).
          {drawnPoints.length >= 3 && (
            <button
              type="button"
              className="btn btn-accent"
              style={{ padding: '3px 8px', fontSize: '0.72rem', marginLeft: '8px' }}
              onClick={(e) => {
                e.stopPropagation();
                onFinishDrawing?.();
              }}
            >
              Finish Polygon
            </button>
          )}
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '3px 8px', fontSize: '0.72rem', marginLeft: '4px' }}
            onClick={(e) => {
              e.stopPropagation();
              onCancelDrawing?.();
            }}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
};
