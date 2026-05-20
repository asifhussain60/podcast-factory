import { Icon } from './Icons'

interface Props {
  rect: DOMRect | null
  onFlag: () => void
}

export function FlagButton({ rect, onFlag }: Props) {
  if (!rect) return null
  const top = Math.max(8, rect.top - 44)
  const left = Math.max(8, rect.left + rect.width / 2 - 70)
  return (
    <button
      onClick={onFlag}
      className="fixed z-50 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-[10px] font-semibold text-xs font-ui text-[#0a0a0a] cursor-pointer"
      style={{
        top,
        left,
        background: 'linear-gradient(135deg, var(--accent-amber) 0%, #d97706 100%)',
        boxShadow: '0 8px 20px rgba(245,158,11,0.5), 0 0 0 1px rgba(245,158,11,0.3)',
        animation: 'flagAppear 0.2s ease-out',
      }}
    >
      <Icon name="flag" size="sm" />
      Flag this passage
    </button>
  )
}
