import type { Route } from "./+types/offline.allowed";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";

/**
 * Which books this viewer may still read — the answer the lease is enforced
 * against.
 *
 * Asif's decision, 2026-08-11: an episode on a phone cannot be re-checked the
 * way `routes/media.$slug.$.tsx` re-checks every byte range, so withdrawing
 * access takes effect the next time the app opens with a network. This route is
 * that check, and `lib/offline.purgeExcept` is what acts on it.
 *
 * It asks `visibleUnits` — the ONE place the entitlement rule is written — and
 * does no filtering of its own. A second predicate here would be a second answer
 * to who may read what, and it would be the one that decides whether somebody's
 * downloads survive.
 *
 * It returns SLUGS ONLY. Titles would make this a catalogue endpoint, and the
 * caller already holds the titles of everything it downloaded.
 *
 * Gated by position under `_authed`, like every other route. Signed out it
 * redirects rather than answering, which the caller treats as "I could not find
 * out" and changes nothing — see `purgeExcept`, which takes null for exactly
 * that case.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;

  const units = await visibleUnits(env.DB, viewer.email);

  return Response.json(
    { slugs: units.map((unit) => unit.slug) },
    // Never cached. The whole value of this answer is that it is current: a
    // stale copy is a withdrawn book staying playable for as long as the cache
    // lives, which is the thing the lease exists to bound.
    { headers: { "Cache-Control": "no-store" } },
  );
}
