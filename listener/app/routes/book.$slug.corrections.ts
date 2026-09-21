import type { Route } from "./+types/book.$slug.corrections";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireModerator } from "~/middleware/moderator";
import { requireUnitAccess } from "~/middleware/entitled";
import { session } from "~/middleware/session";
import {
  CorrectionError,
  addComment,
  decideCorrection,
  findOccurrences,
  listCorrections,
  proposeCorrection,
  proposeMany,
  removeComment,
  removeCorrection,
  reviseCorrection,
  triageSuggestion,
  type Actor,
} from "~/server/corrections.server";
import {
  chapterProgress,
  claimChapter,
  setChapterReviewed,
} from "~/server/moderationProgress.server";
import { historyFor } from "~/server/correctionHistory.server";
import { sourceFor } from "~/server/sourceOcr.server";

/**
 * Corrections on one book — for moderators and admins ONLY.
 *
 * A resource route hung off `book/:slug`, like `marks`, so `requireUnitAccess` reads the SAME
 * `params.slug` the reading page did: an endpoint addressed any other way would need an
 * access rule of its own. Then `requireModerator`, so a reader who can open the book still
 * gets a 404 here — indistinguishable from a route that does not exist.
 *
 * Plain JSON in and out, and the client uses `fetch` rather than a router form submission,
 * for the reason `marks` does: a router submission revalidates every loader on the page, and
 * saving a correction must not reload the chapter the moderator is reading.
 *
 * Every write refuses while the administrator is simulating somebody, by the explicit check at the top
 * of `action`. That check is NOT redundant: while simulating, `isModerator` is the simulated person's
 * OWN status (so the administrator can see a moderator's whole experience), which means the gate above
 * lets a simulated moderator through to READ — and only this check stops them writing as her.
 */
export const middleware: Route.MiddlewareFunction[] = [
  requireUnitAccess,
  requireModerator,
];

const actorOf = (context: Route.LoaderArgs["context"]): Actor => {
  const viewer = context.get(session).viewer;
  if (viewer === null) notFound();
  return {
    email: viewer.email,
    isAdmin: viewer.isAdmin,
    isModerator: viewer.isModerator,
  };
};

/**
 * One GET endpoint, four questions, told apart by the query string:
 *   ?source=<chapter>                       the source text for that chapter
 *   ?occurrences=<words>&chapter=&block=    other places the same words appear
 *   ?history=<id>|all                       the recorded history of one correction, or of all
 *   (nothing)                               the corrections, and how far the book's review has got
 * Each is answered by a function that itself returns nothing for a non-moderator.
 */
export async function loader({ request, params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const actor = actorOf(context);
  const query = new URL(request.url).searchParams;
  const noStore = { headers: { "Cache-Control": "no-store" } };

  const source = query.get("source");
  if (source !== null)
    return Response.json(
      { source: await sourceFor(env.DB, actor, params.slug, source) },
      noStore,
    );

  const history = query.get("history");
  if (history !== null)
    return Response.json(
      {
        history: await historyFor(
          env.DB,
          actor,
          params.slug,
          history === "all" ? null : history,
        ),
      },
      noStore,
    );

  const words = query.get("occurrences");
  if (words !== null)
    return Response.json(
      {
        occurrences: await findOccurrences(env.DB, actor, params.slug, words, {
          anchorKey: query.get("chapter") ?? "",
          blockIndex: Number(query.get("block")),
        }),
      },
      noStore,
    );

  const [corrections, chapters] = await Promise.all([
    listCorrections(env.DB, actor, params.slug),
    chapterProgress(env.DB, actor, params.slug),
  ]);
  // The whole value of this list is that it is current.
  return Response.json({ corrections, chapters }, noStore);
}

const STATUS = {
  forbidden: 403,
  stale: 409,
  invalid: 400,
  missing: 404,
} as const;

export async function action({ request, params, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const actor = actorOf(context);

  // Nothing is written while the administrator is looking as somebody else. Every correction,
  // comment and review mark is keyed on the viewer's address, and during a simulation that IS the
  // simulated person — so pressing a button here would raise, edit or comment AS HER. Refused
  // loudly rather than answered as success: unlike a reading position, a correction is something
  // the administrator would otherwise believe they had made.
  if (context.get(session).simulating !== null)
    return Response.json(
      { error: "You are viewing as somebody else, so nothing is saved." },
      { status: 403 },
    );
  const form = await request.formData();
  const field = (name: string) => form.get(name);
  const id = String(field("id") ?? "");
  const now = new Date().toISOString();

  try {
    switch (String(field("intent"))) {
      case "propose": {
        const created = await proposeCorrection(
          env.DB,
          actor,
          params.slug,
          {
            anchorKey: field("anchorKey"),
            blockIndex: field("blockIndex"),
            startOffset: field("startOffset"),
            endOffset: field("endOffset"),
            quote: field("quote"),
            prefix: field("prefix"),
            proposedText: field("proposedText"),
            rationale: field("rationale"),
            kind: field("kind"),
          },
          now,
        );
        return Response.json({ ok: true, id: created });
      }

      case "revise":
        await reviseCorrection(
          env.DB,
          actor,
          params.slug,
          id,
          {
            proposedText: field("proposedText"),
            rationale: field("rationale"),
            kind: field("kind"),
          },
          now,
        );
        return Response.json({ ok: true });

      // One intent for a moderator withdrawing their own and an admin deleting any; which it
      // is, and whether it is allowed, is decided by `authority` — never by the intent name.
      case "remove":
        await removeCorrection(env.DB, actor, params.slug, id, now);
        return Response.json({ ok: true });

      // A pipeline suggestion: any moderator may confirm it (-> open) or dismiss it.
      case "confirm":
      case "dismiss-suggestion":
        await triageSuggestion(
          env.DB,
          actor,
          params.slug,
          id,
          String(field("intent")) === "confirm" ? "confirm" : "dismiss",
          field("expectedUpdatedAt"),
          field("note"),
          now,
        );
        return Response.json({ ok: true });

      // "Fix everywhere": the same replacement at several places, as ONE reviewed batch.
      case "propose-many": {
        let items: unknown;
        try {
          items = JSON.parse(String(field("items") ?? "[]"));
        } catch {
          return Response.json(
            { error: "Could not read the places." },
            { status: 400 },
          );
        }
        if (!Array.isArray(items))
          return Response.json(
            { error: "Could not read the places." },
            { status: 400 },
          );
        const made = await proposeMany(
          env.DB,
          actor,
          params.slug,
          String(field("quote") ?? ""),
          items,
          {
            proposedText: field("proposedText"),
            rationale: field("rationale"),
            kind: field("kind"),
          },
          now,
        );
        return Response.json({ ok: true, ...made });
      }

      // Any moderator or admin may comment on any correction; only the author (or an admin)
      // may take a comment back. Commenting never changes the correction.
      case "comment":
        await addComment(env.DB, actor, params.slug, id, field("body"), now);
        return Response.json({ ok: true });

      case "uncomment":
        await removeComment(env.DB, actor, params.slug, id, now);
        return Response.json({ ok: true });

      case "review":
        await setChapterReviewed(
          env.DB,
          actor,
          params.slug,
          String(field("anchorKey") ?? ""),
          field("on") === "1",
          now,
        );
        return Response.json({ ok: true });

      case "claim":
        await claimChapter(
          env.DB,
          actor,
          params.slug,
          String(field("anchorKey") ?? ""),
          field("on") === "1",
          now,
        );
        return Response.json({ ok: true });

      case "accept":
      case "dismiss":
        await decideCorrection(
          env.DB,
          actor,
          params.slug,
          id,
          String(field("intent")) === "accept" ? "accepted" : "dismissed",
          field("expectedUpdatedAt"),
          field("note"),
          now,
        );
        return Response.json({ ok: true });

      default:
        return Response.json({ error: "Unknown action." }, { status: 400 });
    }
  } catch (error) {
    if (error instanceof CorrectionError)
      return Response.json(
        { error: error.message },
        { status: STATUS[error.reason] },
      );
    throw error;
  }
}
