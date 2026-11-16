import { useState, useEffect, useCallback, useRef } from 'react'
import { getJob } from '../services/api'
import type { ProcessingJob } from '../types'

interface UseJobPollerOptions {
  intervalMs?: number
  onCompleted?: (job: ProcessingJob) => void
  onFailed?: (job: ProcessingJob) => void
}

interface UseJobPollerReturn {
  job: ProcessingJob | null
  isPolling: boolean
  error: string | null
  startPolling: (jobId: string) => void
  stopPolling: () => void
}

export function useJobPoller(options: UseJobPollerOptions = {}): UseJobPollerReturn {
  const { intervalMs = 2000, onCompleted, onFailed } = options

  const [job, setJob] = useState<ProcessingJob | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const jobIdRef = useRef<string | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsPolling(false)
  }, [])

  const poll = useCallback(async () => {
    if (!jobIdRef.current) return

    try {
      const updatedJob = await getJob(jobIdRef.current)
      setJob(updatedJob)

      if (updatedJob.status === 'completed') {
        stopPolling()
        onCompleted?.(updatedJob)
      } else if (updatedJob.status === 'failed') {
        stopPolling()
        setError(updatedJob.error ?? 'Job thất bại')
        onFailed?.(updatedJob)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Lỗi kiểm tra job'
      setError(message)
      stopPolling()
    }
  }, [stopPolling, onCompleted, onFailed])

  const startPolling = useCallback(
    (jobId: string) => {
      jobIdRef.current = jobId
      setJob(null)
      setError(null)
      setIsPolling(true)

      // Immediate first poll
      void poll()

      intervalRef.current = setInterval(() => {
        void poll()
      }, intervalMs)
    },
    [poll, intervalMs]
  )

  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  return { job, isPolling, error, startPolling, stopPolling }
}
