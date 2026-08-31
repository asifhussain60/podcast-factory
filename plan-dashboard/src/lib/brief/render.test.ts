/**
 * render.test.ts — the processing rules a commission implies are ACTED ON, so
 * every one of them is pinned here.
 *
 * The failure this guards against is the one that cost two chapters of
 * `purification-of-the-heart` on 2026-08-30: a recorded sermon reached an
 * authoring pass that rewrote it into third-person literary prose, because
 * nothing between the form and the pipeline ever said in words that a recording
 * must not be rewritten. The prompt now says it, and this is what keeps it said.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { chapterList, processingRules, type BriefInput } from "./render";
import { STEPS, completenessProblems } from "./fields";

function input(values: Record<string, string>): BriefInput {
  return {
    values,
    bucket: "Sessions",
    briefDir: "/brief",
    repoRoot: "/repo",
    sources: [],
    generatedAt: "2026-08-31T00:00:00Z",
  };
}

const SESSION = {
  source_medium: "audio_lecture",
  chapter_segmentation: "one_per_recording",
  arabic_restoration: "audio_grounded",
};

/** One joined blob, so a rule is found wherever in the list it happens to sit. */
function rules(values: Record<string, string>): string {
  return processingRules(input(values)).join("\n");
}

test("a recorded session is told, in words, that it is never rewritten", () => {
  const out = rules(SESSION);
  assert.match(out, /PROOFREAD only/);
  assert.match(out, /never\s+rewritten, re-voiced, summarised or enriched/);
});

test("a recorded session generates no podcast", () => {
  assert.match(rules(SESSION), /NO podcast is generated/);
  assert.match(rules(SESSION), /no episodes, no NotebookLM upload bundle/);
});

test("a printed book is told none of the session rules", () => {
  const out = rules({ source_medium: "printed_text" });
  assert.doesNotMatch(out, /PROOFREAD only/);
  assert.doesNotMatch(out, /NO podcast is generated/);
});

test("both segmentation answers reach the prompt as distinct instructions", () => {
  assert.match(rules(SESSION), /One chapter per recording/);
  assert.match(
    rules({ ...SESSION, chapter_segmentation: "from_transcript" }),
    /worked out from the transcript/i,
  );
});

test("the chapter count is carried as a guide, and omitted when not given", () => {
  assert.match(
    rules({ ...SESSION, chapter_count_hint: "18" }),
    /roughly 18 chapters/,
  );
  assert.doesNotMatch(rules(SESSION), /roughly/);
  // A printed book gets the same guide, worded for the route that settles it.
  assert.match(
    rules({ source_medium: "printed_text", chapter_count_hint: "12" }),
    /roughly 12 chapters/,
  );
});

test("Arabic is always restored to script, always vowelled, always in its own block", () => {
  const out = rules(SESSION);
  assert.match(out, /back into Arabic script/);
  assert.match(out, /canonical mushaf/);
  assert.match(out, /All Arabic carries its diacritics/);
  assert.match(out, /own styled blocks/);
});

test("the two Arabic-restoration answers give opposite instructions", () => {
  assert.match(rules(SESSION), /check that moment of the recording/);
  assert.match(
    rules({ ...SESSION, arabic_restoration: "text_only" }),
    /unresolved rather than guessing/,
  );
});

test("slide decks are instructed for a session as well as a book", () => {
  for (const medium of ["audio_lecture", "printed_text"]) {
    assert.match(
      rules({ ...SESSION, source_medium: medium }),
      /slide deck for each chapter/,
    );
  }
  assert.match(
    rules({ ...SESSION, slide_deck_mode: "book" }),
    /ONE slide deck covering the whole work/,
  );
  assert.match(
    rules({ ...SESSION, enable_slide_decks: "false" }),
    /no slide decks/,
  );
});

// ── The chapter breakdown ───────────────────────────────────────────────────

test("a pasted chapter list is renumbered rather than double-numbered", () => {
  const got = chapterList(
    input({ chapter_list: "1. Love of the World\n2) Envy\n\n  Anger  \n" }),
  );
  assert.deepEqual(got, ["Love of the World", "Envy", "Anger"]);
});

test("a named chapter list overrides the rough count, on both routes", () => {
  for (const medium of ["audio_lecture", "printed_text"]) {
    const out = rules({
      ...SESSION,
      source_medium: medium,
      chapter_list: "Envy\nAnger\nRancor",
      chapter_count_hint: "99",
    });
    assert.match(out, /There are 3 chapters, named in the list/);
    assert.doesNotMatch(out, /roughly 99/);
  }
});

test("a session with a named list is told not to invent or merge titles", () => {
  const out = rules({ ...SESSION, chapter_list: "Envy\nAnger" });
  assert.match(out, /Do not invent chapter titles/);
  assert.match(out, /do not merge two of them into one/);
});

// ── The readiness gate ──────────────────────────────────────────────────────

test("a commission with no source file is not ready", () => {
  const p = completenessProblems(SESSION, { sourceCount: 0, roles: [] });
  assert.match(p.map((x) => x.reason).join(" "), /no source file/);
});

test("a recorded session is not ready without its recording attached", () => {
  const p = completenessProblems(
    { ...SESSION, chapter_count_hint: "5" },
    { sourceCount: 1, roles: ["primary_source"] },
  );
  assert.match(p.map((x) => x.reason).join(" "), /needs its recording/);
});

test("following the book's chapter list requires the list", () => {
  const p = completenessProblems(
    { ...SESSION, chapter_segmentation: "from_source_toc" },
    { sourceCount: 1, roles: ["source_recording"] },
  );
  assert.match(p.map((x) => x.reason).join(" "), /no list has been given/);
});

test("a complete session commission raises nothing", () => {
  const p = completenessProblems(
    {
      ...SESSION,
      chapter_segmentation: "from_source_toc",
      chapter_list: "Envy\nAnger",
    },
    { sourceCount: 2, roles: ["primary_source", "source_recording"] },
  );
  assert.deepEqual(p, []);
});

test("every readiness problem points at a step you can jump to", () => {
  const p = completenessProblems(SESSION, { sourceCount: 0, roles: [] });
  assert.ok(p.length > 0);
  for (const x of p)
    assert.ok(
      STEPS.some((s) => s.id === x.step),
      String(x.step),
    );
});

test("a book that already exists is not asked to upload its sources again", () => {
  // Its files are in its own folder; nothing is staged when you merely open it.
  // Without this the readiness gate reported a book with a recording on disk as
  // having nothing to work from, and refused to write its brief.
  const p = completenessProblems(
    { ...SESSION, chapter_list: "Envy\nAnger" },
    { sourceCount: 0, roles: [], existing: true },
  );
  assert.deepEqual(p, []);
});

test("a NEW commission is still asked for its sources", () => {
  const p = completenessProblems(
    { ...SESSION, chapter_list: "Envy\nAnger" },
    { sourceCount: 0, roles: [], existing: false },
  );
  assert.match(p.map((x) => x.reason).join(" "), /no source file/);
});

test("chapter problems still apply to a book that exists", () => {
  // Only the UPLOAD checks are skipped for an existing book — a missing chapter
  // list is just as much a gap whether the folder is there or not.
  const p = completenessProblems(
    { ...SESSION, chapter_segmentation: "from_source_toc" },
    { sourceCount: 0, roles: [], existing: true },
  );
  assert.match(p.map((x) => x.reason).join(" "), /no list has been given/);
});

test("each segmentation answer gives its own instruction, and never another's", () => {
  // The third answer was added to the vocabulary but not to the rules, so a
  // book following its source's contents page was told "one chapter per
  // recording" — the instruction contradicting the setting it came from.
  const toc = rules({ ...SESSION, chapter_segmentation: "from_source_toc" });
  assert.match(toc, /teach through a published work chapter by chapter/);
  assert.match(toc, /A recording is NOT one chapter/);
  assert.doesNotMatch(toc, /One chapter per recording\./);

  const per = rules({ ...SESSION, chapter_segmentation: "one_per_recording" });
  assert.match(per, /One chapter per recording\./);
  assert.doesNotMatch(per, /teach through a published work/);

  const tr = rules({ ...SESSION, chapter_segmentation: "from_transcript" });
  assert.match(tr, /worked out from the transcript/i);
  assert.doesNotMatch(tr, /One chapter per recording\./);
});

test("every segmentation answer the form offers has a rule of its own", () => {
  // A fourth option added to the vocabulary without a rule here would silently
  // fall through to the one_per_recording default, which is how the third one
  // went wrong.
  const seen = new Set(
    ["one_per_recording", "from_source_toc", "from_transcript"].map((v) =>
      rules({ ...SESSION, chapter_segmentation: v }),
    ),
  );
  assert.equal(seen.size, 3, "two answers produced identical instructions");
});

test("chapters the recordings miss become one introduction, not a gap", () => {
  const out = processingRules({
    ...input({ ...SESSION, chapter_list: "Envy\nAnger" }),
    uncovered: ["Miserliness", "Hatred"],
  }).join("\n");
  assert.match(out, /condensed into ONE introduction chapter/);
  assert.match(out, /Miserliness, Hatred/);
  assert.match(out, /do not leave the reader to start at the middle/i);
  // The wording Asif corrected: they are not "deliberately excluded".
  assert.doesNotMatch(out, /deliberately not part of this work/);
});

test("a book whose recordings reach every chapter gets no introduction rule", () => {
  const out = processingRules(
    input({ ...SESSION, chapter_list: "Envy\nAnger" }),
  ).join("\n");
  assert.doesNotMatch(out, /introduction chapter/);
});
