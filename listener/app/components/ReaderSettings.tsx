import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { ThemePicker } from "~/components/ThemePicker";
import { useReading } from "~/components/ReadingControls";
import {
  FAMILIES,
  FAMILY_LABELS,
  LEADINGS,
  MEASURES,
  setReading,
  SIZES,
  step,
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

  // The SHARED setting, not a copy. The bar above the page carries typeface and
  // size too, and two independent `useState`s seeded from the same localStorage
  // key would drift apart the moment either was touched.
  const prefs = useReading();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function update(next: ReadingPrefs) {
    setReading(next);
  }

  /**
   * The panel is PORTALLED to <body>, and that is not a nicety.
   *
   * This control sits inside the reading header, which carries `backdrop-blur`.
   * A `backdrop-filter` makes an element the containing block for `position:
   * fixed` descendants (CSS Filter Effects §Painting), so `fixed bottom-0`
   * anchored the bottom sheet to the bottom of the HEADER — 44px tall — and 380
   * of its 445 pixels rendered above the top of the screen. Theme and size were
   * simply unreachable on a phone. Rendering outside that subtree is the fix;
   * removing the blur would have been the other one, and costs the design.
   *
   * Safe against SSR without a mounted flag: `open` starts false and only a
   * click sets it, so this branch never runs on the server.
   */
  const panel = open ? (
    <>
      {/* Click-away. Not focusable and hidden from assistive tech — Escape
          is the keyboard route out. */}
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        onClick={() => setOpen(false)}
        className="pf-scrim"
      />

      <div role="dialog" aria-label="Reading settings" className="pf-sheet">
        <Row label="Theme">
          <ThemePicker />
        </Row>

        <Row label="Typeface">
          <div className="pf-chips">
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
          <div className="pf-chips pf-chips--baseline">
            <Chip
              active={false}
              onClick={() => update({ ...prefs, size: step(SIZES, prefs.size as never, -1) })}
              ariaLabel="Smaller text"
            >
              <span className="pf-chip__a-sm">A</span>
            </Chip>
            <span className="pf-chips__value">{prefs.size}px</span>
            <Chip
              active={false}
              onClick={() => update({ ...prefs, size: step(SIZES, prefs.size as never, 1) })}
              ariaLabel="Larger text"
            >
              <span className="pf-chip__a-lg">A</span>
            </Chip>
          </div>
        </Row>

        <Row label="Line spacing">
          <div className="pf-chips">
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
          <div className="pf-chips">
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
  ) : null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="pf-button pf-button--sm pf-settings-toggle"
      >
        Aa
      </button>

      {panel === null ? null : createPortal(panel, document.body)}
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="pf-sheet__row">
      <span className="pf-label">{label}</span>
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
      className={`pf-chip${active ? " pf-chip--on" : ""}`}
    >
      {children}
    </button>
  );
}
