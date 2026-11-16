import { create } from 'zustand'
import type { Shoreline, ShorelineAnalysis, ShorelineForecast, MapStyle } from '../types'

interface CoastWatchState {
  // Data
  shorelines: Shoreline[]
  selectedShorelineIds: number[]
  activeAnalysis: ShorelineAnalysis | null
  activeForecast: ShorelineForecast | null

  // UI State
  activeYear: number
  mapStyle: MapStyle
  isLoading: boolean
  activeView: 'dashboard' | 'chat' | 'marine'
  yearRange: { from: number; to: number }
  activeMethod: Shoreline['method'] | 'all'

  // Actions
  setShorelines: (shorelines: Shoreline[]) => void
  toggleShorelineSelection: (id: number) => void
  setSelectedShorelineIds: (ids: number[]) => void
  setActiveAnalysis: (analysis: ShorelineAnalysis | null) => void
  setActiveForecast: (forecast: ShorelineForecast | null) => void
  setActiveYear: (year: number) => void
  setMapStyle: (style: MapStyle) => void
  setIsLoading: (loading: boolean) => void
  setActiveView: (view: CoastWatchState['activeView']) => void
  setYearRange: (range: { from: number; to: number }) => void
  setActiveMethod: (method: CoastWatchState['activeMethod']) => void
  clearSelection: () => void
}

const useCoastWatchStore = create<CoastWatchState>((set) => ({
  // Initial state
  shorelines: [],
  selectedShorelineIds: [],
  activeAnalysis: null,
  activeForecast: null,
  activeYear: 2024,
  mapStyle: 'dark',
  isLoading: false,
  activeView: 'dashboard',
  yearRange: { from: 2019, to: 2024 },
  activeMethod: 'all',

  // Actions
  setShorelines: (shorelines) => set({ shorelines }),

  toggleShorelineSelection: (id) =>
    set((state) => {
      const isSelected = state.selectedShorelineIds.includes(id)
      if (isSelected) {
        return { selectedShorelineIds: state.selectedShorelineIds.filter((s) => s !== id) }
      }
      if (state.selectedShorelineIds.length >= 2) {
        return { selectedShorelineIds: [state.selectedShorelineIds[1], id] }
      }
      return { selectedShorelineIds: [...state.selectedShorelineIds, id] }
    }),

  setSelectedShorelineIds: (ids) => set({ selectedShorelineIds: ids }),
  setActiveAnalysis: (analysis) => set({ activeAnalysis: analysis }),

  setActiveForecast: (forecast) => set({ activeForecast: forecast }),

  setActiveYear: (year) => set({ activeYear: year }),

  setMapStyle: (style) => set({ mapStyle: style }),

  setIsLoading: (loading) => set({ isLoading: loading }),

  setActiveView: (view) => set({ activeView: view }),

  setYearRange: (range) => set({ yearRange: range }),

  setActiveMethod: (method) => set({ activeMethod: method }),

  clearSelection: () => set({ selectedShorelineIds: [], activeAnalysis: null }),
}))

export default useCoastWatchStore
