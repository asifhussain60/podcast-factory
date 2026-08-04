import { useId } from "react";
import {
  faBookmark,
  faChevronDown,
  faHouse,
  faListUl,
  faNoteSticky,
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
 *   2. **Selects for spacing and width, a stepper for size.** Three chips each
 *      would be six buttons and the row would not fit a phone. A select is one
 *      control, gets the platform's own picker on touch, and reads its current
 *      value without being opened. Size stays a stepper because it is the setting
 *      a reader nudges repeatedly, and nudging through a picker is two taps a go.
 *
 *   3. **Nothing overlays the text.** The one thing that still floats is the
 *      selection bar, which has to — it points at the words it acts on.
 */
export function ReaderToolbar({
  contentsOpen,
  onToggleContents,
  minutesLeft,
  bookmarked,
  onToggleBookmark,
  notesCount,
  notesOpen,
  onToggleNotes,
}: {
  contentsOpen: boolean;
  onToggleContents: () => void;
  minutesLeft: number;
  bookmarked: boolean;
  onToggleBookmark: () => void;
  notesCount: number;
  notesOpen: boolean;
  onToggleNotes: () => void;
}) {
  const prefs = useReading();
  const id = useId();

  const smallest = prefs.size === SIZES[0];
  const largest = prefs.size === SIZES[SIZES.length - 1];

  return (
    <div className="pf-toolbar">
      {/* ---- Getting about ------------------------------------------------
          The book's name used to live here, doubling as the contents toggle. It
          is set above the toolbar now, at full size, so the toggle says what it
          opens rather than repeating a title printed two lines above it. */}
      <div className="pf-toolbar__group">
        <Link to="/" aria-label="Back to your library" className="pf-toolbar__home">
          <Icon icon={faHouse} title="Back to your library" />
        </Link>

        <button
          type="button"
          onClick={onToggleContents}
          aria-expanded={contentsOpen}
          className="pf-toolbar__contents"
        >
          <Icon icon={faListUl} />
          <span>Contents</span>
          <Icon icon={faChevronDown} className="pf-toolbar__caret" />
        </button>
      </div>

      {/* ---- What you have marked ---------------------------------------- */}
      <div className="pf-toolbar__group">
        <button
          type="button"
          onClick={onToggleBookmark}
          aria-pressed={bookmarked}
          title={bookmarked ? "Remove bookmark" : "Bookmark this place"}
          className="pf-tool"
        >
          <Icon icon={faBookmark} title={bookmarked ? "Remove bookmark" : "Bookmark this place"} />
        </button>

        <button
          type="button"
          onClick={onToggleNotes}
          aria-expanded={notesOpen}
          title="Your notes and highlights"
          className="pf-tool"
        >
          <Icon icon={faNoteSticky} title="Your notes and highlights" />
          {/* Hidden at zero rather than shown as "0": an empty count reads as a
              thing to clear rather than a thing not yet started. */}
          {notesCount > 0 ? <span className="pf-tool__count">{notesCount}</span> : null}
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

      {/* Last, and first to be hidden when the row is tight — it is the one
          thing here that is information rather than a control. */}
      <span className="pf-toolbar__left">
        {minutesLeft === 0 ? "finished" : `${minutesLeft} min left`}
      </span>
    </div>
  );
}
