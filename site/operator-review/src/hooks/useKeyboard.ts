import { useEffect } from 'react'

interface ShortcutHandler {
  cmd?: boolean    // requires meta or ctrl
  key: string      // case-insensitive single char or named ('Enter', 'Escape', etc.)
  handler: (e: KeyboardEvent) => void
  ignoreInInput?: boolean   // skip when activeElement is input/textarea (default true)
}

export function useKeyboard(shortcuts: ShortcutHandler[]) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const activeTag = (document.activeElement?.tagName ?? '').toLowerCase()
      const inInput = activeTag === 'input' || activeTag === 'textarea'

      for (const s of shortcuts) {
        if (s.cmd && !(e.metaKey || e.ctrlKey)) continue
        if (s.key.toLowerCase() !== e.key.toLowerCase()) continue
        if ((s.ignoreInInput ?? false) && inInput) continue
        e.preventDefault()
        s.handler(e)
        return
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [shortcuts])
}
