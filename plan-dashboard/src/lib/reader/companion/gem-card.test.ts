/**
 * One card, two writers — and the parts that must not differ between them.
 *
 * Since 2026-08-06 a Companion explanation can be made two ways: you press Explain
 * and Gemini writes it, or the student-reader pass runs and Claude writes it. The
 * grounding, the persona, the word cap, the citation resolution and the etymology
 * veto are shared code precisely so those are not two answers. These pin the
 * shared half; the bridge test (scripts/gem-card.test.mjs) pins the seam.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { labelFor, LABEL_MAX_CHARS } from "./card-label";
import {
  prepareCard,
  finishCard,
  DEFAULT_MAX_WORDS,
  RESEARCH_NOTICE,
} from "./gem-card.server";

test("a short passage is its own card title", () => {
  assert.equal(
    labelFor("whose witnesses are seven kingdoms"),
    "whose witnesses are seven kingdoms",
  );
});

test("a long passage is elided, never reworded", () => {
  const long = "a".repeat(200);
  const label = labelFor(long);
  assert.ok(label.length <= LABEL_MAX_CHARS);
  assert.ok(label.endsWith("…"));
  assert.ok(
    long.startsWith(label.slice(0, -1)),
    "the kept part is the passage's own opening",
  );
});

test("the title is trimmed, so a selection with trailing space is the same card", () => {
  assert.equal(labelFor("  the seven earths  "), "the seven earths");
});

test("a question turn asks the question; a bare passage asks about the passage", () => {
  const passage = "the witnesses are seven kingdoms";
  const withQuestion = prepareCard({
    concept: passage,
    question: "What are the seven kingdoms?",
  });
  const without = prepareCard({ concept: passage });

  assert.ok(withQuestion.user.includes("What are the seven kingdoms?"));
  assert.ok(!without.user.includes("What are the seven kingdoms?"));
  assert.ok(without.user.includes(passage));
});

test("the chapter is offered for orientation and the passage is what is asked about", () => {
  const prepared = prepareCard({
    concept: "the seven earths followed from it",
    chapterContext:
      "The Master spoke at length about the condensation of heat.",
    question: "What are the seven earths?",
  });
  const chapterAt = prepared.user.indexOf("condensation of heat");
  const askAt = prepared.user.indexOf("What are the seven earths?");
  assert.ok(chapterAt !== -1 && askAt !== -1);
  assert.ok(
    chapterAt < askAt,
    "the model reads the argument first and the ask second",
  );
});

test("grounding is reported, never assumed — a caller can refuse an ungrounded passage", () => {
  // Asif's rule (2026-08-06): no grounding, no card. That is only enforceable if
  // prepareCard says so BEFORE the model runs, which is what makes it free.
  const ungrounded = prepareCard({
    concept: "zzzqqq wwwvvv xxxyyy nnnmmm",
    ground: true,
  });
  assert.equal(ungrounded.grounded, 0);
  assert.equal(ungrounded.morphology, false);
});

test("retrieval is skipped entirely when the caller does not ask for it", () => {
  const typed = prepareCard({ concept: "the imamate", ground: false });
  assert.equal(typed.grounded, 0);
});

test("a card is capped, and the cap falls on a block boundary", () => {
  const blocks = Array.from({ length: 40 }, (_, i) =>
    `Paragraph ${i}. ${"word ".repeat(20)}`.trim(),
  );
  const finished = finishCard({ body: blocks.join("\n\n") });

  assert.ok(finished.body.split(/\s+/).length <= DEFAULT_MAX_WORDS);
  // Whole blocks, in order, from the top: a cap that landed mid-paragraph would
  // truncate a thought.
  const kept = finished.body.split(/\n{2,}/);
  assert.ok(kept.length > 1 && kept.length < blocks.length);
  assert.deepEqual(kept, blocks.slice(0, kept.length));
});

test("an absurd cap is bounded rather than honoured", () => {
  const body = "short body";
  assert.equal(finishCard({ body, maxWords: 10_000 }).body, body);
  // Under the floor, the default applies rather than a 1-word card.
  assert.equal(finishCard({ body, maxWords: 3 }).body, body);
});

test("a Q|Surah:Verse citation is resolved against the mushaf, not left machine-readable", () => {
  const finished = finishCard({ body: "As it says in Q|18:65." });
  assert.ok(
    !finished.body.includes("Q|18:65"),
    "the machine form must never reach a reader",
  );
  assert.ok(finished.body.includes("Al-Kahf"), "the surah is named");
});

test("etymology survives when the corpus does not contradict it", () => {
  const finished = finishCard({
    body: "A card.",
    etymology: ["عِلْم: from the root ع-ل-م, to know."],
  });
  assert.equal(finished.etymology.length, 1);
  assert.equal(finished.etymologyVetoed, 0);
});

test("no etymology is not an error", () => {
  const finished = finishCard({ body: "A card." });
  assert.deepEqual(finished.etymology, []);
  assert.equal(finished.etymologyVetoed, 0);
});

// ─── the researched card: marked at the top, sourced at the bottom ──────────
test("sources are named sites, not opaque redirect links", () => {
  // The card renderer supports bold, italic and lists but NOT links, so a
  // markdown link would print its whole `vertexaisearch…/grounding-api-redirect/`
  // URI as visible text. The site name is also the part a reader can act on.
  const finished = finishCard({
    body: "A card.",
    researchSources: ["ismaililiterature.org", "slideshare.net"],
  });
  assert.ok(!finished.body.includes("http"), "no raw URL reaches the reader");
  assert.ok(finished.body.includes("- ismaililiterature.org"));
});

test("a researched card says so before its first sentence", () => {
  // Asif's 6b: the difference between a card built from his own corpora and one
  // built from the open web has to be visible BEFORE the explanation, not
  // inferable from a source list at the end. This is a religious text.
  const finished = finishCard({
    body: "The rope of God is the covenant.",
    researchSources: ["ismaililiterature.org"],
  });
  assert.ok(finished.body.startsWith(RESEARCH_NOTICE));
  assert.ok(finished.body.includes("ismaililiterature.org"));
  assert.ok(finished.body.includes("Sources consulted"));
});

test("a corpus-grounded card carries no notice and no source list", () => {
  const finished = finishCard({ body: "The rope of God is the covenant." });
  assert.equal(finished.body, "The rope of God is the covenant.");
});

test("the same site returned twice is listed once", () => {
  const dup = "arabic123.com";
  const finished = finishCard({
    body: "A card.",
    researchSources: [dup, dup, "other.org"],
  });
  assert.equal(finished.body.split(dup).length - 1, 1, "listed once");
});

test("a long source list is capped rather than dumped", () => {
  const many = Array.from(
    { length: 12 },
    (_, i) => `[s${i}.org](https://x/${i})`,
  );
  const finished = finishCard({ body: "A card.", researchSources: many });
  const listed = many.filter((s) => finished.body.includes(s));
  assert.ok(listed.length <= 6 && listed.length > 0);
  assert.deepEqual(
    listed,
    many.slice(0, listed.length),
    "the ones it leant on most",
  );
});

test("the notice and sources are added after the cap, so neither can be truncated", () => {
  const long = Array.from({ length: 40 }, (_, i) =>
    `Para ${i}. ${"word ".repeat(20)}`.trim(),
  ).join("\n\n");
  const finished = finishCard({
    body: long,
    maxWords: 60,
    researchSources: ["only.org"],
  });
  assert.ok(
    finished.body.startsWith(RESEARCH_NOTICE),
    "the mark survives the cap",
  );
  assert.ok(finished.body.includes("only.org"), "so do the sources");
});
