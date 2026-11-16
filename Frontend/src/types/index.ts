import type { LineString, FeatureCollection } from 'geojson'

export interface Shoreline {
  id: number
  name: string
  date: string
  year: number
  method: 'ndwi' | 'random_forest' | 'open_source'
  geometry_geojson: LineString | null
  area_water_km2: number | null
  area_land_km2: number | null
  cloud_cover: number | null
  created_at: string
}

export interface ShorelineAnalysis {
  id: number
  shoreline_from_id: number
  shoreline_to_id: number
  epr_m_per_year: number | null
  total_change_m: number | null
  area_lost_km2: number | null
  area_gained_km2: number | null
  transects_geojson: FeatureCollection | null
  iou_score: number | null
  f1_score: number | null
  created_at: string
}

export interface ShorelineForecast {
  id: number
  target_year: number
  method: string
  predicted_geometry: LineString | null
  confidence_interval_low: LineString | null
  confidence_interval_high: LineString | null
  rmse: number | null
  r2_score: number | null
}

export interface ProcessingJob {
  id: string
  type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  params: Record<string, unknown>
  result: Record<string, unknown> | null
  error?: string
  created_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface ShorelineFilters {
  year?: number
  method?: Shoreline['method']
  year_from?: number
  year_to?: number
}

export interface ApiError {
  detail: string
  status_code: number
}

export type MapStyle = 'satellite' | 'street' | 'dark'

export interface YearRange {
  from: number
  to: number
}

// ── Marine / Wave data ────────────────────────────────────────────────────────

export interface MarineCurrentConditions {
  time: string | null
  wave_height_m: number | null
  wave_direction_deg: number | null
  wave_period_s: number | null
  sea_surface_temp_c: number | null
  sea_level_height_m: number | null
  wind_speed_kmh: number | null
  wind_direction_deg: number | null
}

export interface MarineHourlyPoint {
  time: string
  wave_height_m: number | null
  wave_direction_deg: number | null
  wave_period_s: number | null
  swell_wave_height_m: number | null
  wind_wave_height_m: number | null
  ocean_current_velocity_kmh: number | null
  ocean_current_direction_deg: number | null
  sea_surface_temp_c: number | null
  sea_level_height_m: number | null
  wind_speed_kmh: number | null
  wind_direction_deg: number | null
  precipitation_mm: number | null
}

export interface MarineDailyForecast {
  date: string
  avg_wave_height_m: number
  max_wave_height_m: number
  avg_swell_height_m: number
  avg_wind_speed_kmh: number
  risk_score: number
  risk_level: 'low' | 'moderate' | 'high' | 'extreme'
  risk_color: string
}

export interface ErosionRisk {
  score: number
  level: 'low' | 'moderate' | 'high' | 'extreme'
  color: string
  description: string
  season_note: string
  contributing_factors: {
    wave_energy_score: number
    wind_score: number
    seasonal_multiplier: number
    historical_trend_adjustment: number
  }
}

export interface MarineCurrentResponse {
  current: MarineCurrentConditions
  risk: ErosionRisk
  daily_forecast: MarineDailyForecast[]
  hourly_forecast: MarineHourlyPoint[]
  location: {
    name: string
    latitude: number
    longitude: number
  }
}
