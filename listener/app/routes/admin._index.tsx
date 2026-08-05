import { useEffect, useState } from "react";
import {
  faEnvelope,
  faArrowLeft,
  faCheck,
  faChevronDown,
  faChevronRight,
  faEye,
  faLink,
  faPen,
  faPlus,
  faTrash,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import {
  Form,
  Link,
  redirect,
  useFetcher,
  useRouteLoaderData,
  useSearchParams,
} from "react-router";

import type { Route } from "./+types/admin._index";
import type { loader as adminLoader } from "./_authed._admin";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { GrantRow } from "~/components/admin/GrantRow";
import { InviteMessage } from "~/components/admin/InviteMessage";
import { count } from "~/lib/plural";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { startSimulating } from "~/server/simulate.server";
import {
  deletePerson,
  grant,
  grantsFor,
  invite,
  isPeopleFilter,
  listCatalogForAdmin,
  listPeople,
  personByEmail,
  recordEvent,
  renamePerson,
  revokeGrant,
  revokeInvite,
  splitName,
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
  { key: "library", label: "Whole library" },
  { key: "dormant", label: "Gone quiet" },
  { key: "revoked", label: "Revoked" },
];

/**
 * A page of 25, not 50.
 *
 * The table shows five columns per person now, so a page is measured in screens
 * rather than in rows: fifty of these is four scrolls, and a pager nobody reaches
 * is a pager nobody uses.
 */
const PAGE = 25;

export async function loader({ request, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;
  const url = new URL(request.url);

  const selected = url.searchParams.get("email");
  const search = url.searchParams.get("q") ?? "";
  const rawFilter = url.searchParams.get("filter");
  const filter: PeopleFilter = isPeopleFilter(rawFilter) ? rawFilter : "all";
  const page = Math.max(0, Number(url.searchParams.get("page") ?? 0) || 0);

  // Everything the TABLE needs is filtered and paged in SQL; everything one
  // person's panel needs is fetched by key. The catalogue is read only when a
  // person is actually open — it is twenty-three rows today and it is needed to
  // draw the grant list, which nothing on the table view shows.
  const [page_, person] = await Promise.all([
    listPeople(env.DB, { search, filter, limit: PAGE, offset: page * PAGE }),
    selected ? personByEmail(env.DB, selected) : Promise.resolve(null),
  ]);

  const [grants, catalog] = await Promise.all([
    person ? grantsFor(env.DB, person.email) : Promise.resolve([]),
    person ? listCatalogForAdmin(env.DB) : Promise.resolve([] as ContentUnit[]),
  ]);

  return {
    ...page_,
    catalog,
    person,
    search,
    filter,
    page,
    pageSize: PAGE,
    granted: grants.map((g) => `${g.scopeType}:${g.scopeId}`),
    /** Both sides are already normalized, so this is a plain comparison. */
    self: viewer.email,
    /**
     * Where to tell an invited person to go.
     *
     * `BETTER_AUTH_URL` rather than the request's own origin: it is the site's
     * declared absolute base, it is what sign-in redirects to, and it is exactly
     * the address a recipient has to reach. On this machine it is localhost —
     * which is honest and which the dialog says out loud, rather than quietly
     * putting a link into a message that nobody else can open.
     */
    siteUrl: context.get(cloudflare).env.BETTER_AUTH_URL,
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
      // One typed name, two stored columns. The form no longer asks for a note
      // either — the column stays and an existing one is still shown, because
      // deleting what an administrator once wrote is not a form change.
      await invite(env.DB, raw, actor, splitName(text("name")), now);
      return { ok: true, invited: raw.trim(), warnPlusTag: hasUnfoldedPlusTag(raw) };
    }

    case "rename":
      await renamePerson(env.DB, text("email"), text("name"), actor, now);
      return { ok: true };

    case "delete-person": {
      // The same rule the delete button obeys, enforced where it cannot be
      // skipped. Admin is ADMIN_EMAIL and nothing else, so deleting your own
      // invitation locks you out of your own site irrecoverably from the browser
      // — and unlike revoking, there is no row left to restore.
      const target = tryNormalizeEmail(text("email"));
      if (target !== null && target === actor) {
        return { error: "You cannot delete yourself." };
      }
      await deletePerson(env.DB, text("email"), actor, now);
      return { ok: true };
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

    // See the site as this person. The cookie downgrades and nothing else — the
    // rules that make that safe are in server/simulate.server.ts, and the only
    // one that lives here is that starting a simulation is an ADMIN action, so
    // it sits behind this route's own gate like everything else in this file.
    case "simulate": {
      const target = tryNormalizeEmail(text("email"));
      if (target === null) return { error: "That is not an email address." };

      await recordEvent(env.DB, "simulate-start", target, now, actor);
      // To the library, because that is what signing in as them would show.
      return redirect("/", {
        headers: { "Set-Cookie": startSimulating(target, new URL(request.url)) },
      });
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
      // `grantedTo`, not `granted` — the latter is already this action's name
      // for a COUNT on `grant-many`, and reusing it made the panel compare a
      // number against an address and silently never match.
      //
      // Named at all, rather than a bare `ok`, because the invitation message
      // must open after a GRANT and not after a rename or a revoke, which come
      // back from this same switch.
      return { ok: true, grantedTo: text("email") };

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

    // Several books in one press. Each scope still goes through `grant`
    // one at a time rather than through a new bulk writer: that function is
    // already an upsert, so re-granting something is harmless, and it writes its
    // own `access_event` — so ticking four books leaves four audit rows saying
    // exactly what was given, which a single "granted 4 things" row would not.
    case "grant-many": {
      const email = text("email");
      const scopes = form
        .getAll("scope")
        .map(String)
        .map((raw) => raw.split(":", 2))
        // `library` is deliberately not accepted here. It has its own toggle,
        // it is the widest thing this application can give, and a checkbox is
        // the one control where it could ride along unnoticed with four others.
        .filter(([type, id]) => (type === "unit" || type === "work") && Boolean(id));

      for (const [type, id] of scopes) {
        await grant(env.DB, email, type as "unit" | "work", id, actor, now);
      }
      return { ok: true, granted: scopes.length, grantedTo: email };
    }

    default:
      return { error: "Unknown action." };
  }
}

export default function AdminPeople({ loaderData, actionData }: Route.ComponentProps) {
  const { people, total, everyone, catalog, person, search, filter, page, pageSize } = loaderData;
  const granted = new Set(loaderData.granted);
  const [params] = useSearchParams();

  // The tallies belong to the section, not to this page: the strip above the tabs
  // shows three of them and these chips show all seven, and they are the same
  // seven numbers. Read from the parent loader rather than queried again, because
  // two queries for one set of counts is how a chip and a tile come to disagree.
  // The layout is always matched — this route is one of its children — so the
  // lookup cannot miss.
  const { tallies } = useRouteLoaderData<typeof adminLoader>("routes/_authed._admin")!;

  /** Keep the current selection and filter while changing one thing. */
  const withParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === "") next.delete(key);
    else next.set(key, value);
    // Any change to the query is a new result set, so a page number carried over
    // from the old one would land the administrator on an empty page.
    if (key !== "page") next.delete("page");
    const q = next.toString();
    return q === "" ? "." : `?${q}`;
  };

  return (
    <div className="pf-access-split">
      <section className="pf-admin-aside">
        <InviteForm actionData={actionData} />
      </section>

      {/* The right column is the working area, and it holds ONE of two things.
          A hundred-row table and one person's grants cannot both have the width
          they need beside the invite form, and the two are never done at the same
          moment: the table is for finding somebody, the panel is for working on
          them. The person is in the URL, so the swap costs nothing and the back
          button behaves. */}
      <section className="pf-admin-main">
        {person === null && params.get("email") !== null ? (
          <div className="pf-panel">
            <div className="pf-panel__body">
              <EmptyState>No such person.</EmptyState>
              <Link to={withParam("email", "")} className="pf-link">
                Back to everyone
              </Link>
            </div>
          </div>
        ) : person !== null ? (
          <>
            <Link to={withParam("email", "")} className="pf-backlink">
              <Icon icon={faArrowLeft} /> Back to everyone
            </Link>
            <PersonDetail
              person={person}
              catalog={catalog}
              granted={granted}
              isSelf={person.email === loaderData.self}
              siteUrl={loaderData.siteUrl}
              justGranted={
                actionData !== undefined &&
                actionData !== null &&
                "grantedTo" in actionData &&
                // Both sides normalized: the form posts `person.email`, which is
                // the folded address, and that is what the action echoes back.
                actionData.grantedTo === person.email
              }
            />
          </>
        ) : (
          <PeopleTable
            people={people}
            total={total}
            everyone={everyone}
            tallies={tallies}
            search={search}
            filter={filter}
            page={page}
            pageSize={pageSize}
            self={loaderData.self}
            withParam={withParam}
          />
        )}
      </section>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Everyone                                                                    */
/* -------------------------------------------------------------------------- */

function PeopleTable({
  people,
  total,
  everyone,
  tallies,
  search,
  filter,
  page,
  pageSize,
  self,
  withParam,
}: {
  people: Person[];
  total: number;
  everyone: number;
  tallies: Record<PeopleFilter, number>;
  search: string;
  filter: PeopleFilter;
  page: number;
  pageSize: number;
  /** The administrator's own address, which is the one row with no delete. */
  self: string;
  withParam: (key: string, value: string) => string;
}) {
  const [params] = useSearchParams();
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="pf-panel pf-people-panel">
      <div className="pf-panel__head pf-people-head">
        <SearchBox
          id="people-q"
          label="Search people by name or address"
          placeholder="Search by name or address"
          size="wide"
          action={{
            kind: "navigate",
            name: "q",
            value: search,
            // The filter rides along, or searching would silently clear it.
            hidden: filter === "all" ? {} : { filter },
          }}
        />

        <p className="pf-people-head__count">
          {total === everyone
            ? count(everyone, "person", "people")
            : `${total} of ${everyone}`}
        </p>
      </div>

      {/* A wrapping row of filters rather than a select: each carries a count,
          and the counts are half the value — "3 have gone quiet" answers the
          question without the filter being applied at all. */}
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

      {people.length === 0 ? (
        <EmptyState>
          {search === "" ? "Nobody here yet." : `Nobody matches “${search}”.`}
        </EmptyState>
      ) : (
        <div className="pf-table-scroll">
          <table className="pf-table">
            <thead>
              {/* Four columns, not five. The name and the address are ONE column
                  because the working column is 624px wide at this site's page
                  measure and five columns made every address break across three
                  lines mid-word — and because they are one fact: who this is. */}
              <tr>
                <th scope="col" className="pf-table__who">
                  Person
                </th>
                <th scope="col" className="pf-table__tight">
                  Books
                </th>
                <th scope="col" className="pf-table__tight">
                  Signed in
                </th>
                <th scope="col" className="pf-table__tight">
                  Standing
                </th>
                <th scope="col" className="pf-table__acts">
                  <span className="sr-only">Rename or delete</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {people.map((p) => (
                <PersonRow key={p.email} person={p} isSelf={p.email === self} withParam={withParam} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Paging appears only when it applies. A pager under a list of six is
          furniture that says the list might be longer than it is. */}
      {total > pageSize ? (
        <nav aria-label="Pages of people" className="pf-pager">
          <Link
            to={withParam("page", String(page - 1))}
            aria-disabled={page === 0}
            className="pf-button pf-button--sm pf-button--ghost"
          >
            Previous
          </Link>

          <span className="pf-pager__pages">
            {pageWindow(page, pages).map((n) =>
              n === page ? (
                <span key={n} aria-current="page" className="pf-pagenum">
                  {n + 1}
                </span>
              ) : (
                <Link key={n} to={withParam("page", String(n))} className="pf-pagenum">
                  {n + 1}
                </Link>
              ),
            )}
          </span>

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
    </div>
  );
}

/**
 * One row, and the two things it can be doing instead of sitting still.
 *
 * The state is per ROW rather than lifted to the table, because that is what it
 * describes and a table-level "editing" would have to be cleared by every other
 * interaction on the page.
 *
 * Both actions go through `useFetcher`, not `<Form>`. A form POST is a navigation:
 * it revalidates and returns to the top of the page, so renaming somebody on page
 * three of a hundred would answer correctly and then throw away where you were. A
 * fetcher submits, revalidates the table in place, and leaves the scroll alone.
 */
function PersonRow({
  person: p,
  isSelf,
  withParam,
}: {
  person: Person;
  /** Whether this row is the administrator's own. */
  isSelf: boolean;
  withParam: (key: string, value: string) => string;
}) {
  const fetcher = useFetcher();
  const [mode, setMode] = useState<"idle" | "editing" | "confirming">("idle");

  // What was actually RECORDED, which is not always what the row displays: an
  // unnamed person displays their address, and prefilling the box with that would
  // invite saving an address as somebody's name.
  const recorded = [p.firstName, p.lastName].filter(Boolean).join(" ");

  // Confirming takes the WHOLE row, spanning every column.
  // Asked inside the actions cell, the sentence had 80 pixels to say a person's
  // name in and the row grew to three times its height to hold three words and
  // two stacked buttons. A question about the row belongs across the row.
  if (mode === "confirming") {
    return (
      <tr>
        <td colSpan={5} className="pf-confirmrow">
          <fetcher.Form method="post" className="pf-confirm">
            <input type="hidden" name="intent" value="delete-person" />
            <input type="hidden" name="email" value={p.email} />
            <span className="pf-confirm__ask">
              Delete <strong>{p.displayName}</strong>
              {p.grantCount > 0
                ? ` and the ${count(p.grantCount, "book")} they hold?`
                : "?"}{" "}
              This cannot be undone — to stop them signing in but keep what they
              have, revoke them instead.
            </span>
            <button type="submit" className="pf-button pf-button--sm pf-button--danger">
              Delete
            </button>
            <button
              type="button"
              onClick={() => setMode("idle")}
              className="pf-button pf-button--sm pf-button--ghost"
            >
              Keep
            </button>
          </fetcher.Form>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td data-label="Person" className="pf-table__who">
        {mode === "editing" ? (
          <fetcher.Form method="post" className="pf-rowedit" onSubmit={() => setMode("idle")}>
            <input type="hidden" name="intent" value="rename" />
            <input type="hidden" name="email" value={p.email} />
            <label htmlFor={`name-${p.email}`} className="sr-only">
              Name for {p.emailRaw}
            </label>
            {/* autoFocus is right here and almost nowhere else: the field exists
                because a button was just pressed to summon it. */}
            <input
              id={`name-${p.email}`}
              name="name"
              defaultValue={recorded}
              autoFocus
              autoComplete="off"
              placeholder="Their name"
              className="pf-input pf-input--sm"
            />
            <button type="submit" aria-label="Save the name" className="pf-iconbtn">
              <Icon icon={faCheck} />
            </button>
            <button
              type="button"
              onClick={() => setMode("idle")}
              aria-label="Stop renaming"
              className="pf-iconbtn"
            >
              <Icon icon={faXmark} />
            </button>
          </fetcher.Form>
        ) : (
          <Link to={withParam("email", p.email)} className="pf-person">
            {p.displayName}
          </Link>
        )}

        {/* The address, in BOTH states. Printed only when it adds something —
            everyone invited before names existed has the address as their display
            name, and a cell printing it twice reads as a rendering fault — and
            kept while renaming, which is the moment it matters most: the box
            covers the name, so without it the only thing saying whose name is in
            the box is the row's position. */}
        {p.displayName === p.emailRaw ? null : (
          <span className="pf-person__mail">{p.emailRaw}</span>
        )}
      </td>

      <td data-label="Books" className="pf-table__tight">
        {p.library ? (
          <span className="pf-pill pf-pill--accent">Everything</span>
        ) : p.grantCount === 0 ? (
          <span className="pf-quiet">None</span>
        ) : (
          p.grantCount
        )}
      </td>

      <td data-label="Signed in" className="pf-table__tight">
        {p.lastSeenAt === null ? <span className="pf-quiet">Never</span> : when(p.lastSeenAt)}
      </td>

      <td data-label="Standing" className="pf-table__tight">
        <Standing person={p} />
      </td>

      <td data-label="" className="pf-table__acts">
        <div className="pf-rowacts">
          <button
            type="button"
            onClick={() => setMode("editing")}
            aria-label={`Rename ${p.displayName}`}
            className="pf-iconbtn"
          >
            <Icon icon={faPen} />
          </button>
          {/* No delete on your own row, and the server refuses it too. Admin is
              ADMIN_EMAIL and nothing else, so this row is the only thing between
              the administrator and a site they cannot sign in to — and unlike a
              revocation there would be nothing left to restore. */}
          {isSelf ? null : (
            <button
              type="button"
              onClick={() => setMode("confirming")}
              aria-label={`Delete ${p.displayName}`}
              className="pf-iconbtn pf-iconbtn--danger"
            >
              <Icon icon={faTrash} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

/**
 * At most seven page numbers, centred on the one you are reading.
 *
 * Every page as a numbered link is fine at four pages and is a wall at forty, and
 * this table is sized for a library that keeps growing. Previous and Next reach
 * the rest.
 */
function pageWindow(page: number, pages: number): number[] {
  const span = Math.min(7, pages);
  const start = Math.max(0, Math.min(page - Math.floor(span / 2), pages - span));
  return Array.from({ length: span }, (_, i) => start + i);
}

/**
 * Where somebody stands, as one word.
 *
 * The order of these tests is the design. Revoked outranks everything because it
 * is the only one that means "cannot get in". "Invited" beats "No access" for
 * anyone who has never arrived: telling an administrator that a person who has
 * not turned up yet holds no books answers a question nobody asked.
 */
function Standing({ person: p }: { person: Person }) {
  if (p.revokedAt !== null) return <span className="pf-pill pf-pill--danger">Revoked</span>;
  if (p.redeemedAt === null) return <span className="pf-pill pf-pill--warn">Invited</span>;
  if (p.grantCount === 0) return <span className="pf-pill pf-pill--warn">No access</span>;
  return <span className="pf-pill pf-pill--ok">Signed in</span>;
}

/* -------------------------------------------------------------------------- */
/* Inviting                                                                    */
/* -------------------------------------------------------------------------- */

function InviteForm({ actionData }: { actionData: Route.ComponentProps["actionData"] }) {
  const invited = actionData && "invited" in actionData ? actionData.invited : null;

  return (
    <div className="pf-panel">
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
          <Field name="name" label="Name" autoComplete="name" />
          <Field name="email" label="Email address" type="email" required autoComplete="email" />

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
  siteUrl,
  justGranted,
}: {
  person: Person;
  catalog: ContentUnit[];
  granted: Set<string>;
  /** Whether the administrator is looking at their own row. */
  isSelf: boolean;
  /** Where the site lives, for the link in the invitation message. */
  siteUrl: string;
  /** True on the render right after a grant to this person succeeded. */
  justGranted: boolean;
}) {
  const [showMessage, setShowMessage] = useState(false);

  // Opened by the grant itself, so the note to send is in front of the
  // administrator at the moment they have something to tell somebody — rather
  // than depending on them remembering a button afterwards.
  useEffect(() => {
    if (justGranted) setShowMessage(true);
  }, [justGranted]);
  const [find, setFind] = useState("");
  /** Ticked but not yet given — `unit:<slug>` / `work:<slug>`. */
  const [picked, setPicked] = useState<Set<string>>(() => new Set());
  /** Works whose volumes are showing. Collapsed is the default: twelve of the
   *  twenty-three rows in this catalogue are volumes of two works. */
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());

  const works = catalog.filter((u) => u.kind === "work");
  const standalone = catalog.filter((u) => u.kind === "book" && u.workSlug === null);
  const wholeLibrary = granted.has("library:*");
  const searching = find.trim() !== "";

  // Clear the ticks once the grants actually change — every ticked row has by
  // then moved up to "Already given", so a count left behind would offer to give
  // four books that are no longer on the list.
  const grantedKey = [...granted].sort().join("|");
  useEffect(() => setPicked(new Set()), [grantedKey]);

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
          <div className="pf-person__acts">
            {/* Called SIMULATE, and that is not a style preference. It read
                "See as them", which is a better description of what happens and
                a word nobody searches for — Asif went looking for this control
                with Cmd+F on 2026-08-04, typed "simulate", and the page said
                0/0 while the button was on screen. The intent, the banner and
                the way out all say simulate or simulation now, so finding any
                one of them finds all of them.

                Offered even for a revoked person: what they see is /no-access,
                and the banner that appears carries the way back out — the stop
                control is a public route precisely so this cannot be a dead end. */}
            <Form method="post">
              <input type="hidden" name="intent" value="simulate" />
              <input type="hidden" name="email" value={person.email} />
              <button
                type="submit"
                title={`Simulate ${person.displayName} — open the library as they see it`}
                className="pf-button pf-button--ghost pf-button--sm"
              >
                <Icon icon={faEye} /> Simulate
              </button>
            </Form>

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
        </div>

        <div className="pf-panel__body">
          <dl className="pf-facts">
            <Fact label="Invited" value={when(person.invitedAt)} />
            <Fact
              label="First signed in"
              value={person.redeemedAt ? when(person.redeemedAt) : "Never"}
            />
            <Fact
              label="Last signed in"
              value={person.lastSeenAt ? when(person.lastSeenAt) : "Never"}
            />
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
            label="Everything, including anything added later"
            on={wholeLibrary}
            onLabel="Granted"
            fields={{ email: person.email, scopeType: "library", scopeId: "*" }}
          />

          {/* Held first, and always visible — the search below filters what can
              be ADDED, never what is already given, or an administrator could
              type three letters and appear to have revoked everything. */}
          {held.length > 0 ? (
            <>
              {/* `.pf-subhead`, not `.pf-notes__heading`. That one belongs to the
                  reader's drawer, where it is a full-width row of a notes grid —
                  so restyling how a reader's notes are laid out silently
                  restyled this panel. */}
              <h3 className="pf-subhead">Already given</h3>
              {held.map((unit) => (
                <GrantRow
                  key={unit.slug}
                  label={unit.title}
                  hint={unit.kind === "work" ? "All volumes, including future ones" : statusHint(unit)}
                  on
                  onLabel="Granted"
                  fields={{
                    email: person.email,
                    scopeType: unit.kind === "work" ? "work" : "unit",
                    scopeId: unit.slug,
                  }}
                />
              ))}
            </>
          ) : null}

          <h3 className="pf-subhead">Add more</h3>

          {/* OUTSIDE the form below, deliberately. It filters what is shown and
              submits nothing, and a text input inside a form makes Enter grant
              whatever happens to be ticked. */}
          <SearchBox
            id="scope-find"
            label="Search the library"
            placeholder="Search the library"
            size="sm"
            action={{ kind: "filter", value: find, onChange: setFind }}
          />

          {/* ONE form for every book on offer, because provisioning someone new
              was eight page posts. Each ticked box is a `scope` field and the
              action grants them one at a time, so the audit trail still says
              which books rather than "four things". */}
          <Form method="post" preventScrollReset className="pf-stack-sm">
            <input type="hidden" name="intent" value="grant-many" />
            <input type="hidden" name="email" value={person.email} />

            {works.map((work) => {
              // A work already granted is not offered again, and neither are its
              // volumes: the grant covers every one of them, including volumes
              // added later, so the rows would be six ways of saying "yes, still".
              if (granted.has(`work:${work.slug}`)) return null;
              if (!matches(work) && !catalog.some((v) => v.workSlug === work.slug && matches(v))) {
                return null;
              }

              const volumes = catalog
                .filter((u) => u.workSlug === work.slug && matches(u))
                .filter((u) => !granted.has(`unit:${u.slug}`));

              return (
                <WorkScope
                  key={work.slug}
                  work={work}
                  volumes={volumes}
                  total={catalog.filter((u) => u.workSlug === work.slug).length}
                  // Searching expands everything that matched. A collapsed work
                  // hiding the volume someone just searched for reads as the
                  // search being broken.
                  open={searching || expanded.has(work.slug)}
                  frozen={searching}
                  onToggle={() => setExpanded(flip(expanded, work.slug))}
                  picked={picked}
                  onPick={(key) => setPicked(flip(picked, key))}
                  covered={wholeLibrary}
                />
              );
            })}

            {standalone
              .filter(matches)
              .filter((u) => !granted.has(`unit:${u.slug}`))
              .map((unit) => (
                <ScopeCheck
                  key={unit.slug}
                  scope={`unit:${unit.slug}`}
                  label={unit.title}
                  hint={statusHint(unit)}
                  covered={wholeLibrary}
                  picked={picked.has(`unit:${unit.slug}`)}
                  onPick={() => setPicked(flip(picked, `unit:${unit.slug}`))}
                />
              ))}

            {/* Centred and full size. It was a small pill hard against the left
                edge of a tall panel — the least prominent thing on a screen
                whose entire purpose it is. */}
            <div className="pf-scope-actions">
              <button type="submit" disabled={picked.size === 0} className="pf-button pf-button--primary">
                {picked.size === 0
                  ? "Give access to the ticked books"
                  : `Give access to ${count(picked.size, "book")}`}
              </button>

              {/* Available whenever they hold something, because the reason to
                  send the note is not always the moment access was given —
                  somebody loses the link, or never got the first message. */}
              {held.length > 0 || wholeLibrary ? (
                <button
                  type="button"
                  onClick={() => setShowMessage(true)}
                  className="pf-button pf-button--soft"
                >
                  <Icon icon={faEnvelope} />
                  Generate message
                </button>
              ) : null}
            </div>
          </Form>

          <InviteMessage
            open={showMessage}
            onClose={() => setShowMessage(false)}
            displayName={person.displayName}
            email={person.emailRaw || person.email}
            siteUrl={siteUrl}
            books={held.map((u) => u.title)}
            wholeLibrary={wholeLibrary}
          />
        </div>
      </div>
    </>
  );
}

/** A set with one member added or removed — the whole of both pickers' state. */
function flip(current: Set<string>, key: string): Set<string> {
  const next = new Set(current);
  if (!next.delete(key)) next.add(key);
  return next;
}

/**
 * One multi-volume work: a row that expands.
 *
 * The chevron is a SIBLING of the checkbox label, never a parent of it. A work
 * carries two independent controls — "give me all of this" and "show me what is
 * in it" — and nesting either inside the other is both invalid markup and a
 * press that does the wrong thing.
 *
 * Ticking the work disables its volumes rather than hiding them: the volumes are
 * the reason someone opened the row, and a list that empties itself when you
 * tick the thing above it looks like a fault.
 */
function WorkScope({
  work,
  volumes,
  total,
  open,
  frozen,
  onToggle,
  picked,
  onPick,
  covered,
}: {
  work: ContentUnit;
  volumes: ContentUnit[];
  /** Every volume the work has, not just the ones on offer — this is the count. */
  total: number;
  open: boolean;
  /** Held open by a search, so the chevron would be lying if it offered to close. */
  frozen: boolean;
  onToggle: () => void;
  picked: Set<string>;
  onPick: (scope: string) => void;
  covered: boolean;
}) {
  const id = `vols-${work.slug}`;
  const wholeWork = picked.has(`work:${work.slug}`);

  return (
    <div className="pf-scope-work">
      <div className="pf-scope-work__head">
        <button
          type="button"
          onClick={onToggle}
          disabled={frozen}
          aria-expanded={open}
          aria-controls={id}
          aria-label={`${open ? "Hide" : "Show"} the volumes of ${work.title}`}
          className="pf-scope-work__toggle"
        >
          <Icon icon={open ? faChevronDown : faChevronRight} />
        </button>

        <ScopeCheck
          scope={`work:${work.slug}`}
          label={work.title}
          hint={`All ${count(total, "volume")}, including future ones`}
          covered={covered}
          picked={wholeWork}
          onPick={() => onPick(`work:${work.slug}`)}
        />
      </div>

      {open ? (
        <div id={id} className="pf-scope-work__volumes">
          {volumes.map((vol) => (
            <ScopeCheck
              key={vol.slug}
              scope={`unit:${vol.slug}`}
              label={vol.title}
              hint={statusHint(vol)}
              covered={covered || wholeWork}
              coveredNote={wholeWork ? "Covered by the whole work above" : undefined}
              picked={picked.has(`unit:${vol.slug}`)}
              onPick={() => onPick(`unit:${vol.slug}`)}
              disabled={wholeWork}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** One tickable book. A label, so the whole row is the target on a phone. */
function ScopeCheck({
  scope,
  label,
  hint,
  covered = false,
  coveredNote,
  picked,
  onPick,
  disabled = false,
}: {
  /** `unit:<slug>` or `work:<slug>` — the value the action reads back. */
  scope: string;
  label: string;
  hint?: string;
  covered?: boolean;
  coveredNote?: string;
  picked: boolean;
  onPick: () => void;
  disabled?: boolean;
}) {
  return (
    <label className={`pf-scope${disabled ? " pf-scope--off" : ""}`}>
      <input
        type="checkbox"
        name="scope"
        value={scope}
        checked={picked && !disabled}
        onChange={onPick}
        disabled={disabled}
        className="pf-scope__box"
      />
      <span className="pf-scope__what">
        <span className="pf-scope__label">{label}</span>
        {covered ? (
          <span className="pf-scope__hint">
            {coveredNote ?? "Already covered by a wider grant"}
          </span>
        ) : hint ? (
          <span className="pf-scope__hint">{hint}</span>
        ) : null}
      </span>
    </label>
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
