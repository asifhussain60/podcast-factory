import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { AIFeature, AIResult } from '../types'

/**
 * Unified hook for all 10 P25.7 AI features.
 * Returns `run(feature, params)` + a per-feature loading flag.
 */
export function useAI(slug: string) {
  const [loading, setLoading] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<AIResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(
    async <T = unknown>(feature: AIFeature, params: Record<string, unknown> = {}, forceRefresh = false): Promise<AIResult<T> | null> => {
      setLoading(feature)
      setError(null)
      try {
        const r = await api.ai<T>(slug, feature, params, forceRefresh)
        setLastResult(r as AIResult)
        return r
      } catch (e) {
        setError((e as Error).message)
        return null
      } finally {
        setLoading(null)
      }
    },
    [slug],
  )

  return { run, loading, lastResult, error }
}

export function useAIBudget(slug: string | undefined) {
  return useQuery({
    queryKey: ['ai-budget', slug],
    queryFn: () => api.aiBudget(slug!),
    enabled: !!slug,
    refetchInterval: 30_000,
  })
}
