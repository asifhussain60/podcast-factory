import { useState } from 'react'
import { Button } from './ui/Button'
import { Icon } from './Icons'
import type { ReviewStruct } from '../types'

interface Props {
  open: boolean
  slug: string
  review: ReviewStruct
  onClose: () => void
  onApprove: (mode: 'fire' | 'copy', commitMessage: string) => void
}

export function ApproveModal({ open, slug, review, onClose, onApprove }: Props) {
  const [mode, setMode] = useState<'fire' | 'copy'>('fire')
  const summary = buildSummary(review)
  const [msg, setMsg] = useState(`podcast(${slug}): operator transcript review — ${summary}`)

  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 z-60 bg-[rgba(8,11,20,0.7)] backdrop-blur-sm" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[540px] max-w-[92vw] z-70 rounded-[20px] border border-white/10 bg-[rgba(19,23,37,0.85)] backdrop-blur-3xl shadow-[0_18px_40px_rgba(0,0,0,0.55)] overflow-hidden">
        <div className="px-6 py-5 border-b border-white/[0.06]">
          <div className="font-display text-xl font-bold text-ink-50">Approve &amp; Resume</div>
          <div className="text-xs text-ink-200 mt-1 font-mono">{slug} · Phase 0b → Phase 0c</div>
        </div>

        <div className="px-6 py-5 flex flex-col gap-3.5">
          <SummaryCard review={review} />
          <ModeCard mode={mode} setMode={setMode} />
          <CommitMsgCard msg={msg} setMsg={setMsg} />
        </div>

        <div className="px-6 py-3.5 border-t border-white/[0.06] flex justify-between items-center" style={{ background: 'rgba(0,0,0,0.2)' }}>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={() => onApprove(mode, msg)} disabled={!review.approved}>
            <Icon name="check-circle" size="sm" />
            {mode === 'fire' ? 'Approve & Resume' : 'Approve & Copy command'}
          </Button>
        </div>
      </div>
    </>
  )
}

function SummaryCard({ review }: { review: ReviewStruct }) {
  return (
    <div className="rounded-[10px] p-3.5 border border-white/10" style={{ background: 'var(--bg-elevated)' }}>
      <div className="font-display text-[0.65rem] font-semibold uppercase tracking-widest text-ink-200 mb-2.5">
        Review summary
      </div>
      <Row label="Translation issues" v={`${review.translation_issues.length} flags`} warn={review.translation_issues.length > 0} />
      <Row label="Missing passages" v={`${review.missing_passages.length}`} muted={review.missing_passages.length === 0} />
      <Row label="Glossary additions" v={`${review.glossary.length} entries`} muted={review.glossary.length === 0} />
      <Row label="Pronunciation" v={`${review.pronunciation.length}`} muted={review.pronunciation.length === 0} />
      <Row label="AI suggestions" v={`${review.ai_suggestions.length}`} muted={review.ai_suggestions.length === 0} />
      <Row
        label="Content range §7"
        v={
          review.content_range.body_starts_at_page || review.content_range.body_ends_at_page
            ? `${review.content_range.body_starts_at_page ?? '?'} → ${review.content_range.body_ends_at_page ?? '?'}`
            : 'whole transcript'
        }
      />
    </div>
  )
}

function Row({ label, v, warn, muted }: { label: string; v: string; warn?: boolean; muted?: boolean }) {
  return (
    <div className="flex justify-between text-sm py-0.5">
      <span className="text-ink-100">{label}</span>
      <span className={`font-mono ${warn ? 'text-accent-amber' : muted ? 'text-ink-300' : 'text-ink-50'}`}>{v}</span>
    </div>
  )
}

function ModeCard({ mode, setMode }: { mode: 'fire' | 'copy'; setMode: (m: 'fire' | 'copy') => void }) {
  return (
    <div className="rounded-[10px] p-3.5 border border-white/10" style={{ background: 'var(--bg-elevated)' }}>
      <div className="font-ui font-semibold text-sm text-ink-50 mb-2">How to fire the resume?</div>
      <ModeRadio name="resume-mode" cur={mode} val="fire" set={setMode} title="Fire --approve-transcript + stream log" desc="Subprocess starts; log drawer opens; you can cancel." />
      <ModeRadio name="resume-mode" cur={mode} val="copy" set={setMode} title="Copy command to clipboard" desc="Use when running on tmux, remote, or another worktree." />
    </div>
  )
}

function ModeRadio({
  name, cur, val, set, title, desc,
}: {
  name: string; cur: 'fire' | 'copy'; val: 'fire' | 'copy'; set: (m: 'fire' | 'copy') => void; title: string; desc: string
}) {
  return (
    <label className="flex items-start gap-2 py-1 cursor-pointer">
      <input type="radio" name={name} checked={cur === val} onChange={() => set(val)} className="mt-1" style={{ accentColor: 'var(--accent-purple)' }} />
      <div>
        <div className="text-sm text-ink-100">{title}</div>
        <div className="text-[0.7rem] text-ink-200">{desc}</div>
      </div>
    </label>
  )
}

function CommitMsgCard({ msg, setMsg }: { msg: string; setMsg: (m: string) => void }) {
  return (
    <div className="rounded-[10px] p-3.5 border border-white/10" style={{ background: 'var(--bg-elevated)' }}>
      <div className="font-display text-[0.65rem] font-semibold uppercase tracking-widest text-ink-200 mb-2">
        Git commit message (auto, editable)
      </div>
      <input
        value={msg}
        onChange={(e) => setMsg(e.target.value)}
        className="w-full bg-canvas border border-white/10 rounded-md px-2.5 py-1.5 text-ink-50 font-mono text-xs"
      />
    </div>
  )
}

function buildSummary(r: ReviewStruct): string {
  const parts: string[] = []
  if (r.translation_issues.length) parts.push(`${r.translation_issues.length} flags`)
  if (r.missing_passages.length) parts.push(`${r.missing_passages.length} missing`)
  if (r.glossary.length) parts.push(`${r.glossary.length} glossary`)
  if (r.pronunciation.length) parts.push(`${r.pronunciation.length} pron`)
  const cr = r.content_range
  if (cr.body_starts_at_page || cr.body_ends_at_page) {
    parts.push(`range ${cr.body_starts_at_page ?? '?'}-${cr.body_ends_at_page ?? '?'}`)
  }
  return parts.length ? parts.join(', ') : 'no changes'
}
