import { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useQuery } from '@tanstack/react-query'
import { getAnalyses, getShorelines } from '../../services/api'
import { Loader2 } from 'lucide-react'
import type { FeatureCollection, LineString } from 'geojson'

const PLOT_LAYOUT_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'rgba(15,23,42,0.5)',
  font: { family: 'Inter, system-ui, sans-serif', color: '#94a3b8', size: 11 },
  margin: { l: 60, r: 20, t: 30, b: 50 },
}

interface TransectFeature {
  type: 'Feature'
  geometry: LineString
  properties: {
    transect_id: number
    epr?: number
    [key: string]: unknown
  }
}

export default function EPRHeatmap() {
  const { data: shorelines = [], isLoading: shorelineLoading } = useQuery({
    queryKey: ['shorelines'],
    queryFn: () => getShorelines(),
  })

  const { data: analyses = [], isLoading: analysisLoading } = useQuery({
    queryKey: ['analyses'],
    queryFn: () => getAnalyses(),
  })

  const isLoading = shorelineLoading || analysisLoading

  const heatmapData = useMemo(() => {
    if (analyses.length === 0 || shorelines.length === 0) return null

    const years: number[] = []
    const transectData: Record<number, Record<number, number>> = {}

    analyses.forEach((analysis) => {
      const toShoreline = shorelines.find((s) => s.id === analysis.shoreline_to_id)
      if (!toShoreline) return

      const year = toShoreline.year
      if (!years.includes(year)) years.push(year)

      if (analysis.transects_geojson) {
        const features = (analysis.transects_geojson as FeatureCollection)
          .features as TransectFeature[]

        features.forEach((feature) => {
          const transectId = feature.properties.transect_id ?? 0
          const epr = feature.properties.epr ?? 0

          if (!transectData[transectId]) {
            transectData[transectId] = {}
          }
          transectData[transectId][year] = epr
        })
      }
    })

    years.sort((a, b) => a - b)
    const transectIds = Object.keys(transectData)
      .map(Number)
      .sort((a, b) => a - b)

    if (transectIds.length === 0) return null

    const zValues = transectIds.map((tId) =>
      years.map((year) => transectData[tId]?.[year] ?? 0)
    )

    return { years: years.map(String), transectIds: transectIds.map(String), zValues }
  }, [analyses, shorelines])

  if (isLoading) {
    return (
      <div className="card flex items-center justify-center h-full">
        <Loader2 size={20} className="animate-spin text-cyan-400" />
      </div>
    )
  }

  if (!heatmapData) {
    return (
      <div className="card flex items-center justify-center h-full">
        <p className="text-slate-500 text-sm">Chưa có dữ liệu phân tích transect</p>
      </div>
    )
  }

  // Calculate zmin and zmax centered on 0 for RdBu diverging scale
  const allZ = heatmapData.zValues.flat()
  const maxAbs = Math.max(Math.abs(Math.min(...allZ)), Math.abs(Math.max(...allZ)), 1)

  const plotData: Plotly.Data[] = [
    {
      type: 'heatmap',
      x: heatmapData.years,
      y: heatmapData.transectIds,
      z: heatmapData.zValues,
      colorscale: 'RdBu',
      zmin: -maxAbs,
      zmax: maxAbs,
      colorbar: {
        title: { text: 'EPR (m/năm)', font: { color: '#94a3b8', size: 10 } },
        tickfont: { color: '#94a3b8', size: 9 },
        len: 0.8,
      },
      hoverongaps: false,
      hovertemplate: 'Năm: %{x}<br>Transect: %{y}<br>EPR: %{z:.2f} m/năm<extra></extra>',
    },
  ]

  const layout: Partial<Plotly.Layout> = {
    ...PLOT_LAYOUT_BASE,
    title: {
      text: 'Bản đồ nhiệt EPR theo transect',
      font: { color: '#cbd5e1', size: 12 },
      x: 0.01,
    },
    xaxis: {
      title: { text: 'Năm', font: { color: '#64748b', size: 10 } },
      tickfont: { color: '#64748b', size: 10 },
      gridcolor: '#334155',
    },
    yaxis: {
      title: { text: 'Transect (N→S)', font: { color: '#64748b', size: 10 } },
      tickfont: { color: '#64748b', size: 10 },
      gridcolor: '#334155',
    },
  }

  return (
    <div className="h-full">
      <Plot
        data={plotData}
        layout={layout}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  )
}
