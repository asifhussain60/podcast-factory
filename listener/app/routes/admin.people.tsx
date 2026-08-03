import { Form, useSearchParams } from "react-router";

import type { Route } from "./+types/admin.people";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import {
  grant,
  grantsFor,
  invite,
  listCatalogForAdmin,
  listPeople,
  revokeGrant,
  revokeInvite,
  type ContentUnit,
} from "~/server/access.server";
import { hasUnfoldedPlusTag, tryNormalizeEmail } from "~/server/email.server";

export async function loader({ request, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const selected = new URL(request.url).searchParams.get("email");

  const [people, catalog] = await Promise.all([
    listPeople(env.DB),
    listCatalogForAdmin(env.DB),
  ]);

  const person = selected ? (people.find((p) => p.email === selected) ?? null) : null;
  const grants = person ? await grantsFor(env.DB, person.email) : [];

  return {
    people,
    catalog,
    person,
    granted: new Set(grants.map((g) => `${g.scopeType}:${g.scopeId}`)),
  };
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const actor = context.get(session).viewer!.email;
  const form = await request.formData();
  const intent = String(form.get("intent"));
  const now = new Date().toISOString();

  switch (intent) {
    case "invite": {
      const raw = String(form.get("email") ?? "");
      if (tryNormalizeEmail(raw) === null) {
        return { error: `"${raw.trim()}" is not an email address.` };
      }
      await invite(env.DB, raw, actor, String(form.get("note") ?? "") || null, now);
      return { ok: true, warnPlusTag: hasUnfoldedPlusTag(raw) };
    }

    case "revoke-invite":
      await revokeInvite(env.DB, String(form.get("email")), actor, now);
      return { ok: true };

    case "re-invite":
      await invite(env.DB, String(form.get("email")), actor, null, now);
      return { ok: true };

    case "grant":
      await grant(
        env.DB,
        String(form.get("email")),
        form.get("scopeType") as "unit" | "work" | "library",
        String(form.get("scopeId")),
        actor,
        now,
      );
      return { ok: true };

    case "revoke-grant":
      await revokeGrant(
        env.DB,
        String(form.get("email")),
        form.get("scopeType") as "unit" | "work" | "library",
        String(form.get("scopeId")),
        actor,
        now,
      );
      return { ok: true };

    default:
      return { error: "Unknown action." };
  }
}

export default function AdminPeople({ loaderData, actionData }: Route.ComponentProps) {
  const { people, catalog, person, granted } = loaderData;
  const [params] = useSearchParams();

  // Work parents first, then their volumes, then standalone books — the order
  // that makes "grant the whole work" the obvious move.
  const works = catalog.filter((u) => u.kind === "work");
  const standalone = catalog.filter((u) => u.kind === "book" && u.workSlug === null);

  return (
    <div className="pf-admin-split">
      <section>
        <h2 className="pf-section__title">Invite someone</h2>
        <Form method="post" className="pf-form">
          <input type="hidden" name="intent" value="invite" />
          <input
            type="email"
            name="email"
            required
            placeholder="name@example.com"
            className="pf-input"
          />
          <input
            type="text"
            name="note"
            placeholder="Note (optional)"
            className="pf-input"
          />
          <button type="submit" className="pf-button pf-button--primary pf-button--block">
            Send invitation
          </button>
        </Form>

        {actionData && "error" in actionData && actionData.error ? (
          <p className="pf-message pf-message--danger">{actionData.error}</p>
        ) : null}
        {actionData && "warnPlusTag" in actionData && actionData.warnPlusTag ? (
          <p className="pf-message pf-message--warn">
            That address has a <code>+tag</code>. On this domain the tag is part of the
            identity, so it must match the account they sign in with exactly.
          </p>
        ) : null}

        <h2 className="pf-section__title pf-people__heading">People</h2>
        <ul className="pf-people">
          {people.map((p) => (
            <li key={p.email}>
              <a
                href={`/admin/people?email=${encodeURIComponent(p.email)}`}
                aria-current={person?.email === p.email ? "true" : undefined}
                className="pf-card pf-person"
              >
                <span className="pf-person__who">{p.emailRaw}</span>
                <span className="pf-person__what">
                  {p.revokedAt !== null
                    ? "Revoked"
                    : p.grantCount === 0
                      ? "No content yet"
                      : `${p.grantCount} grant${p.grantCount === 1 ? "" : "s"}`}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section>
        {person === null ? (
          <p className="pf-note">
            {params.get("email")
              ? "No such person."
              : "Choose someone to see and change what they can open."}
          </p>
        ) : (
          <>
            <div className="pf-split">
              <h2 className="pf-section__title pf-split__main">{person.emailRaw}</h2>
              <Form method="post">
                <input
                  type="hidden"
                  name="intent"
                  value={person.revokedAt === null ? "revoke-invite" : "re-invite"}
                />
                <input type="hidden" name="email" value={person.email} />
                <button type="submit" className="pf-button pf-button--ghost pf-button--sm">
                  {person.revokedAt === null ? "Revoke sign-in" : "Re-invite"}
                </button>
              </Form>
            </div>

            {person.revokedAt !== null ? (
              <p className="pf-message pf-message--warn">
                Sign-in is revoked and their sessions were ended. What they had is kept
                below, so re-inviting restores it exactly.
              </p>
            ) : null}

            <GrantRow
              email={person.email}
              label="Everything, including anything added later"
              scopeType="library"
              scopeId="*"
              on={granted.has("library:*")}
            />

            {works.map((work) => (
              <div key={work.slug} className="pf-grants__work">
                <GrantRow
                  email={person.email}
                  label={work.title}
                  hint="All volumes, including future ones"
                  scopeType="work"
                  scopeId={work.slug}
                  on={granted.has(`work:${work.slug}`)}
                />
                <div className="pf-grants__volumes">
                  {catalog
                    .filter((u) => u.workSlug === work.slug)
                    .map((vol) => (
                      <GrantRow
                        key={vol.slug}
                        email={person.email}
                        label={vol.title}
                        hint={statusHint(vol)}
                        scopeType="unit"
                        scopeId={vol.slug}
                        on={granted.has(`unit:${vol.slug}`)}
                        covered={granted.has(`work:${work.slug}`) || granted.has("library:*")}
                      />
                    ))}
                </div>
              </div>
            ))}

            <div className="pf-grants__work">
              {standalone.map((unit) => (
                <GrantRow
                  key={unit.slug}
                  email={person.email}
                  label={unit.title}
                  hint={statusHint(unit)}
                  scopeType="unit"
                  scopeId={unit.slug}
                  on={granted.has(`unit:${unit.slug}`)}
                  covered={granted.has("library:*")}
                />
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function statusHint(unit: ContentUnit): string | undefined {
  if (unit.openToAll) return "Open to everyone";
  if (unit.status !== "published") return "Not published yet — a grant waits for it";
  return undefined;
}

function GrantRow({
  email,
  label,
  hint,
  scopeType,
  scopeId,
  on,
  covered = false,
}: {
  email: string;
  label: string;
  hint?: string;
  scopeType: "unit" | "work" | "library";
  scopeId: string;
  on: boolean;
  covered?: boolean;
}) {
  return (
    <Form method="post" className="pf-card pf-grant">
      <input type="hidden" name="intent" value={on ? "revoke-grant" : "grant"} />
      <input type="hidden" name="email" value={email} />
      <input type="hidden" name="scopeType" value={scopeType} />
      <input type="hidden" name="scopeId" value={scopeId} />
      <span className="pf-grant__what">
        <span className="pf-grant__label">{label}</span>
        {covered && !on ? (
          <span className="pf-grant__hint">Already covered by a wider grant</span>
        ) : hint ? (
          <span className="pf-grant__hint">{hint}</span>
        ) : null}
      </span>
      <button
        type="submit"
        aria-pressed={on}
        className={`pf-button pf-button--sm${on ? " pf-button--primary" : ""}`}
      >
        {on ? "Granted" : "Give access"}
      </button>
    </Form>
  );
}
