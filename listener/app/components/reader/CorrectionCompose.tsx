import { useEffect, useState, type ReactNode } from "react";

import { RichNoteEditor } from "~/components/notes/RichNoteEditor";
import { KINDS, type Kind, type Occurrence } from "~/lib/corrections";
import { CorrectionDiff } from "./CorrectionDiff";

export interface Draft {
  /** Set when revising an existing correction rather than raising a new one. */
  id: string | null;
  quote: string;
  prefix: string;
  proposedText: string;
  rationale: string;
  kind: Kind;
}

const KIND_LABELS: Record<Kind, string> = {
  typo: "Typo",
  arabic: "Arabic",
  meaning: "Meaning",
  citation: "Citation",
  formatting: "Formatting",
  other: "Other",
};

/** A few words at most: the kind of selection that is a one-word typo, not a paragraph. */
const isQuick = (quote: string) =>
  quote.length <= 40 && quote.trim().split(/\s+/).length <= 3;

/**
 * Writing a correction: the passage, the source, what kind of fix it is, the replacement, a live
 * preview of exactly what changes, and the reason.
 *
 * A QUICK FIX (a few words) opens as one field and one button — most corrections are a
 * single-word typo, and the full form is heavy for them. "More options" opens the rest.
 *
 * The replacement is PLAIN text and only the reason is rich, and that split is not cosmetic:
 * `book.md` is markdown and corrections are later applied to it, so a replacement captured as
 * editor HTML could not be applied without a converter — a second answer to what the paragraph
 * says. The reason never reaches the book, so it can be as rich as a note.
 */
export function CorrectionCompose({
  draft,
  busy,
  findOthers,
  renderSource,
  onCancel,
  onSubmit,
}: {
  draft: Draft;
  busy: boolean;
  /** Other places the same wording appears; only asked for a NEW correction. */
  findOthers: (quote: string) => Promise<Occurrence[]>;
  /** The source pane, given a way to put selected source words into the replacement. */
  renderSource: (use: (text: string) => void) => ReactNode;
  onCancel: () => void;
  onSubmit: (draft: Draft, alsoAt: Occurrence[]) => void;
}) {
  const quick = draft.id === null && isQuick(draft.quote);
  const [more, setMore] = useState(!quick);
  const [proposed, setProposed] = useState(draft.proposedText);
  const [rationale, setRationale] = useState(draft.rationale);
  const [kind, setKind] = useState<Kind>(quick ? "typo" : draft.kind);
  const [others, setOthers] = useState<Occurrence[]>([]);
  const [chosen, setChosen] = useState<Set<number>>(new Set());
  const unchanged = proposed.trim() === draft.quote.trim();

  useEffect(() => {
    if (draft.id !== null) return;
    let live = true;
    void findOthers(draft.quote).then((found) => {
      if (!live) return;
      setOthers(found);
      setChosen(new Set());
    });
    return () => {
      live = false;
    };
  }, [draft.id, draft.quote, findOthers]);

  const toggle = (i: number) =>
    setChosen((now) => {
      const next = new Set(now);
      if (!next.delete(i)) next.add(i);
      return next;
    });

  const insert = (text: string) =>
    setProposed((now) => (unchanged ? text : `${now} ${text}`));

  return (
    <section className="pf-cx-compose" aria-label="Correct this passage">
      <p className="pf-cx-eyebrow">The passage</p>
      <blockquote className="pf-cx-quote">
        {draft.prefix === "" ? null : <span>…{draft.prefix}</span>}
        <mark className="pf-hl pf-hl--gold">{draft.quote}</mark>
      </blockquote>

      <label className="pf-cx-field">
        <span className="pf-cx-eyebrow">
          {quick ? "Change it to" : "Replacement text"}{" "}
          <em>plain text — this is what goes into the book</em>
        </span>
        <textarea
          value={proposed}
          onChange={(event) => setProposed(event.target.value)}
          rows={quick ? 2 : 4}
          className="pf-cx-textarea"
          autoFocus
        />
      </label>

      <div className="pf-cx-diff" aria-live="polite">
        <p className="pf-cx-eyebrow">What will change</p>
        <p className="pf-cx-diff__body">
          {unchanged ? (
            <span className="pf-cx-hint">
              No change yet — edit the text above.
            </span>
          ) : (
            <CorrectionDiff before={draft.quote} after={proposed} />
          )}
        </p>
      </div>

      {others.length === 0 || unchanged ? null : (
        <fieldset className="pf-cx-occ">
          <legend className="pf-cx-eyebrow">
            Also appears {others.length} time{others.length === 1 ? "" : "s"}{" "}
            elsewhere
          </legend>
          <p className="pf-cx-hint">
            Tick the places to fix too. They are raised together and decided
            together.
          </p>
          {others.map((o, i) => (
            <label
              key={`${o.anchorKey}:${o.blockIndex}`}
              className="pf-cx-occ__row"
            >
              <input
                type="checkbox"
                checked={chosen.has(i)}
                onChange={() => toggle(i)}
              />
              <span>
                <strong>{o.heading}</strong> — …{o.prefix.slice(-30)}
                <mark>{o.quote}</mark>
              </span>
            </label>
          ))}
          <button
            type="button"
            className="pf-button pf-button--sm pf-button--ghost"
            onClick={() =>
              setChosen(
                chosen.size === others.length
                  ? new Set()
                  : new Set(others.map((_, i) => i)),
              )
            }
          >
            {chosen.size === others.length ? "Clear all" : "Select all"}
          </button>
        </fieldset>
      )}

      <details className="pf-cx-sourcebox" open={!quick}>
        <summary className="pf-cx-eyebrow">Check the source</summary>
        {renderSource(insert)}
      </details>

      {more ? (
        <>
          <p className="pf-cx-eyebrow">What kind of fix</p>
          <div
            role="radiogroup"
            aria-label="Kind of correction"
            className="pf-cx-kinds"
          >
            {KINDS.map((k) => (
              <button
                key={k}
                type="button"
                role="radio"
                aria-checked={kind === k}
                onClick={() => setKind(k)}
              >
                {KIND_LABELS[k]}
              </button>
            ))}
          </div>

          <div className="pf-cx-field">
            <span className="pf-cx-eyebrow">
              Why <em>so the person deciding can see your reasoning</em>
            </span>
            <RichNoteEditor
              key={draft.id ?? "new"}
              initialValue={draft.rationale}
              onChange={setRationale}
              placeholder="What does the source say? Give a page or a line if you can."
              ariaLabel="Why this correction"
            />
          </div>
        </>
      ) : (
        <button
          type="button"
          className="pf-cx-more"
          onClick={() => setMore(true)}
        >
          More options — kind of fix and reason
        </button>
      )}

      <div className="pf-cx-actions">
        <button
          type="button"
          onClick={onCancel}
          className="pf-button pf-button--sm pf-button--ghost"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={busy || unchanged || proposed.trim() === ""}
          onClick={() =>
            onSubmit(
              { ...draft, proposedText: proposed, rationale, kind },
              others.filter((_, i) => chosen.has(i)),
            )
          }
          className="pf-button pf-button--sm pf-cx-submit"
        >
          {draft.id !== null
            ? "Save changes"
            : chosen.size > 0
              ? `Submit ${chosen.size + 1} corrections`
              : "Submit correction"}
        </button>
      </div>
    </section>
  );
}
