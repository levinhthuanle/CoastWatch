import { useState } from 'react'
import { GitCompare, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { compareShoreLines, getShorelines } from '../../services/api'
import useCoastWatchStore from '../../store/useCoastWatchStore'
import type { ShorelineAnalysis } from '../../types'

const YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

export default function AnalysisPanel() {
  const { setActiveAnalysis } = useCoastWatchStore()
  const [fromYear, setFromYear] = useState(2019)
  const [toYear, setToYear] = useState(2024)
  const [isComparing, setIsComparing] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<ShorelineAnalysis | null>(null)

  const { data: shorelines = [] } = useQuery({
    queryKey: ['shorelines'],
    queryFn: () => getShorelines(),
  })

  const handleCompare = async () => {
    const fromShoreline = shorelines.find((s) => s.year === fromYear)
    const toShoreline = shorelines.find((s) => s.year === toYear)

    if (!fromShoreline || !toShoreline) {
      setCompareError(`Không tìm thấy dữ liệu cho năm ${fromYear} hoặc ${toYear}`)
      return
    }

    setIsComparing(true)
    setCompareError(null)
    setAnalysis(null)

    try {
      const result = await compareShoreLines(fromShoreline.id, toShoreline.id)
      setAnalysis(result as unknown as ShorelineAnalysis)
      setActiveAnalysis(result as unknown as ShorelineAnalysis)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Không thể thực hiện phân tích'
      setCompareError(message)
    } finally {
      setIsComparing(false)
    }
  }

  const fmt = (val: number | null | undefined, decimals = 2) =>
    val != null ? val.toFixed(decimals) : '--'
  return (
    <div className="h-full flex gap-4 overflow-hidden">
      {/* Controls */}
      <div className="w-56 flex-shrink-0">
        <div className="card h-full flex flex-col gap-3">
          <div className="flex items-center gap-2 text-slate-300">
            <GitCompare size={15} />
            <span className="font-medium text-sm">So sánh đường bờ</span>
          </div>

          <div>
            <label className="label">Từ năm</label>
            <select
              value={fromYear}
              onChange={(e) => setFromYear(Number(e.target.value))}
              className="input text-sm"
              disabled={isComparing}
            >
              {YEARS.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Đến năm</label>
            <select
              value={toYear}
              onChange={(e) => setToYear(Number(e.target.value))}
              className="input text-sm"
              disabled={isComparing}
            >
              {YEARS.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleCompare}
            disabled={isComparing || fromYear === toYear}
            className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isComparing ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Đang phân tích...
              </>
            ) : (
              <>
                <GitCompare size={14} />
                So sánh
              </>
            )}
          </button>

          {compareError && (
            <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-lg p-2">
              <AlertCircle size={13} className="text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-xs">{compareError}</p>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-auto">
        {analysis ? (
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle size={15} className="text-green-400" />
              <span className="text-slate-300 font-medium text-sm">
                Kết quả: {fromYear} → {toYear}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <ResultItem
                label="EPR"
                value={fmt(analysis.epr_m_per_year, 1)}
                unit="m/năm"
                positive={(analysis.epr_m_per_year ?? 0) > 0}
              />
              <ResultItem
                label="Tổng biến động"
                value={fmt(analysis.total_change_m, 0)}
                unit="m"
                positive={(analysis.total_change_m ?? 0) > 0}
              />
              <ResultItem
                label="Diện tích mất"
                value={fmt(analysis.area_lost_km2)}
                unit="km²"
                positive={false}
              />
              <ResultItem
                label="Diện tích bồi"
                value={fmt(analysis.area_gained_km2)}
                unit="km²"
                positive={true}
              />
              <ResultItem
                label="IoU Score"
                value={analysis.iou_score != null ? fmt(analysis.iou_score * 100, 1) : '--'}
                unit="%"
              />
              <ResultItem
                label="F1 Score"
                value={analysis.f1_score != null ? fmt(analysis.f1_score * 100, 1) : '--'}
                unit="%"
              />
            </div>

            {(analysis.epr_m_per_year ?? 0) < 0 && (
              <div className="mt-3 bg-red-500/10 border border-red-500/20 rounded-lg p-2.5">
                <p className="text-red-300 text-xs">
                  ⚠ Bờ biển có xu hướng <strong>xói lở</strong> với tốc độ{' '}
                  {Math.abs(analysis.epr_m_per_year!).toFixed(1)} m/năm
                </p>
              </div>
            )}
            {(analysis.epr_m_per_year ?? 0) > 0 && (
              <div className="mt-3 bg-green-500/10 border border-green-500/20 rounded-lg p-2.5">
                <p className="text-green-300 text-xs">
                  ✓ Bờ biển có xu hướng <strong>bồi tụ</strong> với tốc độ{' '}
                  {analysis.epr_m_per_year!.toFixed(1)} m/năm
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            {isComparing ? (
              <div className="text-center">
                <Loader2 size={24} className="animate-spin text-cyan-400 mx-auto mb-2" />
                <p>Đang thực hiện phân tích...</p>
              </div>
            ) : (
              <p>Chọn hai năm và nhấn "So sánh" để bắt đầu</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface ResultItemProps {
  label: string
  value: string
  unit: string
  positive?: boolean
}

function ResultItem({ label, value, unit, positive }: ResultItemProps) {
  const textColor =
    positive === true
      ? 'text-green-400'
      : positive === false
      ? 'text-red-400'
      : 'text-cyan-400'

  return (
    <div className="bg-slate-700/50 rounded-lg p-2.5">
      <p className="text-slate-500 text-xs mb-0.5">{label}</p>
      <div className="flex items-baseline gap-1">
        <span className={`font-semibold text-base ${textColor}`}>{value}</span>
        <span className="text-slate-500 text-xs">{unit}</span>
      </div>
    </div>
  )
}
