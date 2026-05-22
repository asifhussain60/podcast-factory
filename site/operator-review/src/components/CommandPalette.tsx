import { useState, useEffect, useMemo, useRef } from 'react'
import Fuse from 'fuse.js'
import { Icon } from './Icons'

type Mode = 'search' | 'page'

interface Props {
  open: boolean
  mode: Mode
  pageIndex: { page: number; offset: number }[]
  transcript: string
  onClose: () => void
  onJump: (page: number) => void
}

interface Hit {
  page: number
  snippet: string
}

export function CommandPalette({ open, mode, pageIndex, transcript, onClose, onJump }: Props) {
  const [q, setQ] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setQ('')
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open, mode])

  // Build page-anchored snippets (~120 chars per page) for fuzzy search
  const snippets: Hit[] = useMemo(() => {
    if (pageIndex.length === 0) return []
    const out: Hit[] = []
    for (let i = 0; i < pageIndex.length; i++) {
      const start = pageIndex[i].offset
      const end = i + 1 < pageIndex.length ? pageIndex[i + 1].offset : transcript.length
      const text = transcript
        .slice(start, end)
        .replace(/<!--[^>]*-->/g, '')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 140)
      out.push({ page: pageIndex[i].page, snippet: text })
    }
    return out
  }, [pageIndex, transcript])

  const fuse = useMemo(() => new Fuse(snippets, { keys: ['snippet'], threshold: 0.4 }), [snippets])

  const results: Hit[] = useMemo(() => {
    if (!q.trim()) return snippets.slice(0, 12)
    if (mode === 'page') {
      const n = parseInt(q)
      if (!Number.isNaN(n)) {
        return snippets.filter((s) => s.page === n).concat(snippets.slice(0, 5))
      }
    }
    return fuse.search(q).map((r) => r.item).slice(0, 12)
  }, [q, snippets, fuse, mode])

  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 z-60 bg-[rgba(8,11,20,0.7)] backdrop-blur-sm" onClick={onClose} />
      <div className="fixed left-1/2 top-[22%] -translate-x-1/2 w-[640px] max-w-[90vw] z-70 rounded-[14px] border border-white/10 bg-[rgba(19,23,37,0.85)] backdrop-blur-3xl shadow-[0_18px_40px_rgba(0,0,0,0.55)] overflow-hidden">
        <div className="px-4 py-3.5 border-b border-white/[0.06] flex items-center gap-3">
          <Icon name={mode === 'page' ? 'page' : 'search'} className="text-accent-cyan" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={mode === 'page' ? 'Jump to page... (number or section name)' : 'Search the transcript...'}
            className="flex-1 bg-transparent text-ink-50 placeholder-ink-200 outline-none text-base font-ui"
          />
          <span
            className="inline-flex items-center justify-center px-2 h-6 rounded-md font-mono text-[0.68rem]"
            style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', color: 'var(--text-secondary)' }}
          >
            ESC
          </span>
        </div>
        <div className="max-h-[360px] overflow-y-auto py-1">
          {results.length === 0 && <div className="py-8 text-center text-ink-200 text-sm">No matches</div>}
          {results.map((h, i) => (
            <button
              key={`${h.page}-${i}`}
              onClick={() => {
                onJump(h.page)
                onClose()
              }}
              className="w-full px-4 py-2.5 flex items-center gap-3.5 cursor-pointer hover:bg-[rgba(45,55,72,0.45)] transition"
            >
              <span className="font-mono text-xs text-accent-cyan min-w-[3.5rem] text-left">p. {h.page}</span>
              <span className="text-sm text-ink-100 truncate flex-1 text-left">{h.snippet}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  )
}
