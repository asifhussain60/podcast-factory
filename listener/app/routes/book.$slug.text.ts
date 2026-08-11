import type { Route } from "./+types/book.$slug.text";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { chaptersOf, chapterOf } from "~/server/catalog.server";
import { unitBySlug } from "~/server/access.server";

/**
 * A whole book's prose, for keeping on the device.
 *
 * THE SAME GATE AS THE PAGE. `requireUnitAccess` runs on `params.slug` exactly
 * as it does on the book page and the reading page, so this is not a way to
 * reach a book somebody may not read — it is the reading page's own content,
 * asked for all at once.
 *
 * WHAT IS DELIBERATELY ABSENT: the Scholar Companion. Not filtered out — never
 * queried. Its cards are readable by one account through one function with the
 * gate inside it, and putting a copy into a device store that no such gate
 * guards would be a second route to them that no `viewer.isAdmin` check
 * protects. A test asserts this module never mentions it.
 *
 * The chapters come back as HTML because that is what the database holds: prose
 * is rendered once, at publish time, so the reader and the print edition cannot
 * diverge. Offline reading therefore needs no markdown implementation on the
 * device — the same reason the Worker has none.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const slug = params.slug;

  const [unit, contents] = await Promise.all([
    unitBySlug(env.DB, slug),
    chaptersOf(env.DB, slug),
  ]);

  // Unreachable — the middleware already proved the book is readable — but the
  // loader must not lean on that, or a change to the gate becomes a null
  // dereference here. Same reasoning as the reading page's own loader.
  if (unit === null) notFound();

  // `chaptersOf` is the table of contents and carries no `html` on purpose: a
  // book's prose is megabytes, and every other caller wants the list. So each
  // chapter is read for its body here. Sequential rather than a Promise.all
  // fan-out: D1 answers one statement at a time anyway, and a twenty-chapter
  // book firing twenty concurrent queries only queues them behind each other
  // with a worse failure mode.
  const chapters = [];
  for (const entry of contents) {
    const full = await chapterOf(env.DB, slug, entry.anchorKey);
    if (full !== null) chapters.push(full);
  }

  return Response.json(
    { bookTitle: unit.title, bucket: unit.bucket, chapters },
    // Never cached by anything in between. The device keeps its own copy
    // deliberately, through the store that the lease can reach and empty; a
    // second copy in an HTTP cache is one the lease cannot.
    { headers: { "Cache-Control": "no-store" } },
  );
}
