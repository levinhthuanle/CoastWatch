import { useEffect, useRef, useCallback } from 'react'
import maplibregl from 'maplibre-gl'
import type { Map as MapLibreMap, Popup } from 'maplibre-gl'
import type { Shoreline } from '../../types'
import useCoastWatchStore from '../../store/useCoastWatchStore'

interface ShorelineLayerProps {
  map: MapLibreMap
  shorelines: Shoreline[]
}

// Generates a color for a shoreline based on its year (gradient from green → orange → red)
function getShorelineColor(year: number, minYear = 2019, maxYear = 2024): string {
  const normalized = (year - minYear) / Math.max(maxYear - minYear, 1)
  if (normalized <= 0.5) {
    // Green (#22d3ee) to Yellow (#f59e0b)
    const r = Math.round(34 + (245 - 34) * (normalized * 2))
    const g = Math.round(211 + (158 - 211) * (normalized * 2))
    const b = Math.round(238 + (11 - 238) * (normalized * 2))
    return `rgb(${r},${g},${b})`
  } else {
    // Yellow (#f59e0b) to Red (#ef4444)
    const t = (normalized - 0.5) * 2
    const r = Math.round(245 + (239 - 245) * t)
    const g = Math.round(158 + (68 - 158) * t)
    const b = Math.round(11 + (68 - 11) * t)
    return `rgb(${r},${g},${b})`
  }
}

export default function ShorelineLayer({ map, shorelines }: ShorelineLayerProps) {
  const popupRef = useRef<Popup | null>(null)
  const addedLayersRef = useRef<Set<string>>(new Set())
  const { selectedShorelineIds, toggleShorelineSelection } = useCoastWatchStore()

  const removeAllLayers = useCallback(() => {
    addedLayersRef.current.forEach((layerId) => {
      if (map.getLayer(layerId)) map.removeLayer(layerId)
      if (map.getSource(layerId)) map.removeSource(layerId)
    })
    addedLayersRef.current.clear()
  }, [map])

  useEffect(() => {
    if (!map) return

    removeAllLayers()

    const minYear = Math.min(...shorelines.map((s) => s.year), 2019)
    const maxYear = Math.max(...shorelines.map((s) => s.year), 2024)

    shorelines.forEach((shoreline) => {
      const sourceId = `shoreline-source-${shoreline.id}`
      const layerId = `shoreline-${shoreline.id}`
      const isSelected = selectedShorelineIds.includes(shoreline.id)
      const color = getShorelineColor(shoreline.year, minYear, maxYear)

      if (!map.getSource(sourceId)) {
        if (!shoreline.geometry_geojson) return
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const geom = shoreline.geometry_geojson as any
        map.addSource(sourceId, {
          type: 'geojson',
          data: {
            type: 'Feature',
            geometry: geom,
            properties: {
              id: shoreline.id,
              year: shoreline.year,
              method: shoreline.method,
              name: shoreline.name,
              area_water_km2: shoreline.area_water_km2,
              area_land_km2: shoreline.area_land_km2,
            },
          },
        })
      }

      // Add line layer
      if (!map.getLayer(layerId)) {
        map.addLayer({
          id: layerId,
          type: 'line',
          source: sourceId,
          layout: {
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': color,
            'line-width': isSelected ? 3.5 : 2,
            'line-opacity': isSelected ? 1 : 0.75,
          },
        })

        // Click handler
        map.on('click', layerId, (e) => {
          const feature = e.features?.[0]
          if (!feature) return

          const props = feature.properties as {
            id: string
            year: number
            method: string
            name: string
            area_water_km2: number
            area_land_km2: number
          }

          if (popupRef.current) {
            popupRef.current.remove()
          }

          const methodLabel =
            props.method === 'ndwi'
              ? 'NDWI'
              : props.method === 'random_forest'
              ? 'Random Forest'
              : 'Open Source'

          popupRef.current = new maplibregl.Popup({ closeOnClick: true })
            .setLngLat(e.lngLat)
            .setHTML(
              `<div class="text-sm">
                <p class="font-semibold text-cyan-400 mb-1">${props.name}</p>
                <p class="text-slate-300">Năm: <span class="text-white">${props.year}</span></p>
                <p class="text-slate-300">Phương pháp: <span class="text-white">${methodLabel}</span></p>
                <p class="text-slate-300">Vùng nước: <span class="text-white">${props.area_water_km2?.toFixed(2)} km²</span></p>
                <p class="text-slate-300">Vùng đất: <span class="text-white">${props.area_land_km2?.toFixed(2)} km²</span></p>
                <button
                  onclick="document.dispatchEvent(new CustomEvent('toggleShoreline', {detail: '${props.id}'}))"
                  class="mt-2 px-2 py-1 bg-cyan-500 text-white rounded text-xs w-full"
                >
                  ${selectedShorelineIds.includes(props.id) ? 'Bỏ chọn' : 'Chọn để so sánh'}
                </button>
              </div>`
            )
            .addTo(map)
        })

        map.on('mouseenter', layerId, () => {
          map.getCanvas().style.cursor = 'pointer'
        })

        map.on('mouseleave', layerId, () => {
          map.getCanvas().style.cursor = ''
        })

        addedLayersRef.current.add(layerId)
        addedLayersRef.current.add(sourceId)
      }
    })

    // Custom event for popup button
    const handleToggle = (e: Event) => {
      const customEvent = e as CustomEvent<string>
      toggleShorelineSelection(parseInt(customEvent.detail, 10))
    }
    document.addEventListener('toggleShoreline', handleToggle)

    return () => {
      document.removeEventListener('toggleShoreline', handleToggle)
    }
  }, [map, shorelines, selectedShorelineIds, removeAllLayers, toggleShorelineSelection])

  // Update line widths when selection changes
  useEffect(() => {
    if (!map) return
    shorelines.forEach((shoreline) => {
      const layerId = `shoreline-${shoreline.id}`
      if (map.getLayer(layerId)) {
        const isSelected = selectedShorelineIds.includes(shoreline.id)
        map.setPaintProperty(layerId, 'line-width', isSelected ? 3.5 : 2)
        map.setPaintProperty(layerId, 'line-opacity', isSelected ? 1 : 0.75)
      }
    })
  }, [map, shorelines, selectedShorelineIds])

  useEffect(() => {
    return () => {
      if (popupRef.current) {
        popupRef.current.remove()
      }
    }
  }, [])

  return null
}
