import { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useQuery } from '@tanstack/react-query'
import { getShorelines, getAnalyses } from '../../services/api'
import { Loader2 } from 'lucide-react'

const PLOT_LAYOUT_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { family: 'Inter, system-ui, sans-serif', color: '#94a3b8', size: 11 },
  margin: { l: 50, r: 20, t: 30, b: 50 },
  legend: {
    bgcolor: 'transparent',
    font: { color: '#94a3b8', size: 10 },
  },
  xaxis: {
    gridcolor: '#334155',
    zerolinecolor: '#475569',
    tickfont: { color: '#64748b', size: 10 },
  },
  yaxis: {
    gridcolor: '#334155',
    zerolinecolor: '#475569',
    tickfont: { color: '#64748b', size: 10 },
  },
}

export default function ShorelineChangeChart() {
  const { data: shorelines = [], isLoading: shorelineLoading } = useQuery({
    queryKey: ['shorelines'],
    queryFn: () => getShorelines(),
  })

  const { data: analyses = [], isLoading: analysisLoading } = useQuery({
    queryKey: ['analyses'],
    queryFn: () => getAnalyses(),
  })

  const isLoading = shorelineLoading || analysisLoading

  const chartData = useMemo(() => {
    const sortedShorelines = [...shorelines].sort((a, b) => a.year - b.year)
    const slById = Object.fromEntries(sortedShorelines.map((s) => [s.id, s.year]))

    // Build EPR by "to year" from analyses
    const eprByYear: Record<number, number> = {}
    analyses.forEach((analysis) => {
      const toYear = slById[analysis.shoreline_to_id]
      if (toYear !== undefined && analysis.epr_m_per_year !== null) {
        eprByYear[toYear] = analysis.epr_m_per_year
      }
    })

    const eprYears = Object.keys(eprByYear).map(Number).sort((a, b) => a - b)
    const eprValues = eprYears.map((y) => eprByYear[y])

    return { eprYears, eprValues }
  }, [shorelines, analyses])

  if (isLoading) {
    return (
      <div className="card flex items-center justify-center h-full">
        <Loader2 size={20} className="animate-spin text-cyan-400" />
      </div>
    )
  }

  if (shorelines.length === 0) {
    return (
      <div className="card flex items-center justify-center h-full">
        <p className="text-slate-500 text-sm">Chưa có dữ liệu đường bờ</p>
      </div>
    )
  }

  if (chartData.eprYears.length === 0) {
    return (
      <div className="card flex items-center justify-center h-full">
        <p className="text-slate-500 text-sm">Chưa có dữ liệu phân tích EPR</p>
      </div>
    )
  }

  const plotData: Plotly.Data[] = [
    {
      x: chartData.eprYears,
      y: chartData.eprValues,
      type: 'bar',
      name: 'EPR (m/năm)',
      marker: {
        color: chartData.eprValues.map((v) => (v >= 0 ? '#22d3ee' : '#ef4444')),
        opacity: 0.8,
      },
    },
  ]

  const layout: Partial<Plotly.Layout> = {
    ...PLOT_LAYOUT_BASE,
    title: {
      text: 'Tốc độ biến động bờ biển (EPR)',
      font: { color: '#cbd5e1', size: 12 },
      x: 0.01,
    },
    xaxis: {
      ...PLOT_LAYOUT_BASE.xaxis,
      dtick: 1,
      title: { text: 'Năm', font: { color: '#64748b', size: 10 } },
    },
    yaxis: {
      ...PLOT_LAYOUT_BASE.yaxis,
      title: { text: 'EPR (m/năm)', font: { color: '#64748b', size: 10 } },
      zerolinecolor: '#475569',
      zerolinewidth: 2,
    },
    hovermode: 'x unified',
    showlegend: false,
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
