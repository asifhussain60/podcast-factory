import { useEffect, useRef, useState } from 'react'
import { Button } from './ui/Button'
import { Icon } from './Icons'
import { api, openResumeLog } from '../lib/api'

interface Props {
  open: boolean
  slug: string
  onClose: () => void
}

export function ResumeLogDrawer({ open, slug, onClose }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const [ended, setEnded] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    setLines([])
    setEnded(false)
    const es = openResumeLog(slug)
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        if (data.line !== undefined) setLines((l) => [...l, data.line])
      } catch {/* */}
    }
    es.addEventListener('end', () => {
      setEnded(true)
      es.close()
    })
    es.onerror = () => {
      setEnded(true)
      es.close()
    }
    return () => es.close()
  }, [open, slug])

  // Auto-scroll
  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight })
  }, [lines.length])

  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 z-60 bg-[rgba(8,11,20,0.7)] backdrop-blur-sm" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 w-[540px] max-w-[90vw] z-65 flex flex-col"
        style={{
          background: 'var(--surface-elevated)',
          borderLeft: '1px solid var(--border-default)',
          backdropFilter: 'blur(28px) saturate(180%)',
          transform: 'translateX(0)',
          transition: 'transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)',
        }}>
        <div className="px-5 py-4 border-b border-white/[0.06] flex justify-between items-start">
          <div>
            <div className="font-display font-semibold text-ink-50">Resume log · {slug}</div>
            <div className="text-xs text-ink-200 mt-0.5 flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: ended ? 'var(--text-muted)' : 'var(--accent-emerald)' }}
              />
              {ended ? 'completed' : 'streaming'} · {lines.length} lines
            </div>
          </div>
          <div className="flex gap-2">
            {!ended && (
              <Button
                variant="ghost"
                onClick={() => {
                  api.cancelResume(slug).catch(() => {})
                  onClose()
                }}
                className="border-accent-rose/40 text-accent-rose"
              >
                Cancel
              </Button>
            )}
            <Button variant="ghost" onClick={onClose}>
              <Icon name="x" size="sm" />
              Close
            </Button>
          </div>
        </div>

        <div ref={bodyRef} className="flex-1 overflow-y-auto scroll-thin px-5 py-3 font-mono text-xs text-ink-100 leading-relaxed bg-canvas">
          {lines.length === 0 && !ended && <div className="text-ink-200 italic">Waiting for output…</div>}
          {lines.map((l, i) => (
            <div key={i}>{l}</div>
          ))}
          {ended && <div className="text-ink-200 italic mt-3">— stream ended —</div>}
        </div>
      </div>
    </>
  )
}
