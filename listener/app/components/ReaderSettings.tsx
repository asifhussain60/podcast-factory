import { useEffect, useState } from "react";

import { ThemePicker } from "~/components/ThemePicker";
import {
  applyReading,
  DEFAULT_PREFS,
  FAMILIES,
  FAMILY_LABELS,
  LEADINGS,
  MEASURES,
  SIZES,
  step,
  storedReading,
  type ReadingPrefs,
} from "~/lib/reading";

/**
 * Typography controls for the reading column.
 *
 * A popover on desktop, a bottom sheet on mobile — the same component, placed by
 * CSS, because two components would be two chances for the controls to disagree.
 *
 * Everything applies LIVE, behind the panel. There is no Apply button: the whole
 * point is judging the text at the new setting, which you cannot do if the text
 * is covered until you commit.
 *
 * Size is a stepper, deliberately, not a slider — a slider needs a precise drag
 * and most of this reading happens one-handed on a phone.
 */
export function ReaderSettings() {
  const [open, setOpen] = useState(false);
  const [prefs, setPrefs] = useState<ReadingPrefs>(DEFAULT_PREFS);

  // Read after mount. The server cannot know what is in localStorage, and
  // guessing produces a hydration mismatch.
  useEffect(() => setPrefs(storedReading()), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function update(next: ReadingPrefs) {
    setPrefs(next);
    applyReading(next);
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="rounded-lg border border-pf-rule bg-pf-surface px-3 py-1.5 font-ui text-sm text-pf-ink transition-colors hover:border-pf-accent"
      >
        Aa
      </button>

      {open ? (
        <>
          {/* Click-away. Not focusable and hidden from assistive tech — Escape
              is the keyboard route out. */}
          <button
            type="button"
            aria-hidden="true"
            tabIndex={-1}
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-40 cursor-default bg-transparent"
          />

          <div
            role="dialog"
            aria-label="Reading settings"
            className="fixed inset-x-0 bottom-0 z-50 rounded-t-2xl border-t border-pf-rule bg-pf-elev p-6 shadow-lg sm:absolute sm:inset-x-auto sm:bottom-auto sm:right-0 sm:top-11 sm:w-80 sm:rounded-xl sm:border"
            style={{ boxShadow: "var(--l-shadow)" }}
          >
            <Row label="Theme">
              <ThemePicker />
            </Row>

            <Row label="Typeface">
              <div className="flex flex-wrap gap-1">
                {FAMILIES.map((family) => (
                  <Chip
                    key={family}
                    active={prefs.family === family}
                    onClick={() => update({ ...prefs, family })}
                  >
                    {FAMILY_LABELS[family]}
                  </Chip>
                ))}
              </div>
            </Row>

            <Row label="Size">
              <div className="flex items-center gap-2">
                <Chip
                  active={false}
                  onClick={() => update({ ...prefs, size: step(SIZES, prefs.size as never, -1) })}
                  ariaLabel="Smaller text"
                >
                  <span className="text-xs">A</span>
                </Chip>
                <span className="font-ui text-xs tabular-nums text-pf-muted">{prefs.size}px</span>
                <Chip
                  active={false}
                  onClick={() => update({ ...prefs, size: step(SIZES, prefs.size as never, 1) })}
                  ariaLabel="Larger text"
                >
                  <span className="text-lg leading-none">A</span>
                </Chip>
              </div>
            </Row>

            <Row label="Line spacing">
              <div className="flex gap-1">
                {LEADINGS.map((leading, i) => (
                  <Chip
                    key={leading}
                    active={prefs.leading === leading}
                    onClick={() => update({ ...prefs, leading })}
                  >
                    {["Tight", "Normal", "Loose"][i]}
                  </Chip>
                ))}
              </div>
            </Row>

            <Row label="Line width">
              <div className="flex gap-1">
                {MEASURES.map((measure, i) => (
                  <Chip
                    key={measure}
                    active={prefs.measure === measure}
                    onClick={() => update({ ...prefs, measure })}
                  >
                    {["Narrow", "Normal", "Wide"][i]}
                  </Chip>
                ))}
              </div>
            </Row>
          </div>
        </>
      ) : null}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-b border-pf-rule-soft py-3 first:pt-0 last:border-0 last:pb-0">
      <span className="font-ui text-xs uppercase tracking-widest text-pf-faint">{label}</span>
      {children}
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
  ariaLabel,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  ariaLabel?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      aria-pressed={ariaLabel ? undefined : active}
      className={[
        "flex min-w-9 items-center justify-center rounded-md px-3 py-1.5 font-ui text-sm transition-colors",
        active
          ? "bg-pf-accent text-pf-on-accent"
          : "border border-pf-rule text-pf-muted hover:bg-pf-sunken hover:text-pf-ink",
      ].join(" ")}
    >
      {children}
    </button>
  );
}
