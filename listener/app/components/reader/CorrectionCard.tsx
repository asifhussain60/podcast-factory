import { useState } from "react";
import { faLock } from "@fortawesome/free-solid-svg-icons";

import { Icon } from "~/components/Icon";
import type { Correction } from "~/lib/corrections";
import { renderNote } from "~/lib/richNote";
import { CorrectionAi } from "./CorrectionAi";
import { CorrectionDiff } from "./CorrectionDiff";
import { CorrectionHistory } from "./CorrectionHistory";
import type { CorrectionEvent } from "~/lib/correctionHistory";

/**
 * One correction, with only the controls its viewer may use.
 *
 * `authority` is computed on the SERVER and arrives with the row. The controls hidden here are
 * hidden for tidiness only: the route refuses the same actions regardless, so a request that
 * skips this component gets the same "no".
 */
export function CorrectionCard({
  correction: c,
  busy,
  onEdit,
  onAccept,
  onDismiss,
  onConfirm,
  onRemove,
  onUseSuggestion,
  onComment,
  onUncomment,
  bookTitle,
  loadHistory,
}: {
  correction: Correction;
  busy: boolean;
  onEdit: (c: Correction) => void;
  onAccept: (c: Correction) => void;
  onDismiss: (c: Correction, note: string) => void;
  onConfirm: (c: Correction) => void;
  onRemove: (c: Correction) => void;
  onUseSuggestion: (c: Correction, text: string) => void;
  onComment: (c: Correction, body: string) => void;
  onUncomment: (commentId: string) => void;
  bookTitle: string;
  loadHistory: (id: string) => Promise<CorrectionEvent[]>;
}) {
  const [dismissing, setDismissing] = useState(false);
  const [note, setNote] = useState("");
  const [talking, setTalking] = useState(false);
  const [remark, setRemark] = useState("");
  const suggested = c.status === "suggested";
  // An admin decides directly; a moderator only triages a suggestion.
  const canEditWording = c.authority === "full" || c.authority === "own";

  const status = suggested
    ? "Suggested by the audit"
    : c.status === "accepted"
      ? `Accepted by ${c.decidedByName ?? "an admin"} · waits for the next republish`
      : c.status === "dismissed"
        ? `Dismissed by ${c.decidedByName ?? "an admin"}`
        : c.status === "applied"
          ? "In the book"
          : "Open";

  const button = (
    label: string,
    onClick: () => void,
    variant: "ghost" | "ok" | "danger" = "ghost",
  ) => (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className={`pf-button pf-button--sm ${
        variant === "ok"
          ? "pf-cx-ok"
          : variant === "danger"
            ? "pf-button--ghost pf-cx-danger"
            : "pf-button--ghost"
      }`}
    >
      {label}
    </button>
  );

  return (
    <article
      className="pf-cx-card"
      data-status={c.status}
      data-mine={c.mine}
      id={`correction-${c.id}`}
    >
      <header className="pf-cx-card__top">
        <span className="pf-cx-avatar" aria-hidden="true">
          {c.raisedByName.slice(0, 1).toUpperCase()}
        </span>
        <span className="pf-cx-card__who">
          {c.mine ? "You" : c.raisedByName}
        </span>
        {c.certainty === null ? null : (
          <span className="pf-cx-badge">{c.certainty}% sure</span>
        )}
        {c.batchId === null ? null : (
          <span
            className="pf-cx-badge"
            title="Raised together, decided together"
          >
            batch
          </span>
        )}
        <span className="pf-cx-kind">{c.kind}</span>
      </header>

      <p className="pf-cx-card__change">
        <CorrectionDiff before={c.quote} after={c.proposedText} />
      </p>

      {c.rationaleHtml === "" ? null : (
        <div className="pf-cx-card__why">{renderNote(c.rationaleHtml)}</div>
      )}

      {c.decisionNote === null ? null : (
        <p className="pf-cx-card__why">
          <strong>Decision:</strong> {c.decisionNote}
        </p>
      )}

      {c.review === null ? null : (
        <CorrectionAi
          review={c.review}
          onUseSuggestion={
            canEditWording ? (text) => onUseSuggestion(c, text) : undefined
          }
        />
      )}

      <footer className="pf-cx-card__foot">
        <span className="pf-cx-status" data-status={c.status}>
          {status}
        </span>

        {c.authority === "full" ? (
          <>
            {c.status === "open" || suggested ? (
              <>
                {button("Accept", () => onAccept(c), "ok")}
                {button("Dismiss", () => setDismissing((open) => !open))}
              </>
            ) : null}
            {button("Edit", () => onEdit(c))}
            {button(
              "Delete",
              () => {
                if (
                  window.confirm(
                    "Delete this correction? It disappears from every view.",
                  )
                )
                  onRemove(c);
              },
              "danger",
            )}
          </>
        ) : c.authority === "triage" ? (
          <>
            {button("Confirm", () => onConfirm(c), "ok")}
            {button("Not an error", () => setDismissing((open) => !open))}
          </>
        ) : c.authority === "own" ? (
          <>
            {button("Edit", () => onEdit(c))}
            {button("Withdraw", () => onRemove(c))}
          </>
        ) : (
          <span className="pf-cx-lock">
            <Icon icon={faLock} title="Locked" />
            {c.status !== "open" && c.status !== "suggested"
              ? "Decided — closed to changes"
              : c.mine || c.origin === "sweep"
                ? "Waiting for an admin to decide"
                : `Raised by ${c.raisedByName} — only they or an admin can change this`}
          </span>
        )}
      </footer>

      {/* Commenting is open to every moderator and admin on every correction, whatever its
          status and whoever raised it — it is how moderators discuss each other's work without
          being able to change it. It never touches the correction itself. */}
      <button
        type="button"
        className="pf-cx-talk"
        aria-expanded={talking}
        onClick={() => setTalking((open) => !open)}
      >
        {c.comments.length === 0
          ? "Comment"
          : `${c.comments.length} comment${c.comments.length === 1 ? "" : "s"}`}
      </button>

      <CorrectionHistory
        correction={c}
        bookTitle={bookTitle}
        load={loadHistory}
      />

      {talking ? (
        <div className="pf-cx-thread">
          {c.comments.map((m) => (
            <div key={m.id} className="pf-cx-comment" data-mine={m.mine}>
              <p className="pf-cx-comment__meta">
                <strong>{m.mine ? "You" : m.authorName}</strong>
                {m.canDelete ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onUncomment(m.id)}
                    className="pf-cx-comment__remove"
                  >
                    Remove
                  </button>
                ) : null}
              </p>
              <p className="pf-cx-comment__body">{m.body}</p>
            </div>
          ))}
          <form
            className="pf-cx-comment__form"
            onSubmit={(event) => {
              event.preventDefault();
              if (remark.trim() === "") return;
              onComment(c, remark);
              setRemark("");
            }}
          >
            <label className="pf-cx-field">
              <span className="sr-only">Your comment</span>
              <input
                value={remark}
                onChange={(event) => setRemark(event.target.value)}
                maxLength={2000}
                placeholder="Add a comment for the other moderators…"
                className="pf-cx-textarea"
              />
            </label>
            <button
              type="submit"
              disabled={busy || remark.trim() === ""}
              className="pf-button pf-button--sm"
            >
              Post
            </button>
          </form>
        </div>
      ) : null}

      {dismissing ? (
        <form
          className="pf-cx-dismiss"
          onSubmit={(event) => {
            event.preventDefault();
            onDismiss(c, note);
            setDismissing(false);
            setNote("");
          }}
        >
          <label className="pf-cx-field">
            <span className="pf-cx-eyebrow">
              Reason <em>optional — the person who raised it will see it</em>
            </span>
            <input
              value={note}
              onChange={(event) => setNote(event.target.value)}
              maxLength={500}
              className="pf-cx-textarea"
              autoFocus
            />
          </label>
          <button type="submit" className="pf-button pf-button--sm">
            Dismiss it
          </button>
        </form>
      ) : null}
    </article>
  );
}
