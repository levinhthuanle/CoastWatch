import axios from 'axios'
import type {
  Shoreline,
  ShorelineAnalysis,
  ShorelineForecast,
  ProcessingJob,
  ShorelineFilters,
  MarineCurrentResponse,
} from '../types'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ?? error.message ?? 'Đã xảy ra lỗi không xác định'
    console.error('[API Error]', message)
    return Promise.reject(new Error(message))
  }
)

// Shorelines
export async function getShorelines(filters?: ShorelineFilters): Promise<Shoreline[]> {
  const params = new URLSearchParams()
  if (filters?.year !== undefined) params.append('year', String(filters.year))
  if (filters?.method) params.append('method', filters.method)
  if (filters?.year_from !== undefined) params.append('year_from', String(filters.year_from))
  if (filters?.year_to !== undefined) params.append('year_to', String(filters.year_to))
  const { data } = await apiClient.get<{ items: Shoreline[]; total: number }>('/shorelines', { params })
  return Array.isArray(data) ? data : (data?.items ?? [])
}

export async function getShoreline(id: string): Promise<Shoreline> {
  const { data } = await apiClient.get<Shoreline>(`/shorelines/${id}`)
  return data
}

export async function getShorelineGeoJSON(id: string): Promise<import('geojson').FeatureCollection> {
  const { data } = await apiClient.get<import('geojson').FeatureCollection>(`/shorelines/${id}/geojson`)
  return data
}

export interface ExtractShorelineParams {
  date: string
  method: Shoreline['method']
  bbox?: [number, number, number, number]
  cloud_cover_max?: number
}

export async function extractShoreline(params: ExtractShorelineParams): Promise<ProcessingJob> {
  const { data } = await apiClient.post<ProcessingJob>('/shorelines/extract', params)
  return data
}

// Analysis
export async function getAnalyses(): Promise<ShorelineAnalysis[]> {
  const { data } = await apiClient.get<{ items: ShorelineAnalysis[]; total: number }>('/analysis')
  return Array.isArray(data) ? data : (data?.items ?? [])
}

export async function compareShoreLines(
  from_id: number,
  to_id: number
): Promise<ProcessingJob> {
  const { data } = await apiClient.post<ProcessingJob>('/analysis/compare', {
    shoreline_from_id: from_id,
    shoreline_to_id: to_id,
  })
  return data
}

export async function getAnalysis(id: string): Promise<ShorelineAnalysis> {
  const { data } = await apiClient.get<ShorelineAnalysis>(`/analysis/${id}`)
  return data
}

export async function autoCompareAll(): Promise<{ processed: number; skipped: number; message: string }> {
  const { data } = await apiClient.post('/analysis/auto-compare')
  return data
}

// Forecast
export async function getForecasts(): Promise<ShorelineForecast[]> {
  const { data } = await apiClient.get<{ items: ShorelineForecast[]; total: number }>('/forecast')
  return Array.isArray(data) ? data : (data?.items ?? [])
}

export async function generateForecast(target_year: number): Promise<ProcessingJob> {
  const { data } = await apiClient.post<ProcessingJob>('/forecast/generate', { target_year })
  return data
}

// Jobs
export async function getJob(id: string): Promise<ProcessingJob> {
  const { data } = await apiClient.get<ProcessingJob>(`/jobs/${id}`)
  return data
}

// Chat
export interface ChatResponse {
  reply: string
  session_id: string
  model?: string
  context_used?: boolean
}

export async function sendChatMessage(
  message: string,
  session_id: string
): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>('/chat', { message, session_id })
  return data
}

export default apiClient

// Marine
export async function getMarineCurrentConditions(): Promise<MarineCurrentResponse> {
  const { data } = await apiClient.get<MarineCurrentResponse>('/marine/current')
  return data
}

export async function getMarineForecast(days = 7) {
  const { data } = await apiClient.get('/marine/forecast', { params: { days } })
  return data
}

export async function getMarineHistorical(days = 30) {
  const { data } = await apiClient.get('/marine/historical', { params: { days } })
  return data
}
