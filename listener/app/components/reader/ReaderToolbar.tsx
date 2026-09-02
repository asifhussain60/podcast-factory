import { Fragment, useId, type ReactNode } from "react";
import {
  faAlignJustify,
  faBars,
  faBook,
  faBookOpenReader,
  faBookmark,
  faEye,
  faEyeSlash,
  faGripLines,
  faHouse,
  faListUl,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { ThemePicker } from "~/components/ThemePicker";
import { Tooltip, TooltipProvider } from "~/components/Tooltip";
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
 * Everything that controls the reading view, in one floating side panel.
 *
 * This replaces two surfaces that used to coexist: a typeface-and-size bar under
 * the book title, and a floating "Aa" panel in the top-right carrying theme,
 * typeface, size, spacing and width. Typeface and size appeared in BOTH, which is
 * the specific problem — they wrote the same store, so the two were never wrong
 * relative to each other, but the reader had no way to know that and the panel
 * sat on top of the paragraph whose setting it was there to change.
 *
 * The panel stays at the edge of the reading canvas so the settings remain
 * available halfway through a long chapter. It returns to a compact horizontal
 * dock where the viewport is too narrow to leave a real outer margin.
 *
 * Three decisions shape the layout:
 *
 *   1. **One column when the margin is tight, more only when it is safe.** The
 *      desktop panel stacks its settings vertically. A landscape tablet uses
 *      two columns only for the four compact navigation actions, while an
 *      exceptionally wide display can give the setting groups a second column.
 *      Narrow screens wrap the complete set into a compact multi-row dock.
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
export function ReaderTopActions({
  bookHref,
  bookTitle,
  contentsOpen,
  onToggleContents,
  bookmarked,
  onToggleBookmark,
  hasSourceReference,
  showReadingAssistant,
  readingAssistantEnabled,
  onToggleReadingAssistant,
}: {
  bookHref: string;
  bookTitle: string;
  /** Whether the contents drawer is showing, so the button reads as pressed. */
  contentsOpen: boolean;
  onToggleContents: () => void;
  bookmarked: boolean;
  onToggleBookmark: () => void;
  showReadingAssistant?: boolean;
  readingAssistantEnabled?: boolean;
  onToggleReadingAssistant?: () => void;
  /**
   * Whether THIS chapter has a source-reference row. The toggle is not drawn
   * at all when it does not — most books have no crosswalk, and a control
   * with nothing behind it is worse than no control.
   */
  hasSourceReference: boolean;
}) {
  const prefs = useReading();
  const assistantEnabled = Boolean(readingAssistantEnabled);

  // Built as a list, not inline JSX, so it can be SPLIT — see
  // `.pf-reader-actions__gap` below. Below the tablet gate this bar floats
  // free of the screen edge with Listen astride its top seam (Asif,
  // 2026-09-02, after two earlier attempts: stacking the full orb below the
  // buttons buried several lines of text; shrinking it to an icon-only button
  // lost the "this is different from the others" signal entirely). The gap
  // marker rendered between the two halves is invisible on desktop
  // (`display: none` there, see the CSS) and reserves the orb's own width on
  // a phone, so the row makes real room for it rather than an icon
  // disappearing under it. Order here is the ONLY definition of order — the
  // split is computed from `items.length`, not from which buttons happen to
  // be present, so a source-reference chapter or a non-admin reader still
  // gets a centred gap rather than one pushed off to whichever side ran out
  // of conditionals first.
  const items: { key: string; node: ReactNode }[] = [
    {
      key: "home",
      // ---- Getting about, and what you have marked ------------------------
      // Everything here is a way of GOING somewhere: the library, this book,
      // the chapters, your place in them. Nothing here dresses the page —
      // the theme, face, size, spacing and width all live in the toolbar
      // above. That separation is what lets contents sit in this column at
      // all.
      //
      // It was kept out twice, as the book's title doubling as a toggle and
      // then as a labelled button, on the grounds that a way of LEAVING a
      // chapter does not belong among the controls for how that chapter is
      // SET. Both objections were to a single row that held both kinds of
      // thing. This is no longer that row, so Asif put the chapters back
      // into it (2026-09-01) and took away their edge tab — see
      // `ContentsPanel`.
      node: (
        <Tooltip header="Home" description="Back to your library">
          <Link
            to="/library"
            aria-label="Back to your library"
            className="pf-reader-action pf-reader-action--home"
          >
            <Icon icon={faHouse} title="Back to your library" />
          </Link>
        </Tooltip>
      ),
    },
    {
      key: "contents",
      // Second, and deliberately: after the way out of the book and before
      // everything about this one. Its drawer opens on the left, beside the
      // button, so the movement reads as the same object growing rather than
      // a panel arriving from somewhere else.
      node: (
        <Tooltip
          header="Contents"
          description={
            contentsOpen
              ? "Hide the chapter list"
              : "Jump to any chapter in this book"
          }
        >
          <button
            type="button"
            onClick={onToggleContents}
            aria-expanded={contentsOpen}
            aria-label={contentsOpen ? "Hide contents" : "Show contents"}
            className="pf-reader-action pf-reader-action--contents"
          >
            <Icon
              icon={faListUl}
              title={contentsOpen ? "Hide contents" : "Show contents"}
            />
          </button>
        </Tooltip>
      ),
    },
  ];

  if (showReadingAssistant) {
    items.push({
      key: "assistant",
      node: (
        <Tooltip
          header="Reading assistant"
          description={
            assistantEnabled
              ? "Show one sentence clearly and dim the rest"
              : "Dim most text and make the active sentence clearer"
          }
        >
          <button
            type="button"
            onClick={onToggleReadingAssistant}
            aria-pressed={assistantEnabled}
            className="pf-reader-action pf-reader-action--assistant"
          >
            <Icon
              icon={assistantEnabled ? faEye : faEyeSlash}
              title={
                assistantEnabled
                  ? "Disable reading assistant"
                  : "Enable reading assistant"
              }
            />
          </button>
        </Tooltip>
      ),
    });
  }

  items.push(
    {
      key: "bookmark",
      node: (
        <Tooltip
          header={bookmarked ? "Bookmarked" : "Bookmark"}
          description={
            bookmarked
              ? "Remove the bookmark at your current place"
              : "Mark your place in this chapter, to jump back to it later"
          }
        >
          <button
            type="button"
            onClick={onToggleBookmark}
            aria-pressed={bookmarked}
            className="pf-reader-action pf-reader-action--bookmark"
          >
            <Icon
              icon={faBookmark}
              title={bookmarked ? "Remove bookmark" : "Bookmark this place"}
            />
          </button>
        </Tooltip>
      ),
    },
    {
      key: "book",
      node: (
        <Tooltip
          header="This book"
          description={`Open ${bookTitle}'s reading, listening, deck and print options`}
        >
          <Link
            to={bookHref}
            aria-label={`Open ${bookTitle}`}
            className="pf-reader-action pf-reader-action--book"
          >
            <Icon icon={faBook} title={`Open ${bookTitle}`} />
          </Link>
        </Tooltip>
      ),
    },
  );

  if (hasSourceReference) {
    items.push({
      key: "source",
      node: (
        <Tooltip
          header="Source reference"
          description={
            prefs.showSourceRefs
              ? "Hide the original book's page range and headings"
              : "Show the original book's page range and headings for this chapter"
          }
        >
          <button
            type="button"
            onClick={() =>
              setReading({
                ...prefs,
                showSourceRefs: !prefs.showSourceRefs,
              })
            }
            aria-pressed={prefs.showSourceRefs}
            className="pf-reader-action pf-reader-action--source"
          >
            <Icon
              icon={faBookOpenReader}
              title={
                prefs.showSourceRefs
                  ? "Hide source reference"
                  : "Show source reference"
              }
            />
          </button>
        </Tooltip>
      ),
    });
  }

  const mid = Math.ceil(items.length / 2);
  const start = items.slice(0, mid);
  const end = items.slice(mid);

  return (
    <TooltipProvider>
      <div className="pf-reader-actions" aria-label="Reading actions">
        {/* Real wing ELEMENTS, not just two runs of buttons either side of a
            gap marker — a phone chapter is as likely to carry five buttons as
            four or six, so the two sides are rarely equal in count. Flowing
            them as one row with a wide spacer in the middle let the spacer
            drift wherever `justify-content` happened to put it, which is not
            necessarily the row's own geometric centre; the orb above is fixed
            at that centre regardless (`left: 50%` on `.pf-toolbar-rail`), so
            an uneven split visibly overlapped a button. Two `1fr` grid
            columns either side of a fixed-width centre column (see the
            max-width: 1023px rule near `.pf-reader-listen`) keep the two
            wings equal-WIDTH by construction, however unequal their button
            COUNTS are — which is what actually keeps the gap under the orb. */}
        <div className="pf-reader-actions__wing pf-reader-actions__wing--start">
          {start.map(({ key, node }) => (
            <Fragment key={key}>{node}</Fragment>
          ))}
        </div>
        <span className="pf-reader-actions__gap" aria-hidden="true" />
        <div className="pf-reader-actions__wing pf-reader-actions__wing--end">
          {end.map(({ key, node }) => (
            <Fragment key={key}>{node}</Fragment>
          ))}
        </div>
      </div>
    </TooltipProvider>
  );
}

/**
 * How the page is SET — theme, face, size, spacing, width. Nothing else.
 *
 * It carried a Home link and a Bookmark button until 2026-09-01, kept as
 * "familiar" shortcuts to the same two things the action rail already offers.
 * Asif had them removed: two controls for one action, four inches apart, teach a
 * reader that the two rows mean different things and then disprove it. Going
 * somewhere is the rail's job; this row only dresses the page.
 */
export function ReaderToolbar() {
  const prefs = useReading();
  const id = useId();

  const smallest = prefs.size === SIZES[0];
  const largest = prefs.size === SIZES[SIZES.length - 1];

  return (
    <TooltipProvider>
      <div className="pf-toolbar" data-measure={prefs.measure}>
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
            <Tooltip
              header="Smaller text"
              description="Decrease the reading size"
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
            </Tooltip>
            {/* Announced on change, so a screen-reader user who cannot see the
              text reflow still learns what the buttons did. */}
            <span aria-live="polite" className="pf-stepper__value">
              {prefs.size}
            </span>
            <Tooltip
              header="Larger text"
              description="Increase the reading size"
            >
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
            </Tooltip>
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
              <Tooltip
                key={leading}
                header={`${LEADING_LABELS[leading]} spacing`}
                description={`Set ${LEADING_LABELS[leading].toLowerCase()} space between lines`}
              >
                <button
                  type="button"
                  onClick={() => setReading({ ...prefs, leading })}
                  aria-pressed={prefs.leading === leading}
                  aria-label={`${LEADING_LABELS[leading]} line spacing`}
                  className="pf-stepper__step pf-stepper__step--toggle"
                >
                  <Icon
                    icon={LEADING_ICONS[leading]}
                    title={`${LEADING_LABELS[leading]} line spacing`}
                  />
                </button>
              </Tooltip>
            ))}
          </div>

          {/* Width gets buttons too, now that it has somewhere to go: each step
            widens the SHEET as well as the column, so the top of the scale uses
            the empty half of a desktop window instead of adding white space
            inside the same narrow leaf (Asif, 2026-08-06).

            Hidden only where the viewport is physically too narrow to offer
            three distinct sheets. From an ordinary desktop upward each choice
            has its own responsive cap, so the control remains both available
            and truthful even while a side gutter is reserved for this panel. */}
          <div
            role="group"
            aria-label="Page width"
            className="pf-stepper pf-stepper--sm pf-stepper--wide-only"
          >
            {MEASURES.map((measure) => (
              <Tooltip
                key={measure}
                header={`${MEASURE_LABELS[measure]} width`}
                description={`Set the page to its ${MEASURE_LABELS[measure].toLowerCase()} width`}
              >
                <button
                  type="button"
                  onClick={() => setReading({ ...prefs, measure })}
                  aria-pressed={prefs.measure === measure}
                  aria-label={`${MEASURE_LABELS[measure]} page width`}
                  className="pf-stepper__step pf-stepper__step--toggle"
                >
                  <WidthIcon measure={measure} />
                </button>
              </Tooltip>
            ))}
          </div>
        </div>

        {/* Nothing here is information. "13 min left" sat at the end of the row
          until 2026-08-04 and was the only thing in it that could not be acted
          on — a number that changed as you read, in a bar you open to change a
          setting. */}
      </div>
    </TooltipProvider>
  );
}
