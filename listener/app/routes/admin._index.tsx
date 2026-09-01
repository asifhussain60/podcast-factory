import { useState } from "react";
import {
  faArrowLeft,
  faCheck,
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
import { PersonDetail } from "~/components/admin/PersonDetail";
import { count } from "~/lib/plural";
import { when } from "~/lib/adminDate";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { startSimulating } from "~/server/simulate.server";
import {
  listCatalogForAdmin,
  recordEvent,
  type ContentUnit,
} from "~/server/access.server";
import {
  deletePerson,
  grant,
  grantsFor,
  invite,
  isPeopleFilter,
  listPeople,
  personByEmail,
  renamePerson,
  revokeGrant,
  revokeInvite,
  splitName,
  type PeopleFilter,
  type Person,
} from "~/server/people.server";
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

export function selectedPersonPath(requestUrl: string, email: string): string {
  const from = new URL(requestUrl);
  const params = new URLSearchParams(from.search);
  params.set("email", email);
  params.delete("page");
  // React Router's data submissions can invoke this action through /admin.data
  // with router-only parameters. A post-invite redirect is a browser location,
  // so it must point back at the human page, not the data endpoint that carried
  // the mutation.
  params.delete("_routes");
  const query = params.toString();
  return query === "" ? "/admin" : `/admin?${query}`;
}

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
    /**
     * Whether this person's address carries a `+tag` that folding did not remove.
     *
     * Derived HERE from what was stored, not carried through the invite as a
     * one-shot flag. Inviting now opens the person's panel instead of answering
     * with a message above the table, and a warning that only appeared on the
     * render right after the invite would have been a warning the redirect threw
     * away — while the hazard it describes is a permanent property of the
     * address, true every time this person is opened.
     */
    plusTag: person === null ? false : hasUnfoldedPlusTag(person.emailRaw),
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
      const email = tryNormalizeEmail(raw);
      if (email === null) {
        return { error: `"${raw.trim()}" is not an email address.` };
      }
      // One typed name, two stored columns. The form no longer asks for a note
      // either — the column stays and an existing one is still shown, because
      // deleting what an administrator once wrote is not a form change.
      await invite(env.DB, raw, actor, splitName(text("name")), now);

      // OPEN THE PERSON, rather than answering with a green line above a table
      // of a hundred. Inviting somebody and giving them a book are one act
      // performed in two places, and the second place had to be found by
      // searching for the name just typed.
      //
      // The rest of the query is carried through — the filter and the search
      // that were applied stay applied, so "Back to everyone" returns to the
      // list as it was rather than to the top of an unfiltered one. `page` is
      // dropped because the new person is not on it.
      //
      // The two things the green line used to say are not lost: the `+tag`
      // warning is re-derived on the panel from the address itself, and the
      // reminder to send the link is the Generate message button that is now
      // offered there for anybody selected.
      return redirect(selectedPersonPath(request.url, email));
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
        headers: {
          "Set-Cookie": startSimulating(target, new URL(request.url)),
        },
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
        .filter(
          ([type, id]) => (type === "unit" || type === "work") && Boolean(id),
        );

      for (const [type, id] of scopes) {
        await grant(env.DB, email, type as "unit" | "work", id, actor, now);
      }
      return { ok: true, granted: scopes.length, grantedTo: email };
    }

    default:
      return { error: "Unknown action." };
  }
}

export default function AdminPeople({
  loaderData,
  actionData,
}: Route.ComponentProps) {
  const {
    people,
    total,
    everyone,
    catalog,
    person,
    search,
    filter,
    page,
    pageSize,
  } = loaderData;
  const granted = new Set(loaderData.granted);
  const [params] = useSearchParams();

  // The tallies belong to the section, not to this page: the strip above the tabs
  // shows three of them and these chips show all seven, and they are the same
  // seven numbers. Read from the parent loader rather than queried again, because
  // two queries for one set of counts is how a chip and a tile come to disagree.
  // The layout is always matched — this route is one of its children — so the
  // lookup cannot miss.
  const { tallies } = useRouteLoaderData<typeof adminLoader>(
    "routes/_authed._admin",
  )!;

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
              plusTag={loaderData.plusTag}
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
                <PersonRow
                  key={p.email}
                  person={p}
                  isSelf={p.email === self}
                  withParam={withParam}
                />
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
                <Link
                  key={n}
                  to={withParam("page", String(n))}
                  className="pf-pagenum"
                >
                  {n + 1}
                </Link>
              ),
            )}
          </span>

          <span className="pf-pager__where">
            {page * pageSize + 1}–{Math.min(total, (page + 1) * pageSize)} of{" "}
            {total}
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
            <button
              type="submit"
              className="pf-button pf-button--sm pf-button--danger"
            >
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
          <fetcher.Form
            method="post"
            className="pf-rowedit"
            onSubmit={() => setMode("idle")}
          >
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
            <button
              type="submit"
              aria-label="Save the name"
              className="pf-iconbtn"
            >
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
        {p.lastSeenAt === null ? (
          <span className="pf-quiet">Never</span>
        ) : (
          when(p.lastSeenAt)
        )}
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
  const start = Math.max(
    0,
    Math.min(page - Math.floor(span / 2), pages - span),
  );
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
  if (p.revokedAt !== null)
    return <span className="pf-pill pf-pill--danger">Revoked</span>;
  if (p.redeemedAt === null)
    return <span className="pf-pill pf-pill--warn">Invited</span>;
  if (p.grantCount === 0)
    return <span className="pf-pill pf-pill--warn">No access</span>;
  return <span className="pf-pill pf-pill--ok">Signed in</span>;
}

/* -------------------------------------------------------------------------- */
/* Inviting                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Adding somebody to the invitation list.
 *
 * It answers with an ERROR or with nothing. A successful invite is a redirect
 * onto that person's own panel — see the action — so there is no success message
 * here to write: the panel opening is the confirmation, and it is also the next
 * thing to do. The two notices this used to print both moved with it, to where
 * they remain true rather than lasting one render: the `+tag` warning is derived
 * from the stored address, and the reminder to send the link is a button.
 */
function InviteForm({
  actionData,
}: {
  actionData: Route.ComponentProps["actionData"];
}) {
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
          <Field
            name="email"
            label="Email address"
            type="email"
            required
            autoComplete="email"
          />

          <button
            type="submit"
            className="pf-button pf-button--primary pf-button--block"
          >
            Add to the invitation list
          </button>
        </Form>

        {actionData && "error" in actionData && actionData.error ? (
          <p className="pf-message pf-message--danger">{actionData.error}</p>
        ) : null}

        {/* Said before the press rather than after it, because it is true of
            every invitation and not of one: no mail is sent from this
            application, and there never was a transport. Saving opens the new
            person's page, where the message to send them is a button. */}
        <p className="pf-note--quiet">
          Nothing is emailed. Saving opens their page, where you can give them
          books and copy a message to send.
        </p>
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
