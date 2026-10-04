import { AOI, AnalysisRun, LocationInspection } from '../types';

const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  details?: any;

  constructor(message: string, status: number, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options?: RequestInit, apiBase = API_BASE): Promise<T> {
  const url = `${apiBase}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = body?.error?.detail || body?.detail || `HTTP ${response.status}: Request failed`;
    throw new ApiError(errorMsg, response.status, body);
  }

  return (body && Object.prototype.hasOwnProperty.call(body, 'data') ? body.data : body) as T;
}

export const api = {
  getHealth: () => request<{ status: string; database: string; data_mode: string }>('/health', undefined, ''),

  getAreas: () => request<{ areas: AOI[] }>('/areas').then((res) => res.areas),

  createArea: (name: string, geometry: any) =>
    request<{ area: AOI }>('/areas', {
      method: 'POST',
      body: JSON.stringify({ name, geometry }),
    }).then((res) => res.area),

  deleteArea: (id: string) =>
    request<{ deleted_id: string }>(`/areas/${id}`, {
      method: 'DELETE',
    }),

  runAnalysis: (aoi_id: string, start_date: string, end_date: string, indicators: string[]) =>
    request<{ analysis: AnalysisRun }>('/analysis', {
      method: 'POST',
      body: JSON.stringify({ aoi_id, start_date, end_date, indicators }),
    }).then((res) => res.analysis),

  getAnalysis: (id: string) =>
    request<{ analysis: AnalysisRun }>(`/analysis/${id}`).then((res) => res.analysis),

  inspectLocation: (lat: number, lng: number, analysis_id?: string) => {
    const query = new URLSearchParams({
      lat: lat.toString(),
      lng: lng.toString(),
    });
    if (analysis_id) query.append('analysis_id', analysis_id);
    return request<{ location: LocationInspection }>(`/location?${query.toString()}`).then(
      (res) => res.location
    );
  },
};
