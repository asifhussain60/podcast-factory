import { useId } from "react";
import {
  faAlignJustify,
  faBars,
  faBookmark,
  faGripLines,
  faHouse,
  faPause,
  faPlay,
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
 * How wide the page runs — drawn as the PAGE, at three widths.
 *
 * Its first version drew three stacks of horizontal bars whose length grew, on
 * the reasoning that width is horizontal so the icon should be. Rendered beside
 * the spacing buttons, which are also stacks of horizontal bars, the two groups
 * read as one family of six: the widest width icon and the widest spacing icon
 * were near enough identical to swap. That is the third time this control has
 * been misread, and every time the cause was the same — it borrowed the drawing
 * vocabulary of the setting next to it.
 *
 * So it borrows nothing. A page outline, height fixed, width growing. It shares
 * no line, no stack and no rhythm with the icons beside it, and it names the
 * thing that actually moves: not the text, the sheet the text is printed on.
 *
 * `aria-hidden` because the button around it is already labelled with the
 * setting AND its value ("Wider page width"); announcing the drawing as well
 * would say the same thing twice.
 */
function WidthIcon({ measure }: { measure: (typeof MEASURES)[number] }) {
  // Centred, so growth reads as the page widening from the middle rather than
  // as something being added on the right.
  const width = { 68: 7, 84: 11, 100: 15 }[measure];
  return (
    <svg
      viewBox="0 0 16 16"
      width="1em"
      height="1em"
      aria-hidden="true"
      focusable="false"
    >
      <rect
        x={(16 - width) / 2}
        y="1.5"
        width={width}
        height="13"
        rx="1.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  );
}

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
 *   2. **Buttons for spacing AND for width, a stepper for size.** Six chips do
 *      not fit a phone, which is why only one of the two three-step settings
 *      could have buttons — and that constraint dissolved once width became a
 *      setting that does nothing below 900px: it is hidden exactly where the
 *      room runs out, so the phone still shows one row of three-plus-a-stepper
 *      and the desktop shows both groups. Size stays a stepper because it is
 *      nudged repeatedly, and nudging through a picker is two taps a go.
 *
 *      Spacing and width have swapped controls three times, and every move came
 *      from the same failure: a control that does not look like what it does.
 *      As two selects they both read "Normal" and were indistinguishable, so
 *      width was pulled (2026-08-04) and came back as buttons — drawn with
 *      arrows pushing left and right, which is how it was then read as a
 *      spacing control that moved the wrong axis. It returns as buttons again
 *      (2026-08-06), and what keeps it legible this time is that its icons
 *      share no vocabulary with the ones beside it: lines for spacing, a sheet
 *      for width. See `WidthIcon`.
 *
 *   3. **Nothing overlays the text.** The one thing that still floats is the
 *      selection bar, which has to — it points at the words it acts on.
 */
export function ReaderToolbar({
  bookmarked,
  narrationAvailable = false,
  narrationActive = false,
  onPlayNarration,
  onToggleBookmark,
}: {
  bookmarked: boolean;
  narrationAvailable?: boolean;
  narrationActive?: boolean;
  onPlayNarration?: () => void;
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
        <Link
          to="/"
          aria-label="Back to your library"
          className="pf-toolbar__home"
        >
          <Icon icon={faHouse} title="Back to your library" />
        </Link>

        <button
          type="button"
          onClick={onToggleBookmark}
          aria-pressed={bookmarked}
          title={bookmarked ? "Remove bookmark" : "Bookmark this place"}
          className="pf-tool"
        >
          <Icon
            icon={faBookmark}
            title={bookmarked ? "Remove bookmark" : "Bookmark this place"}
          />
        </button>

        {narrationAvailable ? (
          <button
            type="button"
            onClick={onPlayNarration}
            aria-pressed={narrationActive}
            title={narrationActive ? "Pause chapter audio" : "Listen to this chapter"}
            className="pf-tool pf-tool--listen"
          >
            <Icon
              icon={narrationActive ? faPause : faPlay}
              title={narrationActive ? "Pause chapter audio" : "Listen to this chapter"}
            />
            <span className="sr-only">{narrationActive ? "Pause chapter audio" : "Listen to this chapter"}</span>
          </button>
        ) : null}
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
          onChange={(e) =>
            setReading({ ...prefs, family: e.target.value as Family })
          }
          title="Typeface"
          className="pf-select pf-select--sm pf-select--auto"
        >
          {FAMILIES.map((family) => (
            <option key={family} value={family}>
              {FAMILY_LABELS[family]}
            </option>
          ))}
        </select>

        <div
          role="group"
          aria-label="Text size"
          className="pf-stepper pf-stepper--sm"
        >
          <button
            type="button"
            onClick={() =>
              setReading({
                ...prefs,
                size: step(SIZES, prefs.size as never, -1),
              })
            }
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
            onClick={() =>
              setReading({
                ...prefs,
                size: step(SIZES, prefs.size as never, 1),
              })
            }
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
        <div
          role="group"
          aria-label="Line spacing"
          className="pf-stepper pf-stepper--sm"
        >
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
              <Icon
                icon={LEADING_ICONS[leading]}
                title={`${LEADING_LABELS[leading]} line spacing`}
              />
            </button>
          ))}
        </div>

        {/* Width gets buttons too, now that it has somewhere to go: each step
            widens the SHEET as well as the column, so the top of the scale uses
            the empty half of a desktop window instead of adding white space
            inside the same narrow leaf (Asif, 2026-08-06).

            Hidden below the tablet tier, and that is the honest behaviour rather
            than a tidy-up: under about 900px the sheet is already capped by the
            window, so all three steps render identically and the control would
            be three buttons that do nothing. The CSS hides it; the setting still
            applies if it was chosen on a wider screen. */}
        <div
          role="group"
          aria-label="Page width"
          className="pf-stepper pf-stepper--sm pf-stepper--wide-only"
        >
          {MEASURES.map((measure) => (
            <button
              key={measure}
              type="button"
              onClick={() => setReading({ ...prefs, measure })}
              aria-pressed={prefs.measure === measure}
              aria-label={`${MEASURE_LABELS[measure]} page width`}
              title={`${MEASURE_LABELS[measure]} page width`}
              className="pf-stepper__step pf-stepper__step--toggle"
            >
              <WidthIcon measure={measure} />
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
