/**
 * Advanced search — the only thing that reads the passage index.
 *
 * THE ENTITLEMENT RULE IS NOT RESTATED HERE. Every query below joins to
 * `VISIBLE_SQL` from access.server.ts, the same expression the library grid and
 * the book gate already share, with the viewer's normalized email bound to `?1`.
 * There is no code path in this module that reads `search_passage` without that
 * join, and `test/search-access.test.ts` fails if one appears. A search box is
 * the most tempting place in a site to filter results after fetching them; doing
 * that here would put the prose of every book into a response and trim it in
 * JavaScript, which is the same leak as shipping an index to the browser.
 *
 * WHAT IS DELIBERATELY ABSENT: the Scholar Companion. Its cards are readable by
 * one account through one function with the gate inside that function, so they
 * are not indexed at publish time and are not queried here. A test asserts this
 * module never mentions them — the same assertion book.$slug.text.ts carries.
 *
 * FACET COUNTS ARE COMPUTED WITH EVERY APPLIED FILTER IN FORCE, which is what
 * makes narrowing feel recursive rather than like a fixed panel: pick a
 * collection and the remaining counts are counts *within* it. They count
 * PASSAGES, and the book count is carried separately, because "47" meaning
 * matches and "6" meaning books are both true and answering with only one of
 * them makes the other surprising later.
 */

import { VISIBLE_SQL } from "./access.server";
import { normalizeEmail } from "./email.server";
import { matchExpression, parseQuery } from "~/lib/search-fold";
import type { ParsedQuery } from "~/lib/search-fold";
// The shapes live in ~/lib/search because the RESULTS PAGE renders them in the
// browser. `snippetOf` lives there too and is deliberately NOT re-exported from
// here: re-exporting it would let a component import it from this module, which
// drags VISIBLE_SQL toward the client bundle and fails the build with
// "server-only module referenced by client". It did exactly that once. Types are
// erased and are safe to pass through.
import type { Facet, Hit, Scope } from "~/lib/search";

export type { Facet, Hit, Scope } from "~/lib/search";

const SCOPE_COLUMN: Record<
  Scope,
  "heading_fold" | "body_fold" | "arabic_fold" | undefined
> = {
  all: undefined,
  titles: "heading_fold",
  content: "body_fold",
  verses: "arabic_fold",
};

export interface SearchFilters {
  /** content_unit.bucket — the collection a book belongs to. */
  collections: string[];
  /** search_passage.kind — what sort of thing matched. */
  kinds: string[];
  /** content_unit.slug — one or more books. */
  slugs: string[];
}

export const NO_FILTERS: SearchFilters = {
  collections: [],
  kinds: [],
  slugs: [],
};

export interface SearchResult {
  query: string;
  parsed: ParsedQuery;
  scope: Scope;
  hits: Hit[];
  /** Total matching passages, which is usually more than `hits.length`. */
  total: number;
  books: number;
  facets: { collections: Facet[]; kinds: Facet[]; books: Facet[] };
  /** True when the query held characters but none survived folding. */
  unusable: boolean;
}

/**
 * How many hits one request returns.
 *
 * The results are grouped by kind on the page, so this is a pool that groups are
 * drawn from rather than a page size. It is generous enough that a group is not
 * starved by a commoner one ranking above it, and the true per-group totals come
 * from the facet counts regardless — so a group whose pool is short still reports
 * its real size and offers to show them all, which applies a kind filter and
 * re-queries. Nothing is silently truncated.
 */
const POOL = 120;

const EMPTY: Omit<SearchResult, "query" | "parsed" | "scope"> = {
  hits: [],
  total: 0,
  books: 0,
  facets: { collections: [], kinds: [], books: [] },
  unusable: false,
};

/** `IN (?n, ?n+1, …)` for a bound list, or null when the list is empty. */
function inClause(
  column: string,
  values: string[],
  from: number,
): string | null {
  if (values.length === 0) return null;
  const holes = values.map((_, i) => `?${from + i}`).join(", ");
  return `${column} IN (${holes})`;
}

function hrefFor(row: {
  slug: string;
  kind: string;
  anchor_key: string | null;
  episode_number: number | null;
  id: number;
}): string {
  if (row.kind === "episode") {
    return `/book/${row.slug}${row.episode_number === null ? "" : `#episode-${row.episode_number}`}`;
  }
  if (row.anchor_key === null) return `/book/${row.slug}`;
  // `find` is the passage id. The reading page looks it up and hands the stored
  // quote to resolveAnchor, which either lands on it or reports that the text has
  // moved — it is never told an offset to trust.
  return `/book/${row.slug}/read/${encodeURIComponent(row.anchor_key)}?find=${row.id}`;
}

interface Row {
  id: number;
  slug: string;
  book_title: string;
  bucket: string;
  kind: string;
  anchor_key: string | null;
  heading: string | null;
  ordinal: number;
  episode_number: number | null;
  quote: string;
  arabic: string | null;
  label: string | null;
  surah: number | null;
  ayah: number | null;
}

/**
 * Run a search.
 *
 * The shape of the SQL is the same for both kinds of query and only the WHERE
 * differs: a free-text query matches the index, a reference query matches the
 * two numeric columns. Both are wrapped in the same `visible` join, so neither
 * can reach a book the viewer does not hold, and there is no third branch.
 */
export async function search(
  db: D1Database,
  email: string,
  {
    query,
    scope = "all",
    filters = NO_FILTERS,
  }: { query: string; scope?: Scope; filters?: SearchFilters },
): Promise<SearchResult> {
  const parsed = parseQuery(query);
  const base = { query, parsed, scope };

  if (query.trim() === "") return { ...base, ...EMPTY };
  if (parsed.empty) return { ...base, ...EMPTY, unusable: true };

  // ?1 is the email, always. Everything else is appended in a fixed order so the
  // bindings and the holes cannot drift apart.
  const binds: (string | number)[] = [normalizeEmail(email)];
  const where: string[] = [];

  if (parsed.reference !== null) {
    binds.push(parsed.reference.surah, parsed.reference.ayah);
    where.push(`p.surah = ?${binds.length - 1} AND p.ayah = ?${binds.length}`);
  } else {
    const expression = matchExpression(parsed.terms, SCOPE_COLUMN[scope]);
    if (expression === null) return { ...base, ...EMPTY, unusable: true };
    binds.push(expression);
    where.push(`search_fts MATCH ?${binds.length}`);
  }

  for (const [column, values] of [
    ["v.bucket", filters.collections],
    ["p.kind", filters.kinds],
    ["p.slug", filters.slugs],
  ] as const) {
    const clause = inClause(column, values, binds.length + 1);
    if (clause !== null) {
      where.push(clause);
      binds.push(...values);
    }
  }

  // A reference query has no MATCH, so it must not join the FTS table at all —
  // an unconstrained virtual table in a join is a full scan of the index.
  const source =
    parsed.reference !== null
      ? `search_passage p JOIN visible v ON v.slug = p.slug`
      : `search_fts f
         JOIN search_passage p ON p.id = f.rowid
         JOIN visible v ON v.slug = p.slug`;

  const cte = `WITH visible AS (${VISIBLE_SQL}),
       matched AS (
         SELECT p.id, p.slug, v.title AS book_title, v.bucket, p.kind, p.anchor_key,
                p.heading, p.ordinal, p.episode_number, p.quote, p.arabic, p.label,
                p.surah, p.ayah${parsed.reference === null ? ", f.rank AS rank" : ""}
         FROM ${source}
         WHERE ${where.join(" AND ")}
       )`;

  // Ordered by relevance for a text query; in book order for a reference, where
  // "best match" is meaningless — every row IS the verse.
  const order =
    parsed.reference === null
      ? "ORDER BY rank"
      : "ORDER BY book_title, ordinal";

  const facetQuery = (group: string, value: string, label: string) =>
    db
      .prepare(
        `${cte} SELECT ${value} AS value, ${label} AS label, count(*) AS passages,
                count(DISTINCT slug) AS books
         FROM matched GROUP BY ${group} ORDER BY passages DESC`,
      )
      .bind(...binds)
      .all<Facet>();

  const [hits, totals, byCollection, byKind, byBook] = await Promise.all([
    db
      .prepare(`${cte} SELECT * FROM matched ${order} LIMIT ${POOL}`)
      .bind(...binds)
      .all<Row>(),
    db
      .prepare(
        `${cte} SELECT count(*) AS passages, count(DISTINCT slug) AS books FROM matched`,
      )
      .bind(...binds)
      .first<{ passages: number; books: number }>(),
    facetQuery("bucket", "bucket", "bucket"),
    facetQuery("kind", "kind", "kind"),
    facetQuery("slug, book_title", "slug", "book_title"),
  ]);

  const rows = hits.results ?? [];
  const totalRow = totals ?? { passages: 0, books: 0 };

  return {
    ...base,
    hits: rows.map((r) => ({
      id: r.id,
      slug: r.slug,
      bookTitle: r.book_title,
      bucket: r.bucket,
      kind: r.kind,
      anchorKey: r.anchor_key,
      heading: r.heading,
      ordinal: r.ordinal,
      episodeNumber: r.episode_number,
      quote: r.quote,
      arabic: r.arabic,
      label: r.label,
      surah: r.surah,
      ayah: r.ayah,
      href: hrefFor(r),
    })),
    total: totalRow.passages,
    books: totalRow.books,
    facets: {
      collections: byCollection.results ?? [],
      kinds: byKind.results ?? [],
      books: byBook.results ?? [],
    },
    unusable: false,
  };
}

/**
 * One passage by id, for the reading page's `?find=`.
 *
 * Gated the same way as everything else — it takes the viewer's email and joins
 * to `visible`, so a guessed id in a URL cannot return a passage from a book the
 * reader does not hold. The reading page has already run `requireUnitAccess` on
 * the slug by the time this is called; this is not a substitute for that, it is
 * the same rule applied again at the only other place the row is read, so that
 * neither gate is load-bearing alone.
 */
export async function passageById(
  db: D1Database,
  email: string,
  id: number,
): Promise<{ slug: string; anchorKey: string | null; quote: string } | null> {
  const row = await db
    .prepare(
      `WITH visible AS (${VISIBLE_SQL})
       SELECT p.slug, p.anchor_key, p.quote
       FROM search_passage p JOIN visible v ON v.slug = p.slug
       WHERE p.id = ?2 LIMIT 1`,
    )
    .bind(normalizeEmail(email), id)
    .first<{ slug: string; anchor_key: string | null; quote: string }>();

  return row === null
    ? null
    : { slug: row.slug, anchorKey: row.anchor_key, quote: row.quote };
}
