import { Link } from "react-router";

import type { Route } from "./+types/home";
import { Logo } from "~/components/brand/Logo";
import { ThemePicker } from "~/components/ThemePicker";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";

/**
 * The library.
 *
 * Behind the invited gate, so `viewer` is always present. The list comes from
 * `visibleUnits`, the ONLY place the entitlement rule is written — this loader
 * does no filtering of its own, and adding any would be the start of the rule
 * existing in two places that can disagree.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;

  const units = await visibleUnits(env.DB, viewer.email);

  return {
    siteName: env.PUBLIC_SITE_NAME ?? "Podcast Factory",
    viewer: { name: viewer.name, isAdmin: viewer.isAdmin },
    units,
  };
}

export default function Home({ loaderData }: Route.ComponentProps) {
  const { units, viewer } = loaderData;

  return (
    <div className="min-h-dvh bg-pf-bg">
      <header className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-6">
        <Logo size={44} />
        <div className="flex items-center gap-5">
          {viewer.isAdmin ? (
            <Link
              to="/admin"
              className="font-ui text-sm text-pf-muted transition-colors hover:text-pf-ink"
            >
              Access
            </Link>
          ) : null}
          <ThemePicker />
        </div>
      </header>

      <main id="main" className="mx-auto max-w-5xl px-6 pb-24">
        <section className="border-t border-pf-rule pt-14">
          <p className="font-ui text-xs uppercase tracking-[0.18em] text-pf-muted">
            {loaderData.siteName}
          </p>
          <h1 className="mt-4 max-w-3xl text-balance font-prose text-5xl leading-[1.08] text-pf-ink sm:text-6xl">
            Your library
          </h1>
        </section>

        {units.length === 0 ? (
          <p className="mt-12 max-w-xl font-prose text-lg leading-relaxed text-pf-muted">
            Nothing has been shared with you yet. When something is, it appears
            here.
          </p>
        ) : (
          <ul className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {units.map((unit) => (
              <li key={unit.slug}>
                <Link
                  to={`/book/${unit.slug}`}
                  className="block h-full rounded-xl border border-pf-rule bg-pf-surface p-6 transition-colors hover:border-pf-accent"
                  style={{ boxShadow: "var(--l-shadow)" }}
                >
                  <p className="font-ui text-xs uppercase tracking-widest text-pf-faint">
                    {unit.bucket}
                  </p>
                  <h2 className="mt-2 font-prose text-xl leading-snug text-pf-ink">
                    {unit.title}
                  </h2>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
