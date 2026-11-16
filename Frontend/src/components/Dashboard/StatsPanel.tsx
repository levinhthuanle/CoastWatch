import { Layers, CalendarRange, TrendingDown, TrendingUp, ArrowLeftRight, Satellite } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getShorelines, getAnalyses } from '../../services/api'

function Stat({ label, value, unit, icon, color, sub }: {
  label: string
  value: string
  unit?: string
  icon: React.ReactNode
  color: string
  sub?: string
}) {
  return (
    <div className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border bg-opacity-10 ${color}`}>
      <div className="flex-shrink-0 opacity-80">{icon}</div>
      <div className="min-w-0">
        <p className="text-slate-500 text-xs leading-tight truncate">{label}</p>
        <div className="flex items-baseline gap-1">
          <span className="font-semibold text-sm text-slate-100">{value}</span>
          {unit && <span className="text-slate-500 text-xs">{unit}</span>}
        </div>
        {sub && <p className="text-xs mt-0.5 truncate opacity-70" style={{ color: 'inherit' }}>{sub}</p>}
      </div>
    </div>
  )
}

function Divider() {
  return <div className="w-px h-8 bg-slate-700 flex-shrink-0" />
}

export default function StatsPanel() {
  const { data: shorelineRes } = useQuery({
    queryKey: ['shorelines'],
    queryFn: () => getShorelines(),
    staleTime: 60_000,
  })
  const { data: analysisRes } = useQuery({
    queryKey: ['analyses'],
    queryFn: () => getAnalyses(),
    staleTime: 60_000,
  })

  const shorelines: Array<{ year: number; method: string }> = Array.isArray(shorelineRes) ? shorelineRes : []
  const analyses: Array<{ epr_m_per_year: number | null }> = Array.isArray(analysisRes) ? analysisRes : []

  const count = shorelines.length
  const years = shorelines.map(s => s.year).sort((a, b) => a - b)
  const yearLabel = years.length >= 2 ? `${years[0]}–${years[years.length - 1]}` : years[0]?.toString() ?? '--'

  const methods = [...new Set(shorelines.map(s => s.method))]
  const methodLabel = methods.includes('coastsat') ? 'CoastSat / Sentinel-2'
    : methods.includes('open_source') ? 'GSHHG baseline'
    : '--'

  const eprs = analyses
    .map(a => a.epr_m_per_year)
    .filter((v): v is number => v !== null)
  const avgEpr = eprs.length > 0 ? eprs.reduce((a, b) => a + b, 0) / eprs.length : null
  const minEpr = eprs.length > 0 ? Math.min(...eprs) : null
  const maxEpr = eprs.length > 0 ? Math.max(...eprs) : null

  return (
    <div className="flex items-center gap-2 overflow-x-auto">
      <Stat
        label="Đường bờ biển"
        value={count > 0 ? String(count) : '--'}
        unit={count > 0 ? 'năm' : undefined}
        icon={<Layers size={14} className="text-cyan-400" />}
        color="border-cyan-500/20 bg-cyan-500/5"
        sub={count > 0 ? yearLabel : 'Chưa có dữ liệu'}
      />

      <Divider />

      <Stat
        label="Nguồn dữ liệu"
        value={methodLabel}
        icon={<Satellite size={14} className="text-violet-400" />}
        color="border-violet-500/20 bg-violet-500/5"
        sub={count > 0 ? `${count} snapshot` : undefined}
      />

      <Divider />

      <Stat
        label="Khoảng thời gian"
        value={years.length >= 2 ? yearLabel : '--'}
        icon={<CalendarRange size={14} className="text-amber-400" />}
        color="border-amber-500/20 bg-amber-500/5"
        sub={years.length >= 2 ? `${years.length} năm dữ liệu` : 'Chưa đủ dữ liệu'}
      />

      {avgEpr !== null && (
        <>
          <Divider />
          <Stat
            label="EPR trung bình"
            value={avgEpr.toFixed(1)}
            unit="m/năm"
            icon={<ArrowLeftRight size={14} className="text-cyan-400" />}
            color="border-cyan-500/20 bg-cyan-500/5"
            sub={avgEpr < 0 ? 'Xói lở' : 'Bồi tụ'}
          />
          <Stat
            label="Xói lở nhất"
            value={minEpr!.toFixed(1)}
            unit="m/năm"
            icon={<TrendingDown size={14} className="text-red-400" />}
            color="border-red-500/20 bg-red-500/5"
          />
          <Stat
            label="Bồi tụ nhất"
            value={maxEpr!.toFixed(1)}
            unit="m/năm"
            icon={<TrendingUp size={14} className="text-green-400" />}
            color="border-green-500/20 bg-green-500/5"
          />
        </>
      )}
    </div>
  )
}
