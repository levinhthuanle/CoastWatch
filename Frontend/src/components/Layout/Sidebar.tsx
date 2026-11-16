import {
  BarChart2,
  MessageCircle,
  Waves,
} from 'lucide-react'
import useCoastWatchStore from '../../store/useCoastWatchStore'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart2 },
  { id: 'marine', label: 'Biển / Sóng', icon: Waves },
  { id: 'chat', label: 'Trợ lý AI', icon: MessageCircle },
] as const

export default function Sidebar() {
  const { activeView, setActiveView } = useCoastWatchStore()

  return (
    <aside className="w-56 flex-shrink-0 bg-slate-800 border-r border-slate-700 flex flex-col overflow-hidden">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-slate-700 flex items-center gap-2.5">
        <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center flex-shrink-0">
          <Waves size={18} className="text-white" />
        </div>
        <div>
          <p className="text-white font-semibold text-sm leading-tight">CoastWatch</p>
          <p className="text-slate-400 text-xs">Giám sát bờ biển</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="px-2 py-3 flex-1">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveView(id)}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg mb-0.5 text-sm font-medium transition-colors ${
              activeView === id
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </nav>

      {/* Bottom info */}
      <div className="px-3 py-2 border-t border-slate-700 text-center">
        <p className="text-slate-600 text-xs">Cửa Tùng, Quảng Trị</p>
        <p className="text-slate-700 text-xs">v1.0.0</p>
      </div>
    </aside>
  )
}
