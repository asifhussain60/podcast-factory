/**
 * gem-card.mjs — the Ismaili Scholar, reachable from Python.
 *
 * The student-reader pass runs in Python on `claude -p`; the Scholar's grounding,
 * persona, word cap, Qur'anic citation resolution and etymology veto are
 * TypeScript reading three SQLite files. This is the seam between them, and it is
 * the same shape the Podcast Factory Library uses to reach the site's renderer
 * through `render-chapters.mjs`: ask for the thing, never reimplement it.
 *
 * Porting those steps to Python instead would have created four new TS/Python
 * mirror pairs. This repo has four already and every one is fixture-pinned,
 * because a divergence in a mirror is silent — a drifted citation resolver would
 * print a different verse for the same reference on the site and in the card.
 *
 * THREE COMMANDS, JSON on stdin, JSON on stdout, with the model calls in between
 * belonging to the caller:
 *
 *   prepare  {concept, context?, chapterContext?, bookTitle?, question?, ground?}
 *         -> {ok, system, user, anchor, grounded, morphology, tightenSystem}
 *   parse    {raw}   -- the model's reply, read with the Explain button's parser
 *         -> {ok, body, etymology}
 *   finish   {body, etymology?, tightenedRaw?, maxWords?, researchSources?}
 *         -> {ok, body, etymology, etymologyVetoed, tightened}
 *   research {concept, context?, chapterContext?, bookTitle?, question?, maxWords?}
 *         -> {ok, body, etymology, etymologyVetoed, sources}
 *
 * `parse` is its own step rather than the front of `finish` because the caller
 * has work to do between them: it tightens the PARSED body. Folding the two
 * together meant the tightener was handed the raw envelope, which is how a
 * failure to read that envelope turned into a filed card made of JSON.
 *
 * `research` IS A MODEL CALL, and the only one here (Asif, 2026-08-06). Every
 * other command is deliberately model-free, but the online path cannot be: it is
 * Gemini's Google-Search grounding, and `claude -p` in this repo runs with
 * `--allowedTools Write,Edit,MultiEdit,Read,Bash,Grep,Glob` — no WebSearch, no
 * WebFetch — so Claude physically cannot do it. It is reached ONLY for a passage
 * the knowledge base could not ground, and it COSTS REAL MONEY, unlike the rest
 * of this pipeline. It returns its sources, and a run with no sources is a
 * failure rather than an unsourced answer about a religious text.
 *
 * No file is written. Failure is a JSON object with `ok: false` and a non-zero
 * exit, never a stack trace on stdout.
 */
import "./lib/ts-resolve-hook.mjs";

/** Read all of stdin. Empty input is an empty object, not a crash. */
async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString("utf8").trim();
  return text ? JSON.parse(text) : {};
}

function emit(payload, code = 0) {
  process.stdout.write(JSON.stringify(payload) + "\n");
  process.exitCode = code;
}

async function main() {
  const command = process.argv[2];
  if (!["prepare", "parse", "finish", "research"].includes(command)) {
    emit({ ok: false, error: `unknown command: ${command ?? "(none)"}` }, 2);
    return;
  }

  // Dynamic: the resolve hook above registers at import time, and a static
  // import of a .ts specifier is hoisted above it.
  const card = await import("../src/lib/reader/companion/gem-card.server.ts");

  const input = await readStdin();

  if (command === "prepare") {
    if (typeof input.concept !== "string" || !input.concept.trim()) {
      emit({ ok: false, error: "missing concept" }, 1);
      return;
    }
    const { labelFor } =
      await import("../src/lib/reader/companion/card-label.ts");
    // The tightening instruction travels WITH the turn rather than being asked
    // for separately, so the caller never holds a copy of it. It is the same
    // string the Explain button's tightening pass uses.
    const { ARTICULATION_PROMPT, ARTICULATION_MIN_CHARS } =
      await import("../src/lib/reader/companion/articulate-rules.ts");
    const prepared = card.prepareCard({
      gemId: input.gemId,
      concept: input.concept,
      context: input.context,
      chapterContext: input.chapterContext,
      bookTitle: input.bookTitle,
      question: input.question,
      // A passage is grounded by default here. The button distinguishes a
      // selected passage (grounded) from a typed concept (not), and this
      // command is only ever reached with a passage.
      ground: input.ground !== false,
    });
    emit({
      ok: true,
      system: prepared.system,
      user: prepared.user,
      grounded: prepared.grounded,
      morphology: prepared.morphology,
      anchor: labelFor(input.concept),
      tightenSystem: ARTICULATION_PROMPT,
      tightenMinChars: ARTICULATION_MIN_CHARS,
    });
    return;
  }

  if (command === "parse") {
    if (typeof input.raw !== "string" || !input.raw.trim()) {
      emit({ ok: false, error: "missing raw" }, 1);
      return;
    }
    const { toResult } = await import("../src/lib/reader/gems/engine.ts");
    const parsed = toResult(input.raw);
    if (!parsed.body.trim()) {
      emit({ ok: false, error: "no answer in reply" }, 1);
      return;
    }
    // `toResult` falls back to returning the whole reply as the body when it
    // cannot read the JSON envelope. That is right for a reply that was never
    // JSON and wrong for one that WAS: the fallback hands back the envelope,
    // and what gets filed is a card whose first characters are `{"body": "…`.
    // Measured on this book 2026-08-06 — one card shipped exactly that way, and
    // it survived the tightening pass afterwards because the tightener happily
    // rewrote the envelope too. A reply that still looks like an envelope is a
    // failure, not a card.
    if (/^\s*\{[\s\S]*"body"\s*:/.test(parsed.body)) {
      emit({ ok: false, error: "reply is an unparsed JSON envelope" }, 1);
      return;
    }
    emit({ ok: true, body: parsed.body, etymology: parsed.etymology });
    return;
  }

  if (command === "research") {
    if (typeof input.concept !== "string" || !input.concept.trim()) {
      emit({ ok: false, error: "missing concept" }, 1);
      return;
    }
    const { runGemQuestion } = await import("../src/lib/reader/gems/engine.ts");
    const question = (input.question ?? "").trim() || input.concept.trim();
    // Retry a BUSY model, and only a busy one. Google answers a demand spike
    // with 503 UNAVAILABLE, which says nothing about the passage — without this
    // a transient spike is indistinguishable from "the web had nothing to say",
    // and the caller drops a card for the wrong reason (measured 2026-08-06).
    // Three attempts, backing off, because the alternative is a paid pass that
    // silently thins out whenever Gemini is busy.
    const attempts = 3;
    let result;
    for (let i = 0; i < attempts; i++) {
      try {
        result = await runGemQuestion({
          gemId: input.gemId,
          question,
          context: input.context,
          chapterContext: input.chapterContext,
          bookTitle: input.bookTitle,
          grounded: true,
        });
        break;
      } catch (e) {
        const transient =
          /\b(429|500|502|503|504)\b|UNAVAILABLE|RESOURCE_EXHAUSTED/.test(
            String(e?.message ?? e),
          );
        if (!transient || i === attempts - 1) throw e;
        await new Promise((r) => setTimeout(r, 4000 * (i + 1)));
      }
    }
    const sources = (result.sources ?? []).filter(Boolean);
    if (!result.body.trim()) {
      emit({ ok: false, error: "no answer returned" }, 1);
      return;
    }
    // Asif's rule (2026-08-06, answering 7a): if neither his library nor the
    // open web can stand behind it, no card. A best guess about a religious
    // teaching, filed under a scholar's byline, is the thing he asked not to
    // have. Reported as its own error so the caller can log it plainly.
    if (!sources.length) {
      emit({ ok: false, error: "researched but unsourced" }, 1);
      return;
    }
    const finished = card.finishCard({
      body: result.body,
      etymology: result.etymology,
      maxWords: input.maxWords,
      researchSources: sources,
    });
    emit({ ok: true, ...finished, sources });
    return;
  }

  if (typeof input.body !== "string" || !input.body.trim()) {
    emit({ ok: false, error: "missing body" }, 1);
    return;
  }
  const { articulationGuardsPass } =
    await import("../src/lib/reader/companion/articulate-rules.ts");

  // The tightening pass is an improvement, never a dependency: its output is
  // used only when it kept every Arabic run and every citation and did not grow.
  // It is compared against the PARSED body, because that is what the caller was
  // asked to tighten — handing the tightener an envelope is what let a parse
  // failure be laundered into something that looked like prose.
  let body = input.body;
  let tightened = false;
  if (typeof input.tightenedRaw === "string" && input.tightenedRaw.trim()) {
    const next = input.tightenedRaw
      .replace(/^```(?:markdown)?\s*|\s*```$/g, "")
      .trim();
    if (articulationGuardsPass(body, next)) {
      body = next;
      tightened = true;
    }
  }

  const finished = card.finishCard({
    body,
    etymology: input.etymology,
    maxWords: input.maxWords,
  });
  emit({ ok: true, ...finished, tightened });
}

main().catch((e) => emit({ ok: false, error: String(e?.message ?? e) }, 1));
