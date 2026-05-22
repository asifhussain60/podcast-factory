import { type HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface PillProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: 'default' | 'warn' | 'good' | 'accent' | 'cyan'
}

const TONE: Record<NonNullable<PillProps['tone']>, string> = {
  default: 'border-white/10 text-ink-100',
  warn: 'bg-accent-amber/12 border-accent-amber/40 text-accent-amber',
  good: 'bg-accent-emerald/10 border-accent-emerald/30 text-accent-emerald',
  accent: 'bg-accent-purple/10 border-[rgba(123,97,255,0.35)] text-accent-purple-soft',
  cyan: 'bg-accent-cyan/10 border-[rgba(0,212,255,0.35)] text-accent-cyan',
}

export function Pill({ tone = 'default', className, children, ...rest }: PillProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-xs font-medium',
        TONE[tone],
        className,
      )}
      {...rest}
    >
      {children}
    </span>
  )
}

export function Dot({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <span className={cn('w-2 h-2 rounded-full inline-block shrink-0', className)} style={style} />
}
