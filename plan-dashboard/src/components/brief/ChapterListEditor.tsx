/**
 * ChapterListEditor — the chapter list as editable rows rather than a textarea.
 *
 * Asif, 2026-08-31: "I should be able to edit these. Can you present them in a
 * different input?" A textarea can hold twenty-four chapters but cannot let you
 * do anything to ONE of them: fixing a title means finding it inside a wall of
 * text, and moving one means cutting and pasting a line.
 *
 * THE VALUE IS STILL ONE NEWLINE-JOINED STRING. Deliberately: `chapter_list` is
 * read by the brief renderer, the readiness gate, the YAML store and the
 * pipeline config writer, and every one of them already agrees on that shape.
 * Changing the control must not change the contract — so this is a control, not
 * a new data type, and everything downstream is untouched.
 *
 * PASTE STILL WORKS, and is the fast path for a list you have in your hand:
 * pasting several lines into a row splits them into rows from that point,
 * because pasting a contents page into row 1 and getting one 400-character
 * chapter is not what anybody meant.
 */
import { useRef } from "react";

interface Props {
  /** Newline-joined titles — the field's stored value. */
  value: string;
  onChange: (value: string) => void;
  /** Ties the rows to the field's own <label>, which sits outside this. */
  labelId: string;
  describedBy?: string;
}

function toRows(value: string): string[] {
  return value.split("\n").map((l) => l.replace(/\s+$/, ""));
}

export default function ChapterListEditor({
  value,
  onChange,
  labelId,
  describedBy,
}: Props) {
  // An empty value is ONE empty row, not zero: a list you cannot start typing
  // into needs a button pressed before it does anything, which is a worse
  // starting state than the textarea it replaced.
  const rows = value === "" ? [""] : toRows(value);
  const rootRef = useRef<HTMLOListElement>(null);

  /** Commit rows, dropping the blanks that only exist while you are typing. */
  function commit(next: string[]) {
    onChange(
      next
        .map((r) => r.trim())
        .filter(Boolean)
        .join("\n"),
    );
  }

  /** Move focus to a row after the list re-renders under it. */
  function focusRow(i: number) {
    requestAnimationFrame(() => {
      const inputs = rootRef.current?.querySelectorAll("input");
      const el = inputs?.[Math.max(0, Math.min(i, inputs.length - 1))];
      el?.focus();
      el?.select();
    });
  }

  function setRow(i: number, text: string) {
    const next = [...rows];
    next[i] = text;
    // Not `commit`: trimming empties WHILE typing would delete the row you are
    // in the middle of clearing. The blanks are filtered on every other path.
    onChange(next.join("\n").replace(/\n+$/, "\n").replace(/^\n+/, ""));
  }

  function insertAfter(i: number) {
    const next = [...rows];
    next.splice(i + 1, 0, "");
    onChange(next.join("\n"));
    focusRow(i + 1);
  }

  function remove(i: number) {
    const next = rows.filter((_, n) => n !== i);
    commit(next.length ? next : [""]);
    focusRow(i - 1);
  }

  function move(i: number, by: number) {
    const to = i + by;
    if (to < 0 || to >= rows.length) return;
    const next = [...rows];
    [next[i], next[to]] = [next[to], next[i]];
    commit(next);
    focusRow(to);
  }

  /** A multi-line paste becomes rows, starting at the one pasted into. */
  function onPaste(i: number, e: React.ClipboardEvent<HTMLInputElement>) {
    const text = e.clipboardData.getData("text");
    if (!text.includes("\n")) return;
    e.preventDefault();
    const pasted = text
      .split("\n")
      // The same de-numbering the brief renderer does, so a contents page
      // pasted here and one read from a screenshot come out identical.
      .map((l) =>
        l
          .trim()
          .replace(/^\d+\s*[.)]\s*/, "")
          .trim(),
      )
      .filter(Boolean);
    const next = [...rows];
    next.splice(i, 1, ...pasted);
    commit(next);
    focusRow(i + pasted.length - 1);
  }

  function onKeyDown(i: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      insertAfter(i);
    } else if (e.key === "Backspace" && rows[i] === "" && rows.length > 1) {
      e.preventDefault();
      remove(i);
    } else if (e.key === "ArrowDown" && e.metaKey) {
      e.preventDefault();
      move(i, 1);
    } else if (e.key === "ArrowUp" && e.metaKey) {
      e.preventDefault();
      move(i, -1);
    }
  }

  return (
    <div className="bf-chapters">
      <ol className="bf-chapters-rows" ref={rootRef} aria-labelledby={labelId}>
        {rows.map((row, i) => (
          // Index as key, deliberately: the rows ARE positional, and keying on
          // the text would remount every row below an edited one and lose focus.
          <li className="bf-chapter-row" key={i}>
            <span className="bf-chapter-num" aria-hidden="true">
              {i + 1}
            </span>
            <input
              className="intake-input bf-chapter-input"
              type="text"
              value={row}
              aria-label={`Chapter ${i + 1}`}
              aria-describedby={describedBy}
              placeholder={i === 0 ? "First chapter's title…" : ""}
              onChange={(e) => setRow(i, e.target.value)}
              onPaste={(e) => onPaste(i, e)}
              onKeyDown={(e) => onKeyDown(i, e)}
            />
            <span className="bf-chapter-tools">
              <button
                type="button"
                className="bf-chapter-btn"
                onClick={() => move(i, -1)}
                disabled={i === 0}
                aria-label={`Move chapter ${i + 1} up`}
                title="Move up (⌘↑)"
              >
                ↑
              </button>
              <button
                type="button"
                className="bf-chapter-btn"
                onClick={() => move(i, 1)}
                disabled={i === rows.length - 1}
                aria-label={`Move chapter ${i + 1} down`}
                title="Move down (⌘↓)"
              >
                ↓
              </button>
              <button
                type="button"
                className="bf-chapter-btn bf-chapter-btn--remove"
                onClick={() => remove(i)}
                aria-label={`Remove chapter ${i + 1}`}
                title="Remove"
              >
                ×
              </button>
            </span>
          </li>
        ))}
      </ol>
      <div className="bf-chapters-foot">
        <button
          type="button"
          className="intake-btn intake-btn--ghost bf-chapters-add"
          onClick={() => insertAfter(rows.length - 1)}
        >
          Add a chapter
        </button>
        <span className="intake-hint bf-chapters-count">
          Enter adds a row · ⌘↑ / ⌘↓ moves one · paste a whole list into any row
        </span>
      </div>
    </div>
  );
}
