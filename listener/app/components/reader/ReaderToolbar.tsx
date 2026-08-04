import { useId } from "react";
import {
  faAlignJustify,
  faArrowsLeftRight,
  faArrowsLeftRightToLine,
  faBookmark,
  faHouse,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { ThemePicker } from "~/components/ThemePicker";
import { useReading } from "~/components/useReading";
import {
  FAMILIES,
  FAMILY_LABELS,
  LEADINGS,
  LEADING_LABELS,
  MEASURES,
  MEASURE_LABELS,
  setReading,
  SIZES,
  step,
  type Family,
} from "~/lib/reading";

/**
 * How wide the column is, drawn rather than named.
 *
 * Arrows pulling in, a settled column, arrows pushing out — the icon carries
 * the idea and the word confirms it. As a select it read "Normal" beside the
 * line-spacing select also reading "Normal", which is why line width was taken
 * out entirely on 2026-08-04 and why it can come back now: three buttons and a
 * dropdown cannot be mistaken for each other.
 */
const MEASURE_ICONS: Record<(typeof MEASURES)[number], IconDefinition> = {
  58: faArrowsLeftRightToLine,
  68: faAlignJustify,
  78: faArrowsLeftRight,
};

/**
 * Everything that controls the reading view, in ONE row above it.
 *
 * This replaces two surfaces that used to coexist: a typeface-and-size bar under
 * the book title, and a floating "Aa" panel in the top-right carrying theme,
 * typeface, size, spacing and width. Typeface and size appeared in BOTH, which is
 * the specific problem — they wrote the same store, so the two were never wrong
 * relative to each other, but the reader had no way to know that and the panel
 * sat on top of the paragraph whose setting it was there to change.
 *
 * It is not sticky and not in a header. It sits between the book's title and the
 * page, in the flow, and scrolls away with them — so the only thing over the
 * prose while reading is the prose.
 *
 * Three decisions shape the layout:
 *
 *   1. **One row, on every screen.** Below the tablet tier it scrolls
 *      horizontally rather than collapsing into a popover, because a popover is
 *      the thing being removed. A scrolling strip is the same idiom the mobile
 *      nav already uses.
 *
 *   2. **A select for spacing, a stepper for size.** Three chips each would be
 *      six buttons and the row would not fit a phone. A select is one control,
 *      gets the platform's own picker on touch, and reads its current value
 *      without being opened. Size stays a stepper because it is the setting a
 *      reader nudges repeatedly, and nudging through a picker is two taps a go.
 *
 *      Line WIDTH was a third such control and is gone (Asif, 2026-08-04). It
 *      and line spacing are different settings, but both read "Normal" at their
 *      defaults, so side by side they were two identical dropdowns — and a
 *      control nobody can tell from its neighbour is worse than no control. The
 *      measure keeps its 68ch default; `MEASURES` stays in lib/reading.ts
 *      because a value stored by an earlier visit must still validate.
 *
 *   3. **Nothing overlays the text.** The one thing that still floats is the
 *      selection bar, which has to — it points at the words it acts on.
 */
export function ReaderToolbar({
  bookmarked,
  onToggleBookmark,
}: {
  bookmarked: boolean;
  onToggleBookmark: () => void;
}) {
  const prefs = useReading();
  const id = useId();

  const smallest = prefs.size === SIZES[0];
  const largest = prefs.size === SIZES[SIZES.length - 1];

  return (
    <div className="pf-toolbar">
      {/* ---- Getting about, and what you have marked ----------------------
          Contents is NOT here. It was, twice — as the book's title doubling as a
          toggle, then as a labelled button — and both put a way of LEAVING this
          chapter into the row of controls for how this chapter is SET. It is a
          collapsible panel on the left now, carrying its own affordance. */}
      <div className="pf-toolbar__group">
        <Link to="/" aria-label="Back to your library" className="pf-toolbar__home">
          <Icon icon={faHouse} title="Back to your library" />
        </Link>

        <button
          type="button"
          onClick={onToggleBookmark}
          aria-pressed={bookmarked}
          title={bookmarked ? "Remove bookmark" : "Bookmark this place"}
          className="pf-tool"
        >
          <Icon icon={faBookmark} title={bookmarked ? "Remove bookmark" : "Bookmark this place"} />
        </button>

      </div>

      {/* ---- How the page is set ----------------------------------------- */}
      <div className="pf-toolbar__group pf-toolbar__group--set">
        <ThemePicker compact />

        <label htmlFor={`${id}-face`} className="sr-only">
          Typeface
        </label>
        <select
          id={`${id}-face`}
          value={prefs.family}
          onChange={(e) => setReading({ ...prefs, family: e.target.value as Family })}
          title="Typeface"
          className="pf-select pf-select--sm pf-select--auto"
        >
          {FAMILIES.map((family) => (
            <option key={family} value={family}>
              {FAMILY_LABELS[family]}
            </option>
          ))}
        </select>

        <div role="group" aria-label="Text size" className="pf-stepper pf-stepper--sm">
          <button
            type="button"
            onClick={() => setReading({ ...prefs, size: step(SIZES, prefs.size as never, -1) })}
            disabled={smallest}
            aria-label="Smaller text"
            className="pf-stepper__step"
          >
            &minus;
          </button>
          {/* Announced on change, so a screen-reader user who cannot see the
              text reflow still learns what the buttons did. */}
          <span aria-live="polite" className="pf-stepper__value">
            {prefs.size}
          </span>
          <button
            type="button"
            onClick={() => setReading({ ...prefs, size: step(SIZES, prefs.size as never, 1) })}
            disabled={largest}
            aria-label="Larger text"
            className="pf-stepper__step"
          >
            +
          </button>
        </div>

        <label htmlFor={`${id}-leading`} className="sr-only">
          Line spacing
        </label>
        <select
          id={`${id}-leading`}
          value={prefs.leading}
          onChange={(e) => setReading({ ...prefs, leading: Number(e.target.value) })}
          title="Line spacing"
          className="pf-select pf-select--sm pf-select--auto"
        >
          {LEADINGS.map((leading) => (
            <option key={leading} value={leading}>
              {LEADING_LABELS[leading]}
            </option>
          ))}
        </select>

        <div role="group" aria-label="Line width" className="pf-stepper pf-stepper--sm">
          {MEASURES.map((measure) => (
            <button
              key={measure}
              type="button"
              onClick={() => setReading({ ...prefs, measure })}
              aria-pressed={prefs.measure === measure}
              aria-label={MEASURE_LABELS[measure]}
              title={MEASURE_LABELS[measure]}
              className="pf-stepper__step pf-stepper__step--toggle"
            >
              <Icon icon={MEASURE_ICONS[measure]} title={MEASURE_LABELS[measure]} />
            </button>
          ))}
        </div>
      </div>

      {/* Nothing here is information. "13 min left" sat at the end of the row
          until 2026-08-04 and was the only thing in it that could not be acted
          on — a number that changed as you read, in a bar you open to change a
          setting. */}
    </div>
  );
}
