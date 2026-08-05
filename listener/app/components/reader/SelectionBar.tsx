import { useEffect, useRef, useState } from "react";
import { faNoteSticky, faTrash } from "@fortawesome/free-solid-svg-icons";

import { Icon } from "~/components/Icon";
import { RichNoteEditor } from "~/components/notes/RichNoteEditor";
import { anchorFromSelection, type Anchor } from "~/lib/anchor";
import { COLOURS, COLOUR_LABELS, type Colour } from "~/lib/marks";

/** Where the bar is, in page coordinates, and what it is acting on. */
interface Target {
  top: number;
  left: number;
  anchor: Anchor | null;
  /** Set when the bar was opened by tapping an existing highlight. */
  existingId: string | null;
  existingColour: Colour | null;
  existingNote: string | null;
}

/**
 * The bar that appears over a selection, and over a highlight you tap.
 *
 * One component for both, because they offer almost the same things and a reader
 * does not distinguish them: select text and you can colour it; tap what you
 * coloured and you can recolour it, write on it, or take it off. Two components
 * would be two positioning implementations and two ways to get the arrow wrong.
 *
 * It is the one thing in the reader that still floats over the text — it has to,
 * because it points at the words it acts on. It is dismissed by Escape, by a
 * click elsewhere, and by scrolling, since a bar that stays put while the passage
 * moves away is pointing at nothing.
 */
export function SelectionBar({
  bodyRef,
  onHighlight,
  onRecolour,
  onNote,
  onRemove,
}: {
  bodyRef: React.RefObject<HTMLElement | null>;
  onHighlight: (anchor: Anchor, colour: Colour) => void;
  onRecolour: (id: string, colour: Colour) => void;
  onNote: (id: string | null, anchor: Anchor | null, note: string) => void;
  onRemove: (id: string) => void;
}) {
  const [target, setTarget] = useState<Target | null>(null);
  const [noting, setNoting] = useState(false);
  const [draft, setDraft] = useState("");
  const bar = useRef<HTMLDivElement>(null);

  const close = () => {
    setTarget(null);
    setNoting(false);
    setDraft("");
  };

  useEffect(() => {
    const root = bodyRef.current;
    if (root === null) return;

    /**
     * A pointer release is the signal, not `selectionchange`.
     *
     * `selectionchange` fires continuously mid-drag, so a bar driven by it
     * appears at the first character and jitters along under the finger — and on
     * touch it lands beneath the platform's own callout. Waiting for the release
     * means one placement, at the finished selection.
     */
    const onPointerUp = (event: PointerEvent) => {
      // A press on the bar itself is a button press, not a new selection.
      if (bar.current?.contains(event.target as Node)) return;

      const node = event.target as HTMLElement | null;
      const mark = node?.closest?.("mark.pf-hl") as HTMLElement | null;

      if (mark !== null && mark !== undefined && root.contains(mark)) {
        const rect = mark.getBoundingClientRect();
        setNoting(false);
        setTarget({
          top: rect.top + window.scrollY,
          left: rect.left + window.scrollX + rect.width / 2,
          anchor: null,
          existingId: mark.dataset.markId ?? null,
          existingColour: (colourOf(mark) as Colour | null) ?? null,
          existingNote: mark.dataset.note ?? null,
        });
        return;
      }

      const selection = window.getSelection();
      if (selection === null || selection.isCollapsed) {
        if (!noting) close();
        return;
      }

      const anchor = anchorFromSelection(root, selection);
      if (anchor === null) {
        close();
        return;
      }

      const rect = selection.getRangeAt(0).getBoundingClientRect();
      setNoting(false);
      setTarget({
        top: rect.top + window.scrollY,
        left: rect.left + window.scrollX + rect.width / 2,
        anchor,
        existingId: null,
        existingColour: null,
        existingNote: null,
      });
    };

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };

    // Opening a highlight from the keyboard, for readers who never point.
    const onKeyActivate = (event: KeyboardEvent) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const mark = (event.target as HTMLElement)?.closest?.("mark.pf-hl") as HTMLElement | null;
      if (mark === null || mark === undefined) return;
      event.preventDefault();
      const rect = mark.getBoundingClientRect();
      setNoting(false);
      setTarget({
        top: rect.top + window.scrollY,
        left: rect.left + window.scrollX + rect.width / 2,
        anchor: null,
        existingId: mark.dataset.markId ?? null,
        existingColour: (colourOf(mark) as Colour | null) ?? null,
        existingNote: mark.dataset.note ?? null,
      });
    };

    // Scrolling while writing a note must NOT discard what has been typed.
    const onScroll = () => {
      if (!noting) close();
    };

    document.addEventListener("pointerup", onPointerUp);
    document.addEventListener("keydown", onKey);
    root.addEventListener("keydown", onKeyActivate);
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      document.removeEventListener("pointerup", onPointerUp);
      document.removeEventListener("keydown", onKey);
      root.removeEventListener("keydown", onKeyActivate);
      window.removeEventListener("scroll", onScroll);
    };
  }, [bodyRef, noting]);

  useEffect(() => {
    if (target !== null && target.existingNote !== null) setDraft(target.existingNote);
  }, [target]);

  if (target === null) return null;

  const choose = (colour: Colour) => {
    if (target.existingId !== null) onRecolour(target.existingId, colour);
    else if (target.anchor !== null) onHighlight(target.anchor, colour);
    window.getSelection()?.removeAllRanges();
    close();
  };

  const saveNote = () => {
    onNote(target.existingId, target.anchor, draft);
    window.getSelection()?.removeAllRanges();
    close();
  };

  return (
    <div
      ref={bar}
      role="dialog"
      aria-label="Mark this passage"
      // Writing turns the bar into a sheet of paper. The row of swatches is a
      // control and looks like one; the note is the reader's own words and looks
      // like the thing you write them on.
      className={noting ? "pf-selbar pf-selbar--paper" : "pf-selbar"}
      // The ONLY inline style in the app, and it is a measurement rather than a
      // design decision: where the selection happens to be on the page. Nothing
      // about the bar's appearance is set here — the custom properties feed
      // rules that live in the stylesheet with everything else.
      style={{ "--sel-top": `${target.top}px`, "--sel-left": `${target.left}px` } as React.CSSProperties}
    >
      {noting ? (
        <div className="pf-selbar__note">
          <RichNoteEditor
            key={target.existingId ?? "new"}
            initialValue={draft}
            onChange={setDraft}
            placeholder="What matters about this passage?"
            autoFocus
            ariaLabel="Your note on this passage"
          />
          <div className="pf-selbar__actions">
            <button type="button" onClick={close} className="pf-button pf-button--sm pf-button--ghost">
              Cancel
            </button>
            <button type="button" onClick={saveNote} className="pf-button pf-button--sm pf-button--primary">
              Save note
            </button>
          </div>
        </div>
      ) : (
        <div className="pf-selbar__row">
          <div role="group" aria-label="Highlight colour" className="pf-selbar__colours">
            {COLOURS.map((colour) => (
              <button
                key={colour}
                type="button"
                onClick={() => choose(colour)}
                aria-pressed={target.existingColour === colour}
                aria-label={COLOUR_LABELS[colour]}
                title={COLOUR_LABELS[colour]}
                className={`pf-selbar__colour pf-selbar__colour--${colour}`}
              />
            ))}
          </div>

          <span className="pf-selbar__divider" aria-hidden="true" />

          <button
            type="button"
            onClick={() => setNoting(true)}
            title={target.existingNote ? "Edit note" : "Add note"}
            className="pf-selbar__action"
          >
            <Icon icon={faNoteSticky} title={target.existingNote ? "Edit note" : "Add note"} />
          </button>

          {/* Copy was here and is gone (Asif, 2026-08-04). The browser's own
              selection already copies, on every platform, by the gesture the
              reader already knows — so the button was a second way to do a
              thing that was not broken, taking width from the two that only
              this bar can do. */}
          {target.existingId !== null ? (
            <button
              type="button"
              onClick={() => {
                onRemove(target.existingId!);
                close();
              }}
              title="Remove highlight"
              className="pf-selbar__action pf-selbar__action--danger"
            >
              <Icon icon={faTrash} title="Remove highlight" />
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

/** Read the colour back off a painted mark's class list. */
function colourOf(mark: HTMLElement): string | null {
  for (const colour of COLOURS) if (mark.classList.contains(`pf-hl--${colour}`)) return colour;
  return null;
}
