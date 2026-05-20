import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useBooks() {
  return useQuery({
    queryKey: ['books'],
    queryFn: api.listBooks,
    refetchInterval: 15_000,
  })
}

export function useBook(slug: string | undefined) {
  return useQuery({
    queryKey: ['book', slug],
    queryFn: () => api.getBook(slug!),
    enabled: !!slug,
    refetchInterval: 10_000,
  })
}
