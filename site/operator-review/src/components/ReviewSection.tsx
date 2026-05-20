import { useState, type ReactNode } from 'react'
import { Icon } from './Icons'
import { cn } from '../lib/utils'

interface Props {
  title: string
  count?: number
  tone?: 'default' | 'warn' | 'good' | 'accent'
  defaultOpen?: boolean
  meta?: string
  children: ReactNode
}

export function ReviewSection({ title, count, tone = 'default', defaultOpen = false, meta, children }: Props) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div
      className={cn(
        'rounded-[10px] overflow-hidden backdrop-blur-xl',
        tone === 'default' && 'border border-white/10 bg-[rgba(30,41,59,0.35)]',
        tone === 'warn' && 'border border-accent-amber/30 bg-accent-amber/[0.04]',
        tone === 'good' && 'border border-accent-emerald/30 bg-accent-emerald/[0.04]',
        tone === 'accent' && 'border border-[rgba(123,97,255,0.3)] bg-accent-purple/[0.04]',
      )}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full bg-white/[0.03] hover:bg-white/[0.06] px-3 py-2.5 flex justify-between items-center text-left transition"
      >
        <div className="flex items-center gap-2.5">
          <Icon name="chev-down" size="sm" className={cn('transition-transform', !open && '-rotate-90')} />
          <span className="font-semibold text-sm text-ink-50">{title}</span>
          {typeof count === 'number' && (
            <span
              className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-pill border text-xs font-medium',
                count === 0 ? 'border-white/10 text-ink-100' :
                tone === 'warn' ? 'bg-accent-amber/12 border-accent-amber/40 text-accent-amber' :
                tone === 'accent' ? 'bg-accent-purple/12 border-[rgba(123,97,255,0.35)] text-accent-purple-soft' :
                'border-white/10 text-ink-100',
              )}
            >
              {count}
            </span>
          )}
        </div>
        {meta && <span className="text-xs text-ink-200">{meta}</span>}
      </button>
      {open && <div className="p-3 flex flex-col gap-2">{children}</div>}
    </div>
  )
}
