import { useId } from "react";
import {
  faAlignJustify,
  faBars,
  faBookmark,
  faGripLines,
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
 * How far apart the lines sit, drawn rather than named.
 *
 * Lines packed, lines apart, lines further apart — the SPACE BETWEEN the bars is
 * the whole message, so the metaphor is vertical and no arrow appears in it.
 *
 * These three buttons drove line WIDTH until Asif read them the way they were
 * drawn (2026-08-04): the icons were arrows pulling in and pushing out, which is
 * a horizontal idea, so a control for horizontal space is what they looked like
 * and a control for horizontal space is what they were. The setting a reader
 * reaches for most is spacing; it now has the three buttons and these icons, and
 * width has the select. Nothing was removed — the two swapped places.
 */
const LEADING_ICONS: Record<(typeof LEADINGS)[number], IconDefinition> = {
  1.5: faAlignJustify,
  1.7: faBars,
  1.9: faGripLines,
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
 *   2. **Buttons for spacing, a select for width, a stepper for size.** Six
 *      chips would not fit a phone, so only one of the two three-step settings
 *      can have buttons, and it is the one a reader actually reaches for: line
 *      SPACING. A select is one control, gets the platform's own picker on
 *      touch, and reads its current value without being opened — right for
 *      width, which is set once and left alone. Size stays a stepper because it
 *      is nudged repeatedly, and nudging through a picker is two taps a go.
 *
 *      Spacing and width have swapped controls twice now, and both moves came
 *      from the same failure: a control that does not look like what it does.
 *      As two selects they both read "Normal" and were indistinguishable, so
 *      width was pulled (2026-08-04) and came back as buttons — drawn with
 *      arrows pushing left and right, which is how it was then read as a
 *      spacing control that moved the wrong axis. Whatever holds the buttons
 *      must be drawn on the axis it changes.
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

        {/* Spacing gets the buttons because it is the setting a reader changes
            most, and a button is one press where a select is two. Each one says
            what it sets in full — "Wide line spacing", never a bare "Wide" —
            because the width control beside it has a Wide of its own, and two
            controls stating their value in the same word with nothing to
            separate them is the confusion that took line width off this toolbar
            once already. */}
        <div role="group" aria-label="Line spacing" className="pf-stepper pf-stepper--sm">
          {LEADINGS.map((leading) => (
            <button
              key={leading}
              type="button"
              onClick={() => setReading({ ...prefs, leading })}
              aria-pressed={prefs.leading === leading}
              aria-label={`${LEADING_LABELS[leading]} line spacing`}
              title={`${LEADING_LABELS[leading]} line spacing`}
              className="pf-stepper__step pf-stepper__step--toggle"
            >
              <Icon icon={LEADING_ICONS[leading]} title={`${LEADING_LABELS[leading]} line spacing`} />
            </button>
          ))}
        </div>

        <label htmlFor={`${id}-measure`} className="sr-only">
          Line width
        </label>
        <select
          id={`${id}-measure`}
          value={prefs.measure}
          onChange={(e) => setReading({ ...prefs, measure: Number(e.target.value) })}
          title="Line width"
          className="pf-select pf-select--sm pf-select--auto"
        >
          {MEASURES.map((measure) => (
            <option key={measure} value={measure}>
              {MEASURE_LABELS[measure]}
            </option>
          ))}
        </select>
      </div>

      {/* Nothing here is information. "13 min left" sat at the end of the row
          until 2026-08-04 and was the only thing in it that could not be acted
          on — a number that changed as you read, in a bar you open to change a
          setting. */}
    </div>
  );
}
