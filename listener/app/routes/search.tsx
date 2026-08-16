import {
  faArrowLeft,
  faBookOpen,
  faChevronDown,
  faFileLines,
  faHeadphones,
  faLayerGroup,
  faQuoteLeft,
  faSliders,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";

import type { Route } from "./+types/search";
import { AppShell } from "~/components/AppShell";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
/* `search` is used ONLY inside the loader, so React Router strips it — and with
   it the server module — from the client bundle. Everything the COMPONENT needs
   comes from ~/lib/search, which touches no database. Import `snippetOf` from
   the server module instead and the build fails outright: server-only module
   referenced by client. That is the guard working, not an obstacle. */
import { search } from "~/server/search.server";
import { snippetOf } from "~/lib/search";
import type { Facet, Hit, Scope } from "~/lib/search";

/**
 * Advanced search.
 *
 * THE URL IS THE SEARCH, and that is the whole architecture of this page. Query,
 * scope and every applied facet live in the address bar; nothing that narrows
 * the results is held in component state. Three things fall out of that for
 * free, and they are the reason a `saved_search` table was considered and
 * rejected: a search can be bookmarked, it can be sent to somebody, and the back
 * button walks back up the drill-down one step at a time.
 *
 * A shared search is a QUERY, never RESULTS. Whoever opens the link runs it
 * again under their own entitlements, so a link to a search across six books
 * shows the recipient only the ones they hold. Storing results anywhere — a
 * table, a cache, a file — would be the same leak as shipping the index to the
 * browser, and would arrive by a route nobody would think to audit.
 *
 * The facets are LINKS for the same reason: middle-clickable, copyable, and they
 * work with JavaScript off. What state this page does hold is presentational
 * only — which hit is expanded — and losing it costs the reader nothing.
 */

export function meta({ location }: Route.MetaArgs): Route.MetaDescriptors {
  const q = new URLSearchParams(location.search).get("q")?.trim();
  return [
    {
      title: q
        ? `${q} — search — Podcast Factory`
        : "Advanced search — Podcast Factory",
    },
    {
      name: "description",
      content: "Search the library by more than its title.",
    },
  ];
}

const SCOPES: { value: Scope; label: string }[] = [
  { value: "all", label: "Everything" },
  { value: "titles", label: "Titles" },
  { value: "content", label: "In the text" },
  { value: "verses", label: "Verses" },
];

const isScope = (value: string | null): value is Scope =>
  SCOPES.some((s) => s.value === value);

export async function loader({ request, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer;
  const url = new URL(request.url);

  const raw = url.searchParams.get("scope");
  const scope: Scope = isScope(raw) ? raw : "all";

  const result = await search(env.DB, viewer?.email ?? "", {
    query: url.searchParams.get("q") ?? "",
    scope,
    filters: {
      collections: url.searchParams.getAll("collection"),
      kinds: url.searchParams.getAll("kind"),
      slugs: url.searchParams.getAll("book"),
    },
  });

  return { result, isAdmin: viewer?.isAdmin === true };
}

/* -------------------------------------------------------------------------- */
/* How each kind of hit is titled and drawn                                    */
/* -------------------------------------------------------------------------- */

const KINDS: Record<
  string,
  { label: string; one: string; icon: IconDefinition }
> = {
  chapter: { label: "In the text", one: "passage", icon: faBookOpen },
  verse: { label: "Verses", one: "verse", icon: faQuoteLeft },
  episode: { label: "Episodes", one: "episode", icon: faHeadphones },
  blurb: { label: "About the book", one: "description", icon: faFileLines },
};

/** Fixed, so the page does not rearrange itself as relevance shifts. */
const KIND_ORDER = ["chapter", "verse", "episode", "blurb"];

const kindOf = (kind: string) =>
  KINDS[kind] ?? { label: kind, one: "result", icon: faLayerGroup };

const count = (n: number, one: string) =>
  `${n.toLocaleString()} ${n === 1 ? one : `${one}s`}`;

export default function Search({ loaderData }: Route.ComponentProps) {
  const { result, isAdmin } = loaderData;
  const [params] = useSearchParams();
  const box = useRef<HTMLDivElement>(null);

  const query = result.query;
  const asked = query.trim() !== "";

  /**
   * `/` focuses the box from anywhere on the page.
   *
   * Ignored while the reader is already typing somewhere, or it would swallow a
   * slash in a real query — a Qur'an reference is often typed with one.
   */
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey)
        return;
      const active = document.activeElement;
      if (
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active instanceof HTMLElement && active.isContentEditable)
      ) {
        return;
      }
      event.preventDefault();
      box.current?.querySelector("input")?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Everything except the facets, so a facet link can rebuild the query string
  // without carrying a stale copy of itself.
  const carried = new URLSearchParams();
  if (asked) carried.set("q", query);
  if (result.scope !== "all") carried.set("scope", result.scope);

  const applied = [
    ...params
      .getAll("collection")
      .map((v) => ({ key: "collection", value: v, label: v })),
    ...params
      .getAll("kind")
      .map((v) => ({ key: "kind", value: v, label: kindOf(v).label })),
    ...params.getAll("book").map((v) => ({
      key: "book",
      value: v,
      label: result.facets.books.find((b) => b.value === v)?.label ?? v,
    })),
  ];

  /** The URL with one facet value toggled on or off. */
  const toggled = (key: string, value: string) => {
    const next = new URLSearchParams(carried);
    for (const { key: k, value: v } of applied) {
      if (k === key && v === value) continue; // the one being removed
      next.append(k, v);
    }
    if (!applied.some((a) => a.key === key && a.value === value))
      next.append(key, value);
    return `/search?${next.toString()}`;
  };

  const scopeHref = (scope: Scope) => {
    const next = new URLSearchParams();
    if (asked) next.set("q", query);
    if (scope !== "all") next.set("scope", scope);
    for (const { key, value } of applied) next.append(key, value);
    return `/search?${next.toString()}`;
  };

  const grouped = KIND_ORDER.map((kind) => ({
    kind,
    hits: result.hits.filter((h) => h.kind === kind),
    total: result.facets.kinds.find((f) => f.value === kind)?.passages ?? 0,
  })).filter((g) => g.hits.length > 0);

  return (
    <AppShell here="search" isAdmin={isAdmin}>
      <section className="pf-masthead pf-masthead--tight">
        <h1 className="pf-title">Advanced search</h1>
        <p className="pf-lede">
          Every word of every book you hold — the prose, the verses, the
          episodes. Narrow it as far as you like; the address bar keeps your
          place, so a search can be bookmarked or sent to someone.
        </p>

        <div className="pf-find" ref={box}>
          {/* A real GET form. Enter submits, the browser keeps its own history,
              and the page works with no JavaScript at all. */}
          <SearchBox
            id="advanced-search"
            label="Search the library"
            placeholder="A word, a phrase, or a reference like 2:255"
            size="wide"
            action={{
              kind: "navigate",
              name: "q",
              value: query,
              hidden: Object.fromEntries(
                [...carried.entries()].filter(([k]) => k !== "q"),
              ),
            }}
          />

          {/* Where to look, never what may come back. */}
          <div
            className="pf-swatches pf-find__scope"
            role="group"
            aria-label="Where to search"
          >
            {SCOPES.map((scope) => (
              <Link
                key={scope.value}
                to={scopeHref(scope.value)}
                className="pf-swatch"
                aria-current={result.scope === scope.value ? "true" : undefined}
                preventScrollReset
              >
                {scope.label}
              </Link>
            ))}
          </div>
        </div>

        {applied.length === 0 ? null : (
          <div className="pf-crumbs" aria-label="Filters you have applied">
            <span className="pf-crumbs__lead">Narrowed to</span>
            {applied.map((chip) => (
              <Link
                key={`${chip.key}-${chip.value}`}
                to={toggled(chip.key, chip.value)}
                className="pf-chip pf-chip--applied"
                preventScrollReset
              >
                {chip.label}
                <Icon
                  icon={faXmark}
                  title={`Remove the ${chip.label} filter`}
                />
              </Link>
            ))}
            <Link
              to={`/search?${carried.toString()}`}
              className="pf-crumbs__clear"
              preventScrollReset
            >
              Clear all
            </Link>
          </div>
        )}
      </section>

      {/* Announced, because narrowing replaces the results with no page change a
          screen reader would otherwise notice. */}
      <p aria-live="polite" className="sr-only">
        {!asked
          ? ""
          : `${count(result.total, "result")} in ${count(result.books, "book")}`}
      </p>

      {!asked ? (
        <Prompt />
      ) : result.unusable ? (
        <EmptyState>
          There is nothing to search for in{" "}
          <strong className="pf-strong">{query.trim()}</strong> — try a word or
          a reference like <strong className="pf-strong">2:255</strong>.
        </EmptyState>
      ) : result.total === 0 ? (
        <EmptyState>
          Nothing matches <strong className="pf-strong">{query.trim()}</strong>
          {applied.length > 0 ? " with those filters" : ""}.
          {applied.length > 0 ? (
            <>
              {" "}
              <Link to={`/search?${carried.toString()}`}>Clear them</Link> and
              try again.
            </>
          ) : null}
        </EmptyState>
      ) : (
        <div className="pf-results">
          <Facets result={result} toggled={toggled} applied={applied} />

          <div className="pf-results__list">
            <p className="pf-results__count">
              <strong className="pf-strong">
                {count(result.total, "result")}
              </strong>{" "}
              in {count(result.books, "book")}
              {result.parsed.reference !== null ? (
                <>
                  {" "}
                  for{" "}
                  <span className="pf-ref">
                    {result.parsed.reference.surah}:
                    {result.parsed.reference.ayah}
                  </span>
                </>
              ) : null}
            </p>

            {grouped.map((group) => (
              <Group
                key={group.kind}
                kind={group.kind}
                hits={group.hits}
                total={group.total}
                terms={result.parsed.terms}
                more={toggled("kind", group.kind)}
                filtered={applied.some((a) => a.key === "kind")}
              />
            ))}
          </div>
        </div>
      )}
    </AppShell>
  );
}

/** What the page says before anything has been asked of it. */
function Prompt() {
  return (
    <div className="pf-prompt">
      <p className="pf-prompt__lead">
        <Icon icon={faSliders} /> Three things worth knowing
      </p>
      <ul className="pf-prompt__list">
        <li>
          <strong className="pf-strong">Type it however you spell it.</strong>{" "}
          Arabic matches whether or not you type the vowel marks, and the
          Sessions were transcribed on an Urdu keyboard — searching{" "}
          <span lang="ar">ولي</span> finds those too.
        </li>
        <li>
          <strong className="pf-strong">
            A reference is a jump, not a phrase.
          </strong>{" "}
          Type <span className="pf-ref">2:255</span> to land on every passage
          that quotes it.
        </li>
        <li>
          <strong className="pf-strong">Narrow, then narrow again.</strong>{" "}
          Every filter recounts the ones beside it, so you can see what is left
          before you press.
        </li>
      </ul>
      <p className="pf-prompt__foot">
        <Link to="/" className="pf-button pf-button--soft">
          <Icon icon={faArrowLeft} />
          Back to the library
        </Link>
      </p>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* The facet rail                                                              */
/* -------------------------------------------------------------------------- */

function Facets({
  result,
  toggled,
  applied,
}: {
  result: Route.ComponentProps["loaderData"]["result"];
  toggled: (key: string, value: string) => string;
  applied: { key: string; value: string }[];
}) {
  const groups: { key: string; title: string; facets: Facet[] }[] = [
    {
      key: "collection",
      title: "Collection",
      facets: result.facets.collections,
    },
    { key: "kind", title: "What matched", facets: result.facets.kinds },
    { key: "book", title: "Book", facets: result.facets.books },
  ].filter((g) => g.facets.length > 1 || applied.some((a) => a.key === g.key));

  if (groups.length === 0) return null;

  return (
    <aside className="pf-facets" aria-label="Narrow these results">
      {groups.map((group) => (
        <section key={group.key} className="pf-facets__group">
          <h2 className="pf-facets__title">{group.title}</h2>
          <ul className="pf-facets__list">
            {group.facets.map((facet) => {
              const on = applied.some(
                (a) => a.key === group.key && a.value === facet.value,
              );
              return (
                <li key={facet.value}>
                  <Link
                    to={toggled(group.key, facet.value)}
                    className="pf-facet"
                    /* `aria-current`, not `aria-pressed`: this is a link, and a
                       link is not a toggle button however much it behaves like
                       one here. Pressed-state on an anchor is invalid ARIA and
                       several screen readers drop it silently. */
                    aria-current={on ? "true" : undefined}
                    preventScrollReset
                  >
                    <span className="pf-facet__label">
                      {group.key === "kind" ? (
                        <Icon icon={kindOf(facet.value).icon} />
                      ) : null}
                      {group.key === "kind"
                        ? kindOf(facet.value).label
                        : facet.label}
                    </span>
                    {/* Both numbers, because both are true and answering with one
                        makes the other a surprise later. */}
                    <span className="pf-facet__n">
                      {facet.passages.toLocaleString()}
                      {group.key === "book" ? null : (
                        <span className="pf-facet__books">
                          {" "}
                          in {facet.books}
                        </span>
                      )}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </aside>
  );
}

/* -------------------------------------------------------------------------- */
/* Results                                                                     */
/* -------------------------------------------------------------------------- */

function Group({
  kind,
  hits,
  total,
  terms,
  more,
  filtered,
}: {
  kind: string;
  hits: Hit[];
  total: number;
  terms: string[];
  more: string;
  filtered: boolean;
}) {
  const meta = kindOf(kind);
  return (
    <section className="pf-group">
      <h2 className="pf-group__head">
        <Icon icon={meta.icon} />
        {meta.label}
        <span className="pf-group__n">{count(total, meta.one)}</span>
      </h2>

      <ul className="pf-hits">
        {hits.map((hit) => (
          <HitCard key={hit.id} hit={hit} terms={terms} />
        ))}
      </ul>

      {/* Never truncate silently: if the pool is short of the real total, the
          page says so and offers the rest. */}
      {!filtered && total > hits.length ? (
        <p className="pf-group__more">
          <Link
            to={more}
            className="pf-button pf-button--soft"
            preventScrollReset
          >
            Show all {total.toLocaleString()} {meta.one}s
            <Icon icon={faChevronDown} />
          </Link>
        </p>
      ) : null}
    </section>
  );
}

/**
 * One result.
 *
 * The whole card is a link to the passage. Expanding it to read more is a
 * separate control INSIDE that link's row rather than nested in it, because a
 * button inside a link is neither reliably clickable nor announceable.
 */
function HitCard({ hit, terms }: { hit: Hit; terms: string[] }) {
  const [open, setOpen] = useState(false);
  const verse = hit.kind === "verse";
  const text = verse && hit.arabic !== null ? stripArabic(hit) : hit.quote;
  const long = text !== "" && hit.quote.split(/\s+/).length > 30;

  return (
    <li className={`pf-hit${verse ? " pf-hit--verse" : ""}`}>
      <div className="pf-hit__where">
        <Link to={`/book/${hit.slug}`} className="pf-hit__book">
          {hit.bookTitle}
        </Link>
        {hit.heading === null ? null : (
          <>
            <span className="pf-hit__sep" aria-hidden="true">
              ·
            </span>
            <span className="pf-hit__chapter">{hit.heading}</span>
          </>
        )}
        {hit.surah === null ? null : (
          <span className="pf-ref pf-hit__ref">
            {hit.label ?? `${hit.surah}:${hit.ayah}`}
          </span>
        )}
      </div>

      <Link to={hit.href} className="pf-hit__body" preventScrollReset={false}>
        {verse && hit.arabic !== null ? (
          /* The Arabic in its own right-to-left block, in the face the reading
             edition sets scripture in, with anything else beneath it. Side by
             side only where there is genuinely room — see the stylesheet. */
          <span className="pf-hit__ar" dir="rtl" lang="ar">
            {hit.arabic}
          </span>
        ) : null}

        {/* Rendered only when there is something to render. A verse whose block
            is nothing but the Arabic and its caption has no second column, and
            an empty one would leave the Arabic sitting in half the card looking
            as though its translation had failed to load. */}
        {text === "" ? null : (
          <span className={`pf-hit__text${open ? " is-open" : ""}`}>
            {open ? hit.quote : <Snippet quote={text} terms={terms} />}
          </span>
        )}
      </Link>

      {long ? (
        <button
          type="button"
          className="pf-hit__expand"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "Show less" : "Read around it"}
          <Icon icon={faChevronDown} />
        </button>
      ) : null}
    </li>
  );
}

/**
 * The verse's block text with the Arabic taken out.
 *
 * `quote` deliberately carries the whole block — caption and Arabic together —
 * because that is what the reading page will match on. For DISPLAY the Arabic is
 * already set in its own block above, so repeating it in the snippet would print
 * the verse twice.
 */
function stripArabic(hit: Hit): string {
  const rest = hit.quote.replace(hit.arabic ?? "", "").trim();
  return rest === "" || rest === hit.label ? "" : rest;
}

function Snippet({ quote, terms }: { quote: string; terms: string[] }) {
  if (quote === "") return null;
  return (
    <>
      {snippetOf(quote, terms).map((segment, i) =>
        segment.hit ? (
          <mark key={i} className="pf-hit__mark">
            {segment.text}
          </mark>
        ) : (
          <span key={i}>{segment.text}</span>
        ),
      )}
    </>
  );
}
