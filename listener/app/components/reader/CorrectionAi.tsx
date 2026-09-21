import type { AiReview } from "~/lib/corrections";

const VERDICTS: Record<AiReview["verdict"], string> = {
  supports: "Supports this",
  revise: "Suggests a change",
  reject: "Does not support this",
  needs_human: "Needs a person",
};

const CONFIDENCE: Record<AiReview["confidence"], string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

const MARK = { ok: "✓", warn: "!", no: "✕" } as const;

/**
 * What the AI reviewer made of a correction — advisory, and visibly so.
 *
 * A quiet block under the reasoning, never a button that decides. The verdict is a word, the
 * confidence a phrase and the checks a plain list, so a person can see WHY without opening
 * anything. `needs_human` is a first-class answer, not a failure: "the scan is cut off here" is
 * worth more than a confident guess on a religious text.
 *
 * Everything it shows arrives as data and is rendered by React, so it is escaped — the reviewer's
 * text is never trusted as markup.
 */
export function CorrectionAi({
  review,
  onUseSuggestion,
}: {
  review: AiReview;
  /** Offered only to whoever may edit the proposal; taking it goes through the same gates. */
  onUseSuggestion?: (text: string) => void;
}) {
  return (
    <details className="pf-cx-ai" data-verdict={review.verdict}>
      <summary>
        <span className="pf-cx-ai__badge">AI review</span>
        <strong>{VERDICTS[review.verdict]}</strong>
        <span className="pf-cx-ai__conf">{CONFIDENCE[review.confidence]}</span>
      </summary>

      <p className="pf-cx-ai__text">{review.summary}</p>

      {review.suggestedText === null ? null : (
        <p className="pf-cx-ai__suggest">
          <span>Suggested wording:</span> {review.suggestedText}
          {onUseSuggestion === undefined ? null : (
            <button
              type="button"
              className="pf-button pf-button--sm pf-button--soft"
              onClick={() => onUseSuggestion(review.suggestedText!)}
            >
              Use this wording
            </button>
          )}
        </p>
      )}

      {review.checks.length === 0 ? null : (
        <ul className="pf-cx-ai__checks">
          {review.checks.map((check) => (
            <li key={check.id} data-result={check.result}>
              <span aria-hidden="true">{MARK[check.result]}</span> {check.note}
            </li>
          ))}
        </ul>
      )}

      <p className="pf-cx-ai__note">
        Advisory only — an admin decides.
        {review.sourceKind === "none"
          ? " No source text was available."
          : ` Checked against the ${review.sourceKind === "scan" ? "scanned" : "extracted"} source.`}
      </p>
    </details>
  );
}
