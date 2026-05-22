import { useEffect, useState, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ReviewStruct } from '../types'
import { localStore, reviewDraftKey } from '../lib/utils'
import { useDebouncedValue } from './useDebounce'

const EMPTY: ReviewStruct = {
  schema_version: 1,
  book_slug: '',
  translation_issues: [],
  missing_passages: [],
  glossary: [],
  pronunciation: [],
  free_form_comments: '',
  content_range: { body_starts_at_page: null, body_ends_at_page: null },
  approved: false,
  ai_suggestions: [],
}

interface UseReviewResult {
  review: ReviewStruct
  setReview: (updater: (prev: ReviewStruct) => ReviewStruct) => void
  saveStatus: 'idle' | 'saving' | 'saved' | 'error'
  saveError: string | null
  externalChange: boolean
  reloadFromDisk: () => Promise<void>
  forceSave: () => Promise<void>
}

/**
 * Dual-debounced auto-save:
 *   - every keystroke → localStorage draft (~immediate)
 *   - ~2 sec idle → PUT to backend → operator-review.md on disk
 * External-edit detection via mtime polling every 5 sec.
 */
export function useReview(slug: string): UseReviewResult {
  const draftKey = reviewDraftKey(slug)

  // Initial load — react-query fetches server-side state once
  const { data: serverReview } = useQuery({
    queryKey: ['review', slug],
    queryFn: () => api.getReview(slug),
    staleTime: Infinity,  // we control freshness ourselves via mtime polling
  })

  // Local state — seeded from localStorage draft if present, else server
  const [review, setReviewState] = useState<ReviewStruct>(() => {
    const draft = localStore.get<ReviewStruct>(draftKey)
    if (draft) return draft
    return { ...EMPTY, book_slug: slug }
  })

  useEffect(() => {
    if (serverReview && !localStore.get(draftKey)) {
      setReviewState({ ...serverReview, book_slug: slug })
    }
  }, [serverReview, slug, draftKey])

  // Debounced state for backend PUT (~2 sec idle)
  const debouncedReview = useDebouncedValue(review, 2000)

  // Save status state
  const [saveStatus, setSaveStatus] = useState<UseReviewResult['saveStatus']>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)
  const lastSavedHash = useRef<string>('')

  // Persist to localStorage every change (~immediate)
  useEffect(() => {
    localStore.set(draftKey, review)
  }, [review, draftKey])

  // Push to backend on debounce
  useEffect(() => {
    const hash = JSON.stringify(debouncedReview)
    if (hash === lastSavedHash.current) return
    if (!debouncedReview.book_slug) return
    setSaveStatus('saving')
    api
      .putReview(slug, debouncedReview)
      .then(() => {
        lastSavedHash.current = hash
        setSaveStatus('saved')
        setSaveError(null)
      })
      .catch((e: Error) => {
        setSaveStatus('error')
        setSaveError(e.message)
      })
  }, [debouncedReview, slug])

  const setReview = useCallback(
    (updater: (prev: ReviewStruct) => ReviewStruct) => {
      setReviewState((prev) => updater(prev))
    },
    [],
  )

  const reloadFromDisk = useCallback(async () => {
    const fresh = await api.getReview(slug)
    setReviewState({ ...fresh, book_slug: slug })
    localStore.remove(draftKey)
  }, [slug, draftKey])

  const forceSave = useCallback(async () => {
    await api.putReview(slug, review)
    lastSavedHash.current = JSON.stringify(review)
  }, [slug, review])

  // External-edit detection: poll mtime every 5 sec
  const [externalChange, setExternalChange] = useState(false)
  useEffect(() => {
    let cancelled = false
    let lastKnownMtime = serverReview?.mtime
    const t = setInterval(() => {
      api.getMtime(slug).then((r) => {
        if (cancelled) return
        if (r.mtime && lastKnownMtime && r.mtime > lastKnownMtime + 1) {
          // file changed externally (write outside the app's last save)
          setExternalChange(true)
        }
        if (r.mtime) lastKnownMtime = r.mtime
      }).catch(() => {})
    }, 5000)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [slug, serverReview?.mtime])

  return {
    review,
    setReview,
    saveStatus,
    saveError,
    externalChange,
    reloadFromDisk,
    forceSave,
  }
}
