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
    <div className="grid gap-10 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
      <section>
        <h2 className="font-prose text-xl text-pf-ink">Invite someone</h2>
        <Form method="post" className="mt-4 space-y-3">
          <input type="hidden" name="intent" value="invite" />
          <input
            type="email"
            name="email"
            required
            placeholder="name@example.com"
            className="w-full rounded-lg border border-pf-rule bg-pf-surface px-3 py-2 font-ui text-sm text-pf-ink"
          />
          <input
            type="text"
            name="note"
            placeholder="Note (optional)"
            className="w-full rounded-lg border border-pf-rule bg-pf-surface px-3 py-2 font-ui text-sm text-pf-ink"
          />
          <button
            type="submit"
            className="w-full rounded-lg bg-pf-accent px-4 py-2 font-ui text-sm text-pf-on-accent hover:bg-pf-accent-hover"
          >
            Send invitation
          </button>
        </Form>

        {actionData && "error" in actionData && actionData.error ? (
          <p className="mt-3 font-ui text-sm text-pf-danger">{actionData.error}</p>
        ) : null}
        {actionData && "warnPlusTag" in actionData && actionData.warnPlusTag ? (
          <p className="mt-3 font-ui text-sm text-pf-warn">
            That address has a <code>+tag</code>. On this domain the tag is part of the
            identity, so it must match the account they sign in with exactly.
          </p>
        ) : null}

        <h2 className="mt-10 font-prose text-xl text-pf-ink">People</h2>
        <ul className="mt-4 space-y-2">
          {people.map((p) => {
            const active = person?.email === p.email;
            return (
              <li key={p.email}>
                <a
                  href={`/admin/people?email=${encodeURIComponent(p.email)}`}
                  className={[
                    "block rounded-lg border px-4 py-3 transition-colors",
                    active
                      ? "border-pf-accent bg-pf-surface"
                      : "border-pf-rule bg-pf-surface hover:border-pf-accent",
                  ].join(" ")}
                >
                  <span className="block font-ui text-sm text-pf-ink">{p.emailRaw}</span>
                  <span className="mt-0.5 block font-ui text-xs text-pf-faint">
                    {p.revokedAt !== null
                      ? "Revoked"
                      : p.grantCount === 0
                        ? "No content yet"
                        : `${p.grantCount} grant${p.grantCount === 1 ? "" : "s"}`}
                  </span>
                </a>
              </li>
            );
          })}
        </ul>
      </section>

      <section>
        {person === null ? (
          <p className="font-prose text-pf-muted">
            {params.get("email")
              ? "No such person."
              : "Choose someone to see and change what they can open."}
          </p>
        ) : (
          <>
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="font-prose text-xl text-pf-ink">{person.emailRaw}</h2>
              <Form method="post">
                <input
                  type="hidden"
                  name="intent"
                  value={person.revokedAt === null ? "revoke-invite" : "re-invite"}
                />
                <input type="hidden" name="email" value={person.email} />
                <button
                  type="submit"
                  className="font-ui text-sm text-pf-muted underline hover:text-pf-ink"
                >
                  {person.revokedAt === null ? "Revoke sign-in" : "Re-invite"}
                </button>
              </Form>
            </div>

            {person.revokedAt !== null ? (
              <p className="mt-3 font-ui text-sm text-pf-warn">
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
              <div key={work.slug} className="mt-8">
                <GrantRow
                  email={person.email}
                  label={work.title}
                  hint="All volumes, including future ones"
                  scopeType="work"
                  scopeId={work.slug}
                  on={granted.has(`work:${work.slug}`)}
                />
                <div className="mt-2 space-y-2 pl-6">
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

            <div className="mt-8 space-y-2">
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
    <Form
      method="post"
      className="mt-2 flex items-center justify-between gap-4 rounded-lg border border-pf-rule bg-pf-surface px-4 py-3"
    >
      <input type="hidden" name="intent" value={on ? "revoke-grant" : "grant"} />
      <input type="hidden" name="email" value={email} />
      <input type="hidden" name="scopeType" value={scopeType} />
      <input type="hidden" name="scopeId" value={scopeId} />
      <span className="min-w-0">
        <span className="block truncate font-ui text-sm text-pf-ink">{label}</span>
        {covered && !on ? (
          <span className="mt-0.5 block font-ui text-xs text-pf-faint">
            Already covered by a wider grant
          </span>
        ) : hint ? (
          <span className="mt-0.5 block font-ui text-xs text-pf-faint">{hint}</span>
        ) : null}
      </span>
      <button
        type="submit"
        className={[
          "shrink-0 rounded-md px-3 py-1.5 font-ui text-xs transition-colors",
          on
            ? "bg-pf-accent text-pf-on-accent hover:bg-pf-accent-hover"
            : "border border-pf-rule text-pf-muted hover:text-pf-ink",
        ].join(" ")}
      >
        {on ? "Granted" : "Give access"}
      </button>
    </Form>
  );
}
