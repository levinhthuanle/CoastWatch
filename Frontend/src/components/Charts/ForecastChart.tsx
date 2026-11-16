import { useState } from 'react'
import Plot from 'react-plotly.js'
import { useQuery } from '@tanstack/react-query'
import { getShorelines, getForecasts, generateForecast, getAnalyses } from '../../services/api'
import { Loader2, TrendingUp, AlertCircle } from 'lucide-react'
import useCoastWatchStore from '../../store/useCoastWatchStore'
import { useJobPoller } from '../../hooks/useJobPoller'

const PLOT_LAYOUT_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { family: 'Inter, system-ui, sans-serif', color: '#94a3b8', size: 11 },
  margin: { l: 60, r: 30, t: 40, b: 50 },
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

export default function ForecastChart() {
  const { setActiveForecast } = useCoastWatchStore()
  const [targetYear, setTargetYear] = useState(2027)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)

  const { data: shorelines = [] } = useQuery({
    queryKey: ['shorelines'],
    queryFn: () => getShorelines(),
  })

  const { data: forecasts = [], refetch: refetchForecasts } = useQuery({
    queryKey: ['forecasts'],
    queryFn: () => getForecasts(),
  })

  const { data: analyses = [] } = useQuery({
    queryKey: ['analyses'],
    queryFn: () => getAnalyses(),
  })

  const { startPolling, isPolling } = useJobPoller({
    onCompleted: async () => {
      await refetchForecasts()
      setIsGenerating(false)
    },
    onFailed: (job) => {
      setGenerateError(job.error ?? 'Dự báo thất bại')
      setIsGenerating(false)
    },
  })

  const handleGenerateForecast = async () => {
    setIsGenerating(true)
    setGenerateError(null)
    try {
      const job = await generateForecast(targetYear)
      startPolling(job.id)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Không thể tạo dự báo'
      setGenerateError(message)
      setIsGenerating(false)
    }
  }

  // Build chart data from historical shorelines and analyses
  const sortedShorelines = [...shorelines].sort((a, b) => a.year - b.year)
  const historicalYears = sortedShorelines.map((s) => s.year)

  // Calculate cumulative change in meters from analysis data
  const eprByYear: Record<number, number> = {}
  analyses.forEach((analysis) => {
    const toShoreline = sortedShorelines.find((s) => s.id === analysis.shoreline_to_id)
    if (toShoreline) {
      eprByYear[toShoreline.year] = analysis.epr_m_per_year
    }
  })

  const cumulativeChanges = historicalYears.map((year, i) => {
    if (i === 0) return 0
    const prev = historicalYears[i - 1]
    const yearDiff = year - prev
    return (eprByYear[year] ?? 0) * yearDiff
  })

  // Cumulative sum
  const cumulativeTotal: number[] = []
  let running = 0
  cumulativeChanges.forEach((c) => {
    running += c
    cumulativeTotal.push(running)
  })

  // Find forecast for target year
  const forecast = forecasts.find((f) => f.target_year === targetYear)

  if (forecast) {
    setActiveForecast(forecast)
  }

  const plotData: Plotly.Data[] = []

  if (historicalYears.length > 0) {
    plotData.push({
      x: historicalYears,
      y: cumulativeTotal,
      type: 'scatter',
      mode: 'lines+markers',
      name: 'Vị trí lịch sử',
      marker: { color: '#06b6d4', size: 8, symbol: 'circle' },
      line: { color: '#06b6d4', width: 2 },
    })
  }

  // Trend line using linear regression
  if (cumulativeTotal.length >= 2) {
    const n = historicalYears.length
    const sumX = historicalYears.reduce((a, b) => a + b, 0)
    const sumY = cumulativeTotal.reduce((a, b) => a + b, 0)
    const sumXY = historicalYears.reduce((acc, x, i) => acc + x * cumulativeTotal[i], 0)
    const sumXX = historicalYears.reduce((acc, x) => acc + x * x, 0)
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX)
    const intercept = (sumY - slope * sumX) / n

    const trendX = [
      Math.min(...historicalYears),
      Math.max(...historicalYears, targetYear + 1),
    ]
    const trendY = trendX.map((x) => slope * x + intercept)

    plotData.push({
      x: trendX,
      y: trendY,
      type: 'scatter',
      mode: 'lines',
      name: 'Xu hướng tuyến tính',
      line: { color: '#94a3b8', width: 1.5, dash: 'dot' },
    })

    if (!forecast) {
      const predictedY = slope * targetYear + intercept
      plotData.push({
        x: [targetYear],
        y: [predictedY],
        type: 'scatter',
        mode: 'markers',
        name: `Dự báo ${targetYear}`,
        marker: { color: '#f59e0b', size: 12, symbol: 'diamond' },
        error_y: {
          type: 'constant',
          value: Math.abs(slope * 2),
          visible: true,
          color: '#f59e0b',
        },
      })
    }
  }

  if (forecast) {
    plotData.push({
      x: [forecast.target_year],
      y: [0],
      type: 'scatter',
      mode: 'text+markers',
      name: `Dự báo ${forecast.target_year}`,
      marker: { color: '#f59e0b', size: 14, symbol: 'star' },
      text: [`${forecast.target_year}`],
      textposition: 'top center',
      textfont: { color: '#f59e0b', size: 11 },
    })
  }

  const layout: Partial<Plotly.Layout> = {
    ...PLOT_LAYOUT_BASE,
    title: {
      text: `Dự báo đường bờ đến năm ${targetYear}`,
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
      title: { text: 'Biến đổi tích lũy (m)', font: { color: '#64748b', size: 10 } },
    },
    shapes:
      forecast
        ? [
            {
              type: 'line' as const,
              x0: targetYear,
              x1: targetYear,
              y0: 0,
              y1: 1,
              yref: 'paper' as const,
              line: { color: '#f59e0b', width: 1.5, dash: 'dash' },
            },
          ]
        : [],
    annotations: forecast
      ? [
          {
            x: forecast.target_year,
            y: 1,
            xref: 'x',
            yref: 'paper',
            text: `R²=${forecast.r2_score.toFixed(3)}, RMSE=${forecast.rmse.toFixed(1)}m`,
            showarrow: false,
            font: { color: '#94a3b8', size: 9 },
            bgcolor: '#1e293b',
            bordercolor: '#475569',
            borderwidth: 1,
          },
        ]
      : [],
  }

  return (
    <div className="h-full flex gap-4 overflow-hidden">
      {/* Controls */}
      <div className="w-48 flex-shrink-0">
        <div className="card flex flex-col gap-3">
          <div className="flex items-center gap-2 text-slate-300">
            <TrendingUp size={15} />
            <span className="font-medium text-sm">Tạo dự báo</span>
          </div>

          <div>
            <label className="label">Năm mục tiêu</label>
            <input
              type="number"
              min={2025}
              max={2050}
              value={targetYear}
              onChange={(e) => setTargetYear(Number(e.target.value))}
              className="input text-sm"
              disabled={isGenerating || isPolling}
            />
          </div>

          <button
            onClick={handleGenerateForecast}
            disabled={isGenerating || isPolling}
            className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating || isPolling ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Đang tính...
              </>
            ) : (
              <>
                <TrendingUp size={14} />
                Dự báo
              </>
            )}
          </button>

          {generateError && (
            <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-lg p-2">
              <AlertCircle size={13} className="text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-xs">{generateError}</p>
            </div>
          )}

          {forecast && (
            <div className="bg-slate-700/50 rounded-lg p-2.5 text-xs">
              <p className="text-slate-400 font-medium mb-1">Độ chính xác</p>
              <p className="text-slate-300">
                R²: <span className="text-cyan-400">{forecast.r2_score.toFixed(3)}</span>
              </p>
              <p className="text-slate-300">
                RMSE: <span className="text-cyan-400">{forecast.rmse.toFixed(1)} m</span>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 min-w-0">
        {plotData.length > 0 ? (
          <Plot
            data={plotData}
            layout={layout}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        ) : (
          <div className="card flex items-center justify-center h-full">
            <p className="text-slate-500 text-sm">Chưa có dữ liệu để dự báo</p>
          </div>
        )}
      </div>
    </div>
  )
}
