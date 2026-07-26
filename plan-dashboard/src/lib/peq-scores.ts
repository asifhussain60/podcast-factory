/**
 * peq-scores.ts — TypeScript port of the PEQ (Podcast Episode Quality) scorer.
 *
 * Mirrors the logic in scripts/podcast/_quality.py (the canonical formula —
 * challenger_scoring.py imports from there). Pure maths + regex — no API
 * calls, no external dependencies. Keep in sync with _quality.py in the same
 * commit whenever either side changes (repo mirror contract).
 *
 * FORMULA (K6 — 5-axis):
 *   PEQ = 0.30×Fidelity + 0.20×Voice + 0.18×Structure
 *         + 0.17×Enrichment + 0.15×Interest
 * When the Voice axis is unavailable its weight redistributes to Fidelity.
 * PASS ≥ 85 · WARN 70–84 · FAIL < 70
 */
import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const THRESHOLD_PASS = 85;
export const THRESHOLD_WARN = 70;

// Weights — mirror _quality.py (K6 5-axis; WEIGHT_INTEREST = R_INTEREST_WEIGHT).
const WEIGHT_FIDELITY = 0.3;
const WEIGHT_VOICE = 0.2;
const WEIGHT_STRUCTURE = 0.18;
const WEIGHT_ENRICHMENT = 0.17;
const WEIGHT_INTEREST = 0.15;

// Mirror of _quality.py `_VOICE_SCORER_READY`. The Python voice scorer is
// gated off until the K2+ shared TF-IDF vocabulary exists; while it is off,
// voice scores 0 and its weight redistributes to Fidelity. Flip this only
// when the Python flag flips, or the dashboard will show bigram-ratio noise
// the pipeline never awarded.
const VOICE_SCORER_READY = false;

// Interest-axis patterns — mirror R_INTEREST_* in scripts/podcast/_rules.py.
//
// WORD BOUNDARIES. Python's `\b` is Unicode-aware and JavaScript's is ASCII-only,
// so `دobjectionد` matched here and NOT in _quality.py — the same dialect split that
// silently orphaned Composer edits through anchorKey until 2026-07-20, in an
// Arabic-source project where Arabic-adjacent English is exactly the text at risk.
// Every `\b` that _rules.py actually uses is therefore spelled out as an explicit
// Unicode-aware lookaround
// (`WB` / `WE`, requiring the `u` flag) so the two engines agree by
// construction rather than by coincidence. Python is canonical: it gates real
// bundles, this file only displays. Measured across all 58 chapter sources on
// 2026-07-26: zero Arabic-adjacent trigger hits, so no shipped score moves.
// Pinned by scripts/lib/peq-scores.fixtures.json.
const WB = String.raw`(?<![\p{L}\p{N}_])`;
const WE = String.raw`(?![\p{L}\p{N}_])`;
/** Build a Unicode-aware, case-insensitive interest pattern from a `\b`-style body. */
const ip = (body: string): RegExp => new RegExp(`${WB}(?:${body})${WE}`, "iu");
// Deliberately UNANCHORED — 0 of 8 hook patterns in _rules.py use `\b`, and adding
// boundaries here would silently narrow the axis on the display side only.
const INTEREST_HOOK_PATTERNS = [
  /what (does|would|if|happens|kind of|makes|drives|compels)/i,
  /why (does|would|did|should|is|are|do|must)/i,
  /how (does|can|should|is|are|do|did)/i,
  /imagine (if|a world|that|for a moment)/i,
  /consider (this|the|what|a|that)/i,
  /the question (is|was|becomes|facing|at the heart)/i,
  /here'?s (the|a|what|why|how|something)/i,
  /(let'?s|let us) (begin|start|open|ask|explore|consider)/i,
];
const INTEREST_CHALLENGE_RAISE_PATTERNS = [
  ip(
    String.raw`(objection|challenge|difficulty|problem|paradox|tension|puzzle|obstacle)`,
  ),
  ip(String.raw`(one might (argue|say|object|think|wonder))`),
  ip(String.raw`(it (might|may|could) seem)`),
  ip(String.raw`(but (how|why|what|is this|does this|can))`),
];
const INTEREST_CHALLENGE_RESOLVE_PATTERNS = [
  ip(String.raw`(the answer (is|lies|comes|emerges))`),
  ip(String.raw`(in fact|actually|rather|instead|on the contrary)`),
  ip(
    String.raw`(resolves?|dissolves?|overcomes?|addresses?|answers? (this|that|the))`,
  ),
];
const INTEREST_RELEVANCE_PATTERNS = [
  ip(String.raw`(today|modern|contemporary|our (time|age|era|world|lives?))`),
  ip(String.raw`(we (find|see|live|face|encounter|grapple))`),
  ip(String.raw`(still (holds?|rings? true|matters?|applies?|speaks?))`),
  ip(String.raw`(resonates?|relevant|speaks? to|timeless)`),
  ip(
    String.raw`(in (our|this|any|every) (age|era|time|generation|society|context))`,
  ),
];
const INTEREST_STRAWMAN_DENY = [
  ip(String.raw`obviously (wrong|false|absurd|incorrect|mistaken)`),
  ip(String.raw`clearly (wrong|mistaken|misguided)`),
  ip(String.raw`absurdly`),
  ip(String.raw`(silly (argument|idea|notion|objection))`),
  ip(String.raw`(no (sane|reasonable|serious) person)`),
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PEQAxes {
  fidelity: number; // 0–100
  voice: number; // 0–100 (0 while the voice scorer is gated off)
  structure: number; // 0–100
  enrichment: number; // 0–100
  interest: number; // 0–100 (K6)
  total: number; // 0–100
  verdict: "PASS" | "WARN" | "FAIL";
}

export interface ChapterScore {
  slug: string;
  title: string;
  scores: PEQAxes;
}

export interface BookScore {
  slug: string;
  archetype: string | null;
  avg: number;
  passCount: number;
  warnCount: number;
  failCount: number;
  chapters: ChapterScore[];
}

// ---------------------------------------------------------------------------
// Axis helpers — mirrors Python implementations
// ---------------------------------------------------------------------------

function quranRefs(text: string): number {
  return (text.match(/\bQ?\d+:\d+\b/g) ?? []).length;
}

function domainTerms(text: string): { total: number; glossed: number } {
  const italics = new Set(
    (text.match(/\*([^*]+)\*/g) ?? []).map((s) => s.slice(1, -1)),
  );

  const STOP = new Set([
    "that",
    "this",
    "with",
    "from",
    "into",
    "also",
    "such",
    "when",
    "then",
    "than",
    "what",
    "which",
    "some",
    "have",
    "been",
    "were",
    "they",
    "their",
    "there",
    "here",
    "each",
    "both",
  ]);
  const bareGlosses = new Set<string>();
  for (const m of text.matchAll(
    /\b([A-Za-z\u0101\u012b\u016b\u1e0d\u1e6d\u1e93\u1e25\u1e63\u02bf\u02be]{4,})\s*\([^)]{5,80}\)/g,
  )) {
    if (!STOP.has(m[1].toLowerCase())) bareGlosses.add(m[1]);
  }

  const total =
    italics.size + [...bareGlosses].filter((t) => !italics.has(t)).length;
  const glossedItalic = (text.match(/\*[^*]+\*\s*\([^)]+\)/g) ?? []).length;
  const glossed = glossedItalic + bareGlosses.size;
  return { total, glossed: Math.min(glossed, total) };
}

function arcLabels(text: string): string[] {
  const labels: string[] = [];

  if (
    /let us begin|opening|before we dive|where this chapter picks up|this chapter covers|the argument of this chapter|picks up|chapter picks up|where we left|where the chapter|##\s*(where|opening|introduction|context|background)|established the doctrine|settled the architecture/i.test(
      text,
    )
  ) {
    labels.push("open_hook");
  }
  if (
    /\bfirst\b|\bsecond\b|\bthird\b|point one|point two|##\s*movement\s+\d|##\s*section\s+\d|##\s*part\s+\d|\bmovement \d|\bphase \d|\bstep \d|\bone[,:]|\btwo[,:]|\bthree[,:]|the first|the second|the third/i.test(
      text,
    )
  ) {
    labels.push("three_points");
  }
  if (
    /in closing|to close|so as we end|let that sit|what comes next|where this chapter ends|this is where.*ends|the next (chapter|sub-chapter|section)|we ask god|ask god to|may god|all[aā]h|inshallah|##\s*(what comes next|closing|conclusion|summary|end)|leaves the reader|has earned/i.test(
      text,
    )
  ) {
    labels.push("close");
  }
  return labels;
}

/**
 * Round half-to-EVEN, matching Python's built-in `round()`.
 *
 * `Math.round` rounds half UP, Python rounds half to even, so the two disagree on
 * exact ties: 82.25 became 82.3 here and 82.2 in _quality.py. Enumerating every
 * value from 0 to 100 at 3-decimal granularity, 500 of 100,001 diverge.
 *
 * Honest scope, because the obvious claim is wrong: NONE of those 500 can flip a
 * PASS/WARN/FAIL verdict. A flip would need 84.95 or 69.95, and at both the nearest
 * double sits ABOVE the tie, so half-to-even never engages and the two agree. What
 * diverged was the displayed score against the gated score, by 0.1 — never the
 * verdict. Fixed anyway: one rounding rule is cheaper to reason about than two, and
 * the axis sub-scores feed the total.
 *
 * Python is canonical: it gates real bundles (assemble_bundle, challenger_scoring),
 * this file only displays.
 *
 * IMPLEMENTATION NOTE, learned the hard way. "Scale by 10^digits, then round half to
 * even" does NOT reproduce Python. Python rounds the EXACT decimal value of the
 * double, and multiplying reintroduces error: 77.35 * 10 is 773.5000000000001 in
 * binary, which reads as above-the-tie and rounds up to 77.4, while Python sees the
 * double's true value (77.34999999999999431...) and gives 77.3. Only exact ties like
 * 82.25 (a binary fraction) are genuine ties where half-to-even actually decides.
 *
 * So: expand to a decimal string with `toFixed`, which is specified to use the
 * double's exact value, then round that string. Half-to-even applies only when every
 * remaining digit is zero — a true tie.
 *
 * Pinned by peq-scores.fixtures.json.
 */
export function roundHalfEven(value: number, digits: number): number {
  if (!Number.isFinite(value)) return value;
  const negative = value < 0;
  // 20 fractional digits is enough to distinguish a true tie from binary noise for
  // any double in this scorer's 0–100 range.
  const expanded = Math.abs(value).toFixed(20);
  const dot = expanded.indexOf(".");
  const allDigits = expanded.slice(0, dot) + expanded.slice(dot + 1);
  const keep = dot + digits; // count of digits to retain
  const head = allDigits.slice(0, keep);
  const tail = allDigits.slice(keep);

  let roundUp = false;
  if (tail.length > 0) {
    const first = tail[0];
    if (first > "5") roundUp = true;
    else if (first === "5") {
      const restNonZero = /[1-9]/.test(tail.slice(1));
      // A true tie only when nothing follows the 5; then break to even.
      roundUp = restNonZero || Number(head[head.length - 1]) % 2 === 1;
    }
  }

  const rounded = BigInt(head || "0") + (roundUp ? 1n : 0n);
  const result = Number(rounded) / 10 ** digits;
  return negative ? -result : result;
}

function fidelityScore(sourceIds: string[], foundIds: string[]): number {
  // Mirror _quality._fidelity_score: no source citations → no target → full credit.
  if (sourceIds.length === 0) return 100;
  const s = new Set(sourceIds);
  const f = new Set(foundIds);
  const intersection = [...s].filter((x) => f.has(x)).length;
  const union = new Set([...s, ...f]).size;
  return union === 0 ? 100 : roundHalfEven((intersection / union) * 100, 2);
}

function voiceScore(_text: string, exemplarVector: number[] | null): number {
  // Mirror _quality._voice_score: gated off until the K2+ shared TF-IDF
  // vocabulary is built. While VOICE_SCORER_READY is false this returns 0 and
  // peqTotal() redistributes the Voice weight to Fidelity — same as Python.
  if (!exemplarVector || exemplarVector.length === 0 || !VOICE_SCORER_READY)
    return 0;
  return 0; // K2+: cosine similarity in the shared vocabulary basis (not yet built).
}

function structureScore(arcRules: string[], found: string[]): number {
  if (arcRules.length === 0) return 100;
  const foundSet = new Set(found);
  const hits = arcRules.filter((r) => foundSet.has(r)).length;
  return roundHalfEven((hits / arcRules.length) * 100, 2);
}

function enrichmentScore(
  termCount: number,
  glossedCount: number,
  qrefs: number,
  wordCount: number,
): number {
  if (wordCount === 0) return 0;
  const glossingRatio = glossedCount / Math.max(termCount, 1);
  const quranDensity = Math.min(qrefs / Math.max(wordCount / 100, 1), 1.0);
  return roundHalfEven((0.7 * glossingRatio + 0.3 * quranDensity) * 100, 2);
}

function interestScore(text: string): number {
  // Mirror _quality._interest_score (K6): four sub-signals averaged, ×100.
  if (!text.trim()) return 0;

  const words = text.split(/\s+/).filter(Boolean);
  const first20 = words
    .slice(0, Math.max(Math.floor(words.length * 0.2), 50))
    .join(" ");

  const hook = INTEREST_HOOK_PATTERNS.some((p) => p.test(first20)) ? 1.0 : 0.0;

  const raised = INTEREST_CHALLENGE_RAISE_PATTERNS.some((p) => p.test(text));
  const resolved = INTEREST_CHALLENGE_RESOLVE_PATTERNS.some((p) =>
    p.test(text),
  );
  const challenge = raised && resolved ? 1.0 : raised ? 0.5 : 0.0;

  const relevance = INTEREST_RELEVANCE_PATTERNS.some((p) => p.test(text))
    ? 1.0
    : 0.0;

  const fairness = INTEREST_STRAWMAN_DENY.some((p) => p.test(text)) ? 0.0 : 1.0;

  return roundHalfEven(
    ((hook + challenge + relevance + fairness) / 4.0) * 100,
    2,
  );
}

function peqTotal(
  fidelity: number,
  voice: number,
  structure: number,
  enrichment: number,
  interest: number,
  voiceAvailable: boolean,
): number {
  // Mirror _quality.score(): Voice weight redistributes to Fidelity when the
  // voice axis is unavailable; total clamps to 0–100 and rounds to 1 dp.
  const total = voiceAvailable
    ? WEIGHT_FIDELITY * fidelity +
      WEIGHT_VOICE * voice +
      WEIGHT_STRUCTURE * structure +
      WEIGHT_ENRICHMENT * enrichment +
      WEIGHT_INTEREST * interest
    : (WEIGHT_FIDELITY + WEIGHT_VOICE) * fidelity +
      WEIGHT_STRUCTURE * structure +
      WEIGHT_ENRICHMENT * enrichment +
      WEIGHT_INTEREST * interest;
  return roundHalfEven(Math.min(Math.max(total, 0), 100), 1);
}

function verdict(total: number): "PASS" | "WARN" | "FAIL" {
  return total >= THRESHOLD_PASS
    ? "PASS"
    : total >= THRESHOLD_WARN
      ? "WARN"
      : "FAIL";
}

// ---------------------------------------------------------------------------
// Exemplar vector loader
// ---------------------------------------------------------------------------

const _vectorCache = new Map<string, number[] | null>();

async function loadExemplarVector(
  archetypeSlug: string | null,
): Promise<number[] | null> {
  if (!archetypeSlug) return null;
  if (_vectorCache.has(archetypeSlug)) return _vectorCache.get(archetypeSlug)!;

  // Try both CONTENT/ and content/ case variants (Mac filesystem quirk)
  const candidates = [
    join(
      process.cwd(),
      "..",
      "CONTENT",
      "_shared",
      "archetypes",
      archetypeSlug,
      "exemplar_vector.json",
    ),
    join(
      process.cwd(),
      "..",
      "content",
      "_shared",
      "archetypes",
      archetypeSlug,
      "exemplar_vector.json",
    ),
    join(
      process.cwd(),
      "CONTENT",
      "_shared",
      "archetypes",
      archetypeSlug,
      "exemplar_vector.json",
    ),
    join(
      process.cwd(),
      "content",
      "_shared",
      "archetypes",
      archetypeSlug,
      "exemplar_vector.json",
    ),
  ];
  for (const p of candidates) {
    try {
      const vec = JSON.parse(await readFile(p, "utf-8")) as number[];
      _vectorCache.set(archetypeSlug, vec);
      return vec;
    } catch {
      /* try next */
    }
  }
  _vectorCache.set(archetypeSlug, null);
  return null;
}

// ---------------------------------------------------------------------------
// Per-chapter scorer
// ---------------------------------------------------------------------------

export async function scoreChapter(
  chapterText: string,
  archetypeSlug: string | null,
): Promise<PEQAxes> {
  const exemplar = await loadExemplarVector(archetypeSlug);

  const words = chapterText.split(/\s+/).filter(Boolean).length;
  const qrefs = quranRefs(chapterText);
  const { total: termCount, glossed: glossedCount } = domainTerms(chapterText);
  const arc = arcLabels(chapterText);
  const citationsFound =
    chapterText.match(/(?:quran|hadith|doctrine):\S+/g) ?? [];

  const voiceAvailable = exemplar !== null && VOICE_SCORER_READY;
  const fid = fidelityScore([], citationsFound);
  const voi = voiceScore(chapterText, exemplar);
  const str = structureScore(["open_hook", "three_points", "close"], arc);
  const enr = enrichmentScore(termCount, glossedCount, qrefs, words);
  const int = interestScore(chapterText);
  const tot = peqTotal(fid, voi, str, enr, int, voiceAvailable);

  return {
    fidelity: fid,
    voice: voi,
    structure: str,
    enrichment: enr,
    interest: int,
    total: tot,
    verdict: verdict(tot),
  };
}

// ---------------------------------------------------------------------------
// Whole-book scorer
// ---------------------------------------------------------------------------

const ARC_RULES = ["open_hook", "three_points", "close"];

export async function scoreBook(
  bookDir: string,
  archetypeSlug: string | null,
): Promise<BookScore | null> {
  const chaptersDir = join(bookDir, "chapters");
  let entries: string[];
  try {
    entries = await readdir(chaptersDir);
  } catch {
    return null;
  }

  const txtFiles = entries
    .filter(
      (n) =>
        (n.endsWith(".txt") || n.endsWith(".md")) &&
        !n.startsWith("_") &&
        !n.startsWith("."),
    )
    .sort();

  if (txtFiles.length === 0) return null;

  const exemplar = await loadExemplarVector(archetypeSlug);
  const chapters: ChapterScore[] = [];

  for (const fname of txtFiles) {
    const slug = fname.replace(/\.(txt|md)$/i, "");
    let text = "";
    try {
      text = await readFile(join(chaptersDir, fname), "utf-8");
    } catch {
      continue;
    }

    const title = (() => {
      const m = text.match(/^#\s+(.+)$/m);
      return m
        ? m[1].trim()
        : slug
            .replace(/^ch\d+-/i, "")
            .replace(/-/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase());
    })();

    const words = text.split(/\s+/).filter(Boolean).length;
    const qrefs = quranRefs(text);
    const { total: termCount, glossed: glossedCount } = domainTerms(text);
    const arc = arcLabels(text);
    const citationsFound = text.match(/(?:quran|hadith|doctrine):\S+/g) ?? [];

    const voiceAvailable = exemplar !== null && VOICE_SCORER_READY;
    const fid = fidelityScore([], citationsFound);
    const voi = voiceScore(text, exemplar);
    const str = structureScore(ARC_RULES, arc);
    const enr = enrichmentScore(termCount, glossedCount, qrefs, words);
    const int = interestScore(text);
    const tot = peqTotal(fid, voi, str, enr, int, voiceAvailable);

    chapters.push({
      slug,
      title,
      scores: {
        fidelity: fid,
        voice: voi,
        structure: str,
        enrichment: enr,
        interest: int,
        total: tot,
        verdict: verdict(tot),
      },
    });
  }

  const totals = chapters.map((c) => c.scores.total);
  // No Python peer — the book average is a display-only aggregation. Rounded the
  // same way as everything else here so the file has one rounding rule, not two.
  const avg =
    totals.length > 0
      ? roundHalfEven(totals.reduce((a, b) => a + b, 0) / totals.length, 1)
      : 0;

  return {
    slug: bookDir.split("/").pop() ?? "",
    archetype: archetypeSlug,
    avg,
    passCount: totals.filter((t) => t >= THRESHOLD_PASS).length,
    warnCount: totals.filter((t) => t >= THRESHOLD_WARN && t < THRESHOLD_PASS)
      .length,
    failCount: totals.filter((t) => t < THRESHOLD_WARN).length,
    chapters,
  };
}

// ---------------------------------------------------------------------------
// Human-friendly helpers
// ---------------------------------------------------------------------------

export function verdictLabel(v: "PASS" | "WARN" | "FAIL" | string): string {
  if (v === "PASS") return "Excellent";
  if (v === "WARN") return "Good";
  return "Needs work";
}

export function verdictColor(v: "PASS" | "WARN" | "FAIL" | string): string {
  if (v === "PASS") return "#22c55e"; // green
  if (v === "WARN") return "#f59e0b"; // amber
  return "#ef4444"; // red
}

export function scoreGrade(total: number): string {
  if (total >= 90) return "A";
  if (total >= 85) return "B";
  if (total >= 80) return "C";
  if (total >= 70) return "D";
  return "F";
}

/**
 * Internals exposed for the mirror test ONLY.
 *
 * scripts/lib/peq-scores.test.mjs pins these against the same fixture file that
 * tests/test_peq_mirror.py reads, so the two implementations cannot drift. They are
 * grouped behind one clearly-named export rather than promoted to public API,
 * because nothing in the site should call them directly — the site consumes
 * scoreBook / scoreChapter.
 */
export const __testHooks = {
  weights: {
    fidelity: WEIGHT_FIDELITY,
    voice: WEIGHT_VOICE,
    structure: WEIGHT_STRUCTURE,
    enrichment: WEIGHT_ENRICHMENT,
    interest: WEIGHT_INTEREST,
  },
  voiceScorerReady: VOICE_SCORER_READY,
  patternGroups: {
    hook: INTEREST_HOOK_PATTERNS,
    challenge_raise: INTEREST_CHALLENGE_RAISE_PATTERNS,
    challenge_resolve: INTEREST_CHALLENGE_RESOLVE_PATTERNS,
    relevance: INTEREST_RELEVANCE_PATTERNS,
    strawman_deny: INTEREST_STRAWMAN_DENY,
  },
  interestScore,
  aggregate(
    axes: {
      fidelity: number;
      voice: number;
      structure: number;
      enrichment: number;
      interest: number;
    },
    voiceAvailable: boolean,
  ): { total: number; verdict: "PASS" | "WARN" | "FAIL" } {
    const total = peqTotal(
      axes.fidelity,
      axes.voice,
      axes.structure,
      axes.enrichment,
      axes.interest,
      voiceAvailable,
    );
    return { total, verdict: verdict(total) };
  },
};
