import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { Icon } from './Icons'
import { cn } from '../lib/utils'

interface Props {
  text: string
  pageIndex: { page: number; offset: number }[]
  flaggedPages?: number[]            // page numbers with at least 1 flag
  arabicHighlight?: boolean          // if true wrap arabic-term spans
  diffMode?: boolean                 // if true, show .raw vs .refined diff
  onSelectText?: (text: string, page: number, rect: DOMRect) => void
  onScrollPage?: (page: number) => void
}

// Detect transliterated Arabic terms heuristically (presence of macron, hamza, ʿayn, etc.)
const ARABIC_HINTS = /[āīūʿʾḥḍṣṭẓṛḏǧ]|al-[a-z]/

// Split text on <!-- page N --> markers and render each page as its own block.
export function TranscriptPane({
  text,
  pageIndex,
  arabicHighlight = false,
  diffMode = false,
  onSelectText,
  onScrollPage,
}: Props) {
  const bodyRef = useRef<HTMLDivElement>(null)
  const [currentPage, setCurrentPage] = useState<number>(pageIndex[0]?.page ?? 1)

  // Build page chunks
  const pages = useMemo(() => {
    if (pageIndex.length === 0) {
      return [{ page: 1, text: text }]
    }
    const out: { page: number; text: string }[] = []
    for (let i = 0; i < pageIndex.length; i++) {
      const start = pageIndex[i].offset
      const end = i + 1 < pageIndex.length ? pageIndex[i + 1].offset : text.length
      out.push({ page: pageIndex[i].page, text: text.slice(start, end) })
    }
    return out
  }, [text, pageIndex])

  // Selection → callback
  useEffect(() => {
    function onMouseUp() {
      const sel = window.getSelection()
      if (!sel || sel.rangeCount === 0) return
      const t = sel.toString().trim()
      if (t.length < 5 || t.length > 400) return
      const range = sel.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      // Find which page marker contains the selection
      const ancestor = range.commonAncestorContainer
      let el: HTMLElement | null = ancestor.nodeType === 3 ? ancestor.parentElement : (ancestor as HTMLElement)
      while (el && !el.dataset?.page) el = el.parentElement
      const page = el?.dataset?.page ? parseInt(el.dataset.page) : currentPage
      onSelectText?.(t, page, rect)
    }
    const node = bodyRef.current
    node?.addEventListener('mouseup', onMouseUp)
    return () => node?.removeEventListener('mouseup', onMouseUp)
  }, [onSelectText, currentPage])

  // Scroll tracker
  useEffect(() => {
    const node = bodyRef.current
    if (!node) return
    function onScroll() {
      if (!node) return
      const markers = node.querySelectorAll<HTMLElement>('.page-marker')
      let cur = pageIndex[0]?.page ?? 1
      for (const m of Array.from(markers)) {
        if (m.offsetTop - node.scrollTop < 120) cur = parseInt(m.dataset.page!)
      }
      if (cur !== currentPage) {
        setCurrentPage(cur)
        onScrollPage?.(cur)
      }
    }
    node.addEventListener('scroll', onScroll)
    return () => node.removeEventListener('scroll', onScroll)
  }, [currentPage, pageIndex, onScrollPage])

  return (
    <div className="flex flex-col h-full reader-bg relative">
      <div className="px-4 py-2.5 bg-black/15 border-b border-white/[0.06] flex justify-between items-center sticky top-0 z-20 backdrop-blur-md">
        <div className="flex items-center gap-2 text-xs reader-text" style={{ color: 'var(--reader-text-muted)' }}>
          <span
            className="font-mono px-2 py-0.5 rounded-pill border"
            style={{
              background: 'rgba(0,212,255,0.1)',
              borderColor: 'var(--border-cyan)',
              color: 'var(--accent-cyan)',
            }}
          >
            page {currentPage} / {pages[pages.length - 1]?.page ?? 1}
          </span>
        </div>
        <div className="flex gap-2 items-center text-[0.7rem]" style={{ color: 'var(--reader-text-muted)' }}>
          <Kbd>Cmd</Kbd>
          <Kbd>L</Kbd>
          <span>flag</span>
        </div>
      </div>

      <div ref={bodyRef} className="flex-1 overflow-y-auto scroll-thin py-10 reader-bg">
        <div
          className="mx-auto px-8 reader-text"
          style={{
            maxWidth: 'var(--reader-content-width)',
            fontSize: 'var(--reader-font-size)',
            lineHeight: 'var(--reader-line-height)',
          }}
        >
          {pages.map((p, idx) => (
            <PageBlock
              key={p.page}
              page={p.page}
              text={p.text}
              first={idx === 0}
              arabicHighlight={arabicHighlight}
              diffMode={diffMode}
            />
          ))}
        </div>
      </div>

      {/* Floating page indicator */}
      <div
        className="absolute bottom-5 left-5 flex items-center gap-2 px-3.5 py-2 rounded-[10px] border backdrop-blur-xl font-mono text-xs shadow-lg z-10"
        style={{
          background: 'var(--surface-elevated)',
          borderColor: 'var(--border-default)',
          color: 'var(--text-secondary)',
        }}
      >
        <span style={{ color: 'var(--text-tertiary)' }}>page</span>
        <span className="text-accent-cyan font-semibold">{currentPage}</span>
        <span style={{ color: 'var(--text-tertiary)' }}>of {pages[pages.length - 1]?.page ?? 1}</span>
      </div>
    </div>
  )
}

function PageBlock({
  page,
  text,
  first,
  arabicHighlight,
  diffMode,
}: {
  page: number
  text: string
  first: boolean
  arabicHighlight: boolean
  diffMode: boolean
}) {
  // Naive paragraph split; in real app could parse markdown more carefully.
  const paragraphs = text
    .replace(/<!--\s*page\s+\d+\s*-->/g, '')
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)

  const markerStyle: CSSProperties = first
    ? { borderTop: 'none', paddingTop: 0, marginTop: 0 }
    : { borderTop: '1px dashed rgba(167,139,250,0.25)', paddingTop: '1.5rem', marginTop: '2rem', position: 'relative' }

  return (
    <div className="page-marker" data-page={page} style={markerStyle}>
      {!first && (
        <span
          className="absolute -top-3.5 right-0 px-2.5 py-0.5 rounded-md font-mono text-[0.68rem] border"
          style={{
            background: 'var(--reader-bg)',
            color: 'var(--reader-text-muted)',
            borderColor: 'var(--border-soft)',
            top: '-0.9rem',
          }}
        >
          p. {page}
        </span>
      )}
      {paragraphs.map((p, i) => (
        <Paragraph key={i} text={p} arabicHighlight={arabicHighlight} diffMode={diffMode} />
      ))}
    </div>
  )
}

function Paragraph({
  text,
  arabicHighlight,
  diffMode,
}: {
  text: string
  arabicHighlight: boolean
  diffMode: boolean
}) {
  // Heuristic Arabic highlight: tokenize on word boundaries, wrap matches
  if (!arabicHighlight || !ARABIC_HINTS.test(text)) {
    return <p style={{ margin: '0 0 1em' }}>{text}</p>
  }
  const tokens = text.split(/(\s+)/)
  return (
    <p style={{ margin: '0 0 1em' }}>
      {tokens.map((t, i) =>
        ARABIC_HINTS.test(t) && t.match(/[A-Za-zāīūʿʾḥḍṣṭẓṛḏǧ]/) ? (
          <span
            key={i}
            className="arabic-term"
            style={{
              background:
                'linear-gradient(180deg, transparent 65%, color-mix(in srgb, var(--reader-arabic) 22%, transparent) 65%)',
              padding: '0 0.1em',
              cursor: 'pointer',
            }}
          >
            {t}
          </span>
        ) : (
          t
        ),
      )}
    </p>
  )
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="inline-flex items-center justify-center min-w-[1.5rem] h-[1.5rem] px-1.5 rounded-md font-mono text-[0.7rem]"
      style={{
        background: 'rgba(255,255,255,0.06)',
        border: '1px solid rgba(255,255,255,0.12)',
        color: 'var(--text-secondary)',
      }}
    >
      {children}
    </span>
  )
}
