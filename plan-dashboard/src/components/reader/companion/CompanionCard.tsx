/**
 * CompanionCard — presentational render of ONE companion note.
 *
 * All note formatting lives here and nothing else — change how a note looks by
 * editing this file alone. It holds no state and no persistence; it emits intent
 * (edit / delete) to its parent. Colours come from data-attributes resolved in
 * companion-notes.css (zero inline styles, per the site DoD).
 */
import {
  kindDef,
  sourceProvider,
} from "../../../lib/reader/companion/registry";
import type { CompanionNote } from "../../../lib/reader/companion/types";

interface Props {
  note: CompanionNote;
  /** Present mode hides the edit/delete controls for distraction-free reading. */
  readOnly?: boolean;
  /** This note's passage is the one currently in view in the chapter. */
  active?: boolean;
  onEdit?: (note: CompanionNote) => void;
  onDelete?: (note: CompanionNote) => void;
  /** Scroll the chapter to this note's marked passage. Omitted when the passage
   *  could not be marked (absent from the text, or split by inline markup), so
   *  the pill stays plain text rather than offering a jump that goes nowhere. */
  onReveal?: (note: CompanionNote) => void;
}

function sourceLabel(note: CompanionNote): string | null {
  const s = note.source;
  if (!s) return null;
  if (s.label) return s.label;
  const p = sourceProvider(s.provider);
  return [p.label, s.ref, s.locator].filter(Boolean).join(" · ");
}

export default function CompanionCard({
  note,
  readOnly,
  active,
  onEdit,
  onDelete,
  onReveal,
}: Props) {
  const kind = kindDef(note.kind);
  const src = note.source ? sourceProvider(note.source.provider) : null;
  const label = sourceLabel(note);

  return (
    <article
      className={`cpn-card${active ? " is-active" : ""}`}
      data-kind={note.kind}
      data-note-id={note.id}
    >
      <header className="cpn-card-head">
        <span className="cpn-kind">
          <i className={kind.icon} aria-hidden="true" />
          {kind.label}
        </span>
        {!readOnly && (
          <span className="cpn-card-actions">
            <button
              type="button"
              className="cpn-icon-btn"
              aria-label="Edit note"
              onClick={() => onEdit?.(note)}
            >
              <i className="fa-solid fa-pen" aria-hidden="true" />
            </button>
            <button
              type="button"
              className="cpn-icon-btn"
              aria-label="Delete note"
              onClick={() => onDelete?.(note)}
            >
              <i className="fa-solid fa-trash" aria-hidden="true" />
            </button>
          </span>
        )}
      </header>

      {note.anchor && <p className="cpn-anchor">“{note.anchor}”</p>}
      {note.quote &&
        (onReveal ? (
          /* The passage IS marked in the chapter, so the pill is the way back to
             it — a real button, so it is reachable by keyboard, not a click
             handler bolted onto a paragraph. */
          <button
            type="button"
            className="cpn-quote-mark cpn-quote-mark--jump"
            title={`Go to this passage: ${note.quote}`}
            onClick={() => onReveal(note)}
          >
            <i className="fa-solid fa-highlighter" aria-hidden="true" />{" "}
            {note.quote}
          </button>
        ) : (
          <p className="cpn-quote-mark" title={note.quote}>
            <i className="fa-solid fa-highlighter" aria-hidden="true" />{" "}
            {note.quote}
          </p>
        ))}
      <p className="cpn-body">{note.body}</p>

      {label && (
        <p className="cpn-src" data-provider={note.source?.provider}>
          {src && <i className={src.icon} aria-hidden="true" />}
          {label}
        </p>
      )}
    </article>
  );
}
