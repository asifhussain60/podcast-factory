import { type HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hot?: boolean
  faded?: boolean
}

export function Card({ hot, faded, className, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        'relative rounded-[14px] border bg-gradient-to-br from-[rgba(30,41,59,0.45)] to-[rgba(15,23,42,0.35)]',
        'backdrop-blur-xl transition-all duration-200',
        'hover:-translate-y-0.5 hover:border-white/[0.16] hover:shadow-[0_18px_40px_rgba(0,0,0,0.55)]',
        hot && 'border-2 border-accent-amber/50 shadow-[0_0_0_4px_rgba(245,158,11,0.08)] hover:shadow-[0_0_0_4px_rgba(245,158,11,0.15),0_18px_40px_rgba(0,0,0,0.55)] hover:border-accent-amber/80',
        !hot && 'border-white/10',
        faded && 'opacity-70 hover:opacity-100',
        className,
      )}
      {...rest}
    />
  )
}
