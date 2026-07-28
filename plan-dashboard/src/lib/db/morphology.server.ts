/**
 * morphology.server.ts — the site's read-only window onto the Quranic Arabic
 * Corpus morphology layer.
 *
 * SERVER ONLY (better-sqlite3, per-call open/close — the corpus-grounding
 * pattern). Reads the COMMITTED artifacts the pipeline builds and verifies:
 *
 *   content/knowledge-base/quranic-corpus/morphology.db   (roots/lemmas/segments)
 *   content/knowledge-base/lexicon.jsonl                  (Lane/Maqayis/Mufradat per root)
 *   content/knowledge-base/_index/lexicon-coverage.json   (join coverage)
 *   content/knowledge-base/mirror.db                      (verse text, fts_quran)
 *
 * No model, no network, no writes. Every function degrades to null/[] when an
 * artifact is absent — a missing DB means an empty page state, never a crash.
 * Matching runs in the shared fold space (src/lib/arabic-fold.ts, the pinned
 * TS mirror of the Python side), so the site resolves exactly the terms the
 * pipeline would.
 */
import Database from "better-sqlite3";
import { readFileSync } from "node:fs";

import {
  arabicFold,
  foldsMatch,
  latinFold,
  normalizeArabic,
} from "../arabic-fold";

const KB = (rel: string) =>
  new URL(`../../../../content/knowledge-base/${rel}`, import.meta.url)
    .pathname;

const MORPHOLOGY_DB = KB("quranic-corpus/morphology.db");
const MIRROR_DB = KB("mirror.db");
const LEXICON_JSONL = KB("lexicon.jsonl");
const COVERAGE_JSON = KB("_index/lexicon-coverage.json");

export interface FamilyLemma {
  lemma_bw: string;
  lemma_ar: string;
  pos: string | null;
  occurrence_count: number;
  first_location: string;
}

export interface RootRecord {
  root_bw: string;
  root_ar: string;
  root_dashed: string;
  occurrences: number;
  lemma_count: number;
  family: FamilyLemma[];
  pos_distribution: Record<string, number>;
  lane_en?: string;
  maqayis_ar?: string;
  mufradat_ar?: string;
}

export interface RootListRow {
  root_bw: string;
  root_ar: string;
  occurrence_count: number;
  lemma_count: number;
  has_lane: boolean;
}

function openRo(path: string): Database.Database | null {
  try {
    return new Database(path, { readonly: true, fileMustExist: true });
  } catch {
    return null;
  }
}

// ─── Lexicon (small committed JSONL — parsed once per process) ───────────────
let lexiconCache: Map<string, Record<string, string>> | null = null;

function lexicon(): Map<string, Record<string, string>> {
  if (lexiconCache) return lexiconCache;
  const map = new Map<string, Record<string, string>>();
  try {
    for (const line of readFileSync(LEXICON_JSONL, "utf-8").split("\n")) {
      const t = line.trim();
      if (!t) continue;
      try {
        const rec = JSON.parse(t);
        if (rec.root_skel) map.set(rec.root_skel, rec);
      } catch {
        /* skip malformed line */
      }
    }
  } catch {
    /* lexicon absent — roots simply carry no meanings */
  }
  lexiconCache = map;
  return map;
}

// ─── Corpus overview ─────────────────────────────────────────────────────────
export function morphologyTotals(): Record<string, number> | null {
  const db = openRo(MORPHOLOGY_DB);
  if (!db) return null;
  try {
    const one = (sql: string) => (db!.prepare(sql).get() as { n: number }).n;
    return {
      chapters: one("SELECT COUNT(DISTINCT chapter) AS n FROM segments"),
      verses: one(
        "SELECT COUNT(*) AS n FROM (SELECT DISTINCT chapter, verse FROM segments)",
      ),
      words: one("SELECT COUNT(*) AS n FROM words"),
      segments: one("SELECT COUNT(*) AS n FROM segments"),
      roots: one("SELECT COUNT(*) AS n FROM roots"),
      lemmas: one("SELECT COUNT(*) AS n FROM lemmas"),
    };
  } catch {
    return null;
  } finally {
    db.close();
  }
}

export function laneCoverage(): {
  corpus_roots: number;
  matched: number;
  unmatched: number;
  unmatched_roots: string[];
} | null {
  try {
    const report = JSON.parse(readFileSync(COVERAGE_JSON, "utf-8"));
    const lane = report?.sources?.lane;
    if (!lane) return null;
    return {
      corpus_roots: report.corpus_roots ?? 0,
      matched: lane.matched ?? 0,
      unmatched: lane.unmatched ?? 0,
      unmatched_roots: lane.unmatched_roots ?? [],
    };
  } catch {
    return null;
  }
}

// ─── Root listing + search ───────────────────────────────────────────────────
/**
 * Every root, most frequent first; `q` filters in either script. An Arabic
 * query matches by skeleton against roots AND lemmas (so رحمة finds ر-ح-م); a
 * Latin query matches in the fold space the pipeline searches in.
 */
export function listRoots(q?: string): RootListRow[] {
  const db = openRo(MORPHOLOGY_DB);
  if (!db) return [];
  try {
    const lex = lexicon();
    const rows = db
      .prepare(
        `SELECT r.root_bw, r.root_ar, r.root_skel, r.occurrence_count, r.lemma_count
           FROM roots r ORDER BY r.occurrence_count DESC, r.root_bw`,
      )
      .all() as Array<RootListRow & { root_skel: string }>;
    const withLane = (r: RootListRow & { root_skel: string }): RootListRow => ({
      root_bw: r.root_bw,
      root_ar: r.root_ar,
      occurrence_count: r.occurrence_count,
      lemma_count: r.lemma_count,
      has_lane: Boolean(lex.get(r.root_skel)?.lane_en),
    });
    const query = (q ?? "").trim();
    if (!query) return rows.map(withLane);

    const isArabic = /[؀-ۿ]/.test(query);
    const matchedRoots = new Set<string>();
    if (isArabic) {
      const skel = normalizeArabic(query);
      if (!skel) return [];
      for (const r of rows) {
        if (r.root_skel.includes(skel)) matchedRoots.add(r.root_bw);
      }
      const lemmaHits = db
        .prepare(
          `SELECT DISTINCT root_bw FROM lemmas WHERE lemma_skel LIKE ? AND root_bw IS NOT NULL`,
        )
        .all(`%${skel}%`) as Array<{ root_bw: string }>;
      for (const h of lemmaHits) matchedRoots.add(h.root_bw);
    } else {
      const fold = latinFold(query);
      if (!fold) return [];
      for (const r of rows) {
        if (foldsMatch(fold, arabicFold(r.root_skel)))
          matchedRoots.add(r.root_bw);
      }
      const lemmas = db
        .prepare(
          `SELECT lemma_skel, root_bw FROM lemmas WHERE root_bw IS NOT NULL`,
        )
        .all() as Array<{ lemma_skel: string; root_bw: string }>;
      for (const l of lemmas) {
        if (foldsMatch(fold, arabicFold(l.lemma_skel ?? "")))
          matchedRoots.add(l.root_bw);
      }
    }
    return rows.filter((r) => matchedRoots.has(r.root_bw)).map(withLane);
  } catch {
    return [];
  } finally {
    db.close();
  }
}

/**
 * The full root inventory for the client-side explorer, each row carrying its
 * pre-computed fold keys (the root's own + every derived lemma's), so the
 * island can search both scripts instantly with the shared fold functions and
 * no per-keystroke API call.
 */
export function rootsForExplorer(): Array<
  RootListRow & { root_skel: string; folds: string[] }
> {
  const db = openRo(MORPHOLOGY_DB);
  if (!db) return [];
  try {
    const lex = lexicon();
    const lemmaFolds = new Map<string, Set<string>>();
    for (const row of db
      .prepare(
        `SELECT root_bw, lemma_skel FROM lemmas WHERE root_bw IS NOT NULL`,
      )
      .all() as Array<{ root_bw: string; lemma_skel: string | null }>) {
      const fold = arabicFold(row.lemma_skel ?? "");
      if (!fold) continue;
      if (!lemmaFolds.has(row.root_bw)) lemmaFolds.set(row.root_bw, new Set());
      lemmaFolds.get(row.root_bw)!.add(fold);
    }
    const rows = db
      .prepare(
        `SELECT root_bw, root_ar, root_skel, occurrence_count, lemma_count
           FROM roots ORDER BY occurrence_count DESC, root_bw`,
      )
      .all() as Array<{
      root_bw: string;
      root_ar: string;
      root_skel: string;
      occurrence_count: number;
      lemma_count: number;
    }>;
    return rows.map((r) => ({
      root_bw: r.root_bw,
      root_ar: r.root_ar,
      root_skel: r.root_skel,
      occurrence_count: r.occurrence_count,
      lemma_count: r.lemma_count,
      has_lane: Boolean(lex.get(r.root_skel)?.lane_en),
      folds: [
        ...new Set([
          arabicFold(r.root_skel),
          ...(lemmaFolds.get(r.root_bw) ?? []),
        ]),
      ].filter(Boolean),
    }));
  } catch {
    return [];
  } finally {
    db.close();
  }
}

// ─── Root detail ─────────────────────────────────────────────────────────────
export function rootDetail(rootBw: string): RootRecord | null {
  const db = openRo(MORPHOLOGY_DB);
  if (!db) return null;
  try {
    return rootDetailWith(db, rootBw);
  } catch {
    return null;
  } finally {
    db.close();
  }
}

function rootDetailWith(
  db: Database.Database,
  rootBw: string,
): RootRecord | null {
  const head = db
    .prepare(
      `SELECT root_bw, root_ar, root_skel, occurrence_count, lemma_count FROM roots WHERE root_bw = ?`,
    )
    .get(rootBw) as
    | {
        root_bw: string;
        root_ar: string;
        root_skel: string;
        occurrence_count: number;
        lemma_count: number;
      }
    | undefined;
  if (!head) return null;
  const family = db
    .prepare(
      `SELECT lemma_bw, lemma_ar, pos, occurrence_count FROM lemmas
        WHERE root_bw = ? ORDER BY occurrence_count DESC, lemma_bw`,
    )
    .all(rootBw) as Array<Omit<FamilyLemma, "first_location">>;
  const locations = new Map(
    (
      db
        .prepare(
          `SELECT lemma_bw, chapter || ':' || verse || ':' || word AS loc,
                  MIN(chapter*1000000 + verse*1000 + word)
             FROM segments WHERE root_bw = ? AND lemma_bw IS NOT NULL GROUP BY lemma_bw`,
        )
        .all(rootBw) as Array<{ lemma_bw: string; loc: string }>
    ).map((r) => [r.lemma_bw, r.loc]),
  );
  const posRows = db
    .prepare(
      `SELECT pos, COUNT(*) AS n FROM segments
        WHERE root_bw = ? AND pos IS NOT NULL GROUP BY pos ORDER BY n DESC`,
    )
    .all(rootBw) as Array<{ pos: string; n: number }>;
  const lex = lexicon().get(head.root_skel) ?? {};
  const record: RootRecord = {
    root_bw: head.root_bw,
    root_ar: head.root_ar,
    root_dashed: [...head.root_skel].join("-"),
    occurrences: head.occurrence_count,
    lemma_count: head.lemma_count,
    family: family.map((f) => ({
      ...f,
      first_location: locations.get(f.lemma_bw) ?? "",
    })),
    pos_distribution: Object.fromEntries(posRows.map((p) => [p.pos, p.n])),
  };
  if (lex.lane_en) record.lane_en = lex.lane_en;
  if (lex.maqayis_ar) record.maqayis_ar = lex.maqayis_ar;
  if (lex.mufradat_ar) record.mufradat_ar = lex.mufradat_ar;
  return record;
}

// ─── Term resolution (the etymology-card seam) ───────────────────────────────
/**
 * Resolve one Arabic term (as it appears in a card row) to its root record —
 * or null when the corpus doesn't know it or the match is ambiguous across
 * roots. Same decline-to-judge contract as the Python _resolve_corpus_terms.
 */
export function resolveArabicTerm(arabicTerm: string): RootRecord | null {
  const skel = normalizeArabic(arabicTerm ?? "");
  if (skel.length < 2) return null;
  const db = openRo(MORPHOLOGY_DB);
  if (!db) return null;
  try {
    const hits = db
      .prepare(
        `SELECT DISTINCT root_bw FROM lemmas WHERE lemma_skel = ? AND root_bw IS NOT NULL`,
      )
      .all(skel) as Array<{ root_bw: string }>;
    let roots = hits.map((h) => h.root_bw);
    if (!roots.length) {
      // The term may BE a root's own skeleton (cards often name the bare root).
      const own = db
        .prepare(`SELECT root_bw FROM roots WHERE root_skel = ?`)
        .all(skel) as Array<{ root_bw: string }>;
      roots = own.map((r) => r.root_bw);
    }
    const unique = [...new Set(roots)];
    if (unique.length !== 1) return null; // unknown or ambiguous — decline
    return rootDetailWith(db, unique[0]);
  } catch {
    return null;
  } finally {
    db.close();
  }
}

/**
 * Per-item morphology for an etymology card's rows. Each row is a free string
 * ("رحمة (mercy): …"); the FIRST Arabic run names the term. Index-aligned with
 * the input; unresolvable rows get null and render exactly as before.
 */
export function morphologyForEtymology(items: string[]): (RootRecord | null)[] {
  return (items ?? []).map((item) => {
    const run = (item ?? "").match(/[؀-ۿ]{2,}/);
    return run ? resolveArabicTerm(run[0]) : null;
  });
}

/** Either-script resolution with the same decline-on-ambiguity contract:
 *  exactly one matching root or null. */
export function resolveTermAnyScript(term: string): RootRecord | null {
  const t = (term ?? "").trim();
  if (!t) return null;
  if (/[؀-ۿ]/.test(t)) return resolveArabicTerm(t);
  const matches = listRoots(t);
  return matches.length === 1 ? rootDetail(matches[0].root_bw) : null;
}

// ─── Generation-side helpers (ground before, veto after) ─────────────────────
const ARABIC_RUN_RE = /[؀-ۿ]{2,}/g;
/** A dashed Arabic root as personas write it: ب-ر-ه (2–4 letters). */
const DASHED_ROOT_RE = /[ء-ي]\s*(?:-\s*[ء-ي]\s*){1,3}/;

/**
 * CORPUS GROUND TRUTH block for a passage: every distinct Arabic run that
 * resolves to exactly one root, with its real family and Lane's meaning.
 * Empty string when nothing resolves — the prompt is then exactly as before.
 */
export function morphologyGroundingBlock(passage: string, cap = 6): string {
  const runs = [...new Set((passage ?? "").match(ARABIC_RUN_RE) ?? [])].slice(
    0,
    cap * 3,
  );
  const lines: string[] = [];
  for (const run of runs) {
    if (lines.length >= cap) break;
    const rec = resolveArabicTerm(run);
    if (!rec) continue;
    const fam = rec.family
      .slice(0, 4)
      .map(
        (l) =>
          `${l.lemma_ar} (${l.occurrence_count}x${l.first_location ? `, first at ${l.first_location}` : ""})`,
      )
      .join("; ");
    let line = `- ${run}: root ${rec.root_dashed} (${rec.root_ar}). Real derived words in the Quran: ${fam}.`;
    if (rec.lane_en) line += ` Lane's Lexicon: ${rec.lane_en}`;
    lines.push(line);
  }
  if (!lines.length) return "";
  return [
    "VERIFIED MORPHOLOGY (Quranic Arabic Corpus + Lane's Lexicon — AUTHORITATIVE).",
    "For the terms below the root is verified data, not your recall: use EXACTLY the",
    "given root, pick derivative examples from the listed real words, and base the",
    "core meaning on Lane where given. Never invent a root for any other term.",
    "",
    ...lines,
  ].join("\n");
}

/**
 * Conservative post-generation veto: drop an etymology item ONLY when its term
 * resolves to a unique corpus root AND the item names a dashed root that
 * contradicts it. Unknown terms and unparseable items always pass — this gate
 * can under-fire, never wrongly eat a correct entry.
 */
export function vetoEtymologyItems(items: string[]): {
  kept: string[];
  dropped: string[];
} {
  const kept: string[] = [];
  const dropped: string[] = [];
  for (const item of items ?? []) {
    const term = (item ?? "").match(/[؀-ۿ]{2,}/)?.[0];
    const claimed = (item ?? "").match(DASHED_ROOT_RE)?.[0];
    if (!term || !claimed) {
      kept.push(item);
      continue;
    }
    const rec = resolveArabicTerm(term);
    if (!rec) {
      kept.push(item);
      continue;
    }
    const claimedSkel = normalizeArabic(claimed.replace(/[-\s]/g, ""));
    const trueSkel = rec.root_dashed.replace(/-/g, "");
    if (claimedSkel && claimedSkel !== trueSkel) dropped.push(item);
    else kept.push(item);
  }
  return { kept, dropped };
}

// ─── Verse peek (mushaf mirror) ──────────────────────────────────────────────
export function verseText(
  chapter: number,
  verse: number,
): { arabic: string; english: string } | null {
  const db = openRo(MIRROR_DB);
  if (!db) return null;
  try {
    const row = db
      .prepare(
        `SELECT arabic, pickthall FROM fts_quran WHERE surah = ? AND ayat = ?`,
      )
      .get(chapter, verse) as { arabic: string; pickthall: string } | undefined;
    return row
      ? {
          arabic: row.arabic ?? "",
          // The mirror's translation column carries legacy presentational tags
          // (<I>…</I>, <B></B>) which rendered as literal text in the verse
          // peek (seen in visual QA). Strip markup only — the words all stay.
          english: (row.pickthall ?? "").replace(/<\/?[A-Za-z][^<>]*>/g, ""),
        }
      : null;
  } catch {
    return null;
  } finally {
    db.close();
  }
}
