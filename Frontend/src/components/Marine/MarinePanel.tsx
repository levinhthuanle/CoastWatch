import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMarineCurrentConditions } from '../../services/api'
import type { MarineCurrentResponse, MarineDailyForecast, MarineHourlyPoint } from '../../types'
import { Waves, Wind, AlertTriangle, RefreshCw, TrendingUp, Thermometer, Droplets } from 'lucide-react'

// ── Compass rose ─────────────────────────────────────────────────────────────

function CompassRose({ degrees, label, color = '#22d3ee' }: { degrees: number; label: string; color?: string }) {
  const rad = ((degrees - 90) * Math.PI) / 180
  const cx = 50, cy = 50, r = 32
  const arrowX = cx + r * Math.cos(rad)
  const arrowY = cy + r * Math.sin(rad)
  const tailX = cx - r * 0.6 * Math.cos(rad)
  const tailY = cy - r * 0.6 * Math.sin(rad)
  const perpRad = rad + Math.PI / 2
  const barbLen = 8
  const barbX1 = cx + r * 0.1 * Math.cos(rad) + barbLen * Math.cos(perpRad)
  const barbY1 = cy + r * 0.1 * Math.sin(rad) + barbLen * Math.sin(perpRad)
  const barbX2 = cx + r * 0.1 * Math.cos(rad) - barbLen * Math.cos(perpRad)
  const barbY2 = cy + r * 0.1 * Math.sin(rad) - barbLen * Math.sin(perpRad)
  const cardinals = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  const cardAngles = [270, 315, 0, 45, 90, 135, 180, 225]
  return (
    <svg viewBox="0 0 100 100" className="w-full h-full">
      <circle cx={cx} cy={cy} r={r + 8} fill="none" stroke="#334155" strokeWidth="1" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e293b" strokeWidth="0.5" />
      {cardAngles.map((ang, i) => {
        const ar = ((ang - 90) * Math.PI) / 180
        const x1 = cx + (r + 1) * Math.cos(ar), y1 = cy + (r + 1) * Math.sin(ar)
        const x2 = cx + (r + 7) * Math.cos(ar), y2 = cy + (r + 7) * Math.sin(ar)
        const lx = cx + (r + 14) * Math.cos(ar), ly = cy + (r + 14) * Math.sin(ar)
        const isPrimary = i % 2 === 0
        return (
          <g key={ang}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={isPrimary ? '#94a3b8' : '#475569'} strokeWidth={isPrimary ? 1.5 : 0.8} />
            {isPrimary && <text x={lx} y={ly} textAnchor="middle" dominantBaseline="central" fontSize="6" fill="#94a3b8" fontWeight="600">{cardinals[i]}</text>}
          </g>
        )
      })}
      <line x1={tailX} y1={tailY} x2={arrowX} y2={arrowY} stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      <polygon points={`${arrowX},${arrowY} ${barbX1},${barbY1} ${barbX2},${barbY2}`} fill={color} opacity={0.9} />
      <circle cx={cx} cy={cy} r={3} fill={color} opacity={0.7} />
      <text x={cx} y={cy + r + 22} textAnchor="middle" fontSize="8" fill="#94a3b8">{label}</text>
      <text x={cx} y={cy + r + 30} textAnchor="middle" fontSize="9" fill="#e2e8f0" fontWeight="700">{degrees}°</text>
    </svg>
  )
}

// ── Risk gauge ───────────────────────────────────────────────────────────────

function RiskGauge({ score, level, color, description }: { score: number; level: string; color: string; description: string }) {
  const r = 40, cx = 60, cy = 60
  const circumference = Math.PI * r
  const filled = (score / 100) * circumference
  const levelVi: Record<string, string> = { low: 'THẤP', moderate: 'TRUNG BÌNH', high: 'CAO', extreme: 'NGUY HIỂM' }
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-20">
        <svg viewBox="0 0 120 70" className="w-full h-full">
          <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke="#1e293b" strokeWidth="10" strokeLinecap="round" />
          <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference}`} style={{ filter: `drop-shadow(0 0 4px ${color}88)` }} />
          <text x={cx} y={cy - 4} textAnchor="middle" fontSize="18" fontWeight="800" fill={color}>{Math.round(score)}</text>
          <text x={cx} y={cy + 8} textAnchor="middle" fontSize="7" fill="#64748b">/ 100</text>
        </svg>
      </div>
      <div className="px-3 py-1 rounded-full text-xs font-bold tracking-widest mt-1"
        style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}44` }}>
        {levelVi[level] ?? level.toUpperCase()}
      </div>
      <p className="text-slate-400 text-xs mt-1 text-center leading-tight">{description}</p>
    </div>
  )
}

// ── 7-day forecast strip ─────────────────────────────────────────────────────

function DailyForecastStrip({ days }: { days: MarineDailyForecast[] }) {
  const today = new Date().toISOString().slice(0, 10)
  return (
    <div className="flex gap-1.5 overflow-x-auto pb-1">
      {days.map((d) => {
        const isToday = d.date === today
        const date = new Date(d.date + 'T00:00:00')
        const label = isToday ? 'Hôm nay' : date.toLocaleDateString('vi-VN', { weekday: 'short', day: 'numeric' })
        return (
          <div key={d.date} className={`flex-shrink-0 flex flex-col items-center gap-1 rounded-xl px-3 py-2 border text-center min-w-16 ${
            isToday ? 'bg-slate-700/80 border-slate-600' : 'bg-slate-800/50 border-slate-700/50'
          }`}>
            <span className="text-slate-400 text-xs font-medium">{label}</span>
            <div className="w-full bg-slate-700 rounded-full h-1.5 overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${Math.min(100, (d.max_wave_height_m / 4) * 100)}%`, backgroundColor: d.risk_color }} />
            </div>
            <span className="text-white text-sm font-semibold">{d.max_wave_height_m.toFixed(1)}m</span>
            <span className="text-slate-500 text-xs">{d.avg_wave_height_m.toFixed(1)} avg</span>
            <div className="w-full rounded-md py-0.5 text-center text-xs font-semibold"
              style={{ backgroundColor: `${d.risk_color}22`, color: d.risk_color }}>
              {Math.round(d.risk_score)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Time-series chart ─────────────────────────────────────────────────────────

const PANELS = [
  { key: 'wave_height_m'    as const, label: 'Chiều cao sóng', unit: 'm',    color: '#22d3ee', colorStop: '#0e7490', decimals: 1 },
  { key: 'wind_speed_kmh'   as const, label: 'Tốc độ gió',     unit: 'km/h', color: '#a78bfa', colorStop: '#6d28d9', decimals: 0 },
  { key: 'sea_level_height_m' as const, label: 'Mực nước biển', unit: 'm',   color: '#34d399', colorStop: '#065f46', decimals: 2 },
]

// Catmull-Rom → cubic bezier smooth path
function smoothPath(pts: [number, number][]): string {
  if (pts.length < 2) return ''
  if (pts.length === 2) return `M ${pts[0][0]},${pts[0][1]} L ${pts[1][0]},${pts[1][1]}`
  let d = `M ${pts[0][0]},${pts[0][1]}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(pts.length - 1, i + 2)]
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6
    d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`
  }
  return d
}

function MiniChart({
  data, field, label, unit, color, colorStop, decimals, hoverIdx, onHover,
}: {
  data: MarineHourlyPoint[]
  field: keyof MarineHourlyPoint
  label: string; unit: string; color: string; colorStop: string; decimals: number
  hoverIdx: number | null
  onHover: (i: number | null) => void
}) {
  const W = 560, H = 72, padL = 38, padR = 8, padT = 10, padB = 4
  const vals = data.map(h => h[field] as number | null)
  const nums = vals.filter(v => v !== null) as number[]
  if (nums.length < 2) return null

  const rawMin = Math.min(...nums)
  const rawMax = Math.max(...nums)
  const span = rawMax - rawMin || 1
  // Add 15% padding top/bottom so line doesn't touch edges
  const min = rawMin - span * 0.15
  const max = rawMax + span * 0.15

  const toX = (i: number) => padL + (i / (data.length - 1)) * (W - padL - padR)
  const toY = (v: number) => padT + (1 - (v - min) / (max - min)) * (H - padT - padB)

  const pts: [number, number][] = vals
    .map((v, i) => (v !== null ? [toX(i), toY(v)] : null))
    .filter(Boolean) as [number, number][]

  const linePath = smoothPath(pts)
  const areaPath = linePath + ` L ${toX(data.length - 1)},${H - padB} L ${toX(0)},${H - padB} Z`

  // Y ticks: 3 levels
  const yTicks = [rawMin, (rawMin + rawMax) / 2, rawMax]

  // Time ticks every 12h
  const timeTicks = data
    .map((h, i) => ({ i, h: new Date(h.time).getHours(), time: h.time }))
    .filter(({ h, i }) => (h % 12 === 0) || i === 0)

  // Day breaks
  const dayBreaks = data
    .map((h, i) => ({ i, h: new Date(h.time).getHours() }))
    .filter(({ h, i }) => h === 0 && i > 0)

  const gradId = `g-${field as string}`
  const hovered = hoverIdx !== null ? vals[hoverIdx] : null

  return (
    <div className="relative group">
      {/* Label + current value */}
      <div className="flex items-center justify-between mb-1.5 px-1">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
          <span className="text-xs font-medium text-slate-300">{label}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {hoverIdx !== null && hovered !== null ? (
            <span className="text-sm font-bold tabular-nums" style={{ color }}>
              {hovered.toFixed(decimals)} <span className="text-xs font-normal text-slate-500">{unit}</span>
            </span>
          ) : (
            <span className="text-sm font-bold tabular-nums" style={{ color }}>
              {(vals[0] ?? 0).toFixed(decimals)} <span className="text-xs font-normal text-slate-500">{unit}</span>
            </span>
          )}
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 80 }}
        onMouseLeave={() => onHover(null)}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={colorStop} stopOpacity="0.02" />
          </linearGradient>
          <clipPath id={`clip-${field as string}`}>
            <rect x={padL} y={padT} width={W - padL - padR} height={H - padT - padB} />
          </clipPath>
        </defs>

        {/* Grid lines */}
        {[0.25, 0.5, 0.75, 1].map(f => {
          const y = padT + f * (H - padT - padB)
          return <line key={f} x1={padL} y1={y} x2={W - padR} y2={y} stroke="#1e293b" strokeWidth="0.8" />
        })}

        {/* Day separators */}
        {dayBreaks.map(({ i }) => (
          <line key={i} x1={toX(i)} y1={padT} x2={toX(i)} y2={H - padB}
            stroke="#334155" strokeWidth="1" strokeDasharray="4 3" opacity={0.6} />
        ))}

        {/* Area + line */}
        <g clipPath={`url(#clip-${field as string})`}>
          <path d={areaPath} fill={`url(#${gradId})`} />
          <path d={linePath} fill="none" stroke={color} strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round"
            style={{ filter: `drop-shadow(0 0 3px ${color}66)` }} />
        </g>

        {/* Y-axis labels */}
        {yTicks.map((v, i) => (
          <text key={i} x={padL - 4} y={toY(v) + 3.5} textAnchor="end" fontSize="8.5" fill="#475569">
            {v.toFixed(decimals)}
          </text>
        ))}

        {/* Hover crosshair */}
        {hoverIdx !== null && (
          <>
            <line x1={toX(hoverIdx)} y1={padT} x2={toX(hoverIdx)} y2={H - padB}
              stroke={color} strokeWidth="1" strokeDasharray="3 2" opacity={0.4} />
            {hovered !== null && (
              <circle cx={toX(hoverIdx)} cy={toY(hovered)} r={4}
                fill={color} stroke="#0f172a" strokeWidth="2"
                style={{ filter: `drop-shadow(0 0 4px ${color})` }} />
            )}
          </>
        )}

        {/* Invisible hit areas */}
        {data.map((_, i) => (
          <rect key={i}
            x={toX(i) - (W - padL - padR) / data.length / 2} y={padT}
            width={(W - padL - padR) / data.length} height={H - padT - padB}
            fill="transparent" onMouseEnter={() => onHover(i)} />
        ))}
      </svg>

      {/* X-axis labels (only on last panel, passed as prop) */}
      <div className="flex justify-between px-[38px] mt-0.5">
        {timeTicks.map(({ i, time }) => {
          const d = new Date(time)
          const isDay = d.getHours() === 0
          return (
            <span key={i} className={`text-xs tabular-nums ${isDay ? 'text-slate-400 font-medium' : 'text-slate-600'}`}
              style={{ position: 'absolute', left: `calc(${((toX(i)) / W) * 100}%)`, transform: 'translateX(-50%)' }}>
              {isDay ? d.toLocaleDateString('vi-VN', { weekday: 'short', day: 'numeric' }) : `${d.getHours()}h`}
            </span>
          )
        })}
      </div>
    </div>
  )
}

function TimeSeriesChart({ hourly }: { hourly: MarineHourlyPoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)
  const data = hourly.slice(0, 72)
  if (data.length < 2) return null

  // Shared time axis
  const W = 560, padL = 38, padR = 8
  const toX = (i: number) => padL + (i / (data.length - 1)) * (W - padL - padR)
  const timeTicks = data
    .map((h, i) => ({ i, hr: new Date(h.time).getHours(), time: h.time }))
    .filter(({ hr, i }) => hr % 12 === 0 || i === 0)

  return (
    <div className="space-y-3">
      {PANELS.map(p => (
        <MiniChart key={p.key} data={data} field={p.key} label={p.label} unit={p.unit}
          color={p.color} colorStop={p.colorStop} decimals={p.decimals}
          hoverIdx={hoverIdx} onHover={setHoverIdx} />
      ))}

      {/* Shared X axis */}
      <div className="relative h-5" style={{ marginLeft: 38, marginRight: 8 }}>
        {timeTicks.map(({ i, hr, time }) => {
          const d = new Date(time)
          const isDay = hr === 0
          const pct = ((toX(i) - padL) / (W - padL - padR)) * 100
          return (
            <span key={i}
              className={`absolute text-xs tabular-nums -translate-x-1/2 ${isDay ? 'text-slate-400 font-medium' : 'text-slate-600'}`}
              style={{ left: `${pct}%` }}>
              {isDay ? d.toLocaleDateString('vi-VN', { weekday: 'short', day: 'numeric' }) : `${d.getHours()}h`}
            </span>
          )
        })}
      </div>

      {/* Hover time label */}
      {hoverIdx !== null && (
        <p className="text-center text-xs text-slate-400 -mt-1">
          {new Date(data[hoverIdx].time).toLocaleString('vi-VN', { weekday: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
    </div>
  )
}

// ── Alert banner ──────────────────────────────────────────────────────────────

function AlertBanner({ days }: { days: MarineDailyForecast[] }) {
  const alerts = days.filter(d => d.risk_level === 'extreme' || d.risk_level === 'high')
  if (alerts.length === 0) return null

  const worst = alerts.reduce((a, b) => b.risk_score > a.risk_score ? b : a)
  const date = new Date(worst.date + 'T00:00:00')
  const dateLabel = date.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'numeric' })

  return (
    <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
      <AlertTriangle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-red-300 text-sm font-semibold">Cảnh báo sóng cao</p>
        <p className="text-red-400/80 text-xs mt-0.5">
          {dateLabel}: sóng cao đến {worst.max_wave_height_m.toFixed(1)}m, gió {worst.avg_wind_speed_kmh.toFixed(0)} km/h.
          {alerts.length > 1 ? ` Kéo dài ${alerts.length} ngày.` : ''} Nguy cơ xói lở cao.
        </p>
      </div>
    </div>
  )
}

// ── Main panel ───────────────────────────────────────────────────────────────

export default function MarinePanel() {
  const { data, isLoading, isError, refetch, dataUpdatedAt } = useQuery<MarineCurrentResponse>({
    queryKey: ['marine-current'],
    queryFn: getMarineCurrentConditions,
    refetchInterval: 15 * 60 * 1000,
    staleTime: 10 * 60 * 1000,
  })

  const lastUpdate = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    : null

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-3">
          <Waves size={32} className="text-cyan-400 animate-pulse" />
          <p className="text-slate-400 text-sm">Đang tải dữ liệu biển...</p>
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-3 text-center px-8">
          <AlertTriangle size={28} className="text-amber-400" />
          <p className="text-slate-300 text-sm">Không thể tải dữ liệu biển</p>
          <button onClick={() => void refetch()} className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
            <RefreshCw size={12} /> Thử lại
          </button>
        </div>
      </div>
    )
  }

  const { current, risk, daily_forecast, hourly_forecast } = data

  return (
    <div className="h-full overflow-y-auto bg-slate-900 text-white">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-slate-800 border-b border-slate-700 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Waves size={16} className="text-cyan-400" />
          <span className="text-white font-semibold text-sm">Điều kiện biển</span>
          <span className="text-slate-500 text-xs">Cửa Tùng, Quảng Trị</span>
        </div>
        <div className="flex items-center gap-2">
          {lastUpdate && <span className="text-slate-500 text-xs">Cập nhật {lastUpdate}</span>}
          <button onClick={() => void refetch()} className="text-slate-400 hover:text-slate-200">
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Alert banner */}
        <AlertBanner days={daily_forecast} />

        {/* Top row: compass + gauge + risk */}
        <div className="grid grid-cols-3 gap-4 items-center">
          <div className="flex flex-col items-center">
            <p className="text-slate-500 text-xs mb-1 uppercase tracking-wider">Hướng sóng</p>
            <div className="w-28 h-28">
              {current.wave_direction_deg !== null
                ? <CompassRose degrees={current.wave_direction_deg} label="Sóng" color="#22d3ee" />
                : <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs">N/A</div>}
            </div>
          </div>

          <div className="flex flex-col items-center gap-2">
            <p className="text-slate-500 text-xs uppercase tracking-wider">Hiện tại</p>
            <div className="text-center">
              <p className="text-4xl font-bold text-cyan-400">{(current.wave_height_m ?? 0).toFixed(1)}</p>
              <p className="text-slate-500 text-xs">m sóng</p>
            </div>
            {current.wave_period_s !== null && (
              <p className="text-slate-400 text-xs">Chu kỳ {current.wave_period_s.toFixed(1)}s</p>
            )}
            {/* Sea temp + sea level */}
            <div className="flex gap-3 text-xs">
              {current.sea_surface_temp_c !== null && (
                <div className="flex items-center gap-1 text-orange-400">
                  <Thermometer size={11} />
                  <span>{current.sea_surface_temp_c.toFixed(1)}°C</span>
                </div>
              )}
              {current.sea_level_height_m !== null && (
                <div className="flex items-center gap-1 text-emerald-400">
                  <Droplets size={11} />
                  <span>{current.sea_level_height_m.toFixed(2)}m</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col items-center">
            <p className="text-slate-500 text-xs mb-1 uppercase tracking-wider">Nguy cơ xói lở</p>
            <RiskGauge score={risk.score} level={risk.level} color={risk.color} description={risk.description} />
          </div>
        </div>

        {/* Wind row */}
        <div className="bg-slate-800/60 rounded-xl border border-slate-700 p-3 flex items-center gap-3">
            <div className="w-16 h-16 flex-shrink-0">
              {current.wind_direction_deg !== null
                ? <CompassRose degrees={current.wind_direction_deg} label="Gió" color="#a78bfa" />
                : <Wind size={24} className="text-slate-600" />}
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Gió biển</p>
              {current.wind_speed_kmh !== null ? (
                <>
                  <p className="text-white text-xl font-bold">{current.wind_speed_kmh.toFixed(1)}</p>
                  <p className="text-slate-500 text-xs">km/h</p>
                  <p className="text-violet-400 text-xs mt-1">
                    {current.wind_speed_kmh < 20 ? 'Nhẹ' : current.wind_speed_kmh < 40 ? 'Vừa' : current.wind_speed_kmh < 60 ? 'Mạnh' : 'Bão'}
                  </p>
                </>
              ) : <p className="text-slate-500 text-sm">N/A</p>}
            </div>
          </div>

        {/* Time-series chart */}
        <div className="bg-slate-800/60 rounded-xl border border-slate-700 p-3">
          <div className="flex items-center justify-between mb-3">
            <p className="text-slate-400 text-xs uppercase tracking-wider">Biểu đồ 72 giờ tới</p>
            <TrendingUp size={13} className="text-slate-600" />
          </div>
          <TimeSeriesChart hourly={hourly_forecast} />
        </div>

        {/* 7-day forecast */}
        <div className="bg-slate-800/60 rounded-xl border border-slate-700 p-3">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-3">Dự báo 7 ngày</p>
          <DailyForecastStrip days={daily_forecast} />
          <div className="flex gap-3 mt-2 text-xs text-slate-500">
            <span><span className="text-cyan-400">■</span> Thấp</span>
            <span><span className="text-amber-400">■</span> Trung bình</span>
            <span><span className="text-orange-400">■</span> Cao</span>
            <span><span className="text-red-400">■</span> Nguy hiểm</span>
          </div>
        </div>

        <p className="text-slate-600 text-xs text-center">
          Dữ liệu: Open-Meteo Marine API • Cập nhật mỗi 15 phút
        </p>
      </div>
    </div>
  )
}
