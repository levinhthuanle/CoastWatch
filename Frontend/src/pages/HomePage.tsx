import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Sidebar from '../components/Layout/Sidebar'
import CoastWatchMap from '../components/Map/CoastWatchMap'
import StatsPanel from '../components/Dashboard/StatsPanel'
import AnalysisPanel from '../components/Dashboard/AnalysisPanel'
import ShorelineChangeChart from '../components/Charts/ShorelineChangeChart'
import EPRHeatmap from '../components/Charts/EPRHeatmap'
import ChatPanel from '../components/Chat/ChatPanel'
import MarinePanel from '../components/Marine/MarinePanel'
import useCoastWatchStore from '../store/useCoastWatchStore'
import { getShorelines, getAnalyses, autoCompareAll } from '../services/api'
import { GitCompare, Loader2, CheckCircle2 } from 'lucide-react'

function AutoCompareButton() {
  const queryClient = useQueryClient()
  const [done, setDone] = useState<string | null>(null)

  const { data: shorelines = [] } = useQuery({
    queryKey: ['shorelines'],
    queryFn: () => getShorelines(),
    staleTime: 60_000,
  })
  const { data: analyses = [] } = useQuery({
    queryKey: ['analyses'],
    queryFn: () => getAnalyses(),
    staleTime: 60_000,
  })

  const mutation = useMutation({
    mutationFn: autoCompareAll,
    onSuccess: (result) => {
      setDone(result.message)
      void queryClient.invalidateQueries({ queryKey: ['analyses'] })
      void queryClient.invalidateQueries({ queryKey: ['shorelines'] })
    },
  })

  const shorelineCount = Array.isArray(shorelines) ? shorelines.length : 0
  const analysisCount = Array.isArray(analyses) ? analyses.length : 0
  const canRun = shorelineCount >= 2

  if (!canRun) return null

  // Already fully analyzed
  const expectedPairs = shorelineCount - 1
  if (analysisCount >= expectedPairs && done === null) return null

  return (
    <button
      onClick={() => { setDone(null); mutation.mutate() }}
      disabled={mutation.isPending}
      className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border transition-colors ${
        done
          ? 'border-green-500/30 text-green-400 bg-green-500/10'
          : 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20'
      }`}
    >
      {mutation.isPending ? (
        <><Loader2 size={12} className="animate-spin" /> Đang phân tích...</>
      ) : done ? (
        <><CheckCircle2 size={12} /> {done}</>
      ) : (
        <><GitCompare size={12} /> Tính biến động bờ biển</>
      )}
    </button>
  )
}

export default function HomePage() {
  const { activeView } = useCoastWatchStore()
  const [bottomPanelExpanded, setBottomPanelExpanded] = useState(false)

  if (activeView === 'chat') {
    return (
      <div className="flex h-screen bg-slate-900 overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-hidden">
          <ChatPanel />
        </div>
      </div>
    )
  }

  if (activeView === 'marine') {
    return (
      <div className="flex h-screen bg-slate-900 overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-hidden">
          <MarinePanel />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-slate-900 overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Stats bar */}
        <div className="flex-shrink-0 bg-slate-800 border-b border-slate-700 px-4 py-2">
          <StatsPanel />
        </div>

        {/* Map + bottom panel */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div
            className={`transition-all duration-300 ${bottomPanelExpanded ? 'flex-none' : 'flex-1'}`}
            style={bottomPanelExpanded ? { height: '50%' } : undefined}
          >
            <CoastWatchMap />
          </div>

          <div
            className={`flex-shrink-0 bg-slate-800 border-t border-slate-700 transition-all duration-300 ${
              bottomPanelExpanded ? 'flex-1 min-h-0' : 'h-52'
            }`}
          >
            <div className="flex items-center justify-between px-4 py-1 border-b border-slate-700">
              <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">
                Biểu đồ & Phân tích
              </span>
              <div className="flex items-center gap-2">
                <AutoCompareButton />
                <button
                  onClick={() => setBottomPanelExpanded(!bottomPanelExpanded)}
                  className="text-slate-400 hover:text-slate-200 text-xs p-1 rounded hover:bg-slate-700 transition-colors"
                >
                  {bottomPanelExpanded ? '▼ Thu nhỏ' : '▲ Mở rộng'}
                </button>
              </div>
            </div>
            <div className="p-3 h-full overflow-auto">
              <div className="flex gap-3 h-full overflow-x-auto">
                <div className="flex-1 min-w-64">
                  <ShorelineChangeChart />
                </div>
                <div className="flex-1 min-w-64">
                  <EPRHeatmap />
                </div>
                <div className="flex-1 min-w-64">
                  <AnalysisPanel />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
