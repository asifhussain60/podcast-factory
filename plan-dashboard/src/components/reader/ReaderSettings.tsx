/**
 * ReaderSettings — "Aa" popover for typography + theme + display toggles.
 *
 * Persists via reader-settings.ts to localStorage. Keyboard: ⌘, opens /
 * Esc closes. Opens on the `reader-settings:open` window event so
 * FloatingActions can forward to it. No Tailwind utility classes — all
 * visual rules live in chapter-viewer.css under `.reader-settings-*`.
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
  type EditHighlight,
} from '../../lib/reader/reader-settings';

const EDIT_SWATCHES: { id: EditHighlight; label: string }[] = [
  { id: 'emerald', label: 'Emerald' },
  { id: 'amber',   label: 'Amber' },
  { id: 'sky',     label: 'Sky' },
  { id: 'rose',    label: 'Rose' },
  { id: 'violet',  label: 'Violet' },
];

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
const THEMES: { id: ThemeName; label: string }[] = [
  { id: 'light', label: 'Light' },
  { id: 'sepia', label: 'Sepia' },
  { id: 'dark',  label: 'Dark' },
  { id: 'hc',    label: 'A11y' },
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
    const onDocPointer = (e: MouseEvent) => {
      if (!open) return;
      const t = e.target as HTMLElement;
      if (!t) return;
      if (panelRef.current?.contains(t)) return;
      if (t.closest('[aria-label="Reader settings"]')) return;
      setOpen(false);
    };
    window.addEventListener('reader-settings:open', onOpen);
    window.addEventListener('keydown', onKey);
    window.addEventListener('reader-settings-changed', onChanged as EventListener);
    document.addEventListener('mousedown', onDocPointer);
    return () => {
      window.removeEventListener('reader-settings:open', onOpen);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('reader-settings-changed', onChanged as EventListener);
      document.removeEventListener('mousedown', onDocPointer);
    };
  }, [open]);

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
        className="reader-settings-trigger"
        title="Reader settings (⌘,)"
        aria-label="Reader settings"
        aria-expanded={open}
      >
        Aa
      </button>

      {open && (
        <div
          className="reader-settings-overlay"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
        >
          <div
            ref={panelRef}
            className="reader-settings-panel"
            role="dialog"
            aria-label="Reader settings"
          >
            <div className="reader-settings-head">
              <h2 className="reader-settings-title">Reader settings</h2>
              <div className="reader-settings-head-right">
                {saved && <span className="reader-settings-saved">✓ Saved</span>}
                <button onClick={() => setOpen(false)} className="reader-settings-close" aria-label="Close">✕</button>
              </div>
            </div>

            <Section label="Theme">
              <div className="reader-settings-grid reader-settings-grid--4">
                {THEMES.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => patch({ theme: t.id })}
                    className={chip(s.theme === t.id) + ' is-stacked'}
                    aria-pressed={s.theme === t.id}
                  >
                    <span className={`reader-settings-theme-swatch reader-settings-theme-swatch--${t.id}`} />
                    <span className="reader-settings-chip-label">{t.label}</span>
                  </button>
                ))}
              </div>
            </Section>

            <Section label="Reading font">
              <div className="reader-settings-grid reader-settings-grid--3">
                {FONTS.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => patch({ font: f.id })}
                    className={chip(s.font === f.id) + ` is-stacked reader-settings-font--${f.id}`}
                    title={f.note ? `${f.label} — ${f.note}` : f.label}
                    aria-pressed={s.font === f.id}
                  >
                    <span className="reader-settings-font-sample">{f.sample}</span>
                    <span className="reader-settings-chip-label">{f.label.split(' ')[0]}</span>
                  </button>
                ))}
              </div>
            </Section>

            <Section label="Font size">
              <div className="reader-settings-grid reader-settings-grid--5">
                {SIZES.map((sz) => (
                  <button
                    key={sz}
                    onClick={() => patch({ size: sz })}
                    className={chip(s.size === sz) + ` reader-settings-size--${sz}`}
                    aria-pressed={s.size === sz}
                  >
                    <span>A</span>
                  </button>
                ))}
              </div>
            </Section>

            <Section label="Line spacing">
              <div className="reader-settings-grid reader-settings-grid--3">
                {LINE_HEIGHTS.map((lh) => (
                  <button key={lh.value} onClick={() => patch({ lineHeight: lh.value })} className={chip(s.lineHeight === lh.value)} aria-pressed={s.lineHeight === lh.value}>
                    {lh.label}
                  </button>
                ))}
              </div>
            </Section>

            <Section label="Reading width">
              <div className="reader-settings-grid reader-settings-grid--4">
                {WIDTHS.map((w) => (
                  <button key={w.id} onClick={() => patch({ width: w.id })} className={chip(s.width === w.id)} aria-pressed={s.width === w.id}>
                    {w.label}
                  </button>
                ))}
              </div>
            </Section>

            <Section label="Edit highlight">
              <div className="reader-settings-grid reader-settings-grid--5">
                {EDIT_SWATCHES.map((sw) => (
                  <button
                    key={sw.id}
                    onClick={() => patch({ editHighlight: sw.id })}
                    className={chip(s.editHighlight === sw.id) + ' is-stacked'}
                    aria-pressed={s.editHighlight === sw.id}
                    title={sw.label}
                  >
                    <span className={`reader-settings-edit-swatch reader-settings-edit-swatch--${sw.id}`} />
                    <span className="reader-settings-chip-label">{sw.label.slice(0,3)}</span>
                  </button>
                ))}
              </div>
            </Section>

            <Section label="Display">
              <div className="reader-settings-toggles">
                <Toggle label="Arabic script overlay" checked={s.arabicOverlay} onChange={(v) => patch({ arabicOverlay: v })} />
                <Toggle label="Drop cap on first paragraph" checked={s.dropCap} onChange={(v) => patch({ dropCap: v })} />
                <Toggle label="Focus mode (dim other paragraphs)" checked={s.focusMode} onChange={(v) => patch({ focusMode: v })} hint="press f to toggle" />
              </div>
            </Section>

            <div className="reader-settings-foot">
              <button onClick={reset} className="reader-settings-reset">Reset to defaults</button>
              <span className="reader-settings-hint">⌘, opens · Esc closes</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="reader-settings-section">
      <div className="reader-settings-section-label">{label}</div>
      {children}
    </div>
  );
}

function chip(active: boolean): string {
  return `reader-settings-chip ${active ? 'is-active' : ''}`;
}

function Toggle({ label, checked, onChange, hint }: { label: string; checked: boolean; onChange: (v: boolean) => void; hint?: string }) {
  return (
    <label className="reader-settings-toggle">
      <span className="reader-settings-toggle-label">
        {label}
        {hint && <span className="reader-settings-toggle-hint">{hint}</span>}
      </span>
      <span
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`reader-settings-switch ${checked ? 'is-on' : 'is-off'}`}
      >
        <span className="reader-settings-switch-knob" />
      </span>
    </label>
  );
}
