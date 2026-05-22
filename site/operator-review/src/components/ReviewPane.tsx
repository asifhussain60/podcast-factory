import type { ReviewStruct, FlagRow } from '../types'
import { ReviewSection } from './ReviewSection'
import { Icon } from './Icons'

interface Props {
  review: ReviewStruct
  setReview: (updater: (prev: ReviewStruct) => ReviewStruct) => void
  saveStatus: 'idle' | 'saving' | 'saved' | 'error'
}

export function ReviewPane({ review, setReview, saveStatus }: Props) {
  const updateFlag = (
    section: 'translation_issues' | 'missing_passages',
    index: number,
    patch: Partial<FlagRow>,
  ) => {
    setReview((prev) => ({
      ...prev,
      [section]: prev[section].map((r, i) => (i === index ? { ...r, ...patch } : r)),
    }))
  }
  const removeFlag = (section: 'translation_issues' | 'missing_passages', index: number) => {
    setReview((prev) => ({ ...prev, [section]: prev[section].filter((_, i) => i !== index) }))
  }
  const addFlag = (section: 'translation_issues' | 'missing_passages') => {
    setReview((prev) => ({
      ...prev,
      [section]: [...prev[section], { page: 1, quote: '', note: '', recurring_pattern: false }],
    }))
  }

  return (
    <div className="flex flex-col h-full" style={{ background: 'var(--bg-canvas-alt)' }}>
      <div className="px-4 py-2.5 border-b border-white/[0.06] flex justify-between items-center text-xs">
        <span className="font-display font-semibold text-ink-50">Review form</span>
        <span className="text-ink-200 font-mono text-[0.7rem]">
          {saveStatus === 'saving' && 'saving…'}
          {saveStatus === 'saved' && 'saved · auto 2s'}
          {saveStatus === 'error' && <span className="text-accent-rose">save failed</span>}
          {saveStatus === 'idle' && 'auto-save · 2s idle'}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto scroll-thin px-4 py-4 flex flex-col gap-3">

        <ReviewSection
          title="Translation issues"
          count={review.translation_issues.length}
          tone={review.translation_issues.length ? 'warn' : 'default'}
          defaultOpen
          meta="page-anchored"
        >
          {review.translation_issues.map((row, i) => (
            <FlagRowEditor
              key={i}
              row={row}
              onChange={(patch) => updateFlag('translation_issues', i, patch)}
              onRemove={() => removeFlag('translation_issues', i)}
            />
          ))}
          <button
            onClick={() => addFlag('translation_issues')}
            className="w-full py-2 border border-dashed border-white/10 rounded-[10px] text-xs text-ink-200 hover:text-white hover:border-[rgba(123,97,255,0.35)] transition"
          >
            + Add manually (or flag from transcript)
          </button>
        </ReviewSection>

        <ReviewSection
          title="Missing or scrambled passages"
          count={review.missing_passages.length}
          meta="page-anchored"
        >
          {review.missing_passages.map((row, i) => (
            <FlagRowEditor
              key={i}
              row={row}
              onChange={(patch) => updateFlag('missing_passages', i, patch)}
              onRemove={() => removeFlag('missing_passages', i)}
            />
          ))}
          <button
            onClick={() => addFlag('missing_passages')}
            className="w-full py-2 border border-dashed border-white/10 rounded-[10px] text-xs text-ink-200 hover:text-white transition"
          >
            + Add
          </button>
        </ReviewSection>

        <ReviewSection title="Glossary additions" count={review.glossary.length}>
          {review.glossary.map((row, i) => (
            <div key={i} className="bg-[var(--bg-elevated)] rounded-[10px] p-2.5 border-l-2 border-accent-cyan">
              <input
                value={row.term}
                onChange={(e) =>
                  setReview((prev) => ({
                    ...prev,
                    glossary: prev.glossary.map((g, gi) =>
                      gi === i ? { ...g, term: e.target.value } : g,
                    ),
                  }))
                }
                placeholder="term"
                className="w-full bg-canvas border border-white/10 rounded-md px-2 py-1 text-ink-50 text-xs mb-1.5 focus:outline-none focus:border-accent-purple"
              />
              <textarea
                rows={2}
                value={row.definition}
                onChange={(e) =>
                  setReview((prev) => ({
                    ...prev,
                    glossary: prev.glossary.map((g, gi) =>
                      gi === i ? { ...g, definition: e.target.value } : g,
                    ),
                  }))
                }
                placeholder="definition"
                className="w-full bg-canvas border border-white/10 rounded-md px-2 py-1 text-ink-50 text-xs resize-y focus:outline-none focus:border-accent-purple"
              />
            </div>
          ))}
          <button
            onClick={() =>
              setReview((prev) => ({
                ...prev,
                glossary: [...prev.glossary, { term: '', definition: '' }],
              }))
            }
            className="w-full py-2 border border-dashed border-white/10 rounded-[10px] text-xs text-ink-200 hover:text-white transition"
          >
            + Add glossary entry
          </button>
        </ReviewSection>

        <ReviewSection title="Pronunciation corrections" count={review.pronunciation.length}>
          {review.pronunciation.map((row, i) => (
            <div key={i} className="bg-[var(--bg-elevated)] rounded-[10px] p-2.5 flex gap-2">
              <input
                value={row.term}
                onChange={(e) =>
                  setReview((prev) => ({
                    ...prev,
                    pronunciation: prev.pronunciation.map((g, gi) =>
                      gi === i ? { ...g, term: e.target.value } : g,
                    ),
                  }))
                }
                placeholder="term"
                className="flex-1 bg-canvas border border-white/10 rounded-md px-2 py-1 text-ink-50 text-xs"
              />
              <input
                value={row.correct}
                onChange={(e) =>
                  setReview((prev) => ({
                    ...prev,
                    pronunciation: prev.pronunciation.map((g, gi) =>
                      gi === i ? { ...g, correct: e.target.value } : g,
                    ),
                  }))
                }
                placeholder="correct pronunciation"
                className="flex-1 bg-canvas border border-white/10 rounded-md px-2 py-1 text-ink-50 text-xs"
              />
            </div>
          ))}
          <button
            onClick={() =>
              setReview((prev) => ({
                ...prev,
                pronunciation: [...prev.pronunciation, { term: '', correct: '' }],
              }))
            }
            className="w-full py-2 border border-dashed border-white/10 rounded-[10px] text-xs text-ink-200 hover:text-white transition"
          >
            + Add
          </button>
        </ReviewSection>

        <ReviewSection title="Free-form comments">
          <textarea
            rows={4}
            value={review.free_form_comments}
            onChange={(e) => setReview((prev) => ({ ...prev, free_form_comments: e.target.value }))}
            placeholder="Anything that doesn't fit a category above — observations about the source, voice shifts, sections to consider rebuilding..."
            className="w-full bg-canvas border border-white/10 rounded-md px-2 py-1 text-ink-50 text-xs resize-y focus:outline-none focus:border-accent-purple"
          />
        </ReviewSection>

        <ContentRangeEditor review={review} setReview={setReview} />

        <ApproveBox review={review} setReview={setReview} />
      </div>
    </div>
  )
}

function FlagRowEditor({
  row,
  onChange,
  onRemove,
}: {
  row: FlagRow
  onChange: (patch: Partial<FlagRow>) => void
  onRemove: () => void
}) {
  return (
    <div
      className="rounded-[10px] p-2.5 text-xs"
      style={{ background: 'var(--bg-elevated)', borderLeft: '2px solid var(--accent-amber)' }}
    >
      <div className="flex justify-between text-ink-200 mb-1.5 text-[0.7rem]">
        <span className="font-mono">page {row.page}</span>
        <button onClick={onRemove} className="hover:text-accent-rose">
          <Icon name="x" size="sm" />
        </button>
      </div>
      {row.quote && <div className="text-ink-100 italic mb-1.5 leading-snug">"{row.quote}"</div>}
      <textarea
        rows={2}
        value={row.note}
        onChange={(e) => onChange({ note: e.target.value })}
        placeholder="Your note — what's wrong / what it should say"
        className="w-full bg-canvas border border-white/10 rounded-md px-2 py-1 text-ink-50 text-xs resize-y focus:outline-none focus:border-accent-purple"
      />
      <label className="flex items-center gap-1.5 mt-1.5 text-[0.7rem] text-ink-200 cursor-pointer">
        <input
          type="checkbox"
          checked={row.recurring_pattern}
          onChange={(e) => onChange({ recurring_pattern: e.target.checked })}
          className="accent-accent-purple"
        />
        Recurring pattern (P25.6)
      </label>
    </div>
  )
}

function ContentRangeEditor({
  review,
  setReview,
}: {
  review: ReviewStruct
  setReview: (u: (p: ReviewStruct) => ReviewStruct) => void
}) {
  const cr = review.content_range
  const isSet = cr.body_starts_at_page !== null || cr.body_ends_at_page !== null
  return (
    <div
      className="rounded-[10px] overflow-hidden border"
      style={{
        borderColor: isSet ? 'rgba(16,185,129,0.3)' : 'var(--border-default)',
        background: isSet ? 'rgba(16,185,129,0.04)' : 'var(--surface-base)',
      }}
    >
      <div className="px-3 py-2.5 flex justify-between items-center">
        <div className="flex items-center gap-2">
          {isSet ? (
            <Icon name="check-circle" size="sm" className="text-accent-emerald" />
          ) : (
            <Icon name="page" size="sm" className="text-ink-200" />
          )}
          <span className="font-semibold text-sm text-ink-50">Content range (§7)</span>
        </div>
        <span className="text-xs" style={{ color: isSet ? 'var(--accent-emerald)' : 'var(--text-tertiary)' }}>
          {isSet ? `${cr.body_starts_at_page ?? '?'} → ${cr.body_ends_at_page ?? '?'} · set` : 'not set'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3.5 p-3 text-xs">
        <div>
          <label className="text-ink-200 block mb-1">Body starts at page</label>
          <input
            type="number"
            value={cr.body_starts_at_page ?? ''}
            onChange={(e) => {
              const v = e.target.value === '' ? null : parseInt(e.target.value)
              setReview((p) => ({ ...p, content_range: { ...p.content_range, body_starts_at_page: v } }))
            }}
            className="w-full bg-canvas border border-white/10 rounded-md px-2 py-1.5 text-ink-50 font-mono"
          />
        </div>
        <div>
          <label className="text-ink-200 block mb-1">Body ends at page</label>
          <input
            type="number"
            value={cr.body_ends_at_page ?? ''}
            onChange={(e) => {
              const v = e.target.value === '' ? null : parseInt(e.target.value)
              setReview((p) => ({ ...p, content_range: { ...p.content_range, body_ends_at_page: v } }))
            }}
            className="w-full bg-canvas border border-white/10 rounded-md px-2 py-1.5 text-ink-50 font-mono"
          />
        </div>
        <div className="col-span-2 text-[0.7rem] text-ink-200 leading-relaxed">
          Pages outside this range (preface, index, biblio) are excluded from Phase 0c+ ingestion. Leave blank to ingest the whole transcript.
        </div>
      </div>
    </div>
  )
}

function ApproveBox({
  review,
  setReview,
}: {
  review: ReviewStruct
  setReview: (u: (p: ReviewStruct) => ReviewStruct) => void
}) {
  const total =
    review.translation_issues.length + review.missing_passages.length + review.glossary.length
  return (
    <div
      className="rounded-[10px] overflow-hidden"
      style={{ border: '2px solid rgba(123,97,255,0.4)', background: 'rgba(123,97,255,0.05)' }}
    >
      <label className="flex items-start gap-2.5 p-3.5 cursor-pointer">
        <input
          type="checkbox"
          checked={review.approved}
          onChange={(e) => setReview((p) => ({ ...p, approved: e.target.checked }))}
          className="w-4 h-4 mt-0.5"
          style={{ accentColor: 'var(--accent-purple)' }}
        />
        <div>
          <div className="font-semibold text-sm text-ink-50">I approve this transcript</div>
          <div className="text-[0.7rem] text-ink-200 mt-1">
            {total} flagged item{total === 1 ? '' : 's'} will pass into the Phase 0c prompt as{' '}
            <code className="text-accent-cyan font-mono text-[0.68rem]">&lt;operator-review&gt;</code>{' '}
            context
          </div>
        </div>
      </label>
    </div>
  )
}
