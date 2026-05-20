import type {
  AIBudget,
  AIFeature,
  AIResult,
  BooksList,
  BookSummary,
  ReviewStruct,
  TranscriptResponse,
} from '../types'

// Same-origin via Vite proxy (/api/* → http://localhost:8766/api/*).
// In production the SPA could be served by the FastAPI backend directly
// or via a Cloudflare worker mirroring the journal pattern.
const BASE = ''

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(new Error('timeout')), 60_000)
  let resp: Response
  try {
    resp = await fetch(BASE + path, {
      credentials: 'include',
      signal: ctl.signal,
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } finally {
    clearTimeout(timer)
  }
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    const err = new Error(`HTTP ${resp.status}: ${text.slice(0, 400)}`) as Error & {
      status?: number
    }
    err.status = resp.status
    throw err
  }
  return (await resp.json()) as T
}

export const api = {
  listBooks: () => http<BooksList>('/api/books'),

  getBook: (slug: string) => http<BookSummary>(`/api/books/${slug}`),

  getTranscript: (slug: string) =>
    http<TranscriptResponse>(`/api/books/${slug}/transcript`),

  getReview: (slug: string) => http<ReviewStruct>(`/api/books/${slug}/review`),

  putReview: (slug: string, body: ReviewStruct) =>
    http<{ ok: boolean; slug: string; mtime: number; bytes_written: number }>(
      `/api/books/${slug}/review`,
      { method: 'PUT', body: JSON.stringify(body) },
    ),

  getMtime: (slug: string) =>
    http<{ exists: boolean; mtime: number | null }>(`/api/books/${slug}/mtime`),

  approve: (slug: string, body: { mode: 'fire' | 'copy'; commit_message?: string }) =>
    http<{
      ok: boolean
      mode: string
      pid?: number
      command?: string
      cwd?: string
      git: { committed: boolean; message?: string; stderr?: string; error?: string }
    }>(`/api/books/${slug}/approve`, { method: 'POST', body: JSON.stringify(body) }),

  cancelResume: (slug: string) =>
    http<{ ok: boolean; cancelled: boolean }>(`/api/books/${slug}/resume-log`, {
      method: 'DELETE',
    }),

  ai: <T = unknown>(slug: string, feature: AIFeature, params: Record<string, unknown> = {}, forceRefresh = false) =>
    http<AIResult<T>>(`/api/books/${slug}/ai/${feature}`, {
      method: 'POST',
      body: JSON.stringify({ params, force_refresh: forceRefresh }),
    }),

  aiBudget: (slug: string) => http<AIBudget>(`/api/books/${slug}/ai/budget`),
}

/**
 * Open an SSE connection to the resume log for a book.
 * Returns an EventSource the caller closes when done.
 */
export function openResumeLog(slug: string): EventSource {
  return new EventSource(`/api/books/${slug}/resume-log`)
}
