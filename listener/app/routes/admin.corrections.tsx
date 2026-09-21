import { useEffect, useState } from "react";
import { Link, useFetcher } from "react-router";

import type { Route } from "./+types/admin.corrections";
import { CorrectionAi } from "~/components/reader/CorrectionAi";
import { CorrectionDiff } from "~/components/reader/CorrectionDiff";
import { EmptyState } from "~/components/EmptyState";
import { count } from "~/lib/plural";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import {
  CorrectionError,
  decideCorrection,
  decideMany,
  listUndecided,
  triageSuggestion,
  type Actor,
  type UndecidedCorrection,
} from "~/server/corrections.server";

/**
 * Every correction waiting on a decision, across every book — for the admin, from the keyboard.
 *
 * Reading forty corrections one card at a time is the admin's bottleneck, so this is built to be
 * cleared quickly: `j`/`k` to move, `a` to accept, `d` to dismiss, and one button to accept every
 * correction the AI reviewer supports with high confidence after a glance.
 *
 * Nested under the admin layout, so `requireAdmin` guards both the page and its action. Every
 * accept carries the concurrency token the admin SAW: one that changed since is skipped and
 * reported, never applied, so "accept all" cannot ship a proposal nobody read.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;
  const actor: Actor = {
    email: viewer.email,
    isAdmin: viewer.isAdmin,
    isModerator: viewer.isModerator,
  };
  return { queue: await listUndecided(env.DB, actor) };
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;
  const actor: Actor = {
    email: viewer.email,
    isAdmin: viewer.isAdmin,
    isModerator: viewer.isModerator,
  };
  const form = await request.formData();
  const field = (name: string) => String(form.get(name) ?? "");
  const now = new Date().toISOString();

  try {
    switch (field("intent")) {
      case "accept":
      case "dismiss": {
        const accept = field("intent") === "accept";
        const status = field("status");
        // A suggestion the admin dismisses goes through the suggestion path (its own audit row);
        // everything else is an ordinary decision.
        if (!accept && status === "suggested")
          await triageSuggestion(
            env.DB,
            actor,
            field("slug"),
            field("id"),
            "dismiss",
            field("expectedUpdatedAt"),
            field("note"),
            now,
          );
        else
          await decideCorrection(
            env.DB,
            actor,
            field("slug"),
            field("id"),
            accept ? "accepted" : "dismissed",
            field("expectedUpdatedAt"),
            field("note"),
            now,
          );
        return { ok: true as const };
      }

      case "accept-supported": {
        const picks = JSON.parse(field("picks")) as {
          slug: string;
          id: string;
          expectedUpdatedAt: string;
        }[];
        return {
          ok: true as const,
          ...(await decideMany(env.DB, actor, picks, now)),
        };
      }

      default:
        return { error: "Unknown action." };
    }
  } catch (error) {
    if (error instanceof CorrectionError) return { error: error.message };
    throw error;
  }
}

const supported = (c: UndecidedCorrection) =>
  c.review?.verdict === "supports" && c.review.confidence === "high";

export default function AdminCorrections({ loaderData }: Route.ComponentProps) {
  const { queue } = loaderData;
  const fetcher = useFetcher<typeof action>();
  const [at, setAt] = useState(0);
  const current = queue[Math.min(at, queue.length - 1)];
  const easy = queue.filter(supported);

  const decide = (intent: "accept" | "dismiss", c: UndecidedCorrection) =>
    fetcher.submit(
      {
        intent,
        slug: c.slug,
        id: c.id,
        status: c.status,
        expectedUpdatedAt: c.updatedAt,
      },
      { method: "post" },
    );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      // Never steal a keystroke from somebody typing.
      const target = event.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      if (
        target?.isContentEditable ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      )
        return;

      if (event.key === "j") setAt((i) => Math.min(i + 1, queue.length - 1));
      else if (event.key === "k") setAt((i) => Math.max(i - 1, 0));
      else if (
        (event.key === "a" || event.key === "d") &&
        current &&
        fetcher.state === "idle"
      )
        decide(event.key === "a" ? "accept" : "dismiss", current);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (queue.length === 0)
    return <EmptyState>Nothing is waiting on a decision.</EmptyState>;

  return (
    <div className="pf-cx-triage">
      <p className="pf-cx-triage__hint">
        <kbd>j</kbd> / <kbd>k</kbd> move · <kbd>a</kbd> accept · <kbd>d</kbd>{" "}
        dismiss · {count(queue.length, "correction is", "corrections are")}{" "}
        waiting
      </p>

      {easy.length === 0 ? null : (
        <fetcher.Form
          method="post"
          onSubmit={(event) => {
            if (
              !window.confirm(
                `Accept the ${easy.length} the AI supports with high confidence? Each is checked against what you saw.`,
              )
            )
              event.preventDefault();
          }}
        >
          <input type="hidden" name="intent" value="accept-supported" />
          <input
            type="hidden"
            name="picks"
            value={JSON.stringify(
              easy.map((c) => ({
                slug: c.slug,
                id: c.id,
                expectedUpdatedAt: c.updatedAt,
              })),
            )}
          />
          <button type="submit" className="pf-button pf-cx-ok">
            Accept all {easy.length} the AI supports with high confidence
          </button>
        </fetcher.Form>
      )}

      {fetcher.data && "error" in fetcher.data ? (
        <p role="alert" className="pf-message pf-message--warn">
          {fetcher.data.error}
        </p>
      ) : null}
      {fetcher.data && "accepted" in fetcher.data ? (
        <p role="status" className="pf-message">
          Accepted {fetcher.data.accepted}
          {fetcher.data.skipped > 0
            ? `; skipped ${fetcher.data.skipped} that changed since you looked`
            : ""}
          .
        </p>
      ) : null}

      {queue.map((c, i) => (
        <article
          key={c.id}
          className="pf-cx-card"
          data-status={c.status}
          aria-current={i === at ? "true" : undefined}
        >
          <header className="pf-cx-card__top">
            <strong className="pf-cx-triage__book">{c.bookTitle}</strong>
            <span className="pf-cx-card__who">{c.raisedByName}</span>
            {c.certainty === null ? null : (
              <span className="pf-cx-badge">{c.certainty}% sure</span>
            )}
            <span className="pf-cx-kind">{c.kind}</span>
          </header>
          <p className="pf-cx-card__change">
            <CorrectionDiff before={c.quote} after={c.proposedText} />
          </p>
          {c.review === null ? null : <CorrectionAi review={c.review} />}
          <footer className="pf-cx-card__foot">
            <button
              type="button"
              onClick={() => decide("accept", c)}
              className="pf-button pf-button--sm pf-cx-ok"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => decide("dismiss", c)}
              className="pf-button pf-button--sm pf-button--ghost"
            >
              Dismiss
            </button>
            <Link
              to={`/book/${c.slug}/read/${encodeURIComponent(c.anchorKey)}`}
              className="pf-button pf-button--sm pf-button--ghost"
            >
              Open in the book
            </Link>
          </footer>
        </article>
      ))}
    </div>
  );
}
