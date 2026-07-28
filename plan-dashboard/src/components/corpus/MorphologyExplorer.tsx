/**
 * MorphologyExplorer.tsx — root-first explorer over the Quranic Arabic Corpus
 * morphology layer (/corpus/morphology).
 *
 * The page ships the full committed root inventory (1,642 rows with fold keys);
 * search runs entirely client-side in the shared fold space (src/lib/arabic-fold
 * — the pinned TS mirror of the pipeline's matching), so "rahma" and رحمة find
 * the same root the pipeline would resolve. Detail (derived family, POS spread,
 * Lane's meaning, verse peeks) is fetched per root from the read-only API.
 * No model anywhere on this page — every fact is committed reference data.
 */
import { useMemo, useState } from "react";

import {
  arabicFold,
  foldsMatch,
  latinFold,
  normalizeArabic,
} from "../../lib/arabic-fold";
import { apiFetch } from "../../lib/api-fetch";

export interface ExplorerRoot {
  root_bw: string;
  root_ar: string;
  root_skel: string;
  occurrence_count: number;
  lemma_count: number;
  has_lane: boolean;
  folds: string[];
}

interface FamilyLemma {
  lemma_bw: string;
  lemma_ar: string;
  pos: string | null;
  occurrence_count: number;
  first_location: string;
}

interface RootDetail {
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

interface VersePeek {
  ref: string;
  arabic: string;
  english: string;
}

interface Props {
  roots: ExplorerRoot[];
  unmatchedRoots: string[];
}

const PAGE = 60;

export default function MorphologyExplorer({ roots, unmatchedRoots }: Props) {
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState(PAGE);
  const [openRoot, setOpenRoot] = useState<string | null>(null);
  const [detail, setDetail] = useState<RootDetail | null>(null);
  const [detailError, setDetailError] = useState(false);
  const [verse, setVerse] = useState<VersePeek | null>(null);
  const [showUnmatched, setShowUnmatched] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim();
    if (!q) return roots;
    if (/[؀-ۿ]/.test(q)) {
      const skel = normalizeArabic(q);
      const qFold = arabicFold(skel);
      return roots.filter(
        (r) =>
          (skel && r.root_skel.includes(skel)) ||
          r.root_ar.includes(q) ||
          (qFold && r.folds.some((f) => f === qFold || f === qFold + "h")),
      );
    }
    const fold = latinFold(q);
    if (!fold) return roots;
    return roots.filter((r) => r.folds.some((f) => foldsMatch(fold, f)));
  }, [roots, query]);

  async function toggleRoot(rootBw: string) {
    setVerse(null);
    if (openRoot === rootBw) {
      setOpenRoot(null);
      setDetail(null);
      return;
    }
    setOpenRoot(rootBw);
    setDetail(null);
    setDetailError(false);
    try {
      const res = await apiFetch<RootDetail>(
        `/api/corpus/morphology?root=${encodeURIComponent(rootBw)}`,
      );
      setDetail(res);
    } catch {
      setDetailError(true);
    }
  }

  async function peekVerse(loc: string) {
    const [chapter, verseNo] = loc.split(":");
    const ref = `${chapter}:${verseNo}`;
    if (verse?.ref === ref) {
      setVerse(null);
      return;
    }
    try {
      setVerse(
        await apiFetch<VersePeek>(`/api/corpus/morphology?verse=${ref}`),
      );
    } catch {
      setVerse(null);
    }
  }

  return (
    <div className="mx">
      <div className="mx-search">
        <label className="mx-search-label" htmlFor="mx-q">
          Search roots
        </label>
        <input
          id="mx-q"
          type="search"
          className="mx-search-input"
          placeholder="Either script — rahma, tawakkul, رحم, سكينة …"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShown(PAGE);
          }}
        />
        <p className="mx-search-count" role="status">
          {filtered.length.toLocaleString()} of {roots.length.toLocaleString()}{" "}
          roots
        </p>
      </div>

      <ul className="mx-list">
        {filtered.slice(0, shown).map((r) => (
          <li
            key={r.root_bw}
            className="mx-root"
            data-open={openRoot === r.root_bw}
          >
            <button
              type="button"
              className="mx-root-head"
              aria-expanded={openRoot === r.root_bw}
              onClick={() => void toggleRoot(r.root_bw)}
            >
              <span className="mx-root-ar" lang="ar" dir="rtl">
                {r.root_ar}
              </span>
              <span className="mx-root-bw">{r.root_bw}</span>
              <span className="mx-root-meta">
                {r.occurrence_count.toLocaleString()}× · {r.lemma_count}{" "}
                {r.lemma_count === 1 ? "word" : "words"}
                {r.has_lane ? " · Lane" : ""}
              </span>
            </button>
            {openRoot === r.root_bw && (
              <div className="mx-detail">
                {detailError && (
                  <p className="mx-empty">Could not load this root.</p>
                )}
                {!detail && !detailError && (
                  <p className="mx-empty">Loading…</p>
                )}
                {detail && (
                  <>
                    <p className="mx-detail-root">
                      {/* <bdi> isolates the RTL root from the count that follows:
                          without it the bidi algorithm pulls "69" in front of the
                          Arabic and orphans the "×" (seen in visual QA). */}
                      Root <bdi>{detail.root_dashed}</bdi> —{" "}
                      {detail.occurrences.toLocaleString()}× in the Quran ·{" "}
                      {Object.entries(detail.pos_distribution)
                        .map(([pos, n]) => `${pos} ${n}`)
                        .join(" · ")}
                    </p>
                    <ul className="mx-family">
                      {detail.family.map((lem) => (
                        <li key={lem.lemma_bw} className="mx-lemma">
                          <span className="mx-lemma-ar" lang="ar" dir="rtl">
                            {lem.lemma_ar}
                          </span>
                          <span className="mx-lemma-meta">
                            {lem.lemma_bw}
                            {lem.pos ? ` · ${lem.pos}` : ""} ·{" "}
                            {lem.occurrence_count}×
                          </span>
                          {lem.first_location && (
                            <button
                              type="button"
                              className="mx-loc"
                              onClick={() => void peekVerse(lem.first_location)}
                            >
                              first at {lem.first_location}
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                    {verse && (
                      <blockquote className="mx-verse">
                        <p lang="ar" dir="rtl">
                          {verse.arabic}
                        </p>
                        <p>
                          {verse.english} <cite>Q {verse.ref}</cite>
                        </p>
                      </blockquote>
                    )}
                    {detail.lane_en && (
                      <p className="mx-lane">
                        <strong>Lane's Lexicon.</strong> {detail.lane_en}
                      </p>
                    )}
                    {detail.maqayis_ar && (
                      <p className="mx-lane" lang="ar" dir="rtl">
                        {detail.maqayis_ar}
                      </p>
                    )}
                    {detail.mufradat_ar && (
                      <p className="mx-lane" lang="ar" dir="rtl">
                        {detail.mufradat_ar}
                      </p>
                    )}
                    <p className="mx-src">
                      Quranic Arabic Corpus (Kais Dukes, GPL)
                      {detail.lane_en ? " · Lane's Lexicon" : ""}
                    </p>
                  </>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>

      {filtered.length > shown && (
        <button
          type="button"
          className="mx-more"
          onClick={() => setShown((n) => n + PAGE)}
        >
          Show {Math.min(PAGE, filtered.length - shown)} more
        </button>
      )}
      {!filtered.length && (
        <p className="mx-empty">
          No root matches. Try the bare consonants ("s-k-n"), a derived word
          ("sakina"), or Arabic script.
        </p>
      )}

      <section className="mx-coverage">
        <h2>Meaning coverage</h2>
        <p>
          {(roots.length - unmatchedRoots.length).toLocaleString()} of{" "}
          {roots.length.toLocaleString()} roots carry Lane's classical meaning.{" "}
          {unmatchedRoots.length > 0 && (
            <button
              type="button"
              className="mx-unmatched-toggle"
              aria-expanded={showUnmatched}
              onClick={() => setShowUnmatched((v) => !v)}
            >
              {showUnmatched ? "Hide" : "Show"} the {unmatchedRoots.length}{" "}
              without
            </button>
          )}
        </p>
        {showUnmatched && (
          <p className="mx-unmatched" lang="ar" dir="rtl">
            {unmatchedRoots.join(" · ")}
          </p>
        )}
      </section>
    </div>
  );
}
