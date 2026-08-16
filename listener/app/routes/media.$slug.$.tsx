import type { Route } from "./+types/media.$slug.$";
import { cloudflare } from "~/context";
import { parseRange } from "~/lib/media-range";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { mediaByKey } from "~/server/catalog.server";

/**
 * Audio, print editions, covers and deck pages — everything the reader
 * downloads or streams.
 *
 * A resource route: no component, so the response is the file itself.
 *
 * THE ACCESS RULE IS THE SAME ONE THE PAGE USED. `requireUnitAccess` runs on
 * `params.slug` exactly as it does on the book page, so a media URL cannot be
 * the back door into a book somebody may not read. There is deliberately no
 * signed-URL scheme: a signed URL is a second authorisation path with its own
 * expiry, its own secret and its own bugs, and it keeps working after a grant is
 * revoked. This one re-checks the grant on every byte range.
 *
 * The row's OWN slug is compared against the URL's as well. They are the same
 * today because a key begins with its slug, but the day a key format stops being
 * self-describing, the URL segment would quietly become the authorisation claim
 * — which is the shape of every path-traversal bug ever written.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, request, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);

  const rest = params["*"];
  if (!rest) notFound();

  const key = `${params.slug}/${rest}`;
  const asset = await mediaByKey(env.DB, key);

  if (asset === null || asset.slug !== params.slug) notFound();

  // Inventoried but not uploaded. The ordinary state today, because R2 is not
  // enabled on the account yet — the site never links to one of these, and the
  // 404 matches what a truly absent file would give.
  if (asset.uploadedAt === null) notFound();

  const bucket = (env as Env & { MEDIA?: R2Bucket }).MEDIA;
  if (bucket === undefined) notFound();

  const range = parseRange(request.headers.get("Range"), asset.bytes);

  const object = await bucket.get(key, range === null ? undefined : { range });
  if (object === null) notFound();

  const headers = new Headers({
    "Content-Type": asset.contentType,
    // Long-lived because a media key is immutable: re-publishing changed audio
    // writes a new object under the same key only if the file itself changed,
    // and the sha256 in media_asset is what detects that. `private` because
    // this is entitled content and must never sit in a shared cache.
    "Cache-Control": "private, max-age=604800",
    "Accept-Ranges": "bytes",
    "Content-Length": String(range === null ? asset.bytes : range.length),
  });

  if (range !== null) {
    headers.set(
      "Content-Range",
      `bytes ${range.offset}-${range.offset + range.length - 1}/${asset.bytes}`,
    );
  }

  return new Response(object.body, { status: range === null ? 200 : 206, headers });
}
