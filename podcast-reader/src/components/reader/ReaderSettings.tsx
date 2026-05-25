/**
 * ReaderSettings — iOS-Reader-style "Aa" popover for typography + theme.
 *
 * Single discoverable trigger. Desktop: 320px popover anchored to the
 * trigger button. Mobile (<768px): bottom sheet with backdrop. Persists
 * via reader-settings.ts to localStorage. Keyboard: ⌘, opens / Esc
 * closes. Also opens on the `reader-settings:open` window event so
 * FloatingActions can forward to it.
 */

import { useEffect, useRef, useState } from 'react';
import {
  loadSettings,
  saveSettings,
  resetSettings,
  type ReaderSettings,
  type ThemeName,
  type FontName,
  type WidthName,
} from '~/lib/reader-settings';

const FONTS: { id: FontName; label: string; sample: string; note?: string }[] = [
  { id: 'source-serif', label: 'Source Serif',   sample: 'Aa' },
  { id: 'eb-garamond',  label: 'EB Garamond',     sample: 'Aa' },
  { id: 'iowan',        label: 'Iowan Old Style', sample: 'Aa' },
  { id: 'inter',        label: 'Inter (sans)',    sample: 'Aa' },
  { id: 'lexend',       label: 'Lexend',          sample: 'Aa', note: 'reading-research-backed' },
  { id: 'opendyslexic', label: 'OpenDyslexic',    sample: 'Aa', note: 'weighted letterforms' },
];

const SIZES: ReaderSettings['size'][] = [16, 18, 19, 21, 23];
const LINE_HEIGHTS: { value: ReaderSettings['lineHeight']; label: string }[] = [
  { value: 1.5, label: 'Compact' },
  { value: 1.7, label: 'Comfortable' },
  { value: 1.9, label: 'Airy' },
];
const WIDTHS: { id: WidthName; label: string }[] = [
  { id: 'narrow', label: 'Narrow' },
  { id: 'medium', label: 'Medium' },
  { id: 'wide',   label: 'Wide' },
  { id: 'full',   label: 'Full' },
];
const THEMES: { id: ThemeName; label: string; swatch: string }[] = [
  { id: 'light', label: 'Light', swatch: '#fafaf7' },
  { id: 'sepia', label: 'Sepia', swatch: '#f1e7d0' },
  { id: 'dark',  label: 'Dark',  swatch: '#1a2030' },
  { id: 'hc',    label: 'A11y',  swatch: '#ffffff' },
];

export default function ReaderSettingsPanel() {
  const [open, setOpen] = useState(false);
  const [s, setS] = useState<ReaderSettings>(() => loadSettings());
  const [saved, setSaved] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setS(loadSettings());
    const onOpen = () => setOpen(true);
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === ',') { e.preventDefault(); setOpen((v) => !v); }
      else if (e.key === 'Escape') setOpen(false);
    };
    const onChanged = (e: Event) => {
      const next = (e as CustomEvent<ReaderSettings>).detail;
      if (next) setS(next);
    };
    window.addEventListener('reader-settings:open', onOpen);
    window.addEventListener('keydown', onKey);
    window.addEventListener('reader-settings-changed', onChanged as EventListener);
    return () => {
      window.removeEventListener('reader-settings:open', onOpen);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('reader-settings-changed', onChanged as EventListener);
    };
  }, []);

  const patch = (p: Partial<ReaderSettings>) => {
    const next = saveSettings(p);
    setS(next);
    setSaved(true);
    setTimeout(() => setSaved(false), 900);
  };

  const reset = () => { setS(resetSettings()); setSaved(true); setTimeout(() => setSaved(false), 900); };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-8 w-9 items-center justify-center rounded-md border border-stone-300 bg-white font-serif text-[14px] font-semibold text-stone-700 transition hover:border-amber-400 hover:text-amber-700 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-200"
        title="Reader settings (⌘,)"
        aria-label="Reader settings"
        aria-expanded={open}
      >
        Aa
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 sm:bg-transparent"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
        >
          {/* Mobile backdrop */}
          <div className="absolute inset-0 bg-stone-900/30 sm:hidden" />
          <div
            ref={panelRef}
            className="absolute bottom-0 left-0 right-0 max-h-[88vh] overflow-y-auto rounded-t-xl border border-stone-200 bg-white p-5 shadow-2xl sm:bottom-auto sm:left-auto sm:right-6 sm:top-14 sm:w-[340px] sm:rounded-xl dark:border-stone-700 dark:bg-stone-800"
            role="dialog"
            aria-label="Reader settings"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-ui text-[12px] font-semibold uppercase tracking-wider text-stone-500">Reader settings</h2>
              <div className="flex items-center gap-2">
                {saved && <span className="font-ui text-[10px] text-emerald-600">✓ Saved</span>}
                <button onClick={() => setOpen(false)} className="text-stone-400 hover:text-stone-900 dark:hover:text-stone-100" aria-label="Close">✕</button>
              </div>
            </div>

            {/* Theme */}
            <Section label="Theme">
              <div className="grid grid-cols-4 gap-2">
                {THEMES.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => patch({ theme: t.id })}
                    className={chip(s.theme === t.id) + ' flex flex-col items-center gap-1 py-2'}
                    aria-pressed={s.theme === t.id}
                  >
                    <span className="block h-5 w-5 rounded-full border border-stone-300" style={{ background: t.swatch }} />
                    <span className="text-[11px]">{t.label}</span>
                  </button>
                ))}
              </div>
            </Section>

            {/* Font */}
            <Section label="Reading font">
              <div className="grid grid-cols-3 gap-1.5">
                {FONTS.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => patch({ font: f.id })}
                    className={chip(s.font === f.id) + ' flex flex-col items-center px-2 py-1.5'}
                    title={f.note ? `${f.label} — ${f.note}` : f.label}
                    style={{ fontFamily: fontFamilyOf(f.id) }}
                    aria-pressed={s.font === f.id}
                  >
                    <span className="text-base leading-none">{f.sample}</span>
                    <span className="mt-0.5 font-ui text-[9px] uppercase tracking-wider text-stone-500">{f.label.split(' ')[0]}</span>
                  </button>
                ))}
              </div>
            </Section>

            {/* Size */}
            <Section label="Font size">
              <div className="grid grid-cols-5 gap-1.5">
                {SIZES.map((sz) => (
                  <button
                    key={sz}
                    onClick={() => patch({ size: sz })}
                    className={chip(s.size === sz) + ' py-1.5'}
                    aria-pressed={s.size === sz}
                  >
                    <span style={{ fontSize: `${Math.max(11, sz * 0.6)}px` }}>A</span>
                  </button>
                ))}
              </div>
            </Section>

            {/* Line height */}
            <Section label="Line spacing">
              <div className="grid grid-cols-3 gap-1.5">
                {LINE_HEIGHTS.map((lh) => (
                  <button key={lh.value} onClick={() => patch({ lineHeight: lh.value })} className={chip(s.lineHeight === lh.value)} aria-pressed={s.lineHeight === lh.value}>
                    {lh.label}
                  </button>
                ))}
              </div>
            </Section>

            {/* Width */}
            <Section label="Reading width">
              <div className="grid grid-cols-4 gap-1.5">
                {WIDTHS.map((w) => (
                  <button key={w.id} onClick={() => patch({ width: w.id })} className={chip(s.width === w.id)} aria-pressed={s.width === w.id}>
                    {w.label}
                  </button>
                ))}
              </div>
            </Section>

            {/* Toggles */}
            <Section label="Display">
              <div className="space-y-2">
                <Toggle label="Arabic script overlay" checked={s.arabicOverlay} onChange={(v) => patch({ arabicOverlay: v })} />
                <Toggle label="Drop cap on first paragraph" checked={s.dropCap} onChange={(v) => patch({ dropCap: v })} />
                <Toggle label="Focus mode (dim other paragraphs)" checked={s.focusMode} onChange={(v) => patch({ focusMode: v })} hint="press f to toggle" />
              </div>
            </Section>

            <div className="mt-3 flex items-center justify-between border-t border-stone-200 pt-3 dark:border-stone-700">
              <button onClick={reset} className="font-ui text-[11px] text-stone-500 underline-offset-2 hover:text-amber-700 hover:underline">
                Reset to defaults
              </button>
              <span className="font-ui text-[10px] text-stone-400">⌘, opens · Esc closes</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="mb-1.5 font-ui text-[10px] font-semibold uppercase tracking-wider text-stone-500">{label}</div>
      {children}
    </div>
  );
}

function chip(active: boolean): string {
  return (
    'rounded-md border text-center text-[12px] transition select-none ' +
    (active
      ? 'border-amber-500 bg-amber-50 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100'
      : 'border-stone-200 bg-white text-stone-700 hover:border-stone-400 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-200')
  );
}

function Toggle({ label, checked, onChange, hint }: { label: string; checked: boolean; onChange: (v: boolean) => void; hint?: string }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 rounded-md px-2 py-1.5 text-[12px] hover:bg-stone-50 dark:hover:bg-stone-700/50">
      <span className="text-stone-700 dark:text-stone-200">
        {label}
        {hint && <span className="ml-2 font-ui text-[10px] text-stone-400">{hint}</span>}
      </span>
      <span
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={
          'relative inline-block h-5 w-9 rounded-full transition ' +
          (checked ? 'bg-amber-500' : 'bg-stone-300 dark:bg-stone-600')
        }
      >
        <span
          className={
            'absolute top-0.5 inline-block h-4 w-4 rounded-full bg-white shadow transition ' +
            (checked ? 'left-[18px]' : 'left-0.5')
          }
        />
      </span>
    </label>
  );
}

function fontFamilyOf(id: FontName): string {
  switch (id) {
    case 'source-serif': return '"Source Serif 4", Georgia, serif';
    case 'eb-garamond':  return '"EB Garamond", Georgia, serif';
    case 'iowan':        return '"Iowan Old Style", Charter, Georgia, serif';
    case 'inter':        return 'Inter, system-ui, sans-serif';
    case 'lexend':       return 'Lexend, Inter, system-ui, sans-serif';
    case 'opendyslexic': return 'OpenDyslexic, Lexend, sans-serif';
  }
}
