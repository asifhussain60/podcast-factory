import { Icon } from './Icons'
import { cn } from '../lib/utils'

interface Props {
  budget?: { spent_usd: number; budget_usd: number; remaining_usd: number }
  loading?: string | null   // currently-running feature id
  onAction: (action: string) => void
  arabicOn: boolean
}

export function AIAssistBar({ budget, loading, onAction, arabicOn }: Props) {
  return (
    <div
      className="border-b py-2 px-5 flex items-center gap-3 text-sm relative z-25"
      style={{
        background: 'linear-gradient(90deg, rgba(123,97,255,0.10), rgba(0,212,255,0.05))',
        borderColor: 'var(--border-accent)',
      }}
    >
      <div className="flex items-center gap-1.5 font-semibold text-accent-purple-soft">
        <Icon name="sparkle" size="sm" className="text-accent-purple" />
        AI Assist
      </div>

      <div className="flex gap-1.5 items-center">
        <AIAction id="preflight" loading={loading} onClick={onAction}>
          <Icon name="search" size="sm" />
          Pre-flight scan
        </AIAction>
        <AIAction id="arabic" loading={loading} onClick={onAction} active={arabicOn}>
          <Icon name="sparkle" size="sm" />
          Arabic terms
        </AIAction>
        <AIAction id="summarize" loading={loading} onClick={onAction}>
          <Icon name="list-tree" size="sm" />
          Page summaries
        </AIAction>
        <AIAction id="suggest-flags" loading={loading} onClick={onAction}>
          <Icon name="flag" size="sm" />
          Suggest flags
        </AIAction>
        <AIAction id="episode-plan" loading={loading} onClick={onAction}>
          <Icon name="brain" size="sm" />
          Episode plan
        </AIAction>
        <AIAction id="voice-shift" loading={loading} onClick={onAction}>
          <Icon name="diff" size="sm" />
          Voice shifts
        </AIAction>
      </div>

      <div className="ml-auto flex items-center gap-2 text-xs text-ink-200">
        {budget ? (
          <>
            <span
              className="w-2 h-2 rounded-full"
              style={{
                background:
                  budget.remaining_usd < 0.5 ? 'var(--accent-amber)' : 'var(--accent-emerald)',
              }}
            />
            ${budget.spent_usd.toFixed(2)} / ${budget.budget_usd.toFixed(2)}
          </>
        ) : (
          <span className="text-ink-300">ready</span>
        )}
      </div>
    </div>
  )
}

function AIAction({
  id,
  loading,
  onClick,
  children,
  active,
}: {
  id: string
  loading?: string | null
  onClick: (id: string) => void
  children: React.ReactNode
  active?: boolean
}) {
  const isLoading = loading === id
  return (
    <button
      onClick={() => onClick(id)}
      disabled={isLoading}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-pill border text-xs font-ui transition',
        active
          ? 'bg-accent-cyan/10 border-[rgba(0,212,255,0.4)] text-accent-cyan shadow-[0_0_10px_rgba(0,212,255,0.2)]'
          : 'bg-accent-purple/10 border-[rgba(123,97,255,0.35)] text-accent-purple-soft hover:bg-accent-purple/20 hover:border-accent-purple/50 hover:text-white hover:shadow-[0_0_10px_rgba(123,97,255,0.3)]',
        isLoading && 'opacity-60 cursor-wait',
      )}
    >
      {isLoading ? <span className="animate-spin">⟳</span> : children}
    </button>
  )
}
