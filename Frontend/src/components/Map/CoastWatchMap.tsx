import { useEffect, useRef, useState, useCallback } from 'react'
import maplibregl from 'maplibre-gl'
import type { Map as MapLibreMap } from 'maplibre-gl'
import { Layers, Navigation, MapPin, Loader2 } from 'lucide-react'
import useCoastWatchStore from '../../store/useCoastWatchStore'
import { useShorelinesByYearRange } from '../../hooks/useShorelines'
import { useMarineCurrent } from '../../hooks/useMarine'
import ShorelineLayer from './ShorelineLayer'
import MarineMapOverlay from '../Marine/MarineMapOverlay'
import YearRangeSlider from './YearRangeSlider'

const CUA_TUNG_CENTER: [number, number] = [107.04, 17.02]
const CUA_TUNG_ZOOM = 13
const TILE_BASE = '/tiles'

const SATELLITE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'esri-satellite': {
      type: 'raster',
      tiles: [`${TILE_BASE}/satellite/{z}/{x}/{y}`],
      tileSize: 256,
      attribution: 'Tiles © Esri',
      maxzoom: 19,
    },
    'osm-labels': {
      type: 'raster',
      tiles: [`${TILE_BASE}/osm/{z}/{x}/{y}`],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
      maxzoom: 19,
    },
  },
  layers: [
    { id: 'satellite', type: 'raster', source: 'esri-satellite' },
    { id: 'labels', type: 'raster', source: 'osm-labels', paint: { 'raster-opacity': 0.3 } },
  ],
}

export default function CoastWatchMap() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const mapLoadedRef = useRef(false)
  const [showYearFilter, setShowYearFilter] = useState(false)

  const { yearRange, activeMethod, activeAnalysis, activeForecast } = useCoastWatchStore()

  const { data: shorelines = [], isLoading } = useShorelinesByYearRange(
    yearRange.from,
    yearRange.to
  )

  const { data: marineData } = useMarineCurrent()

  const filteredShorelines =
    activeMethod === 'all'
      ? shorelines
      : shorelines.filter((s) => s.method === activeMethod)

  const initMap = useCallback(() => {
    if (!mapContainerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: SATELLITE_STYLE,
      center: CUA_TUNG_CENTER,
      zoom: CUA_TUNG_ZOOM,
      attributionControl: false,
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

    map.on('load', () => {
      mapLoadedRef.current = true
      setMapLoaded(true)
    })

    mapRef.current = map
  }, [])

  useEffect(() => {
    initMap()
    return () => {
      if (mapRef.current) {
        mapLoadedRef.current = false
        mapRef.current.remove()
        mapRef.current = null
        setMapLoaded(false)
      }
    }
  }, [initMap])

  // Add forecast layers when activeForecast changes
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded || !activeForecast) return

    const forecastLayerId = 'forecast-layer'
    const confidenceLowId = 'confidence-low'
    const confidenceHighId = 'confidence-high'

    // Remove old layers
    ;[forecastLayerId, confidenceLowId, confidenceHighId].forEach((id) => {
      if (map.getLayer(id)) map.removeLayer(id)
      if (map.getSource(id)) map.removeSource(id)
    })

    // Add forecast line (dashed)
    map.addSource(forecastLayerId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: activeForecast.predicted_geometry,
        properties: { year: activeForecast.target_year },
      },
    })
    map.addLayer({
      id: forecastLayerId,
      type: 'line',
      source: forecastLayerId,
      paint: {
        'line-color': '#f59e0b',
        'line-width': 2,
        'line-dasharray': [6, 3],
        'line-opacity': 0.9,
      },
    })

    // Confidence interval low
    map.addSource(confidenceLowId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: activeForecast.confidence_interval_low,
        properties: {},
      },
    })
    map.addLayer({
      id: confidenceLowId,
      type: 'line',
      source: confidenceLowId,
      paint: {
        'line-color': '#f59e0b',
        'line-width': 1,
        'line-dasharray': [3, 3],
        'line-opacity': 0.4,
      },
    })

    // Confidence interval high
    map.addSource(confidenceHighId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: activeForecast.confidence_interval_high,
        properties: {},
      },
    })
    map.addLayer({
      id: confidenceHighId,
      type: 'line',
      source: confidenceHighId,
      paint: {
        'line-color': '#f59e0b',
        'line-width': 1,
        'line-dasharray': [3, 3],
        'line-opacity': 0.4,
      },
    })
  }, [mapLoaded, activeForecast])

  // Add analysis transects when activeAnalysis changes
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded || !activeAnalysis?.transects_geojson) return

    const transectsLayerId = 'transects-layer'

    if (map.getLayer(transectsLayerId)) map.removeLayer(transectsLayerId)
    if (map.getSource(transectsLayerId)) map.removeSource(transectsLayerId)

    map.addSource(transectsLayerId, {
      type: 'geojson',
      data: activeAnalysis.transects_geojson,
    })
    map.addLayer({
      id: transectsLayerId,
      type: 'line',
      source: transectsLayerId,
      paint: {
        'line-color': [
          'case',
          ['>', ['get', 'epr_m_per_year'], 0],
          '#22d3ee',
          '#ef4444',
        ],
        'line-width': 1.5,
        'line-opacity': 0.7,
      },
    })
  }, [mapLoaded, activeAnalysis])

  const fitToCuaTung = () => {
    if (!mapRef.current) return
    mapRef.current.flyTo({
      center: CUA_TUNG_CENTER,
      zoom: CUA_TUNG_ZOOM,
      duration: 1500,
      easing: (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
    })
  }

  return (
    <div className="relative w-full h-full bg-slate-900">
      {/* Map container */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-slate-800/90 backdrop-blur-sm rounded-lg px-4 py-2 flex items-center gap-2 border border-slate-700">
          <Loader2 size={14} className="text-cyan-400 animate-spin" />
          <span className="text-slate-300 text-sm">Đang tải dữ liệu...</span>
        </div>
      )}

      {/* Year filter control */}
      <div className="absolute top-4 left-4">
        <button
          onClick={() => setShowYearFilter(!showYearFilter)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
            showYearFilter
              ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
              : 'bg-slate-800/90 border-slate-700 text-slate-300 hover:text-white hover:border-slate-600'
          }`}
        >
          <Layers size={14} />
          Lọc năm ({yearRange.from}–{yearRange.to})
        </button>
        {showYearFilter && (
          <div className="mt-2">
            <YearRangeSlider />
          </div>
        )}
      </div>

      {/* Fit to Cua Tung button */}
      <div className="absolute bottom-12 left-4">
        <button
          onClick={fitToCuaTung}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-slate-800/90 border-slate-700 text-slate-300 hover:text-white hover:border-cyan-500/50 hover:text-cyan-400 text-sm font-medium transition-colors"
        >
          <MapPin size={14} />
          Cửa Tùng
        </button>
      </div>

      {/* Shoreline count */}
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2">
        <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-slate-700">
          <span className="text-slate-400 text-xs">
            <span className="text-cyan-400 font-medium">{filteredShorelines.length}</span> đường bờ
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-12 right-28 bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700 p-2.5">
        <p className="text-slate-500 text-xs mb-1.5 font-medium">Năm</p>
        {yearRange.from === yearRange.to ? (
          <div className="flex items-center gap-1.5 text-xs">
            <div className="w-3 h-1.5 rounded bg-cyan-400" />
            <span className="text-cyan-400 font-medium">{yearRange.from}</span>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-1">
              <div className="w-12 h-1.5 rounded" style={{
                background: 'linear-gradient(to right, #22d3ee, #f59e0b, #ef4444)'
              }} />
            </div>
            <div className="flex justify-between text-xs text-slate-500 mt-0.5">
              <span>{yearRange.from}</span>
              <span>{yearRange.to}</span>
            </div>
          </>
        )}
        {activeAnalysis && (
          <>
            <div className="border-t border-slate-700 mt-2 pt-2">
              <p className="text-slate-500 text-xs mb-1">Transect EPR</p>
              <div className="flex items-center gap-1.5 text-xs">
                <div className="w-3 h-0.5 bg-cyan-400" />
                <span className="text-slate-400">Bồi tụ</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs mt-0.5">
                <div className="w-3 h-0.5 bg-red-400" />
                <span className="text-slate-400">Xói lở</span>
              </div>
            </div>
          </>
        )}
        {activeForecast && (
          <div className="border-t border-slate-700 mt-2 pt-2">
            <div className="flex items-center gap-1.5 text-xs">
              <div className="w-4 border-t-2 border-dashed border-amber-400" />
              <span className="text-slate-400">Dự báo {activeForecast.target_year}</span>
            </div>
          </div>
        )}
      </div>

      {/* Navigation hint */}
      <div className="absolute bottom-4 left-4">
        <div className="flex items-center gap-1.5 text-slate-600 text-xs">
          <Navigation size={10} />
          <span>Nhấp vào đường bờ để xem thông tin</span>
        </div>
      </div>

      {/* Render ShorelineLayer only when map is loaded */}
      {mapLoaded && mapRef.current && (
        <ShorelineLayer map={mapRef.current} shorelines={filteredShorelines} />
      )}
      {/* Marine wave overlay */}
      {mapLoaded && mapRef.current && (
        <MarineMapOverlay map={mapRef.current} marine={marineData} />
      )}
    </div>
  )
}
