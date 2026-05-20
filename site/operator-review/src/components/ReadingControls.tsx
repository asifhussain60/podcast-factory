import { useState, useRef, useEffect } from 'react'
import { Icon } from './Icons'
import { cn } from '../lib/utils'
import { useReadingControls } from '../hooks/useReadingControls'
import type { ReaderFont, ReaderLine, ReaderTheme, ReaderWidth } from '../types'

export function ReadingControls() {
  const { controls, setFont, setLine, setWidth, setTheme, setSize, cycleTheme } =
    useReadingControls()
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  // Click outside closes
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!open) return
      const t = e.target as Node
      if (panelRef.current?.contains(t) || triggerRef.current?.contains(t)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  return (
    <div className="relative flex items-center gap-3 bg-[rgba(19,23,37,0.85)] backdrop-blur-xl px-5 py-2 border-b border-white/10 z-30">
      <span className="text-xs text-ink-200 font-medium uppercase tracking-wider">Reading</span>

      <div className="flex items-center gap-1.5">
        <IconBtn onClick={() => setSize(controls.size - 1)} title="Smaller">
          <Icon name="minus" size="sm" />
        </IconBtn>
        <span className="font-mono text-xs text-ink-100 min-w-[2.8rem] text-center">
          {controls.size} px
        </span>
        <IconBtn onClick={() => setSize(controls.size + 1)} title="Larger">
          <Icon name="plus" size="sm" />
        </IconBtn>
      </div>

      <div className="w-px h-5 bg-white/10" />

      <IconBtn onClick={cycleTheme} title="Cycle theme">
        <Icon name="theme" size="sm" />
      </IconBtn>

      <button
        ref={triggerRef}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-pill border text-xs font-ui transition',
          open
            ? 'bg-accent-purple/10 border-[rgba(123,97,255,0.35)] text-accent-purple-soft shadow-[0_0_10px_rgba(123,97,255,0.2)]'
            : 'border-white/10 text-ink-100 hover:bg-[rgba(30,41,59,0.35)] hover:text-white hover:border-[rgba(123,97,255,0.35)]',
        )}
      >
        <Icon name="sliders" size="sm" />
        <span>Reading controls</span>
        <Icon
          name="chev-down"
          size="sm"
          className={cn('transition-transform', open && 'rotate-180')}
        />
      </button>

      {open && (
        <div
          ref={panelRef}
          className="absolute top-full right-5 mt-2 w-[460px] bg-[rgba(19,23,37,0.85)] border border-white/10 rounded-[14px] shadow-[0_18px_40px_rgba(0,0,0,0.55)] backdrop-blur-3xl p-5 z-40"
          style={{ animation: 'fadeIn 0.22s ease-out' }}
        >
          <PanelSection title="Font family">
            <div className="flex gap-1.5">
              <FontPill cur={controls.font} val="lato" set={setFont}>
                Lato
              </FontPill>
              <FontPill
                cur={controls.font}
                val="cormorant"
                set={setFont}
                style={{ fontFamily: 'Cormorant Garamond, serif', fontStyle: 'italic' }}
              >
                Cormorant
              </FontPill>
              <FontPill
                cur={controls.font}
                val="lora"
                set={setFont}
                style={{ fontFamily: 'Lora, serif' }}
              >
                Lora
              </FontPill>
              <FontPill cur={controls.font} val="opendyslexic" set={setFont}>
                Dyslexic
              </FontPill>
            </div>
          </PanelSection>

          <PanelSection title="Font size">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={13}
                max={24}
                value={controls.size}
                onChange={(e) => setSize(parseInt(e.target.value))}
                className="flex-1 h-1.5 rounded-pill outline-none cursor-pointer"
                style={{
                  background:
                    'linear-gradient(90deg, var(--rose) 0%, var(--lavender) 50%, var(--accent-cyan) 100%)',
                  appearance: 'none',
                  WebkitAppearance: 'none',
                }}
              />
              <span className="font-mono text-sm text-accent-cyan min-w-12 text-right">
                {controls.size} px
              </span>
            </div>
          </PanelSection>

          <PanelSection title="Line spacing">
            <div className="flex gap-1.5">
              <LinePill cur={controls.line} val="tight" set={setLine}>
                Tight
              </LinePill>
              <LinePill cur={controls.line} val="normal" set={setLine}>
                Normal
              </LinePill>
              <LinePill cur={controls.line} val="loose" set={setLine}>
                Loose
              </LinePill>
            </div>
          </PanelSection>

          <PanelSection title="Content width">
            <div className="flex gap-1.5">
              <WidthPill cur={controls.width} val="narrow" set={setWidth}>
                Narrow
              </WidthPill>
              <WidthPill cur={controls.width} val="medium" set={setWidth}>
                Medium
              </WidthPill>
              <WidthPill cur={controls.width} val="wide" set={setWidth}>
                Wide
              </WidthPill>
            </div>
          </PanelSection>

          <PanelSection title="Theme" last>
            <div className="flex gap-2">
              <ThemeSwatch cur={controls.theme} val="dark" set={setTheme} swatch="from-[#0a0d18] to-[#1a1f2e]">
                Dark
              </ThemeSwatch>
              <ThemeSwatch cur={controls.theme} val="sepia" set={setTheme} swatch="from-[#f4ecd8] to-[#d6c8a8]">
                Sepia
              </ThemeSwatch>
              <ThemeSwatch cur={controls.theme} val="light" set={setTheme} swatch="from-[#ffffff] to-[#f0f0f0]">
                Light
              </ThemeSwatch>
            </div>
          </PanelSection>
        </div>
      )}
    </div>
  )
}

function IconBtn({ children, onClick, title }: { children: React.ReactNode; onClick?: () => void; title?: string }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="w-8 h-8 inline-flex items-center justify-center bg-[rgba(30,41,59,0.35)] border border-white/10 rounded-[10px] text-ink-100 hover:bg-[rgba(45,55,72,0.45)] hover:text-white hover:border-[rgba(123,97,255,0.35)] hover:shadow-[0_0_10px_rgba(123,97,255,0.2)] transition"
    >
      {children}
    </button>
  )
}

function PanelSection({ title, children, last }: { title: string; children: React.ReactNode; last?: boolean }) {
  return (
    <div className={cn(!last && 'mb-4')}>
      <div className="font-display text-[0.7rem] font-semibold uppercase tracking-widest text-ink-200 mb-2">
        {title}
      </div>
      {children}
    </div>
  )
}

interface PillSetProps<T extends string> {
  cur: T
  val: T
  set: (v: T) => void
  children: React.ReactNode
  style?: React.CSSProperties
}

function FontPill(props: PillSetProps<ReaderFont>) {
  return <PillBtn {...props} />
}
function LinePill(props: PillSetProps<ReaderLine>) {
  return <PillBtn {...props} />
}
function WidthPill(props: PillSetProps<ReaderWidth>) {
  return <PillBtn {...props} />
}

function PillBtn<T extends string>({ cur, val, set, children, style }: PillSetProps<T>) {
  const active = cur === val
  return (
    <button
      onClick={() => set(val)}
      style={style}
      className={cn(
        'flex-1 min-w-[70px] px-2.5 py-2 rounded-[10px] border text-xs font-ui text-center transition',
        active
          ? 'bg-gradient-to-br from-accent-purple/[0.18] to-accent-cyan/[0.10] text-white border-accent-purple/45 ring-1 ring-accent-purple/20 ring-inset'
          : 'bg-[rgba(30,41,59,0.35)] border-white/10 text-ink-100 hover:bg-[rgba(45,55,72,0.45)] hover:text-white hover:border-[rgba(123,97,255,0.35)]',
      )}
    >
      {children}
    </button>
  )
}

function ThemeSwatch({
  cur,
  val,
  set,
  swatch,
  children,
}: {
  cur: ReaderTheme
  val: ReaderTheme
  set: (v: ReaderTheme) => void
  swatch: string
  children: React.ReactNode
}) {
  const active = cur === val
  return (
    <button
      onClick={() => set(val)}
      className={cn(
        'flex-1 flex flex-col items-center gap-1.5 px-2 py-2.5 rounded-[10px] border transition',
        active
          ? 'border-accent-purple bg-accent-purple/10 shadow-[0_0_10px_rgba(123,97,255,0.2)]'
          : 'border-white/10 bg-[rgba(30,41,59,0.35)] hover:bg-[rgba(45,55,72,0.45)] hover:border-[rgba(123,97,255,0.35)]',
      )}
    >
      <span className={cn('w-7 h-7 rounded-full border border-black/40 shadow-inner bg-gradient-to-br', swatch)} />
      <span className="text-xs text-ink-100">{children}</span>
    </button>
  )
}
