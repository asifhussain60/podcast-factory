"""_book_brief_prompts.py — the four briefs the condensation lane sends to a model.

Kept apart from `_book_brief` for the reason `_book_frontmatter` keeps its own
prompt beside its gate and `_apparatus_steps` keeps the step vocabulary beside
nothing at all: a prompt is TUNED, repeatedly, by someone reading the output it
produced, and a file of prompts can be read end to end while a file of prompts
interleaved with subprocess handling cannot.

FOUR CALLS, AND WHY IT IS NOT ONE
---------------------------------
`analyse` runs per section and is the only call that sees the book's actual prose.
`draft` sees no prose at all — it writes from the ranked plan, which is what stops
the result being a chain of chapter summaries: there are no chapters in front of
it to summarise. `adjudicate` and `repair` see the draft and the plan but, again,
never the source, so neither can quietly re-import a sentence the ranking dropped.

THE GENRE STRATEGIES ARE CLAUSES, NOT SEPARATE PROMPTS
-------------------------------------------------------
A separate prompt per book type is four more things to keep in step with every
later tuning, and the parts that differ between a novella and a treatise are
narrow: what counts as essential, and what may be flattened. So the strategy is
one interpolated block and everything else is shared.
"""

from __future__ import annotations

from typing import Any

#: What each strategy PROTECTS, in the words the analysis and drafting calls both
#: read. Keyed by the name `_book_brief.strategy_for` resolves from the book's
#: declared content profile — never guessed from the prose, for the same reason
#: `narrative_frame` is a declared source property rather than an inference.
STRATEGIES: dict[str, str] = {
    "narrative": """This is a work of FICTION or narrative. Treat as essential: the main
characters and what each of them wants; the relationships between them; the central
conflict; every turning point and the cause-and-effect that links them; what the
characters come to understand; the climax; the resolution; the ending as it actually
lands; and the themes the story is built to carry.
Setting matters only where it acts on the story. Scene-setting, atmosphere and
description are compressible to a clause. NEVER drop a causal link merely to save
words — "she left" is not a substitute for why she left. The ending is essential and
is never omitted or left implied.""",
    "doctrinal": """This is a work of PHILOSOPHY, THEOLOGY or doctrine. Treat as
essential: definitions; the logical progression from premise to conclusion; every
distinction the author draws; objections the author raises and the answers given;
the interpretive and historical context a claim depends on; and the conclusions.
Keep clear at every point WHO is speaking — what the author asserts, what an
opposing position asserts, and what is reported from a source. Never collapse two
distinct positions into a single generic statement, and never state a qualified
claim as an absolute. A doctrinal claim rendered slightly wrong is worse than one
omitted.""",
    "technical": """This is a TECHNICAL or ACADEMIC work. Treat as essential: the core
concepts and their definitions; the dependencies between them; mechanisms, models
and algorithms; the evidence that carries the argument; and the caveats and
conditions on each result. Never remove a concept that later material depends on.
Prefer exact technical language over a simplification that changes the meaning.""",
    "expository": """This is a work of NONFICTION argument. Treat as essential: the
central thesis; the major arguments and the reasoning that supports them; key
concepts, definitions and frameworks; important distinctions; the qualifications and
counterarguments the author takes seriously; the conclusions; and the practical
implications.
Examples and anecdotes are omitted unless one is needed to make an idea intelligible,
is unusually strong evidence, or is referred back to later. Where several examples
make the same point, keep the strongest one or state the pattern. Never turn a
qualified claim ("usually, under these conditions") into an absolute.""",
    "biographical": """This is a BIOGRAPHY or MEMOIR. Treat as essential: the stages of
the life that changed its direction; the formative experiences; the major
relationships; the decisions and their consequences; the achievements and the
failures; the historical context where it acts on the life; how the person's
outlook changed; and the author's own interpretation of events. Produce an account,
not a timeline — dates serve the causation, never replace it.""",
}

_ANALYSE = """You are an editor reading ONE section of a book in order to build a
structured record of what it contains. You are NOT writing prose and NOT summarising.

{strategy}

SECTION {index} OF {total}: {title}

---
{body}
---

Return ONE JSON object, no commentary and no code fence:

{{
  "title": "{title}",
  "purpose": "one sentence: what this section does for the book as a whole",
  "points": [
    {{
      "text": "one self-contained sentence stating the point, understandable by someone who has not read the book",
      "kind": "thesis|claim|definition|framework|distinction|caveat|event|turn|cause|resolution|relationship|theme|evidence|example|anecdote|context",
      "weight": 1-5,
      "depends_on": ["S01-P02"],
      "entities": ["proper nouns or defined terms this point concerns"]
    }}
  ]
}}

RULES
- `weight` is how much a reader's understanding of THE WHOLE BOOK suffers if this
  point is missing. 5 = the book does not make sense without it. 1 = decoration.
  Judge against the book, not against this section: a section can contain nothing
  above weight 2 and that is a legitimate answer.
- Do NOT inflate. If most points here are ordinary, most weights are 2 or 3.
- `depends_on` refers to point ids from EARLIER sections, listed below. Use it when
  this point is unintelligible without that one. Leave it empty if unsure.
- 4 to 12 points. A long section is not automatically more points; a dense one is.
- Every point must be traceable to this section's text. Invent nothing.
{prior}"""

_DRAFT = """You are writing a condensed standalone version of a book: one continuous
piece of prose that gives a reader the substance of the whole book without reading it.

BOOK: {title}{author}

{strategy}

{register}

WHAT YOU ARE WRITING FROM
Below is a ranked plan of the material that survived editorial selection, grouped by
where it came from and marked with the word budget each group has earned. The budget
is allocated by IMPORTANCE, not by how long that part of the book was — a group with
a small budget was a long stretch of book that matters little, and you must respect
that rather than restore its length.

You do NOT have the book's text. Write only what the plan states. If the plan does
not say something, it does not go in.

TOTAL BUDGET: {total} words, a HARD MAXIMUM. Aim for {target}.
  opening/orientation: about {opening} words
  body: about {body} words, split as marked below
  close: about {closing} words

{outline}

HOW IT MUST READ
- As ONE piece of writing, intentionally composed. Not a set of summaries joined up.
- NEVER write "In Chapter 3...", "the author then discusses...", "this book argues...",
  "in the next section...". Explain the material directly, in its own right.
- Points marked ESSENTIAL must all be present. Points marked SUPPORTING may be
  compressed into a clause or folded into a neighbouring idea.
- Preserve causation. Where the plan gives A leading to B leading to C, the prose
  must carry the chain, not the endpoints.
- Preserve conditions and qualifications exactly as the plan states them. Do not
  promote a qualified claim to an absolute.
- Use headings ONLY if the piece genuinely needs two or three; most do not. Never
  more than three. No bullet lists. Narrative prose throughout.
- Invent nothing: no facts, examples, quotations, events, motives or conclusions
  beyond the plan. If something is unclear in the plan, leave it out.
- Do not mention this plan, the condensation, the word budget, or yourself.

OUTPUT
Return ONLY the condensed prose, under {total} words. No title line, no preamble,
no code fence."""

_ADJUDICATE = """Below is a condensed version of a book, and a list of points that were
required to appear in it. A crude text search could not find these points; the search
is lexical and misses paraphrase, so most of them are probably present in other words.

Decide, for each, whether its SUBSTANCE is actually conveyed by the draft.

DRAFT
---
{draft}
---

POINTS TO CHECK
{points}

Return ONE JSON object, no commentary and no code fence:
{{"missing": ["S01-P02", ...]}}

A point counts as PRESENT if a reader of the draft would come away knowing it, in
whatever words. It is MISSING only if the draft does not convey it at all. Do not
list a point merely because the draft states it more briefly than you would."""

_REPAIR = """Below is a condensed version of a book. A review found that it omits
material that was required to be in it, and may contain the other problems listed.

Revise it. Do not rewrite it from scratch: keep the existing prose, its order and its
voice, and make the smallest changes that fix the findings.

{register}

CURRENT DRAFT ({current} words)
---
{draft}
---

FINDINGS TO FIX
{findings}

MATERIAL TO WORK IN
{missing}

RULES
- The result must be under {total} words. It is currently {current}. If working the
  missing material in pushes you over, take the words from the least important
  material already present — never by deleting something the findings called
  essential, and never by cutting a sentence off mid-thought.
- Add nothing beyond the material listed above.
- Same rules as before: one continuous piece, no chapter references, no bullets, no
  meta-commentary, causation preserved, qualifications preserved.

Return ONLY the revised prose. No preamble, no code fence."""


def analyse_prompt(*, strategy: str, index: int, total: int, title: str, body: str, prior: str = "") -> str:
    return _ANALYSE.format(
        strategy=STRATEGIES.get(strategy, STRATEGIES["expository"]),
        index=index,
        total=total,
        title=title,
        body=body,
        prior=("\n\nPOINT IDS FROM EARLIER SECTIONS (for depends_on):\n" + prior) if prior else "",
    )


def draft_prompt(*, facts: dict[str, Any], strategy: str, register: str, plan: dict[str, Any], outline: str) -> str:
    total = int(plan["total_words"])
    return _DRAFT.format(
        title=facts.get("title") or "this book",
        author=(f"\nAUTHOR: {facts['author']}" if facts.get("author") else ""),
        strategy=STRATEGIES.get(strategy, STRATEGIES["expository"]),
        register=register,
        total=total,
        target=int(total * 0.94),
        opening=plan["opening_words"],
        body=plan["body_words"],
        closing=plan["closing_words"],
        outline=outline,
    )


def adjudicate_prompt(*, draft: str, points: str) -> str:
    return _ADJUDICATE.format(draft=draft, points=points)


def repair_prompt(*, draft: str, register: str, findings: str, missing: str, total: int) -> str:
    return _REPAIR.format(
        draft=draft,
        register=register,
        findings=findings or "- (none beyond the omissions below)",
        missing=missing or "- (none)",
        total=total,
        current=len(draft.split()),
    )
