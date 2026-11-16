import useCoastWatchStore from '../../store/useCoastWatchStore'

const YEARS = [2020, 2021, 2022, 2023, 2024]

export default function YearRangeSlider() {
  const { yearRange, setYearRange } = useCoastWatchStore()

  const selectedYear = yearRange.from === yearRange.to ? yearRange.from : null

  const selectYear = (year: number) => {
    setYearRange({ from: year, to: year })
  }

  const selectAll = () => {
    setYearRange({ from: YEARS[0], to: YEARS[YEARS.length - 1] })
  }

  return (
    <div className="bg-slate-800/90 backdrop-blur-sm rounded-xl border border-slate-700 p-3 w-56">
      <p className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
        Năm đường bờ biển
      </p>

      <div className="flex flex-col gap-1">
        {YEARS.map((year) => {
          const isSelected = selectedYear === year
          return (
            <button
              key={year}
              onClick={() => selectYear(year)}
              className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                isSelected
                  ? 'bg-cyan-500/20 border border-cyan-500/60 text-cyan-400'
                  : 'bg-slate-700/50 border border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }`}
            >
              <span>{year}</span>
              {isSelected && (
                <span className="text-xs text-cyan-500">◀ đang xem</span>
              )}
            </button>
          )
        })}

        <button
          onClick={selectAll}
          className={`mt-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            selectedYear === null
              ? 'bg-amber-500/20 border border-amber-500/60 text-amber-400'
              : 'bg-slate-700/50 border border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-700'
          }`}
        >
          Hiện tất cả ({YEARS[0]}–{YEARS[YEARS.length - 1]})
        </button>
      </div>
    </div>
  )
}
