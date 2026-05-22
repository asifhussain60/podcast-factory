import { useNavigate } from 'react-router-dom'
import type { BookSummary } from '../types'
import { Card } from './ui/Card'
import { Pill, Dot } from './ui/Pill'
import { Button } from './ui/Button'
import { Icon } from './Icons'

interface Props {
  book: BookSummary
}

export function BookCard({ book }: Props) {
  const navigate = useNavigate()
  const needsReview = book.phase_status === 'halted-for-transcript-review'
  const isShipped = book.phase_status === 'shipped' || book.phase_status === 'done'
  const inFlight = !needsReview && !isShipped && book.phase_status !== 'unknown'

  return (
    <Card
      hot={needsReview}
      faded={isShipped}
      className="p-5 cursor-pointer"
      onClick={() => {
        if (needsReview) navigate(`/books/${book.slug}`)
      }}
    >
      {needsReview && (
        <span className="absolute -top-2.5 right-3.5 bg-accent-amber text-[#0a0a0a] px-2.5 py-1 rounded-md text-xs font-bold font-display tracking-wide shadow-[0_4px_12px_rgba(245,158,11,0.4)]">
          YOUR REVIEW →
        </span>
      )}

      <div className="flex justify-between items-start mb-2.5">
        {needsReview ? (
          <Pill tone="warn">
            <Dot style={{ background: 'var(--accent-amber)' }} />
            P22 gate · halted
          </Pill>
        ) : isShipped ? (
          <Pill tone="good">
            <Dot style={{ background: 'var(--accent-emerald)' }} />
            Shipped
          </Pill>
        ) : inFlight ? (
          <Pill tone="accent">
            <Dot style={{ background: 'var(--accent-purple)' }} className="animate-pulse" />
            {book.current_phase || 'In flight'}
          </Pill>
        ) : (
          <Pill>
            <Dot style={{ background: 'var(--text-muted)' }} />
            {book.phase_status}
          </Pill>
        )}
        <span className="font-mono text-xs text-ink-200">
          {book.page_count > 0 ? `${book.page_count} pp` : ''}
        </span>
      </div>

      <div className="font-display text-lg font-semibold text-ink-50 mb-0.5 tracking-tight">
        {book.slug}
      </div>
      <div className="text-xs text-ink-200 mb-3.5">
        {needsReview
          ? 'English transcript ready · awaiting your review'
          : isShipped
          ? 'Shipped · archive view available'
          : `Working through ${book.current_phase || 'pipeline'}`}
      </div>

      <div className="h-1 bg-white/5 rounded-pill overflow-hidden mb-2.5">
        <div
          className={
            needsReview
              ? 'h-full bg-accent-amber w-full'
              : isShipped
              ? 'h-full bg-accent-emerald w-full'
              : 'h-full bg-gradient-to-r from-accent-purple-soft to-accent-cyan'
          }
          style={{
            width: needsReview || isShipped ? '100%' : '50%',
          }}
        />
      </div>

      <div className="flex justify-between text-xs text-ink-200">
        <span>
          {book.ocr_confidence !== null && book.ocr_confidence !== undefined
            ? `OCR conf ${book.ocr_confidence}%`
            : book.has_transcript
            ? 'transcript ready'
            : '—'}
        </span>
        <span>
          {needsReview ? 'est. 8 min review' : isShipped ? 'archive' : '—'}
        </span>
      </div>

      {needsReview && (
        <Button
          variant="primary"
          size="md"
          className="w-full mt-3 justify-center"
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/books/${book.slug}`)
          }}
        >
          <Icon name="edit" size="sm" />
          Open review
        </Button>
      )}
    </Card>
  )
}
