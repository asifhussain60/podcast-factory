import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { IconSprite, Icon } from '../components/Icons'
import { ReadingControls } from '../components/ReadingControls'
import { AIAssistBar } from '../components/AIAssistBar'
import { TranscriptPane } from '../components/TranscriptPane'
import { ReviewPane } from '../components/ReviewPane'
import { ApproveBar } from '../components/ApproveBar'
import { ApproveModal } from '../components/ApproveModal'
import { ResumeLogDrawer } from '../components/ResumeLogDrawer'
import { FlagButton } from '../components/FlagButton'
import { CommandPalette } from '../components/CommandPalette'
import { useTranscript } from '../hooks/useTranscript'
import { useReview } from '../hooks/useReview'
import { useBook } from '../hooks/useBooks'
import { useAI, useAIBudget } from '../hooks/useAI'
import { useKeyboard } from '../hooks/useKeyboard'
import { api } from '../lib/api'
import type { AIFeature } from '../types'

export function EditorPage() {
  const { slug = '' } = useParams()
  const navigate = useNavigate()
  const book = useBook(slug)
  const transcript = useTranscript(slug)
  const { review, setReview, saveStatus, externalChange, reloadFromDisk } = useReview(slug)
  const { run, loading } = useAI(slug)
  const budget = useAIBudget(slug)

  const [arabicOn, setArabicOn] = useState(false)
  const [diffMode, setDiffMode] = useState(false)
  const [selectionRect, setSelectionRect] = useState<DOMRect | null>(null)
  const [selectedText, setSelectedText] = useState('')
  const [selectedPage, setSelectedPage] = useState(0)

  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteMode, setPaletteMode] = useState<'search' | 'page'>('search')

  const [approveOpen, setApproveOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Keyboard shortcuts
  useKeyboard([
    { cmd: true, key: 'f', handler: () => { setPaletteMode('search'); setPaletteOpen(true) } },
    { cmd: true, key: 'p', handler: () => { setPaletteMode('page'); setPaletteOpen(true) } },
    { cmd: true, key: 'd', handler: () => setDiffMode((v) => !v) },
    { cmd: true, key: 'k', handler: () => handleAI('preflight') },
    { cmd: true, key: 'Enter', handler: () => setApproveOpen(true) },
    { cmd: true, key: '=', handler: () => {/* size handled by ReadingControls */} },
    { cmd: true, key: '-', handler: () => {/* size handled by ReadingControls */} },
    { key: 'Escape', handler: () => {
      setPaletteOpen(false)
      setApproveOpen(false)
      setDrawerOpen(false)
      setSelectionRect(null)
    }},
  ])

  const handleAI = async (feature: string) => {
    if (feature === 'arabic') {
      setArabicOn((v) => !v)
      // first toggle on: also scan (cached)
      if (!arabicOn) {
        await run('arabic' as AIFeature)
      }
      return
    }
    await run(feature as AIFeature)
  }

  const handleFlag = () => {
    if (!selectedText) return
    setReview((prev) => ({
      ...prev,
      translation_issues: [
        ...prev.translation_issues,
        { page: selectedPage, quote: selectedText, note: '', recurring_pattern: false },
      ],
    }))
    setSelectionRect(null)
    window.getSelection()?.removeAllRanges()
  }

  const handleApprove = async (mode: 'fire' | 'copy', commitMessage: string) => {
    setApproveOpen(false)
    try {
      const r = await api.approve(slug, { mode, commit_message: commitMessage })
      if (mode === 'copy' && r.command) {
        await navigator.clipboard.writeText(r.command).catch(() => {})
      } else if (mode === 'fire') {
        setDrawerOpen(true)
      }
    } catch (e) {
      // TODO: toast
      console.error(e)
    }
  }

  return (
    <>
      <IconSprite />
      <div className="absolute inset-0 flex flex-col overflow-hidden">
        <header
          className="px-5 py-3.5 flex justify-between items-center backdrop-blur-xl border-b"
          style={{ background: 'var(--surface-elevated)', borderColor: 'var(--border-default)' }}
        >
          <div className="flex items-center gap-3.5">
            <button
              onClick={() => navigate('/')}
              className="p-2 rounded-[10px] border border-white/10 text-ink-100 hover:bg-[rgba(30,41,59,0.35)] hover:text-white transition"
              title="Back to books"
            >
              <Icon name="arrow-left" size="sm" />
            </button>
            <div>
              <div className="font-display font-semibold text-base text-ink-50">{slug}</div>
              <div className="text-xs text-ink-200 font-mono">
                {book.data ? `${book.data.page_count} pages · OCR ${book.data.ocr_confidence ?? '?'}% · ${book.data.phase_status}` : 'loading…'}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2.5 text-xs">
            <span
              className="px-2.5 py-1 rounded-pill border text-[0.7rem] flex items-center gap-1.5"
              style={{
                background: saveStatus === 'saved' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                borderColor: saveStatus === 'saved' ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)',
                color: saveStatus === 'saved' ? 'var(--accent-emerald)' : 'var(--accent-amber)',
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: saveStatus === 'saved' ? 'var(--accent-emerald)' : 'var(--accent-amber)' }} />
              {saveStatus === 'saved' ? 'Saved' : saveStatus === 'saving' ? 'Saving…' : saveStatus === 'error' ? 'Save failed' : 'idle'}
            </span>
          </div>
        </header>

        {externalChange && (
          <div className="bg-accent-amber/10 border-b border-accent-amber/30 px-5 py-2 text-xs text-accent-amber flex justify-between items-center">
            <span>operator-review.md was changed externally (e.g., VS Code). Reload from disk?</span>
            <div className="flex gap-2">
              <button
                onClick={() => reloadFromDisk()}
                className="px-2.5 py-0.5 rounded border border-accent-amber/40 text-accent-amber hover:bg-accent-amber/10"
              >
                Reload
              </button>
            </div>
          </div>
        )}

        <ReadingControls />
        <AIAssistBar
          budget={budget.data}
          loading={loading}
          onAction={handleAI}
          arabicOn={arabicOn}
        />

        <div className="flex-1 grid grid-cols-12 overflow-hidden">
          <div className="col-span-7 border-r border-white/10">
            {transcript.isLoading && <div className="p-10 text-ink-200">Loading transcript…</div>}
            {transcript.error && (
              <div className="p-10 text-accent-rose font-mono text-sm">
                Error: {(transcript.error as Error).message}
              </div>
            )}
            {transcript.data && (
              <TranscriptPane
                text={transcript.data.text}
                pageIndex={transcript.data.page_index}
                arabicHighlight={arabicOn}
                diffMode={diffMode}
                onSelectText={(t, page, rect) => {
                  setSelectedText(t)
                  setSelectedPage(page)
                  setSelectionRect(rect)
                }}
              />
            )}
          </div>
          <div className="col-span-5 flex flex-col">
            <ReviewPane review={review} setReview={setReview} saveStatus={saveStatus} />
            <ApproveBar
              saveStatus={saveStatus}
              flagCount={review.translation_issues.length + review.missing_passages.length}
              onApprove={() => setApproveOpen(true)}
            />
          </div>
        </div>
      </div>

      <FlagButton rect={selectionRect} onFlag={handleFlag} />

      <CommandPalette
        open={paletteOpen}
        mode={paletteMode}
        pageIndex={transcript.data?.page_index ?? []}
        transcript={transcript.data?.text ?? ''}
        onClose={() => setPaletteOpen(false)}
        onJump={(page) => {
          // simple jump: find the page marker DOM element and scroll into view
          const el = document.querySelector(`.page-marker[data-page="${page}"]`)
          el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }}
      />

      <ApproveModal
        open={approveOpen}
        slug={slug}
        review={review}
        onClose={() => setApproveOpen(false)}
        onApprove={handleApprove}
      />

      <ResumeLogDrawer open={drawerOpen} slug={slug} onClose={() => setDrawerOpen(false)} />
    </>
  )
}
