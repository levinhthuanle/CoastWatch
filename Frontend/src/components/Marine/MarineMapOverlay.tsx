/**
 * Marine overlay on the MapLibre map.
 * Renders:
 * 1. Animated risk marker (HTML Marker) at Cửa Tùng
 * 2. Wave approach dashed line showing wave direction
 */
import { useEffect, useRef } from 'react'
import type { Map as MapLibreMap } from 'maplibre-gl'
import maplibregl from 'maplibre-gl'
import type { MarineCurrentResponse } from '../../types'

const CUA_TUNG_LNG = 107.04
const CUA_TUNG_LAT = 17.02

interface MarineOverlayProps {
  map: MapLibreMap
  marine: MarineCurrentResponse | undefined
}

export default function MarineMapOverlay({ map, marine }: MarineOverlayProps) {
  const markerRef = useRef<maplibregl.Marker | null>(null)
  const arrowSourceId = 'marine-wave-arrow'

  useEffect(() => {
    if (!marine) return

    const { current, risk } = marine

    // ── 1. Animated risk marker (HTML element via maplibre Marker) ──
    if (markerRef.current) {
      markerRef.current.remove()
    }

    const el = document.createElement('div')
    el.className = 'marine-risk-marker'
    el.style.cssText = `
      display: flex;
      flex-direction: column;
      align-items: center;
      cursor: pointer;
      filter: drop-shadow(0 2px 8px ${risk.color}88);
    `

    const arrowDeg = current.wave_direction_deg ?? 0
    const arrowSvg = `
      <svg width="48" height="48" viewBox="0 0 48 48" style="transform: rotate(${arrowDeg}deg); transition: transform 0.5s ease;">
        <circle cx="24" cy="24" r="20" fill="${risk.color}22" stroke="${risk.color}" stroke-width="1.5"/>
        <!-- animated pulse ring -->
        <circle cx="24" cy="24" r="20" fill="none" stroke="${risk.color}" stroke-width="1" opacity="0.6">
          <animate attributeName="r" from="20" to="30" dur="2s" repeatCount="indefinite"/>
          <animate attributeName="opacity" from="0.6" to="0" dur="2s" repeatCount="indefinite"/>
        </circle>
        <!-- Arrow pointing up = direction of wave travel -->
        <line x1="24" y1="28" x2="24" y2="12" stroke="${risk.color}" stroke-width="2.5" stroke-linecap="round"/>
        <polygon points="24,8 20,16 28,16" fill="${risk.color}"/>
      </svg>
    `

    const levelVi: Record<string, string> = {
      low: 'Thấp', moderate: 'Vừa', high: 'Cao', extreme: 'Nguy hiểm'
    }
    const badge = `
      <div style="
        background: ${risk.color}dd;
        color: white;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        margin-top: -4px;
        white-space: nowrap;
        border: 1px solid ${risk.color};
      ">
        ⚡ ${Math.round(risk.score)} • ${levelVi[risk.level] ?? risk.level}
      </div>
    `

    const heightLabel = current.wave_height_m != null
      ? `<div style="color: #94a3b8; font-size: 10px; margin-top: 2px;">🌊 ${current.wave_height_m.toFixed(1)}m</div>`
      : ''

    el.innerHTML = arrowSvg + badge + heightLabel

    markerRef.current = new maplibregl.Marker({ element: el, anchor: 'bottom' })
      .setLngLat([CUA_TUNG_LNG, CUA_TUNG_LAT])
      .addTo(map)

    // ── 2. Wave approach dashed line ──
    if (map.getLayer(arrowSourceId)) map.removeLayer(arrowSourceId)
    if (map.getSource(arrowSourceId)) map.removeSource(arrowSourceId)

    const waveDir = (current.wave_direction_deg ?? 0) * (Math.PI / 180)
    const offsetDist = 0.04
    const srcPoint: [number, number] = [
      CUA_TUNG_LNG + offsetDist * Math.sin(waveDir),
      CUA_TUNG_LAT + offsetDist * Math.cos(waveDir),
    ]

    map.addSource(arrowSourceId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: [srcPoint, [CUA_TUNG_LNG, CUA_TUNG_LAT]] },
        properties: {},
      },
    })
    map.addLayer({
      id: arrowSourceId,
      type: 'line',
      source: arrowSourceId,
      paint: {
        'line-color': risk.color,
        'line-width': Math.max(1.5, (risk.score / 100) * 4),
        'line-opacity': 0.75,
        'line-dasharray': [4, 2],
      },
    })

    return () => {
      markerRef.current?.remove()
      markerRef.current = null
      try {
        // map.getStyle() throws if the map was removed — use as a liveness check
        map.getStyle()
        if (map.getLayer(arrowSourceId)) map.removeLayer(arrowSourceId)
        if (map.getSource(arrowSourceId)) map.removeSource(arrowSourceId)
      } catch {
        // map was already destroyed — nothing to clean up
      }
    }
  }, [map, marine])

  return null
}
