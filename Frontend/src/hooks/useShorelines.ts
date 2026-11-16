import { useQuery } from '@tanstack/react-query'
import { getShorelines } from '../services/api'
import type { ShorelineFilters } from '../types'

export function useShorelines(filters?: ShorelineFilters) {
  return useQuery({
    queryKey: ['shorelines', filters],
    queryFn: () => getShorelines(filters),
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  })
}

export function useShorelinesByYearRange(from: number, to: number) {
  const singleYear = from === to ? from : undefined
  return useQuery({
    queryKey: ['shorelines', 'range', from, to],
    queryFn: () =>
      singleYear !== undefined
        ? getShorelines({ year: singleYear })
        : getShorelines({ year_from: from, year_to: to }),
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  })
}
