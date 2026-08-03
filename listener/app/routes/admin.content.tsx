import { Form } from "react-router";

import type { Route } from "./+types/admin.content";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { holdersOf, listCatalogForAdmin, setOpenToAll } from "~/server/access.server";

/**
 * The catalog, from the other direction: for each book, who can open it.
 *
 * "What can this person see" and "who can see this book" are both real questions
 * and neither answers the other, so both screens exist over the same tables.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const catalog = await listCatalogForAdmin(env.DB);

  const readable = catalog.filter((u) => u.kind !== "work");
  const holders = await Promise.all(readable.map((u) => holdersOf(env.DB, u.slug)));

  return {
    units: readable.map((unit, i) => ({ ...unit, holders: holders[i] })),
  };
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const actor = context.get(session).viewer!.email;
  const form = await request.formData();

  // `open_to_all` is a privilege bit. It is writable ONLY from here, behind an
  // admin session — never by the phase-3 publish endpoint, which authenticates
  // with a bearer token and names its columns explicitly.
  await setOpenToAll(
    env.DB,
    String(form.get("slug")),
    form.get("open") === "1",
    actor,
    new Date().toISOString(),
  );

  return { ok: true };
}

export default function AdminContent({ loaderData }: Route.ComponentProps) {
  return (
    <div className="pf-stack-sm">
      {loaderData.units.map((unit) => (
        <article key={unit.slug} className="pf-card pf-card--padded">
          <div className="pf-split">
            <div className="pf-split__main">
              <h2 className="pf-row__main">{unit.title}</h2>
              <p className="pf-note pf-note--quiet">
                {unit.bucket}
                {unit.workSlug ? ` · part of ${unit.workSlug}` : ""}
                {unit.status === "published" ? "" : ` · ${unit.status}`}
              </p>
            </div>

            <Form method="post">
              <input type="hidden" name="slug" value={unit.slug} />
              <input type="hidden" name="open" value={unit.openToAll ? "0" : "1"} />
              <button
                type="submit"
                aria-pressed={unit.openToAll}
                className={`pf-button pf-button--sm${unit.openToAll ? " pf-button--primary" : ""}`}
              >
                {unit.openToAll ? "Open to everyone · make private" : "Open to everyone"}
              </button>
            </Form>
          </div>

          <p className="pf-note pf-note--quiet pf-card__foot">
            {unit.status !== "published"
              ? "Not published, so nobody can open it yet — grants made now take effect when it publishes."
              : unit.openToAll
                ? "Everyone invited can open this."
                : unit.holders.length === 0
                  ? "Nobody has been given this."
                  : `Given to ${unit.holders.join(", ")}`}
          </p>
        </article>
      ))}
    </div>
  );
}
