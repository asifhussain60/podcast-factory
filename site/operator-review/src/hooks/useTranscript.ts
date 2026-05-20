import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useTranscript(slug: string | undefined) {
  return useQuery({
    queryKey: ['transcript', slug],
    queryFn: () => api.getTranscript(slug!),
    enabled: !!slug,
    staleTime: Infinity,
  })
}
