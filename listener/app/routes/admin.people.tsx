import { useState } from "react";
import { faCheck, faLink, faMagnifyingGlass, faPlus } from "@fortawesome/free-solid-svg-icons";
import { Form, Link, useSearchParams, useSubmit } from "react-router";

import type { Route } from "./+types/admin.people";
import { Icon } from "~/components/Icon";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import {
  grant,
  grantsFor,
  invite,
  isPeopleFilter,
  listCatalogForAdmin,
  listPeople,
  peopleTallies,
  personByEmail,
  revokeGrant,
  revokeInvite,
  type ContentUnit,
  type PeopleFilter,
  type Person,
} from "~/server/access.server";
import { hasUnfoldedPlusTag, tryNormalizeEmail } from "~/server/email.server";

/** The filter chips, in the order they are offered. */
const FILTERS: { key: PeopleFilter; label: string }[] = [
  { key: "all", label: "Everyone" },
  { key: "active", label: "Signed in" },
  { key: "never", label: "Never signed in" },
  { key: "waiting", label: "No access yet" },
  { key: "revoked", label: "Revoked" },
];

const PAGE = 50;

export async function loader({ request, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;
  const url = new URL(request.url);

  const selected = url.searchParams.get("email");
  const search = url.searchParams.get("q") ?? "";
  const rawFilter = url.searchParams.get("filter");
  const filter: PeopleFilter = isPeopleFilter(rawFilter) ? rawFilter : "all";
  const page = Math.max(0, Number(url.searchParams.get("page") ?? 0) || 0);

  // Everything the LIST needs is filtered and paged in SQL; everything the
  // DETAIL pane needs is fetched by key. Neither reads the whole table, which is
  // the difference between this screen and the one it replaces — that one loaded
  // every invitation and every catalogue row on every render.
  const [page_, tallies, catalog, person] = await Promise.all([
    listPeople(env.DB, { search, filter, limit: PAGE, offset: page * PAGE }),
    peopleTallies(env.DB),
    listCatalogForAdmin(env.DB),
    selected ? personByEmail(env.DB, selected) : Promise.resolve(null),
  ]);

  const grants = person ? await grantsFor(env.DB, person.email) : [];

  return {
    ...page_,
    tallies,
    catalog,
    person,
    search,
    filter,
    page,
    pageSize: PAGE,
    granted: grants.map((g) => `${g.scopeType}:${g.scopeId}`),
    /** Both sides are already normalized, so this is a plain comparison. */
    self: viewer.email,
  };
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const actor = context.get(session).viewer!.email;
  const form = await request.formData();
  const intent = String(form.get("intent"));
  const now = new Date().toISOString();
  const text = (name: string) => String(form.get(name) ?? "");

  switch (intent) {
    case "invite": {
      const raw = text("email");
      if (tryNormalizeEmail(raw) === null) {
        return { error: `"${raw.trim()}" is not an email address.` };
      }
      await invite(
        env.DB,
        raw,
        actor,
        { firstName: text("firstName"), lastName: text("lastName"), note: text("note") },
        now,
      );
      return { ok: true, invited: raw.trim(), warnPlusTag: hasUnfoldedPlusTag(raw) };
    }

    case "revoke-invite": {
      // The server's copy of the rule the screen also draws. Admin is
      // ADMIN_EMAIL and nothing else, and revoking deletes live sessions — so an
      // administrator who reached this by any route other than the button (a
      // stale tab, a hand-made POST) would lock themselves out of their own site
      // irrecoverably from the browser.
      const target = tryNormalizeEmail(text("email"));
      if (target !== null && target === actor) {
        return { error: "You cannot revoke your own sign-in." };
      }
      await revokeInvite(env.DB, text("email"), actor, now);
      return { ok: true };
    }

    // No name and no note: `invite` COALESCEs both, so restoring someone keeps
    // everything already recorded about them.
    case "re-invite":
      await invite(env.DB, text("email"), actor, {}, now);
      return { ok: true };

    case "grant":
      await grant(
        env.DB,
        text("email"),
        form.get("scopeType") as "unit" | "work" | "library",
        text("scopeId"),
        actor,
        now,
      );
      return { ok: true };

    case "revoke-grant":
      await revokeGrant(
        env.DB,
        text("email"),
        form.get("scopeType") as "unit" | "work" | "library",
        text("scopeId"),
        actor,
        now,
      );
      return { ok: true };

    default:
      return { error: "Unknown action." };
  }
}

export default function AdminPeople({ loaderData, actionData }: Route.ComponentProps) {
  const { people, total, everyone, tallies, catalog, person, search, filter, page, pageSize } =
    loaderData;
  const granted = new Set(loaderData.granted);
  const [params] = useSearchParams();
  const submit = useSubmit();

  /** Keep the current selection and filter while changing one thing. */
  const withParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === "") next.delete(key);
    else next.set(key, value);
    // Any change to the query is a new result set, so a page number carried over
    // from the old one would land the administrator on an empty page.
    if (key !== "page") next.delete("page");
    return `?${next.toString()}`;
  };

  return (
    <div className="pf-admin-split">
      <section className="pf-admin-list">
        <InviteForm actionData={actionData} />

        {/* ---- Finding someone ------------------------------------------- */}
        <div className="pf-admin-find">
          <Form
            method="get"
            role="search"
            onChange={(e) => submit(e.currentTarget)}
            className="pf-search"
          >
            {/* The selection and the filter ride along as hidden fields, or
                searching would silently clear both. */}
            {params.get("email") ? (
              <input type="hidden" name="email" value={params.get("email")!} />
            ) : null}
            {filter !== "all" ? <input type="hidden" name="filter" value={filter} /> : null}

            <Icon icon={faMagnifyingGlass} className="pf-search__icon" />
            <label htmlFor="people-q" className="sr-only">
              Search people by name or address
            </label>
            <input
              id="people-q"
              type="search"
              name="q"
              defaultValue={search}
              placeholder="Search by name or address"
              className="pf-search__input"
            />
          </Form>

          <div role="group" aria-label="Filter people" className="pf-filters">
            {FILTERS.map((f) => (
              <Link
                key={f.key}
                to={withParam("filter", f.key === "all" ? "" : f.key)}
                aria-current={filter === f.key ? "true" : undefined}
                className="pf-filter"
              >
                {f.label}
                <span className="pf-filter__count">{tallies[f.key]}</span>
              </Link>
            ))}
          </div>
        </div>

        <p className="pf-note--quiet pf-admin-count">
          {total === everyone
            ? `${everyone} ${everyone === 1 ? "person" : "people"}`
            : `${total} of ${everyone} people`}
        </p>

        {people.length === 0 ? (
          <p className="pf-empty">
            {search === "" ? "Nobody here yet." : `Nobody matches “${search}”.`}
          </p>
        ) : (
          <ul className="pf-people">
            {people.map((p) => (
              <li key={p.email}>
                <Link
                  to={withParam("email", p.email)}
                  aria-current={person?.email === p.email ? "true" : undefined}
                  className="pf-person"
                >
                  <span className="pf-person__who">{p.displayName}</span>
                  {/* Only when it adds something. Anyone invited before names
                      existed has the address AS their display name, and a row
                      printing it twice reads as a rendering fault. */}
                  {p.displayName === p.emailRaw ? null : (
                    <span className="pf-person__mail">{p.emailRaw}</span>
                  )}
                  <span className="pf-person__what">{standing(p)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        {/* Paging appears only when it applies. A pager under a list of six is
            furniture that says the list might be longer than it is. */}
        {total > pageSize ? (
          <nav aria-label="More people" className="pf-pager">
            <Link
              to={withParam("page", String(page - 1))}
              aria-disabled={page === 0}
              className="pf-button pf-button--sm pf-button--ghost"
            >
              Previous
            </Link>
            <span className="pf-pager__where">
              {page * pageSize + 1}–{Math.min(total, (page + 1) * pageSize)} of {total}
            </span>
            <Link
              to={withParam("page", String(page + 1))}
              aria-disabled={(page + 1) * pageSize >= total}
              className="pf-button pf-button--sm pf-button--ghost"
            >
              Next
            </Link>
          </nav>
        ) : null}
      </section>

      <section className="pf-admin-detail">
        {person === null ? (
          <p className="pf-note">
            {params.get("email")
              ? "No such person."
              : "Choose someone to see and change what they can open."}
          </p>
        ) : (
          <PersonDetail
            person={person}
            catalog={catalog}
            granted={granted}
            isSelf={person.email === loaderData.self}
          />
        )}
      </section>
    </div>
  );
}

/** One line summarising where somebody stands, for the list. */
function standing(p: Person): string {
  if (p.revokedAt !== null) return "Revoked";
  if (p.grantCount === 0) return p.redeemedAt === null ? "Invited — no access yet" : "No access yet";
  const books = `${p.grantCount} ${p.grantCount === 1 ? "grant" : "grants"}`;
  return p.redeemedAt === null ? `${books} · never signed in` : books;
}

function InviteForm({ actionData }: { actionData: Route.ComponentProps["actionData"] }) {
  const invited = actionData && "invited" in actionData ? actionData.invited : null;

  return (
    <div className="pf-panel pf-invite">
      <div className="pf-panel__head">
        <h2 className="pf-panel__title">
          <Icon icon={faPlus} /> Invite someone
        </h2>
      </div>

      <div className="pf-panel__body">
        <Form method="post" className="pf-form">
          <input type="hidden" name="intent" value="invite" />

          {/* Labelled, not placeholder-only. A placeholder disappears the moment
              anyone types, so a half-filled form stops saying what its fields
              are — and assistive technology never had the label at all. */}
          <div className="pf-form__pair">
            <Field name="firstName" label="First name" autoComplete="given-name" />
            <Field name="lastName" label="Last name" autoComplete="family-name" />
          </div>

          <Field name="email" label="Email address" type="email" required autoComplete="email" />
          <Field name="note" label="Note (optional)" hint="Only you see this." />

          <button type="submit" className="pf-button pf-button--primary pf-button--block">
            Add to the invitation list
          </button>
        </Form>

        {actionData && "error" in actionData && actionData.error ? (
          <p className="pf-message pf-message--danger">{actionData.error}</p>
        ) : null}

        {actionData && "warnPlusTag" in actionData && actionData.warnPlusTag ? (
          <p className="pf-message pf-message--warn">
            That address has a <code>+tag</code>. On this domain the tag is part of the identity, so
            it must match the account they sign in with exactly.
          </p>
        ) : null}

        {/* The button used to say "Send invitation" and no invitation was ever
            sent — there is no mail transport in this application. It now says
            what it does, and hands over the link to pass on by whatever means
            the administrator was already using. */}
        {invited !== null ? (
          <p className="pf-message pf-message--ok">
            <Icon icon={faCheck} /> {invited} can now sign in. Nothing was emailed — send them the
            link yourself:{" "}
            <span className="pf-invite__link">
              <Icon icon={faLink} /> podcast-factory.safinaverse.com
            </span>
          </p>
        ) : null}
      </div>
    </div>
  );
}

function Field({
  name,
  label,
  hint,
  type = "text",
  required = false,
  autoComplete,
}: {
  name: string;
  label: string;
  hint?: string;
  type?: string;
  required?: boolean;
  autoComplete?: string;
}) {
  return (
    <div className="pf-field">
      <label htmlFor={`invite-${name}`} className="pf-label">
        {label}
      </label>
      <input
        id={`invite-${name}`}
        name={name}
        type={type}
        required={required}
        autoComplete={autoComplete}
        aria-describedby={hint ? `invite-${name}-hint` : undefined}
        className="pf-input"
      />
      {hint ? (
        <span id={`invite-${name}-hint`} className="pf-field__hint">
          {hint}
        </span>
      ) : null}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* One person, and what they can open                                          */
/* -------------------------------------------------------------------------- */

function PersonDetail({
  person,
  catalog,
  granted,
  isSelf,
}: {
  person: Person;
  catalog: ContentUnit[];
  granted: Set<string>;
  /** Whether the administrator is looking at their own row. */
  isSelf: boolean;
}) {
  const [find, setFind] = useState("");

  const works = catalog.filter((u) => u.kind === "work");
  const standalone = catalog.filter((u) => u.kind === "book" && u.workSlug === null);
  const wholeLibrary = granted.has("library:*");

  const matches = (u: ContentUnit) =>
    find.trim() === "" || u.title.toLowerCase().includes(find.trim().toLowerCase());

  // What they already hold, gathered first. The screen this replaces rendered
  // the entire catalogue as a flat list of toggles — twenty-three rows today,
  // and the question an administrator arrives with is "what does this person
  // have", which was the one thing that list never answered directly.
  const held = catalog.filter(
    (u) => granted.has(`unit:${u.slug}`) || granted.has(`work:${u.slug}`),
  );

  return (
    <>
      <div className="pf-panel">
        <div className="pf-panel__head pf-split">
          <div className="pf-split__main">
            <h2 className="pf-panel__title pf-panel__title--name">{person.displayName}</h2>
            {/* Only when it adds something. For anyone invited before names
                existed, `displayName` IS the address, and printing it twice
                reads as a rendering fault rather than as a fact. */}
            {person.displayName === person.emailRaw ? null : (
              <p className="pf-person__mail">{person.emailRaw}</p>
            )}
          </div>

          {/* You cannot revoke yourself.
              Admin is `ADMIN_EMAIL` and nothing else, so the administrator's own
              invite row is the one thing standing between them and a site they
              can no longer sign in to — and `revokeInvite` deletes live sessions,
              so the lock-out would be immediate and would need a database edit to
              undo. Offering the button and refusing the action would be worse
              than not offering it; this says why instead. */}
          {isSelf ? (
            <p className="pf-note--quiet">This is you.</p>
          ) : (
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
          )}
        </div>

        <div className="pf-panel__body">
          <dl className="pf-facts">
            <Fact label="Invited" value={when(person.invitedAt)} />
            <Fact label="First signed in" value={person.redeemedAt ? when(person.redeemedAt) : "Never"} />
            <Fact label="Last signed in" value={person.lastSeenAt ? when(person.lastSeenAt) : "Never"} />
            <Fact label="Books" value={wholeLibrary ? "Everything" : String(person.grantCount)} />
          </dl>
          {person.note ? <p className="pf-note--quiet">{person.note}</p> : null}

          {person.revokedAt !== null ? (
            <p className="pf-message pf-message--warn">
              Sign-in is revoked and their sessions were ended. What they had is kept below, so
              re-inviting restores it exactly.
            </p>
          ) : null}
        </div>
      </div>

      <div className="pf-panel">
        <div className="pf-panel__head">
          <h2 className="pf-panel__title">What they can open</h2>
        </div>

        <div className="pf-panel__body pf-stack-sm">
          <GrantRow
            email={person.email}
            label="Everything, including anything added later"
            scopeType="library"
            scopeId="*"
            on={wholeLibrary}
          />

          {/* Held first, and always visible — the search below filters what can
              be ADDED, never what is already given, or an administrator could
              type three letters and appear to have revoked everything. */}
          {held.length > 0 ? (
            <>
              <h3 className="pf-notes__heading">Already given</h3>
              {held.map((unit) => (
                <GrantRow
                  key={unit.slug}
                  email={person.email}
                  label={unit.title}
                  hint={unit.kind === "work" ? "All volumes, including future ones" : statusHint(unit)}
                  scopeType={unit.kind === "work" ? "work" : "unit"}
                  scopeId={unit.slug}
                  on
                />
              ))}
            </>
          ) : null}

          <h3 className="pf-notes__heading">Add more</h3>

          <div className="pf-search pf-search--sm">
            <Icon icon={faMagnifyingGlass} className="pf-search__icon" />
            <label htmlFor="scope-find" className="sr-only">
              Search the library
            </label>
            <input
              id="scope-find"
              type="search"
              value={find}
              onChange={(e) => setFind(e.target.value)}
              placeholder="Search the library"
              className="pf-search__input"
            />
          </div>

          {works.map((work) =>
            matches(work) || catalog.some((v) => v.workSlug === work.slug && matches(v)) ? (
              <div key={work.slug} className="pf-grants__work">
                {granted.has(`work:${work.slug}`) ? null : (
                  <GrantRow
                    email={person.email}
                    label={work.title}
                    hint="All volumes, including future ones"
                    scopeType="work"
                    scopeId={work.slug}
                    on={false}
                  />
                )}
                <div className="pf-grants__volumes">
                  {catalog
                    .filter((u) => u.workSlug === work.slug && matches(u))
                    .filter((u) => !granted.has(`unit:${u.slug}`))
                    .map((vol) => (
                      <GrantRow
                        key={vol.slug}
                        email={person.email}
                        label={vol.title}
                        hint={statusHint(vol)}
                        scopeType="unit"
                        scopeId={vol.slug}
                        on={false}
                        covered={granted.has(`work:${work.slug}`) || wholeLibrary}
                      />
                    ))}
                </div>
              </div>
            ) : null,
          )}

          {standalone
            .filter(matches)
            .filter((u) => !granted.has(`unit:${u.slug}`))
            .map((unit) => (
              <GrantRow
                key={unit.slug}
                email={person.email}
                label={unit.title}
                hint={statusHint(unit)}
                scopeType="unit"
                scopeId={unit.slug}
                on={false}
                covered={wholeLibrary}
              />
            ))}
        </div>
      </div>
    </>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="pf-facts__row">
      <dt className="pf-facts__label">{label}</dt>
      <dd className="pf-facts__value">{value}</dd>
    </div>
  );
}

/**
 * A date an administrator can read.
 *
 * Rendered from the ISO string with an explicit locale rather than
 * `toLocaleDateString()` bare: the server and the browser can disagree about the
 * default locale, and a date that changes shape on hydration is a mismatch React
 * will report.
 */
function when(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

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
    <Form method="post" className="pf-grant">
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
