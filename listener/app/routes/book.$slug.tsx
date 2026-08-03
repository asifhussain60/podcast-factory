import { Link } from "react-router";

import type { Route } from "./+types/book.$slug";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { unitBySlug } from "~/server/access.server";

/**
 * Layer 4. The gate is here rather than on a shared parent so it can read
 * `params.slug` directly instead of re-deriving it from the URL.
 *
 * Because it is MIDDLEWARE, the `_routes` single-fetch filter cannot skip it:
 * `filterMatchesToLoad` (single-fetch.js:79-84) selects which LOADERS run, and
 * middleware wraps the whole call. A gate written as a parent loader would fall
 * to `GET /book/x.data?_routes=routes/book.$slug`.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const unit = await unitBySlug(env.DB, params.slug);

  // Unreachable in practice — the middleware already proved it is readable —
  // but the loader must not assume that, or a future change to the gate turns
  // into a null dereference here.
  if (unit === null) notFound();

  return { unit };
}

export default function BookDetail({ loaderData }: Route.ComponentProps) {
  const { unit } = loaderData;

  return (
    <div className="min-h-dvh bg-pf-bg">
      <main id="main" className="mx-auto max-w-3xl px-6 py-16">
        <Link
          to="/"
          className="font-ui text-sm text-pf-muted transition-colors hover:text-pf-ink"
        >
          Library
        </Link>
        <p className="mt-10 font-ui text-xs uppercase tracking-widest text-pf-faint">
          {unit.bucket}
        </p>
        <h1 className="mt-2 font-prose text-4xl leading-tight text-pf-ink">{unit.title}</h1>
        <p className="mt-8 font-prose text-pf-muted">
          Episodes, the reading edition and the slide decks arrive in the next
          phases. Reaching this page at all is what proves the access gate.
        </p>
      </main>
    </div>
  );
}
