import { faUserPlus } from "@fortawesome/free-solid-svg-icons";
import { Form, Link, useSearchParams } from "react-router";

import type { Route } from "./+types/admin.content";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { GrantRow } from "~/components/admin/GrantRow";
import { ToggleButton } from "~/components/admin/ToggleButton";
import { count } from "~/lib/plural";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { listCatalogForAdmin } from "~/server/access.server";
import {
  grant,
  holdersOf,
  listPeople,
  revokeGrant,
  setOpenToAll,
} from "~/server/people.server";

/**
 * The catalog, from the other direction: for each book, who can open it.
 *
 * "What can this person see" and "who can see this book" are both real questions
 * and neither answers the other, so both screens exist over the same tables.
 *
 * This one grew a second half. As the library grows the common act stops being
 * "give this person their books" — done once, when someone joins — and becomes
 * "give this new book to the fifteen people who should have it". Doing that on
 * the people screen is fifteen visits; here it is one.
 */
export async function loader({ request, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const url = new URL(request.url);
  const selected = url.searchParams.get("slug");
  const search = url.searchParams.get("q") ?? "";

  const catalog = await listCatalogForAdmin(env.DB);
  const readable = catalog.filter((u) => u.kind !== "work");
  const holders = await Promise.all(
    readable.map((u) => holdersOf(env.DB, u.slug)),
  );
  const units = readable.map((u, i) => ({ ...u, holders: holders[i] }));

  // The selected book is taken from the list already loaded rather than fetched
  // again — it carries its holders, which a fresh `unitBySlug` would not, and a
  // second query could disagree with the first about `open_to_all`.
  const unit = selected
    ? (units.find((u) => u.slug === selected) ?? null)
    : null;

  // The people list is loaded only when a book is open for provisioning, and it
  // is searched and capped in SQL — the same discipline as the people screen.
  const candidates = unit
    ? await listPeople(env.DB, { search, filter: "all", limit: 25 })
    : { people: [], total: 0, everyone: 0 };

  return {
    units,
    unit,
    candidates: candidates.people,
    candidateTotal: candidates.total,
    // Only DIRECT grants. The toggle writes a `unit` grant, so somebody covered
    // by a library grant must not show as "Has it" — pressing it would revoke a
    // row that does not exist and appear to do nothing.
    holding: unit
      ? unit.holders.filter((h) => h.via === "unit").map((h) => h.email)
      : [],
    search,
  };
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const actor = context.get(session).viewer!.email;
  const form = await request.formData();
  const intent = String(form.get("intent") ?? "open-to-all");
  const now = new Date().toISOString();

  switch (intent) {
    // `open_to_all` is a privilege bit. It is writable ONLY from here, behind an
    // admin session — never by the publish endpoint, which names its columns
    // explicitly and is grepped by a test for exactly that.
    case "open-to-all":
      await setOpenToAll(
        env.DB,
        String(form.get("slug")),
        form.get("open") === "1",
        actor,
        now,
      );
      return { ok: true };

    case "grant":
      await grant(
        env.DB,
        String(form.get("email")),
        "unit",
        String(form.get("slug")),
        actor,
        now,
      );
      return { ok: true };

    case "revoke-grant":
      await revokeGrant(
        env.DB,
        String(form.get("email")),
        "unit",
        String(form.get("slug")),
        actor,
        now,
      );
      return { ok: true };

    default:
      return { error: "Unknown action." };
  }
}

export default function AdminContent({ loaderData }: Route.ComponentProps) {
  const { units, unit, candidates, candidateTotal, search } = loaderData;
  const holding = new Set(loaderData.holding);
  const [params] = useSearchParams();

  const withParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === "") next.delete(key);
    else next.set(key, value);
    return `?${next.toString()}`;
  };

  return (
    <div className="pf-admin-split">
      <section className="pf-admin-list pf-stack-sm">
        {units.map((u) => (
          <article
            key={u.slug}
            aria-current={unit?.slug === u.slug ? "true" : undefined}
            className="pf-card pf-card--padded pf-unit"
          >
            <div className="pf-split">
              <div className="pf-split__main">
                <h2 className="pf-row__main">{u.title}</h2>
                <p className="pf-note pf-note--quiet">
                  {u.bucket}
                  {u.workSlug ? ` · part of ${u.workSlug}` : ""}
                  {u.status === "published" ? "" : ` · ${u.status}`}
                </p>
              </div>

              <Form method="post">
                <input type="hidden" name="intent" value="open-to-all" />
                <input type="hidden" name="slug" value={u.slug} />
                <input
                  type="hidden"
                  name="open"
                  value={u.openToAll ? "0" : "1"}
                />
                <ToggleButton on={u.openToAll}>
                  {u.openToAll
                    ? "Open to everyone · make private"
                    : "Open to everyone"}
                </ToggleButton>
              </Form>
            </div>

            <div className="pf-split pf-card__foot">
              <p className="pf-note pf-note--quiet pf-split__main">
                {u.status !== "published"
                  ? "Not published, so nobody can open it yet — grants made now take effect when it publishes."
                  : u.openToAll
                    ? "Everyone invited can open this."
                    : u.holders.length === 0
                      ? "Nobody has been given this."
                      : `${count(u.holders.length, "person has", "people have")} this`}
              </p>

              <Link
                to={withParam("slug", unit?.slug === u.slug ? "" : u.slug)}
                className="pf-button pf-button--sm pf-button--soft"
              >
                <Icon icon={faUserPlus} />
                {unit?.slug === u.slug ? "Done" : "Who has this"}
              </Link>
            </div>
          </article>
        ))}
      </section>

      <section className="pf-admin-detail">
        {unit === null ? (
          <EmptyState>
            Choose a book to see who has it and give it to more people.
          </EmptyState>
        ) : (
          <div className="pf-panel">
            <div className="pf-panel__head">
              <h2 className="pf-panel__title">Who can open {unit.title}</h2>
            </div>

            <div className="pf-panel__body pf-stack-sm">
              {unit.openToAll ? (
                <p className="pf-message pf-message--warn">
                  This book is open to everyone invited, so the grants below
                  make no difference while that stays on.
                </p>
              ) : null}

              <SearchBox
                id="holders-q"
                label="Search people"
                placeholder="Search people by name or address"
                size="sm"
                action={{
                  kind: "navigate",
                  name: "q",
                  value: search,
                  // Or narrowing the list would close the book being provisioned.
                  hidden: { slug: unit.slug },
                }}
              />

              {candidates.length === 0 ? (
                <EmptyState>
                  {search === ""
                    ? "Nobody has been invited yet."
                    : `Nobody matches “${search}”.`}
                </EmptyState>
              ) : (
                candidates.map((p) => (
                  <GrantRow
                    key={p.email}
                    label={p.displayName}
                    // The address, and — the half the other screen's copy of this
                    // row had lost — whether they can still sign in at all.
                    hint={`${p.revokedAt !== null ? "Sign-in revoked · " : ""}${p.emailRaw}`}
                    on={holding.has(p.email)}
                    onLabel="Has it"
                    fields={{ email: p.email, slug: unit.slug }}
                  />
                ))
              )}

              {candidateTotal > candidates.length ? (
                <p className="pf-note--quiet">
                  Showing {candidates.length} of {candidateTotal}. Search to
                  narrow the list.
                </p>
              ) : null}

              {/* The toggle above writes a grant on THIS book only, so it must
                  not appear able to take away access somebody holds through the
                  whole library or through a parent work — pressing it would
                  revoke a grant that is not there and appear to do nothing. */}
              {unit.holders.some((h) => h.via !== "unit") ? (
                <p className="pf-note--quiet">
                  {unit.holders
                    .filter((h) => h.via !== "unit")
                    .map((h) => h.displayName)
                    .join(", ")}{" "}
                  can also open this, through a wider grant. Change that on
                  their own page.
                </p>
              ) : null}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
