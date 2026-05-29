/**
 * StudioVersePopover — dedicated, self-contained Quran verse popover for the WC8 Studio PoC.
 *
 * Replaces the reused QuranPopover, whose chapter-viewer.css uses `--color-*` design tokens
 * that don't exist in the PoC theme (`--c-*`) — so its card rendered transparent. This control
 * is built on @floating-ui/react (already installed): correct placement (flip/shift, stays in
 * the viewport, always on top), an OPAQUE golden-themed card, the verse in a beautiful Arabic
 * webfont (Amiri) and the translation in a compatible serif. External CSS only (repo DoD).
 *
 * Hover any `.sp-vchip` (the chapter:verse chip, carries data-surah/data-verse) → fetches
 * /api/quran/verse?key=S:V (cached in localStorage). Stays open while hovering chip or card.
 */
import { useEffect, useRef, useState } from 'react';
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/react';

interface VerseData {
  surah_number: number;
  surah_name_en: string;
  surah_name_ar: string;
  surah_name_meaning: string;
  verse_key: string;
  verse_range: string;
  arabic: string;
  translation: string;
  translation_source: string;
  audio_url?: string | null;
}

const CACHE_KEY = (k: string) => `pf-reader:quran:${k}`;
function readCache(k: string): VerseData | null {
  try { const raw = localStorage.getItem(CACHE_KEY(k)); return raw ? JSON.parse(raw) as VerseData : null; } catch { return null; }
}
function writeCache(k: string, v: VerseData): void {
  try { localStorage.setItem(CACHE_KEY(k), JSON.stringify(v)); } catch { /* ignore */ }
}

export default function StudioVersePopover() {
  const [open, setOpen] = useState(false);
  const [vkey, setVkey] = useState<string | null>(null);
  const [data, setData] = useState<VerseData | null>(null);
  const [loading, setLoading] = useState(false);
  const closeTimer = useRef<number | null>(null);
  const hoverTimer = useRef<number | null>(null);

  const { refs, floatingStyles } = useFloating({
    open,
    placement: 'bottom',
    middleware: [offset(10), flip({ padding: 12 }), shift({ padding: 12 })],
    whileElementsMounted: autoUpdate,
  });

  const cancelClose = () => { if (closeTimer.current) { window.clearTimeout(closeTimer.current); closeTimer.current = null; } };
  const scheduleClose = () => { cancelClose(); closeTimer.current = window.setTimeout(() => setOpen(false), 360); };

  useEffect(() => {
    const root = document.querySelector('.prose-body');
    if (!root) return;

    const openFor = async (el: HTMLElement, k: string) => {
      refs.setReference({ getBoundingClientRect: () => el.getBoundingClientRect() });
      cancelClose();
      setVkey(k);
      setOpen(true);
      const cached = readCache(k);
      if (cached) { setData(cached); setLoading(false); return; }
      setData(null);
      setLoading(true);
      try {
        const res = await fetch(`/api/quran/verse?key=${encodeURIComponent(k)}`);
        if (!res.ok) throw new Error(String(res.status));
        const d = await res.json() as VerseData;
        writeCache(k, d);
        setData((prev) => (k === k ? d : prev));
      } catch { /* leave loading false; card shows the key */ } finally {
        setLoading(false);
      }
    };

    const keyFrom = (el: HTMLElement): string | null => {
      const s = el.getAttribute('data-surah');
      const v = el.getAttribute('data-verse');
      return s && v ? `${s}:${v}` : null;
    };

    const onOver = (e: Event) => {
      const chip = (e.target as HTMLElement).closest('.sp-vchip') as HTMLElement | null;
      if (!chip) return;
      const k = keyFrom(chip);
      if (!k) return;
      if (hoverTimer.current) window.clearTimeout(hoverTimer.current);
      hoverTimer.current = window.setTimeout(() => openFor(chip, k), 180);
    };
    const onOut = (e: Event) => {
      const chip = (e.target as HTMLElement).closest('.sp-vchip');
      if (!chip) return;
      if (hoverTimer.current) { window.clearTimeout(hoverTimer.current); hoverTimer.current = null; }
      scheduleClose();
    };
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };

    root.addEventListener('mouseover', onOver);
    root.addEventListener('mouseout', onOut);
    document.addEventListener('keydown', onEsc);
    return () => {
      root.removeEventListener('mouseover', onOver);
      root.removeEventListener('mouseout', onOut);
      document.removeEventListener('keydown', onEsc);
    };
  }, [refs]);

  if (!open || !vkey) return null;
  const [surah, verse] = vkey.split(':');

  return (
    <div
      ref={refs.setFloating}
      style={floatingStyles}
      className="sv-pop"
      role="dialog"
      aria-label={`Quran ${vkey}`}
      onMouseEnter={cancelClose}
      onMouseLeave={scheduleClose}
    >
      <div className="sv-pop__head">
        <span className="sv-pop__surah">
          Surah {String(data?.surah_number ?? Number(surah)).padStart(3, '0')} · {data?.surah_name_en ?? '…'}
          {data?.surah_name_meaning && <span className="sv-pop__mean"> — {data.surah_name_meaning}</span>}
        </span>
        <span className="sv-pop__head-right">
          <span className="sv-pop__ar-name" lang="ar" dir="rtl">{data?.surah_name_ar ?? ''}</span>
          <span className="sv-pop__badge">{data?.verse_range?.split(':')[1] ?? verse}</span>
        </span>
      </div>
      <div className="sv-pop__body">
        {loading && !data ? (
          <div className="sv-pop__loading">Loading {vkey}…</div>
        ) : (
          <>
            {data?.arabic && <p className="sv-pop__arabic" lang="ar" dir="rtl">{data.arabic}</p>}
            {data?.translation && <p className="sv-pop__trans">{data.translation}</p>}
            <div className="sv-pop__foot">
              <span className="sv-pop__src">{data?.translation_source ?? 'quran.com'}</span>
              <a className="sv-pop__open" href={`https://quran.com/${surah}/${verse}`} target="_blank" rel="noreferrer">Open ↗</a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
