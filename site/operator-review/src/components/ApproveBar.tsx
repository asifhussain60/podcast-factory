import { Button } from './ui/Button'
import { Icon } from './Icons'

interface Props {
  saveStatus: 'idle' | 'saving' | 'saved' | 'error'
  flagCount: number
  onApprove: () => void
}

export function ApproveBar({ saveStatus, flagCount, onApprove }: Props) {
  return (
    <div
      className="px-4 py-3.5 flex justify-between items-center backdrop-blur-xl border-t"
      style={{ background: 'var(--surface-elevated)', borderColor: 'var(--border-default)' }}
    >
      <div className="text-xs">
        <div className="font-semibold text-ink-50">
          {flagCount} flag{flagCount === 1 ? '' : 's'} pending
        </div>
        <div className="text-ink-200 mt-0.5">
          {saveStatus === 'saving' && 'Saving…'}
          {saveStatus === 'saved' && 'Auto-saved · 0 unsaved changes · last commit pending'}
          {saveStatus === 'error' && (
            <span className="text-accent-rose">Save failed — check backend</span>
          )}
          {saveStatus === 'idle' && 'Auto-save · 0 unsaved changes'}
        </div>
      </div>
      <Button variant="primary" size="md" onClick={onApprove}>
        <Icon name="check-circle" size="sm" />
        Approve &amp; Resume
      </Button>
    </div>
  )
}
