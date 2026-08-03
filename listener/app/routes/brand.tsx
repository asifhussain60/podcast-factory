import { Link } from "react-router";
import { Colophon, Qalam, Strapwork } from "~/components/brand/marks";
import { Wordmark, type MarkName } from "~/components/brand/Logo";
import { ThemePicker } from "~/components/ThemePicker";

/* Scratch surface for choosing the mark. Not linked from the product nav, and
   deleted once the choice is made. */

const CANDIDATES: { name: MarkName; title: string; note: string }[] = [
  {
    name: "strapwork",
    title: "Strapwork",
    note: "An eight-fold girih knot as one interlaced ribbon. The canonical non-figurative Islamic ornament, reduced to a single unbroken stroke — a quiet metaphor for an unbroken chain of narration.",
  },
  {
    name: "colophon",
    title: "Colophon",
    note: "Five bars of a level meter whose rhythm continues as three rules of text. Says podcast and book in one glyph, works at 16px on day one, and the bars can animate while something is playing.",
  },
  {
    name: "qalam",
    title: "Qalam",
    note: "A reed pen nib split by its slit, at the head of three rules. A pen starting a paragraph, or a playhead at the head of a track. The most restrained of the three.",
  },
];

function MarkAt({ name, size, compact }: { name: MarkName; size: number; compact?: boolean }) {
  if (name === "colophon") return <Colophon size={size} compact={compact} />;
  if (name === "qalam") return <Qalam size={size} compact={compact} />;
  return <Strapwork size={size} compact={compact} />;
}

export default function Brand() {
  return (
    <div className="min-h-dvh bg-pf-bg">
      <header className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-6">
        <Link to="/" className="font-ui text-sm text-pf-muted underline">
          Back
        </Link>
        <ThemePicker />
      </header>

      <main id="main" className="mx-auto max-w-5xl px-6 pb-24">
        <h1 className="font-prose text-4xl text-pf-ink">Three marks</h1>
        <p className="mt-3 max-w-2xl font-ui text-sm leading-relaxed text-pf-muted">
          Switch the theme above to see each on stone, sepia and dark. The small
          square at the right of each row is the favicon reduction, which drops
          the detail that collapses below about 24 pixels.
        </p>

        <div className="mt-12 space-y-6">
          {CANDIDATES.map((c) => (
            <section
              key={c.name}
              className="rounded-xl border border-pf-rule bg-pf-surface p-8 shadow-pf"
            >
              <div className="flex flex-wrap items-start justify-between gap-8">
                <div className="flex items-center gap-8 text-pf-ink">
                  <MarkAt name={c.name} size={96} />
                  <div className="flex items-center gap-4">
                    <MarkAt name={c.name} size={44} />
                    <Wordmark name={c.name} />
                  </div>
                </div>

                <div className="flex items-center gap-4 text-pf-ink">
                  <span className="flex flex-col items-center gap-2">
                    <MarkAt name={c.name} size={32} compact />
                    <span className="font-ui text-[0.65rem] text-pf-faint">32px</span>
                  </span>
                  <span className="flex flex-col items-center gap-2">
                    <MarkAt name={c.name} size={16} compact />
                    <span className="font-ui text-[0.65rem] text-pf-faint">16px</span>
                  </span>
                </div>
              </div>

              <h2 className="mt-8 font-prose text-2xl text-pf-ink">{c.title}</h2>
              <p className="mt-2 max-w-3xl font-ui text-sm leading-relaxed text-pf-muted">
                {c.note}
              </p>
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}
