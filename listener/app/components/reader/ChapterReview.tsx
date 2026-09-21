import type { ChapterProgress } from "~/lib/corrections";

/**
 * "I have read this chapter against the source" — and how far the whole book has got.
 *
 * Without it a book with no corrections is indistinguishable from a book nobody read, and there is
 * no honest way to say a book is ready to come out of moderation. A chapter can also be CLAIMED, so
 * two people do not read the same one.
 */
export function ChapterReview({
  chapters,
  current,
  busy,
  onReview,
  onClaim,
}: {
  chapters: ChapterProgress[];
  current: string;
  busy: boolean;
  onReview: (anchorKey: string, on: boolean) => void;
  onClaim: (anchorKey: string, on: boolean) => void;
}) {
  if (chapters.length === 0) return null;

  const done = chapters.filter((c) => c.reviewedByName !== null).length;
  const here = chapters.find((c) => c.anchorKey === current);

  return (
    <section className="pf-cx-progress" aria-label="Review progress">
      <p className="pf-cx-progress__line">
        <strong>
          {done} of {chapters.length}
        </strong>{" "}
        chapters read against the source
      </p>
      <progress
        className="pf-cx-progress__bar"
        max={chapters.length}
        value={done}
        aria-label="Chapters reviewed"
      />

      {here === undefined ? null : (
        <div className="pf-cx-progress__here">
          {here.reviewedByName !== null ? (
            <>
              <span>
                Read by {here.reviewedByMe ? "you" : here.reviewedByName}
              </span>
              <button
                type="button"
                disabled={busy}
                onClick={() => onReview(here.anchorKey, false)}
                className="pf-button pf-button--sm pf-button--ghost"
              >
                Undo
              </button>
            </>
          ) : (
            <>
              {here.claimedByName === null ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onClaim(here.anchorKey, true)}
                  className="pf-button pf-button--sm pf-button--ghost"
                >
                  I am reading this one
                </button>
              ) : (
                <span>
                  {here.claimedByMe ? "You are" : `${here.claimedByName} is`}{" "}
                  reading this one
                  {here.claimedByMe ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onClaim(here.anchorKey, false)}
                      className="pf-button pf-button--sm pf-button--ghost"
                    >
                      Release
                    </button>
                  ) : null}
                </span>
              )}
              <button
                type="button"
                disabled={busy}
                onClick={() => onReview(here.anchorKey, true)}
                className="pf-button pf-button--sm pf-cx-ok"
              >
                Mark this chapter read
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}
