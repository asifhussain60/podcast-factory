import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

type Variant = 'primary' | 'ghost' | 'icon'
type Size = 'sm' | 'md' | 'lg' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

const VARIANT: Record<Variant, string> = {
  primary:
    'bg-gradient-to-br from-accent-purple to-[#5a3fd9] text-white font-semibold shadow-[0_4px_12px_-2px_rgba(124,92,255,0.45),inset_0_1px_0_rgba(255,255,255,0.2)] hover:-translate-y-px hover:brightness-[1.08] hover:shadow-[0_0_30px_rgba(123,97,255,0.55),0_0_60px_rgba(123,97,255,0.25)] active:translate-y-0 disabled:opacity-50 disabled:pointer-events-none',
  ghost:
    'bg-transparent text-ink-100 border border-white/10 hover:bg-white/[0.04] hover:border-white/[0.16] disabled:opacity-50',
  icon:
    'bg-[rgba(30,41,59,0.35)] text-ink-100 border border-white/10 hover:bg-[rgba(45,55,72,0.45)] hover:text-white hover:border-[rgba(123,97,255,0.35)]',
}

const SIZE: Record<Size, string> = {
  sm: 'px-2.5 py-1 text-xs gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-5 py-2.5 text-base gap-2.5',
  icon: 'w-8 h-8 p-0 inline-flex items-center justify-center',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = 'ghost', size = 'md', children, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        'inline-flex items-center rounded-[10px] font-ui transition-all duration-150',
        VARIANT[variant],
        SIZE[size],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  )
})
