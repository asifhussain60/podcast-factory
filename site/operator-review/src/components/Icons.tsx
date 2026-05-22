/**
 * SVG icon sprite (Lucide-style). Mirrors the mock's inline sprite.
 * Render once at app root via <IconSprite/>; reference anywhere with <Icon name="..."/>.
 */
import { cn } from '../lib/utils'

export const ICON_NAMES = [
  'arrow-left', 'minus', 'plus', 'theme', 'search', 'page', 'diff', 'sliders',
  'chev-down', 'chev-right', 'flag', 'branch', 'check-circle', 'keyboard',
  'x', 'edit', 'cmd', 'sparkle', 'brain', 'help', 'list-tree',
] as const

export type IconName = typeof ICON_NAMES[number]

export function IconSprite() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" style={{ display: 'none' }} aria-hidden="true">
      <symbol id="i-arrow-left" viewBox="0 0 24 24"><path d="M19 12H5M11 6l-6 6 6 6" /></symbol>
      <symbol id="i-minus" viewBox="0 0 24 24"><path d="M5 12h14" /></symbol>
      <symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></symbol>
      <symbol id="i-theme" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M12 2a10 10 0 0 0 0 20z" fill="currentColor" stroke="none" /></symbol>
      <symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" /></symbol>
      <symbol id="i-page" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></symbol>
      <symbol id="i-diff" viewBox="0 0 24 24"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" /></symbol>
      <symbol id="i-sliders" viewBox="0 0 24 24"><line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" /><line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" /><line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" /><line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" /></symbol>
      <symbol id="i-chev-down" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" /></symbol>
      <symbol id="i-chev-right" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6" /></symbol>
      <symbol id="i-flag" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></symbol>
      <symbol id="i-branch" viewBox="0 0 24 24"><line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><path d="M18 9a9 9 0 0 1-9 9" /></symbol>
      <symbol id="i-check-circle" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M9 12l2 2 4-4" /></symbol>
      <symbol id="i-keyboard" viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="14" rx="2" /><line x1="6" y1="10" x2="6.01" y2="10" /><line x1="10" y1="10" x2="10.01" y2="10" /><line x1="14" y1="10" x2="14.01" y2="10" /><line x1="18" y1="10" x2="18.01" y2="10" /><line x1="6" y1="14" x2="6.01" y2="14" /><line x1="18" y1="14" x2="18.01" y2="14" /><line x1="10" y1="14" x2="14" y2="14" /></symbol>
      <symbol id="i-x" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></symbol>
      <symbol id="i-edit" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></symbol>
      <symbol id="i-cmd" viewBox="0 0 24 24"><circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" /><circle cx="6" cy="18" r="2" /><circle cx="18" cy="18" r="2" /></symbol>
      <symbol id="i-sparkle" viewBox="0 0 24 24"><path d="M12 3l1.5 5L18 9l-5 1.5L12 15l-1-4.5L6 9l4.5-1z" /></symbol>
      <symbol id="i-brain" viewBox="0 0 24 24"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2z" /><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2z" /></symbol>
      <symbol id="i-help" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></symbol>
      <symbol id="i-list-tree" viewBox="0 0 24 24"><path d="M21 12h-8M21 6h-8M21 18h-8M3 6v.01M3 12v.01M3 18v.01M3 6c1 0 2 1 2 2v8c0 1 1 2 2 2" /></symbol>
    </svg>
  )
}

interface IconProps extends React.SVGProps<SVGSVGElement> {
  name: IconName
  size?: 'sm' | 'md' | 'lg'
}

export function Icon({ name, size = 'md', className, ...rest }: IconProps) {
  const sizeClass = size === 'sm' ? 'icon icon-sm' : size === 'lg' ? 'icon icon-lg' : 'icon'
  return (
    <svg className={cn(sizeClass, className)} {...rest}>
      <use href={`#i-${name}`} />
    </svg>
  )
}
