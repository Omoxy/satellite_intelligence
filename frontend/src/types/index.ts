export interface BBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface Centroid {
  lat: number;
  lng: number;
}

export interface AOI {
  id: string;
  name: string;
  geometry: any;
  area_sq_km: number;
  centroid: Centroid;
  bbox: BBox;
  is_predefined: boolean;
  created_at: string;
}

export interface Histogram {
  bins: number[];
  counts: number[];
}

export interface IndicatorStats {
  indicator: string;
  mean: number | null;
  min: number | null;
  max: number | null;
  std: number | null;
  pixel_count: number | null;
  nodata_count: number | null;
  histogram: Histogram | null;
  raster_overlay: string | null;
}

export interface ChangeResult {
  indicator: string;
  period1_mean: number | null;
  period2_mean: number | null;
  absolute_change: number | null;
  percentage_change: number | null;
  increase_pct: number | null;
  decrease_pct: number | null;
  stable_pct: number | null;
  change_overlay: string | null;
}

export interface TimeseriesPoint {
  date: string;
  mean: number | null;
  min: number | null;
  max: number | null;
  data_quality: 'good' | 'partial' | 'poor';
}

export interface AnomalyResult {
  indicator: string;
  baseline_value: number | null;
  current_value: number | null;
  deviation: number | null;
  threshold: number | null;
  classification: 'normal' | 'watch' | 'warning' | 'alert';
  description: string;
}

export interface ClassificationResult {
  class_name: string;
  area_pct: number | null;
  pixel_count: number | null;
}

export interface AnalysisSummary {
  study_area_name: string;
  area_sq_km: number;
  analysis_period: string;
  data_source: string;
  cloud_cover_pct: number;
  primary_vegetation_status: string;
  change_trend: string;
  vegetation_anomaly_status: string;
  limitations: string[];
}

export interface AnalysisRun {
  id: string;
  aoi_id: string;
  aoi: AOI;
  start_date: string;
  end_date: string;
  status: string;
  data_source: string;
  cloud_cover_pct: number | null;
  processing_notes: string | null;
  indicators: Record<string, IndicatorStats>;
  change_detection: ChangeResult[];
  timeseries: Record<string, TimeseriesPoint[]>;
  anomalies: AnomalyResult[];
  classification: ClassificationResult[];
  summary: AnalysisSummary;
  created_at: string;
  completed_at: string | null;
}

export interface LocationInspection {
  lat: number;
  lng: number;
  indicators: {
    ndvi: number | null;
    ndmi: number | null;
    ndwi: number | null;
    ndbi: number | null;
  };
  historical_comparison: {
    baseline_mean_ndvi: number;
    current_ndvi: number | null;
    z_score: number;
    historical_samples_count: number;
  };
  anomaly_status: 'NORMAL' | 'WATCH' | 'WARNING' | 'ALERT';
  interpretation: string;
}
