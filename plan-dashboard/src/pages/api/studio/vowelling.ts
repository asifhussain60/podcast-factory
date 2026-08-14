/**
 * vowelling.ts — propose, review and apply Arabic diacritics.
 *
 *   GET  /api/studio/vowelling?slug=X         → { proposals, candidates }
 *   POST /api/studio/vowelling {slug, action} where action is:
 *          "run"     — vowel ONE passage handed in as {text} and return it; the
 *                      Composer's Diacritics button. No sidecar, no review queue
 *                      (see vowelOneRun for why the review step is gone)
 *          "propose" — ask Gemini to vowel every bare non-Qur'anic run, keep only
 *                      what passes the skeleton gate, write the proposals sidecar
 *          "decide"  — {id, status, resolved?, note?} accept / reject one proposal
 *          "apply"   — write every accepted proposal into book.md, via the
 *                      Composer's own chapter writer
 *
 * WHY THIS SHAPE. Vowelling this book's Arabic cannot be a recovery job: the
 * printed source is a bare critical edition (verified against the page images), so
 * the marks are not there to be found. They can only be supplied.
 *
 * THE POLICY REVERSED ON 2026-07-29 (Asif). This route was built around
 * propose → human accepts → apply, on the argument that a wrong vowel flips an
 * Arabic verb from active to passive in a book that is largely reported speech.
 * Asif's direction is that diacritics are ALWAYS applied: he does not read Arabic,
 * and an unvowelled run is not "unverified" to him, it is unreadable. A gate whose
 * effect is to keep marks off the page is a gate that makes the book worse for the
 * person it is for. The batch propose/decide/apply flow below is kept — it is still
 * the way to vowel a whole book in reviewable steps — but acceptance is no longer
 * the price of a vowel mark, and the Composer's Diacritics button applies on click.
 *
 * TWO INVARIANTS, both enforced here rather than trusted:
 *   1. A proposal may differ from its source in MARKS ONLY. `rejectionReason` in
 *      scripts/lib/vowelling.mjs is the gate, and it runs on the way IN from the
 *      model and again on the way in from a human edit. A model that reaches for
 *      the mushaf's Uthmani spelling, drops a clause or "corrects" a word is
 *      refused and never reaches a reviewer.
 *   2. Qur'anic runs are never proposed for. They are already vowelled from the
 *      canonical mushaf, which is real provenance; re-vowelling them could only
 *      make them worse.
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { writeChapterBody } from "../../../lib/reader/book-md-write";
import {
  generate,
  generateWithGrounding,
  rateLimitCheck,
} from "../../../lib/reader/gemini-server";
import {
  needsSearchFallback,
  cleanModelReply,
  NEEDS_SEARCH_TOKEN,
} from "../../../lib/reader/vowel-fix";
import { anchorKey } from "../../../../scripts/lib/anchor-key.mjs";
import { readQuranicRuns } from "../../../../scripts/lib/book-html.mjs";
import {
  loadProposals,
  saveProposals,
  rejectionReason,
  transferMarks,
  isVowellingCandidate,
  markCount,
  skeleton,
} from "../../../../scripts/lib/vowelling.mjs";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const MODEL = "pro"; // vocalisation is a reasoning task, not a lookup
const ARABIC_LINE_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;

/** Stable id for a run, so re-proposing updates rather than duplicates. */
const runId = (chapterKey: string, source: string): string =>
  `${chapterKey}:${createHash("sha256").update(skeleton(source), "utf8").digest("hex").slice(0, 10)}`;

interface Candidate {
  chapterKey: string;
  chapterTitle: string;
  source: string;
}

/**
 * Every bare, non-Qur'anic Arabic run in the book, with the chapter it belongs to.
 *
 * Runs are read as whole LINES of a blockquote, which is the unit book.md stores an
 * Arabic passage in and therefore the unit a replacement can target unambiguously.
 * Anything already vowelled, too short, or resolved against the mushaf is skipped.
 */
function collectCandidates(bookDir: string): Candidate[] {
  const bookMd = join(bookDir, "book", "book.md");
  if (!existsSync(bookMd)) return [];
  const quranic = readQuranicRuns(bookDir) as Set<string>;
  const out: Candidate[] = [];
  const seen = new Set<string>();
  let chapterKey = "";
  let chapterTitle = "";
  for (const raw of readFileSync(bookMd, "utf-8").split("\n")) {
    if (/^##\s+/.test(raw)) {
      chapterKey = anchorKey(raw);
      chapterTitle = raw
        .replace(/^##\s+/, "")
        .replace(/^\d+\.\s*/, "")
        .trim();
      continue;
    }
    if (!ARABIC_LINE_RE.test(raw)) continue;
    const text = raw.replace(/^>\s?/, "").trim();
    if (!text || quranic.has(text)) continue;
    // A DISPLAY run, not a prose line that happens to carry an inline term. The
    // first cut matched any line containing Arabic and duly offered to rewrite
    // "The narrator said: Then the Master set a…" — an English sentence with one
    // Arabic word in it. Replacing a whole prose line is precisely the edit this
    // route must never make, so the line has to be Arabic with at most incidental
    // Latin (a stray reference marker), not the other way round.
    const latin = (text.match(/[A-Za-z]/g) || []).length;
    const arabic = (text.match(/[\u0600-\u06FF]/g) || []).length;
    if (latin > 2 || arabic < latin * 4) continue;
    if (!isVowellingCandidate(text)) continue;
    const id = runId(chapterKey, text);
    if (seen.has(id)) continue; // the same run twice in a chapter is one decision
    seen.add(id);
    out.push({ chapterKey, chapterTitle, source: text });
  }
  return out;
}

const SYSTEM = `You add Arabic vowel marks (tashkeel) and nothing else.

You will be given one Arabic passage from a classical Ismaili teaching text. Return
the SAME passage with full tashkeel applied.

ABSOLUTE CONSTRAINTS — a response that breaks any of these is discarded:
- Do not add, remove, reorder or change ANY letter. The consonantal skeleton of your
  answer must be byte-identical to the input. This is checked mechanically.
- Do not "correct" spelling, do not substitute Uthmani Qur'anic orthography, do not
  normalise hamza forms, do not change punctuation or word order.
- Write the definite article with a PLAIN alif (\u0627). Never use alif wasla
  (\u0671) - it is a different character, so "\u0671\u0644\u0625\u0631\u0627\u062f\u0629" for "\u0627\u0644\u0625\u0631\u0627\u062f\u0629" is a letter change and the whole
  answer is discarded, however correct the vowelling around it.
- Do not translate, explain, or add commentary. Return only the vowelled Arabic.
- Where the vocalisation is genuinely ambiguous, choose the reading that the
  surrounding sense supports and still return only the passage.

Return the vowelled Arabic on a single line, with no quotes and no preamble.`;

/**
 * The Composer button's OWN system prompt (2026-08-14) — deliberately NOT the
 * marks-only SYSTEM above, which the batch propose/decide/apply path below
 * still uses unchanged. See vowel-fix.ts's header for the full history of why
 * this one call site is allowed to touch letters and that one is not.
 */
const FIX_AND_VOWEL_SYSTEM = `You are given one Arabic passage from a classical Ismaili teaching text, as it
currently appears in a manuscript being prepared for publication. It may already be
correct, or it may carry a small transcription error from scanning or typing — a
misplaced or doubled letter, a dropped word, a wrong hamza form.

Your task, in order:
1. If the passage has a clear transcription error, correct it — changing as little
   as possible. Preserve the wording and meaning exactly; fix only what is plainly
   wrong. If the passage is already correct, change nothing but its marks.
2. Apply full tashkeel (vowel marks) to the corrected passage.

If you do not recognise this passage and are not confident of its accurate wording —
for example because it is a specific hadith, Qur'anic verse, or named scholarly
quotation you cannot verify from what you know — respond with EXACTLY the single
line ${NEEDS_SEARCH_TOKEN} and nothing else. Do not guess at an unfamiliar quotation.

Do not translate, explain, or add commentary. Return only the corrected, vowelled
Arabic passage on a single line (or exactly ${NEEDS_SEARCH_TOKEN}).`;

/** The grounded (Google Search) fallback prompt, used only when the primary
 *  call above returned NEEDS_SEARCH or something unusable. Asked to "search,
 *  then determine intelligently" rather than ever refuse outright — Asif's
 *  own instruction was that this path must always return its best answer,
 *  never come back empty. */
function groundedFixPrompt(source: string): string {
  return `Search for the accurate, correctly-written form of this Arabic passage from a classical Islamic or Ismaili teaching text. It may be a hadith, a Qur'anic verse, or a named scholarly quotation, and the version below may carry a small transcription error from scanning:

"${source}"

If you find an authoritative published source for this exact passage, return it corrected to match that source and fully vowelled with tashkeel, on a single line, nothing else. If you cannot find an exact published match, use your own best understanding of classical Arabic to determine the most likely correct and fully vowelled form of THIS passage as given, and return that instead — always return one best answer, never leave it blank and never refuse.`;
}

export const GET: APIRoute = async ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  try {
    const proposals = loadProposals(bookDir);
    const candidates = collectCandidates(bookDir);
    const proposed = new Set(proposals.map((p: { id: string }) => p.id));
    return apiOk({
      slug,
      proposals,
      // What a "propose" run would newly cover — so the UI can say "12 passages
      // have no proposal yet" instead of making the reviewer infer it.
      unproposed: candidates.filter(
        (c) => !proposed.has(runId(c.chapterKey, c.source)),
      ).length,
      candidates: candidates.length,
    });
  } catch (e) {
    return apiServerError(`Failed to read vowelling state: ${String(e)}`);
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }
  const slug = String(body.slug ?? "").trim();
  const action = String(body.action ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  try {
    if (action === "run") return await vowelOneRun(body);
    if (action === "propose") return await propose(slug, bookDir, body);
    if (action === "decide") return decide(slug, bookDir, body);
    if (action === "apply") return apply(slug, bookDir);
    return apiError(`Unknown action: ${action || "(none)"}`);
  } catch (e) {
    return apiServerError(`Vowelling ${action} failed: ${String(e)}`);
  }
};

/**
 * Fix and vowel ONE run, handed in by the Composer's Diacritics button — no
 * sidecar, no proposal record, no review queue.
 *
 * WHY THIS EXISTS ALONGSIDE `propose` (Asif, 2026-07-29). The batch path above was
 * built around a rule that has since been reversed: it treated a supplied vowel as
 * something a human must ratify one passage at a time. Asif does not read Arabic
 * unvowelled — for him a bare run is unreadable, so withholding marks pending
 * review is not caution, it is the panel refusing to do its job. Diacritics are
 * applied on the spot now.
 *
 * THE MARKS-ONLY SKELETON GATE NO LONGER APPLIES HERE (Asif, 2026-08-14) —
 * `rejectionReason`/`isVowellingCandidate` still gate the batch path below
 * unchanged, but this ONE call site was explicitly asked to also fix wrong
 * Arabic, not only add missing marks. See vowel-fix.ts's header for the full
 * reasoning and the boundary of what changed.
 *
 * TWO STAGES. A fast, cheap, non-grounded call tries first — for a passage
 * the model can confidently place, this is a single round trip. If it comes
 * back empty, unusable, or the model itself says it isn't sure
 * (`NEEDS_SEARCH_TOKEN`), a second call retries WITH Google Search grounding,
 * asked to find an authoritative source or, failing that, determine the most
 * likely correct form itself — that stage is instructed to always return an
 * answer, never come back empty.
 *
 * The reply is text only. The caller replaces the selection in the open editor, so
 * the write travels the Composer's own edit path (composer-edits.json) like any
 * other human edit and survives a re-compose.
 */
async function vowelOneRun(body: Record<string, unknown>): Promise<Response> {
  const source = String(body.text ?? "").trim();
  if (!source) return apiError("No text to vowel");
  if (!ARABIC_LINE_RE.test(source))
    return apiError("That selection has no Arabic script in it");
  // The same ratio `collectCandidates` applies above: predominantly Arabic, not
  // merely containing some. An English paragraph quoting three Arabic words would
  // ask the model to return English it is forbidden to touch.
  const latin = (source.match(/[A-Za-z]/g) || []).length;
  const arabic = (source.match(/[؀-ۿ]/g) || []).length;
  if (latin > 2 || arabic < latin * 4)
    return apiError(
      "Select the Arabic passage on its own, not the English around it",
    );
  // Deliberately NO "already vowelled" refusal here — unlike the batch path,
  // this button is also meant to fix a passage that already carries marks
  // but has them wrong, so "already has some tashkeel" is not a reason to
  // decline the request.

  const gate = rateLimitCheck();
  if (!gate.ok)
    return apiError(
      `Rate limited — retry in ${Math.ceil((gate.retryMs ?? 0) / 1000)}s`,
      429,
    );

  const primary = (
    await generate({
      model: MODEL,
      systemInstruction: FIX_AND_VOWEL_SYSTEM,
      contents: [{ role: "user", parts: [{ text: source }] }],
      // Same budget and temperature as the batch path, and for the same reasons
      // documented there: 2.5 Pro spends this allowance on thinking before it
      // writes, and vocalising a fixed text should be reproducible.
      maxOutputTokens: 4000,
      temperature: 0.1,
    })
  ).trim();

  let settled: string | null;
  let sources: string[] = [];
  let usedSearch = false;
  if (!needsSearchFallback(primary)) {
    settled = cleanModelReply(primary);
  } else {
    usedSearch = true;
    const grounded = await generateWithGrounding(groundedFixPrompt(source), {
      model: MODEL,
      temperature: 0.2,
      maxOutputTokens: 2000,
    });
    settled = cleanModelReply(grounded.text);
    sources = grounded.sources;
  }

  if (!settled)
    return apiError("Couldn't produce a corrected, vowelled passage");

  return apiOk({
    source,
    vowelled: settled,
    marksAdded: markCount(settled) - markCount(source),
    // The whole point of the letter-fixing capability is that it CAN differ
    // from the source in more than marks — this reports whether it actually
    // did, so the caller can tell the person "the Arabic itself changed"
    // rather than let a silent letter fix look identical to a plain
    // vowelling in the status line.
    fixed: skeleton(settled) !== skeleton(source),
    usedSearch,
    sources,
  });
}

async function propose(
  slug: string,
  bookDir: string,
  body: Record<string, unknown>,
): Promise<Response> {
  const gate = rateLimitCheck();
  if (!gate.ok)
    return apiError(
      `Rate limited — retry in ${Math.ceil((gate.retryMs ?? 0) / 1000)}s`,
      429,
    );

  // A bounded batch by default. Vocalising a whole book in one request is a long
  // wall-clock and a large spend for output nobody has looked at yet; the reviewer
  // should see the first handful and judge whether the model is any good at this
  // passage type before paying for the rest.
  const limit = Math.max(1, Math.min(40, Number(body.limit ?? 8)));
  const existing = loadProposals(bookDir);
  const byId = new Map(existing.map((p: { id: string }) => [p.id, p]));
  const todo = collectCandidates(bookDir)
    .filter((c) => !byId.has(runId(c.chapterKey, c.source)))
    .slice(0, limit);

  const added: unknown[] = [];
  const refused: { source: string; reason: string }[] = [];
  for (const c of todo) {
    let text;
    try {
      text = (
        await generate({
          model: MODEL,
          systemInstruction: SYSTEM,
          contents: [{ role: "user", parts: [{ text: c.source }] }],
          // Vocalisation is a short answer preceded by real deliberation, and 2.5
          // Pro's thinking tokens are drawn from THIS budget. The helper's 600
          // default left nothing for the visible answer and every call returned
          // empty — the same thinking-token starvation gemini-server.ts warns
          // about for Flash. The passages are one or two lines, so the headroom
          // costs nothing when the model is brief.
          maxOutputTokens: 4000,
          // Vocalising a fixed text is not a creative task: the same passage should
          // come back the same way twice.
          temperature: 0.1,
        })
      ).trim();
    } catch (e) {
      refused.push({ source: c.source, reason: `model error: ${String(e)}` });
      continue;
    }
    // Models like to wrap a one-line answer in quotes or a code fence.
    const cleaned = text
      .replace(/^```[a-z]*\s*/i, "")
      .replace(/```$/, "")
      .replace(/^["'«»]+|["'«»]+$/g, "")
      .split("\n")
      .find((l) => ARABIC_LINE_RE.test(l))
      ?.trim();
    // Same recovery as the single-selection path above.
    const settled = transferMarks(c.source, cleaned ?? "") ?? cleaned;
    const reason = rejectionReason(c.source, settled ?? "");
    if (reason) {
      // Refusals are REPORTED, not swallowed. A passage the model keeps failing on
      // is a passage a human should look at directly.
      refused.push({ source: c.source, reason });
      continue;
    }
    const proposal = {
      id: runId(c.chapterKey, c.source),
      chapter_key: c.chapterKey,
      chapter_title: c.chapterTitle,
      source: c.source,
      proposed: settled,
      resolved: settled,
      status: "pending",
      marks_added: markCount(settled ?? "") - markCount(c.source),
      model: MODEL,
      proposed_at: new Date().toISOString(),
      decided_at: "",
      note: "",
    };
    existing.push(proposal);
    added.push(proposal);
  }
  saveProposals(bookDir, existing);
  return apiOk({ slug, added: added.length, refused, proposals: existing });
}

function decide(
  slug: string,
  bookDir: string,
  body: Record<string, unknown>,
): Response {
  const id = String(body.id ?? "").trim();
  const status = String(body.status ?? "").trim();
  if (!id) return apiError("Missing id");
  if (!["pending", "accepted", "rejected"].includes(status))
    return apiError("status must be pending, accepted or rejected");

  const proposals = loadProposals(bookDir);
  const target = proposals.find((p: { id: string }) => p.id === id);
  if (!target) return apiError(`Proposal not found: ${id}`, 404);
  if (target.status === "applied")
    return apiError(
      "Already applied — edit the chapter in the Composer instead",
    );

  // A human may hand-correct the vocalisation, and the SAME gate applies: their
  // edit is still only allowed to change marks. This is not distrust of the
  // reviewer — it is what keeps "the letters are the source's" true of the artifact
  // regardless of who typed last.
  if (body.resolved !== undefined) {
    const resolved = String(body.resolved);
    const reason = rejectionReason(target.source, resolved);
    if (reason) return apiError(`Rejected: ${reason}`);
    target.resolved = resolved;
    target.marks_added = markCount(resolved) - markCount(target.source);
  }
  target.status = status;
  target.note = String(body.note ?? target.note ?? "");
  target.decided_at = new Date().toISOString();
  saveProposals(bookDir, proposals);
  return apiOk({ slug, proposal: target });
}

function apply(slug: string, bookDir: string): Response {
  const proposals = loadProposals(bookDir);
  const accepted = proposals.filter(
    (p: { status: string }) => p.status === "accepted",
  );
  if (!accepted.length) return apiError("Nothing accepted to apply");

  const bookMd = join(bookDir, "book", "book.md");
  if (!existsSync(bookMd)) return apiError("book.md not found", 404);

  // Group by chapter: one write per chapter, so the Composer sidecar records one
  // durable edit per chapter rather than one per mark.
  const byChapter = new Map<string, typeof accepted>();
  for (const p of accepted) {
    const list = byChapter.get(p.chapter_key) ?? [];
    list.push(p);
    byChapter.set(p.chapter_key, list);
  }

  const results: {
    chapter: string;
    applied: number;
    ok: boolean;
    error?: string;
  }[] = [];
  for (const [chapterKey, items] of byChapter) {
    // Read the chapter body fresh for each chapter — a previous iteration has
    // already rewritten the file.
    const lines = readFileSync(bookMd, "utf-8").split("\n");
    let start = -1;
    let end = lines.length;
    for (let i = 0; i < lines.length; i += 1) {
      if (!/^##\s+/.test(lines[i])) continue;
      if (start === -1 && anchorKey(lines[i]) === chapterKey) start = i;
      else if (start !== -1) {
        end = i;
        break;
      }
    }
    if (start === -1) {
      results.push({
        chapter: chapterKey,
        applied: 0,
        ok: false,
        error: "chapter not found",
      });
      continue;
    }
    let bodyText = lines.slice(start + 1, end).join("\n");
    let n = 0;
    for (const p of items) {
      if (!bodyText.includes(p.source)) continue; // the run moved; leave it pending
      bodyText = bodyText.split(p.source).join(p.resolved);
      p.status = "applied";
      p.decided_at = new Date().toISOString();
      n += 1;
    }
    if (!n) {
      results.push({
        chapter: chapterKey,
        applied: 0,
        ok: false,
        error: "no run matched",
      });
      continue;
    }
    const res = writeChapterBody(bookDir, chapterKey, bodyText.trim());
    results.push({
      chapter: chapterKey,
      applied: n,
      ok: res.ok,
      error: res.ok ? undefined : res.error,
    });
  }
  saveProposals(bookDir, proposals);
  return apiOk({ slug, results });
}
