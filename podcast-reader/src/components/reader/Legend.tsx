/**
 * Legend — on-demand help drawer that explains the visual vocabulary of the
 * reader (section headers, numbered circles, per-category typography,
 * metadata chips, keyboard shortcuts).
 *
 * UI: a small "?" button pinned in the top-right of the page header. Click
 * opens a right-side drawer; pressing Escape, clicking the backdrop, or
 * clicking the X closes it. The drawer never blocks reading — it's purely
 * informational and can be re-opened any time.
 */

import { useEffect, useState } from 'react';
import { Info, X } from 'lucide-react';

export default function Legend() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
      if (e.key === '?' && (e.shiftKey || e.key === '?')) {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // Global shortcut: press "?" to open
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.key === '?' && !open) {
        e.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <>
      {/* Fixed top-right of viewport (not constrained by content max-width).
          Refined neutral treatment — always findable, never shouting. */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Show reader legend (or press ?)"
        className="font-ui fixed top-4 right-4 z-40 inline-flex items-center gap-1.5 rounded-md border border-stone-400 bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-stone-700 shadow-sm backdrop-blur transition hover:border-stone-700 hover:bg-white hover:text-stone-900"
        aria-label="Open legend"
      >
        <Info className="h-3.5 w-3.5 text-stone-500" />
        <span>Legend</span>
        <kbd className="font-ui inline-flex h-4 min-w-4 items-center justify-center rounded border border-stone-300 bg-stone-50 px-1 text-[10px] font-bold text-stone-600">?</kbd>
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-stone-900/30"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          {/* Drawer */}
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Reader legend"
            className="fixed inset-y-0 right-0 z-50 w-full max-w-md overflow-y-auto bg-white shadow-2xl"
          >
            <header className="sticky top-0 flex items-center justify-between border-b border-stone-200 bg-white/95 px-5 py-3 backdrop-blur">
              <h2 className="font-ui text-sm font-semibold uppercase tracking-wider text-stone-700">
                Legend
              </h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="font-ui rounded p-1 text-stone-500 hover:bg-stone-100 hover:text-stone-900"
                aria-label="Close legend"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="space-y-8 px-5 py-6 text-sm text-stone-700">
              <Section title="Color theme — two axes">
                <p className="text-xs leading-relaxed text-stone-600">
                  Colors are assigned by <em>meaning</em>, not decoration.
                </p>
                <KeyDef label="Sidebar nav">
                  <strong>Amber</strong> = source/chapters · <strong>Sky blue</strong> = derived/episodes. These two are paired on the source-vs-derived axis.
                </KeyDef>
                <KeyDef label="Body refs">
                  <strong>Indigo</strong> = Quran · <strong>Sepia</strong> = Hadith · <strong>Muted stone</strong> = Arabic transliteration. These three are on the content-categories axis and never share colors with sidebar nav.
                </KeyDef>
                <KeyDef label="Neutrals">
                  Section headers, page chrome, and unsemantic structure use warm grays only — no category color.
                </KeyDef>
              </Section>

              <Section title="Content surfaces">
                <Item>
                  <Bullet color="amber" />
                  <div>
                    <strong>Source chapter</strong> — raw refined book text from{' '}
                    <code className="rounded bg-stone-100 px-1 py-0.5 text-xs">chapters/ch01.txt</code>.
                    The author's actual prose.
                  </div>
                </Item>
                <Item>
                  <Bullet color="emerald" />
                  <div>
                    <strong>Episode contract</strong> — briefing YAML from{' '}
                    <code className="rounded bg-stone-100 px-1 py-0.5 text-xs">chapter-contracts/*.yml</code>.
                    Metadata about how an episode adapts a source chapter (audience, tensions, anchor passages, tone). This is what you're looking at on episode pages.
                  </div>
                </Item>
                <Item>
                  <Bullet color="violet" />
                  <div>
                    <strong>Episode narrative</strong> — actual script from{' '}
                    <code className="rounded bg-stone-100 px-1 py-0.5 text-xs">episodes/EP01.txt</code>.
                    The prose that drives the podcast. <em>Not yet wired into the reader — ask if you want it surfaced.</em>
                  </div>
                </Item>
              </Section>

              <Section title="Episode contract sections">
                <KeyDef label="Audience & framing">Who the episode is written for and what worldview it assumes.</KeyDef>
                <KeyDef label="Key tensions">Numbered intellectual debates the episode must walk through. The black numbered circles are sequential ordinals.</KeyDef>
                <KeyDef label="Tone constraints">Editorial guardrails — how to handle quotes, when to attribute, what NOT to collapse.</KeyDef>
                <KeyDef label="Anchor passages">Verbatim quotations from the source that must appear in the episode. The green left-border highlights these.</KeyDef>
                <KeyDef label="Show notes">Final blurb and bullet points published alongside the audio.</KeyDef>
              </Section>

              <Section title="Metadata chips (under the title)">
                <KeyDef label="Angle">Editorial stance — e.g. faithful_exposition, polemical, comparative.</KeyDef>
                <KeyDef label="Format">deep_dive, primer, debate, etc.</KeyDef>
                <KeyDef label="Hosts">Voice dynamic — e.g. curious_mind + scholar_companion.</KeyDef>
                <KeyDef label="Length">Target runtime — short, standard, extended.</KeyDef>
                <KeyDef label="Adaptation">Faithful (stay close to source) vs interpretive.</KeyDef>
                <KeyDef label="Source ch.">Which source chapter (number or slug) this episode adapts.</KeyDef>
              </Section>

              <Section title="Reference highlighting">
                <p className="mb-3 text-xs text-stone-500">
                  Inline references are auto-detected and styled with a distinct font + tint per category. The Refs bar near the top of each reader page shows counts and lets you toggle categories on/off.
                </p>
                <RefSample id="quran" glyph="📖" label="Quran" sample="Quran 54:49" font="EB Garamond · 600 · upright" />
                <RefSample id="hadith" glyph="📜" label="Hadith" sample="Flee from Allah's qada to His qadar" font="EB Garamond · italic" />
                <RefSample id="arabic" glyph="ع" label="Arabic" sample="al-qada · taʾwīl · ḥaqīqa" font="Gentium Plus · italic" />
              </Section>

              <Section title="Keyboard shortcuts">
                <KbdRow label="Next / previous Quran ref" keys={['n', 'N']} />
                <KbdRow label="Next / previous Hadith ref" keys={['h', 'H']} />
                <KbdRow label="Next / previous Arabic ref" keys={['a', 'A']} />
                <KbdRow label="Open / close this legend" keys={['?', 'Esc']} />
              </Section>

              <Section title="Coming in later phases">
                <ul className="list-disc space-y-1.5 pl-5 text-xs">
                  <li>Gutter glyphs in the left margin aligned to ref-containing lines</li>
                  <li>Scrollbar density rail (right edge) showing ref distribution</li>
                  <li>Per-section ref counts in the TOC</li>
                  <li>Selection-based comments that flow to Claude Code</li>
                  <li>Cmd-K search across the book</li>
                  <li>Persistent typography preferences</li>
                </ul>
              </Section>
            </div>
          </aside>
        </>
      )}
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="font-ui mb-3 text-xs font-semibold uppercase tracking-wider text-stone-500">
        {title}
      </h3>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function Item({ children }: { children: React.ReactNode }) {
  return <div className="flex items-start gap-3">{children}</div>;
}

const BULLET_COLOR: Record<string, string> = {
  amber: 'bg-amber-200',
  emerald: 'bg-emerald-200',
  violet: 'bg-violet-200',
  sky: 'bg-sky-200',
};
function Bullet({ color }: { color: string }) {
  return <span className={`mt-1.5 inline-block h-2.5 w-2.5 shrink-0 rounded-full ${BULLET_COLOR[color] ?? 'bg-stone-200'}`} />;
}

function KeyDef({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3">
      <dt className="font-ui text-xs font-medium text-stone-600">{label}</dt>
      <dd className="text-xs leading-relaxed text-stone-700">{children}</dd>
    </div>
  );
}

function KbdRow({ label, keys }: { label: string; keys: string[] }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-stone-600">{label}</span>
      <span className="flex gap-1">
        {keys.map((k) => (
          <kbd key={k} className="font-ui rounded border border-stone-300 bg-stone-50 px-1.5 py-0.5 text-[10px] font-medium text-stone-700">
            {k}
          </kbd>
        ))}
      </span>
    </div>
  );
}

function RefSample({
  id,
  glyph,
  label,
  sample,
  font,
}: {
  id: string;
  glyph: string;
  label: string;
  sample: string;
  font: string;
}) {
  return (
    <div className="grid grid-cols-[24px_1fr] gap-3 py-1">
      <span className="text-base leading-none" aria-hidden>{glyph}</span>
      <div>
        <div className="flex items-baseline gap-2">
          <span className="font-ui text-xs font-medium uppercase tracking-wider text-stone-700">{label}</span>
          <span className={`ref ref-${id} text-sm`}>{sample}</span>
        </div>
        <div className="font-ui mt-0.5 text-[10px] text-stone-400">{font}</div>
      </div>
    </div>
  );
}
