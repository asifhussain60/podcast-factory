import type { Route } from "./+types/book.$slug.marks";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { session } from "~/middleware/session";
import {
  countryCodeFromRequest,
  recordUsageActivity,
} from "~/server/analytics.server";
import {
  addBookmark,
  InvalidMarkError,
  marksFor,
  removeAnnotation,
  removeBookmark,
  removeEpisodeNote,
  saveAnnotation,
  saveEpisodeNote,
  setListening,
  setProgress,
} from "~/server/marks.server";

/**
 * One person's marks in one book: read them, write them.
 *
 * A resource route (no default export), so it answers with JSON rather than a
 * document. It hangs off `/book/:slug/` for a reason that is structural rather
 * than tidy: `requireUnitAccess` reads `params.slug`, so mounting here means this
 * endpoint runs the EXACT check the reading page ran, on the same parameter,
 * through the same resolver. An endpoint at `/api/marks?slug=…` would need its
 * own access rule — a second rule, which is a rule that can drift.
 *
 * It sits inside `_authed` in app/routes.ts like everything else. Position is the
 * policy; nothing here compares a pathname.
 *
 * The write side takes form data with an `intent`, which is this application's
 * existing write idiom (see the admin action in admin.people.tsx). The client
 * posts through `useFetcher`, so the same shape serves a JS caller and a plain
 * form, and `navigator.sendBeacon` — which can only send a body, never a header —
 * can post progress on page-hide without a special case.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer;

  // Unreachable — requireUnitAccess has already 404'd a null viewer. Narrowing
  // rather than asserting, because the day that changes this should stop
  // compiling rather than start writing rows keyed on "undefined".
  if (viewer === null) notFound();

  return marksFor(env.DB, viewer.email, params.slug);
}

export async function action({ request, params, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const { viewer, simulating } = context.get(session);
  if (viewer === null) notFound();

  /* ---- Nothing is written while the administrator is looking as somebody ----
     Every mark in this application is keyed on `viewer.email`, and during a
     simulation that IS the simulated person — so reading a chapter this way
     would move their bookmark, repaint their highlights and overwrite where they
     had got to. Seeing what someone sees must not edit what they have.

     Answered as success rather than refused, deliberately. The client keeps an
     outbox and retries what fails, so a 403 here would build a queue that
     flushes the moment the simulation ends — as the ADMINISTRATOR, which is the
     very write this is preventing. The banner on every page says nothing is
     saved, so the only party who could be misled has already been told.       */
  if (simulating !== null) return { ok: true, simulated: true };

  const form = await request.formData();
  const intent = String(form.get("intent"));
  const slug = params.slug;
  const email = viewer.email;
  const now = new Date().toISOString();
  const countryCode = countryCodeFromRequest(request);

  const field = (name: string) => form.get(name);

  try {
    switch (intent) {
      case "progress": {
        const anchorKey = field("anchorKey");
        await setProgress(
          env.DB,
          email,
          slug,
          {
            anchorKey,
            fraction: field("fraction"),
            chaptersDone: field("chaptersDone") ?? 0,
          },
          now,
        );
        await recordUsageActivity(env.DB, {
          email,
          slug,
          kind: "read",
          targetKey: String(anchorKey),
          countryCode,
          now,
        }).catch(() => undefined);
        break;
      }

      case "listening": {
        const number = field("number");
        await setListening(
          env.DB,
          email,
          slug,
          { number, seconds: field("seconds") },
          now,
        );
        await recordUsageActivity(env.DB, {
          email,
          slug,
          kind: "listen",
          targetKey: String(number),
          countryCode,
          now,
        }).catch(() => undefined);
        break;
      }

      case "bookmark":
        await addBookmark(
          env.DB,
          email,
          slug,
          {
            id: field("id"),
            anchorKey: field("anchorKey"),
            blockIndex: field("blockIndex"),
            label: field("label"),
          },
          now,
        );
        break;

      case "unbookmark":
        await removeBookmark(env.DB, email, slug, field("id"), now);
        break;

      // One intent for create, recolour and note-edit alike. They are the same
      // UPSERT with different fields changed, and splitting them into three
      // intents would mean three code paths that must agree about what an
      // annotation is.
      case "annotate":
        await saveAnnotation(
          env.DB,
          email,
          slug,
          {
            id: field("id"),
            anchorKey: field("anchorKey"),
            blockIndex: field("blockIndex"),
            startOffset: field("startOffset"),
            endOffset: field("endOffset"),
            quote: field("quote"),
            prefix: field("prefix"),
            colour: field("colour"),
            note: field("note"),
          },
          now,
        );
        break;

      case "unannotate":
        await removeAnnotation(env.DB, email, slug, field("id"), now);
        break;

      // The audio counterpart of `annotate`, and one intent for the same reason:
      // marking a moment with no words and adding the words an hour later are the
      // same row written twice, not two kinds of thing.
      case "episode-note":
        await saveEpisodeNote(
          env.DB,
          email,
          slug,
          {
            id: field("id"),
            number: field("number"),
            seconds: field("seconds"),
            note: field("note"),
            quote: field("quote"),
          },
          now,
        );
        break;

      case "un-episode-note":
        await removeEpisodeNote(env.DB, email, slug, field("id"), now);
        break;

      default:
        return { error: "Unknown action." };
    }
  } catch (error) {
    // A malformed mark is the caller's problem and must not become a 500 — the
    // client replays its outbox, and a 500 is indistinguishable from "the
    // network was down", so it would replay forever. A named error tells it to
    // drop the item instead.
    if (error instanceof InvalidMarkError)
      return { error: error.message, permanent: true };
    throw error;
  }

  return { ok: true };
}
