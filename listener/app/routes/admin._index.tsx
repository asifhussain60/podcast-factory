import { Link } from "react-router";

import type { Route } from "./+types/admin._index";
import { cloudflare } from "~/context";
import { listCatalogForAdmin, listPeople } from "~/server/access.server";

export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const [people, catalog] = await Promise.all([
    listPeople(env.DB),
    listCatalogForAdmin(env.DB),
  ]);

  const live = people.filter((p) => p.revokedAt === null);

  return {
    invited: live.length,
    revoked: people.length - live.length,
    withoutAccess: live.filter((p) => p.grantCount === 0).length,
    published: catalog.filter((u) => u.status === "published" && u.kind !== "work").length,
    openToAll: catalog.filter((u) => u.openToAll).length,
    total: catalog.filter((u) => u.kind !== "work").length,
  };
}

export default function AdminOverview({ loaderData }: Route.ComponentProps) {
  const d = loaderData;

  return (
    <div className="space-y-10">
      <section>
        <h2 className="font-prose text-xl text-pf-ink">People</h2>
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <Stat label="Invited" value={d.invited} />
          <Stat label="Revoked" value={d.revoked} />
          <Stat
            label="Invited but given nothing"
            value={d.withoutAccess}
            hint={d.withoutAccess > 0 ? "They sign in to an empty library." : undefined}
          />
        </dl>
        <Link
          to="/admin/people"
          className="mt-4 inline-block font-ui text-sm text-pf-accent hover:underline"
        >
          Manage people
        </Link>
      </section>

      <section>
        <h2 className="font-prose text-xl text-pf-ink">Content</h2>
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <Stat label="Readable now" value={d.published} hint={`of ${d.total} known`} />
          <Stat label="Open to everyone" value={d.openToAll} />
          <Stat label="Not yet published" value={d.total - d.published} />
        </dl>
        <Link
          to="/admin/content"
          className="mt-4 inline-block font-ui text-sm text-pf-accent hover:underline"
        >
          Manage content
        </Link>
      </section>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="rounded-xl border border-pf-rule bg-pf-surface p-5">
      <dt className="font-ui text-xs uppercase tracking-widest text-pf-faint">{label}</dt>
      <dd className="mt-2 font-prose text-3xl text-pf-ink">{value}</dd>
      {hint ? <p className="mt-1 font-ui text-xs text-pf-muted">{hint}</p> : null}
    </div>
  );
}
