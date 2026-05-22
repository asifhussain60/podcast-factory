import { useState, useEffect, useCallback } from 'react'
import type { ReaderFont, ReaderLine, ReaderTheme, ReaderWidth } from '../types'

const STORAGE_KEY = 'reader-controls-v1'

interface ReadingControls {
  font: ReaderFont
  size: number
  line: ReaderLine
  width: ReaderWidth
  theme: ReaderTheme
}

const DEFAULT: ReadingControls = {
  font: 'lato',
  size: 17,
  line: 'normal',
  width: 'medium',
  theme: 'dark',
}

/**
 * Reading-controls state with localStorage persistence.
 * Mutates <html data-reader-*> attrs + --reader-font-size CSS var.
 */
export function useReadingControls() {
  const [controls, setControls] = useState<ReadingControls>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) return { ...DEFAULT, ...(JSON.parse(raw) as ReadingControls) }
    } catch { /* ignore */ }
    return DEFAULT
  })

  // Sync to <html> attrs + CSS var on change
  useEffect(() => {
    const html = document.documentElement
    html.dataset.readerFont = controls.font
    html.dataset.readerLine = controls.line
    html.dataset.readerWidth = controls.width
    html.dataset.readerTheme = controls.theme
    html.style.setProperty('--reader-font-size', `${controls.size}px`)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(controls))
    } catch { /* quota */ }
  }, [controls])

  const setFont = useCallback((font: ReaderFont) => setControls((c) => ({ ...c, font })), [])
  const setLine = useCallback((line: ReaderLine) => setControls((c) => ({ ...c, line })), [])
  const setWidth = useCallback((width: ReaderWidth) => setControls((c) => ({ ...c, width })), [])
  const setTheme = useCallback((theme: ReaderTheme) => setControls((c) => ({ ...c, theme })), [])
  const setSize = useCallback((size: number) => setControls((c) => ({ ...c, size: Math.max(13, Math.min(24, size)) })), [])
  const cycleTheme = useCallback(() => {
    const order: ReaderTheme[] = ['dark', 'sepia', 'light']
    setControls((c) => ({ ...c, theme: order[(order.indexOf(c.theme) + 1) % order.length] }))
  }, [])

  return { controls, setFont, setLine, setWidth, setTheme, setSize, cycleTheme }
}
