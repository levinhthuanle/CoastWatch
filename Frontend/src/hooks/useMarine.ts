import { useQuery } from '@tanstack/react-query'
import { getMarineCurrentConditions, getMarineHistorical } from '../services/api'
import type { MarineCurrentResponse } from '../types'

export function useMarineCurrent() {
  return useQuery<MarineCurrentResponse>({
    queryKey: ['marine-current'],
    queryFn: getMarineCurrentConditions,
    staleTime: 10 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useMarineHistorical(days = 30) {
  return useQuery({
    queryKey: ['marine-historical', days],
    queryFn: () => getMarineHistorical(days),
    staleTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}
