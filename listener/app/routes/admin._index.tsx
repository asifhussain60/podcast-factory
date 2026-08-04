import { Link } from "react-router";

import type { Route } from "./+types/admin._index";
import { cloudflare } from "~/context";
import { listCatalogForAdmin, peopleTallies } from "~/server/access.server";

/**
 * Counted in SQL, not in JavaScript.
 *
 * This used to call `listPeople()` and take `.length` of the result — loading
 * every invitation row, with a correlated grant count on each, to display five
 * numbers. It worked at eight people and would have gone on working badly for a
 * long time before anyone noticed. `peopleTallies` asks the database the five
 * questions it is built to answer.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const [tallies, catalog] = await Promise.all([
    peopleTallies(env.DB),
    listCatalogForAdmin(env.DB),
  ]);

  return {
    invited: tallies.all - tallies.revoked,
    revoked: tallies.revoked,
    withoutAccess: tallies.waiting,
    neverSignedIn: tallies.never,
    published: catalog.filter((u) => u.status === "published" && u.kind !== "work").length,
    openToAll: catalog.filter((u) => u.openToAll).length,
    total: catalog.filter((u) => u.kind !== "work").length,
  };
}

export default function AdminOverview({ loaderData }: Route.ComponentProps) {
  const d = loaderData;

  return (
    <div className="pf-stack-lg">
      <section>
        <h2 className="pf-section__title">People</h2>
        <dl className="pf-stats">
          <Stat label="Invited" value={d.invited} />
          <Stat
            label="Never signed in"
            value={d.neverSignedIn}
            hint={d.neverSignedIn > 0 ? "They may not have the link." : undefined}
          />
          <Stat
            label="Invited but given nothing"
            value={d.withoutAccess}
            hint={d.withoutAccess > 0 ? "They sign in to an empty library." : undefined}
          />
          <Stat label="Revoked" value={d.revoked} />
        </dl>
        <Link to="/admin/people" className="pf-link">
          Manage people
        </Link>
      </section>

      <section>
        <h2 className="pf-section__title">Content</h2>
        <dl className="pf-stats">
          <Stat label="Readable now" value={d.published} hint={`of ${d.total} known`} />
          <Stat label="Open to everyone" value={d.openToAll} />
          <Stat label="Not yet published" value={d.total - d.published} />
        </dl>
        <Link to="/admin/content" className="pf-link">
          Manage content
        </Link>
      </section>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="pf-stat">
      <dt className="pf-stat__label">{label}</dt>
      <dd className="pf-stat__value">{value}</dd>
      {hint ? <p className="pf-note pf-note--quiet">{hint}</p> : null}
    </div>
  );
}
