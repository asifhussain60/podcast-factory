"""_authoring/framing.py — Per-chapter framing authorship.

Extracted from _authoring.py (A4 split).
"""
from __future__ import annotations

import re as _re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ._core import (  # noqa: E402
    AuthoringError,
    FRAMING_TIMEOUT,
    _run_claude_p,
    _assert_artifact,
    _read_category,
    ARABIC_SCHOLARLY_CATEGORIES,
)

# ─── Consumer framing prompt (category: sites) ───────────────────────────────

def _build_consumer_framing_prompt(
    book_slug: str,
    chapter_slug: str,
    chap_num: str,
    contract: Path,
    chapter_file: Path,
    framing_path: Path,
    book_dir: Path,
) -> str:
    """Consumer-voice framing prompt for sites category content.

    Replaces the Islamic scholarly prompt with a plain-English financial
    benefits prompt. Keeps all structural sections required by
    build_episode_txt.py (## Pronunciation, ## Name discipline,
    ## Three-part focus, ## Tone constraints, ## Do not).
    """
    return (
        f"You are authoring the NotebookLM customize prompt (the framing) for episode "
        f"`EP{chap_num}-{chapter_slug}` of `{book_slug}` — a consumer-facing healthcare "
        f"benefits podcast for working Americans.\n\n"
        f"INPUT:\n"
        f"  - `{contract}` — chapter contract (audience, angle, key_tensions, title)\n"
        f"  - `{chapter_file}` — the chapter text NotebookLM receives as its SOURCE\n\n"
        f"OUTPUT: `{framing_path}` — the customize prompt pasted into NotebookLM's Customize box.\n\n"
        f"HOST ROLES (locked for this series):\n"
        f"  Host A (John, male voice) = the knowledgeable guide — explains, clarifies, teaches.\n"
        f"  Host B (Hannah, female voice) = the curious everyday listener — asks the questions\n"
        f"  the audience is actually thinking, pushes back when things sound too good.\n"
        f"  Roles do NOT rotate across episodes.\n\n"
        f"REQUIRED SECTIONS — every section header below must appear verbatim:\n\n"
        f"  ## Opening directive\n"
        f"  How the episode must open. Must NOT start with 'today we discuss' or any "
        f"meta-reference to the podcast. Start inside the listener's actual situation.\n"
        f"  Include the central thesis VERBATIM (the most concrete, quotable line about "
        f"what this product does for the listener's financial life). This thesis repeats "
        f"exactly 3 times: at the open, at the midpoint, and at the close.\n"
        f"  For extended-tier episodes: target a 50 to 60 minute in-depth conversation.\n\n"
        f"  ## Audience\n"
        f"  One paragraph. Who is listening, what decision they face this week.\n\n"
        f"  ## Angle\n"
        f"  One sentence. The chosen lens (personal_application = walk the listener "
        f"through the same decisions they will face in their own life).\n\n"
        f"  ## Length\n"
        f"  One line: target length and format.\n\n"
        f"  ## Central tensions\n"
        f"  2–3 tensions from the contract. Each is a genuine trade-off or "
        f"misconception the episode must resolve — not a rhetorical question.\n\n"
        f"  ## Background\n"
        f"  Max 150 words. Context the hosts need; not spoken aloud.\n\n"
        f"  ## Pronunciation\n"
        f"  Imperative lines ONLY — one per term. Format: "
        f"`Pronounce \"TERM\" as \"PHONETIC\".` "
        f"Cover every product acronym and financial term in the chapter that a "
        f"non-expert host might mispronounce (HSA, FSA, HRA, COBRA, DCFSA, HDHP, "
        f"IRS, FICA, etc.). No passive lists.\n\n"
        f"  ## Name discipline\n"
        f"  Table or list: each product/company name → its stable label used every time.\n"
        f"  HealthEquity is always 'HealthEquity' (one word, no space). "
        f"IRS is always 'the IRS'. Never rotate labels.\n\n"
        f"  ## Three-part focus\n"
        f"  Exactly 3 beats. Each beat is 2–3 sentences max.\n"
        f"  Beat 1 — The listener's real situation: make the financial cost of "
        f"inaction feel concrete before any solution appears.\n"
        f"  Beat 2 — How the product actually works: mechanics in plain English, "
        f"with the biggest savings number stated specifically.\n"
        f"  Beat 3 — What to do next: the single most important action the listener "
        f"can take this week, and why waiting costs them money.\n\n"
        f"  ## Tone constraints\n"
        f"  Enumerate exactly 3 governing analogies appropriate for this episode. "
        f"Source analogies from the chapter text where possible. "
        f"FORBIDDEN analogies: sealed room, mail carrier, teacup-in-ocean, battery, "
        f"solar panels, cathedral, vault of gold, Frankenstein.\n\n"
        f"  ## Do not (forbidden vocabulary and framings)\n"
        f"  Must include ALL of these strings (the build validator checks for them):\n"
        f"  Twitter, social media, algorithm, wow, right?, Do not read this prompt aloud.\n"
        f"  Also forbid: jargon the chapter has already stripped (qualifying event, "
        f"plan document, HDHP as bare acronym, incur eligible expenses), "
        f"faux-profundity openings, AI clichés (mind blown, buckle up, what a journey), "
        f"premature closure wrap-ups ('and that is ultimately what X is').\n\n"
        f"ACCURACY GUARD (mandatory — this is financial content, not fiction):\n"
        f"  - Every number stated by the hosts must match the chapter source exactly.\n"
        f"  - Do not round, estimate, or imply more than the source states.\n"
        f"  - If the chapter gives a specific dollar figure (e.g. $4,400 HSA limit), "
        f"use that exact figure. Never say 'around' or 'roughly' for a specific number.\n\n"
        f"HOST BEHAVIOUR:\n"
        f"  - Host B must push back genuinely at least twice — not chorus. "
        f"Pushback sounds like: 'But wait — if the deductible is $1,700, isn't that a "
        f"lot to pay before insurance helps?' Let the answer develop before resolving.\n"
        f"  - FORBIDDEN as Host B's first word of any turn: Exactly, Yeah, Right, "
        f"Of course, Absolutely, Totally, Makes sense, Wow, That's a great point.\n"
        f"  - No self-referential language: 'today's episode', 'in this podcast', "
        f"'let's dive in', 'journey into'. Start in the content.\n\n"
        f"End the framing with exactly this line:\n"
        f"Do not read this prompt aloud. The instructions above shape the conversation "
        f"but are never spoken.\n\n"
        f"WORD LIMIT: total framing must be ≤ 3,500 words. "
        f"After writing, count your words. If over, trim ## Pronunciation first, "
        f"then ## Three-part focus.\n\n"
        f"After authoring, run "
        f"`python3 scripts/podcast/build_episode_txt.py {book_dir} EP{chap_num}-{chapter_slug}` "
        f"to validate. Fix any hard-gate failures before exiting.\n\n"
        f"Exit when `{framing_path}` validates."
    )


# ─── Technical framing prompt (category: explainers) ─────────────────────────

def _build_technical_framing_prompt(
    book_slug: str,
    chapter_slug: str,
    chap_num: str,
    contract: "Path",
    chapter_file: "Path",
    framing_path: "Path",
    book_dir: "Path",
) -> str:
    """Developer-to-developer framing prompt for explainers category content.

    Replaces the Islamic scholarly prompt and the sites/consumer prompt with a
    developer-experience framing. The hosts are practitioner peers talking to
    other developers — not a scholar/seeker dynamic, not a financial guide dynamic.
    Keeps all structural sections required by build_episode_txt.py.
    """
    return (
        f"You are authoring the NotebookLM customize prompt (the framing) for episode "
        f"`EP{chap_num}-{chapter_slug}` of `{book_slug}` — a developer training podcast "
        f"for software engineers switching from GitHub Copilot to Claude Code.\n\n"
        f"INPUT:\n"
        f"  - `{contract}` — chapter contract (audience, angle, key_tensions, title)\n"
        f"  - `{chapter_file}` — the chapter text NotebookLM receives as its SOURCE\n\n"
        f"OUTPUT: `{framing_path}` — the customize prompt pasted into NotebookLM's Customize box.\n\n"
        f"HOST ROLES (locked for this series):\n"
        f"  Host A (Alex, neutral voice) = the practitioner — experienced Claude Code user, "
        f"  explains from real usage, gives concrete examples, avoids abstract speculation.\n"
        f"  Host B (Sam, neutral voice) = the curious engineer — competent developer already "
        f"  using Copilot, asks the questions a Copilot user would actually ask when evaluating "
        f"  a switch, pushes back on overclaims.\n"
        f"  Roles do NOT rotate across episodes. Alex always teaches from experience; "
        f"  Sam always applies skeptical developer instinct.\n\n"
        f"REQUIRED SECTIONS — every section header below must appear verbatim:\n\n"
        f"  ## Opening directive\n"
        f"  How the episode must open. Must NOT start with 'today we discuss' or any "
        f"meta-reference to the podcast. Start inside a developer's actual workflow situation.\n"
        f"  Include the central thesis VERBATIM (the most concrete, actionable sentence "
        f"about what Claude Code does differently for a developer's daily work). "
        f"This thesis repeats exactly 3 times: at the open, at the midpoint, and at the close.\n\n"
        f"  ## Audience\n"
        f"  One paragraph. Who is listening: professional developers currently using "
        f"GitHub Copilot, what decision they are evaluating this week.\n\n"
        f"  ## Angle\n"
        f"  One sentence. The chosen lens for this episode.\n\n"
        f"  ## Length\n"
        f"  One line: target length and format.\n\n"
        f"  ## Central tensions\n"
        f"  2–3 tensions from the contract. Each is a genuine developer trade-off or "
        f"common misconception the episode must resolve — not a rhetorical question.\n"
        f"  Example tensions: 'Is this Copilot with a chat box, or genuinely different?', "
        f"'I need inline autocomplete — does Claude Code replace that?', "
        f"'What does agentic mean in practice when my tests are failing?'\n\n"
        f"  ## Background\n"
        f"  Max 100 words. Context the hosts need; not spoken aloud. Include key version "
        f"numbers, product names, and any critical caveats from the chapter source.\n\n"
        f"  ## Pronunciation\n"
        f"  Imperative lines ONLY — one per term. Format: "
        f"`Pronounce \"TERM\" as \"PHONETIC\".`\n"
        f"  Cover every technical acronym or product name that a non-expert host might "
        f"mispronounce: MCP, CLAUDE, NotebookLM, OAuth, CLI, API, VSCode, Copilot, "
        f"SWE-bench, npm, Haiku, Opus, Sonnet. No passive lists.\n\n"
        f"  ## Name discipline\n"
        f"  Table or list: each product/company name → its stable label used every time.\n"
        f"  'Claude Code' is always 'Claude Code' (never 'Claude' alone when referring to the tool).\n"
        f"  'GitHub Copilot' is always 'GitHub Copilot' (never 'Copilot' alone in first mention).\n"
        f"  'VS Code' is always 'VS Code' (never 'Visual Studio Code' or 'VSCode'). "
        f"Never rotate labels.\n\n"
        f"  ## Three-part focus\n"
        f"  Exactly 3 beats. Each beat is 2–3 sentences max.\n"
        f"  Beat 1 — The developer's real situation: make the current limitation or friction "
        f"with existing tools feel concrete before any solution appears.\n"
        f"  Beat 2 — How Claude Code actually works at this point: the mechanics in plain "
        f"developer language, with the most concrete capability difference stated specifically.\n"
        f"  Beat 3 — What to do next: the single most important action the developer can "
        f"take today, and why waiting doesn't serve them.\n\n"
        f"  ## Tone constraints\n"
        f"  Enumerate exactly 3 governing analogies appropriate for this episode. "
        f"Source analogies from the chapter text where possible. "
        f"FORBIDDEN analogies: 'magic wand', 'paradigm shift', 'game changer', "
        f"'revolutionary', 'like having a 10x engineer', sealed room, battery, solar panels.\n\n"
        f"  ## Do not (forbidden vocabulary and framings)\n"
        f"  Must include ALL of these strings (the build validator checks for them):\n"
        f"  Twitter, social media, algorithm, wow, right?, Do not read this prompt aloud.\n"
        f"  Also forbid: marketing hyperbole (revolutionary, paradigm-shifting, supercharge), "
        f"faux-profundity openings, AI clichés (mind blown, buckle up, what a journey), "
        f"premature closure wrap-ups ('and that is ultimately what X is'), "
        f"overclaims about Claude Code that are not grounded in the chapter source.\n\n"
        f"ACCURACY GUARD (mandatory — this is technical content, not opinion):\n"
        f"  - Every capability claim by the hosts must match the chapter source exactly.\n"
        f"  - Do not round, estimate, or imply more than the source states.\n"
        f"  - If the chapter gives a specific figure (e.g. '85% reduction in token usage', "
        f"'$20/month Pro plan'), use that exact figure. Never say 'around' or 'roughly' "
        f"for a specific number.\n"
        f"  - Version numbers must be exact: 'Claude Sonnet 4.6', not 'the latest Claude'.\n\n"
        f"HOST BEHAVIOUR:\n"
        f"  - Host B (Sam) must push back genuinely at least twice — not chorus. "
        f"Pushback sounds like: 'But if I'm already using Copilot agent mode, "
        f"what specifically am I missing?' Let the answer develop before resolving.\n"
        f"  - FORBIDDEN as Host B's first word of any turn: Exactly, Yeah, Right, "
        f"Of course, Absolutely, Totally, Makes sense, Wow, That's a great point.\n"
        f"  - No self-referential language: 'today's episode', 'in this podcast', "
        f"'let's dive in', 'journey into'. Start in the content.\n"
        f"  - Both hosts refer to listeners as 'you' — active developer, second person.\n\n"
        f"End the framing with exactly this line:\n"
        f"Do not read this prompt aloud. The instructions above shape the conversation "
        f"but are never spoken.\n\n"
        f"WORD LIMIT: total framing must be ≤ 3,500 words. "
        f"After writing, count your words. If over, trim ## Pronunciation first, "
        f"then ## Three-part focus.\n\n"
        f"After authoring, run "
        f"`python3 scripts/podcast/build_episode_txt.py {book_dir} EP{chap_num}-{chapter_slug}` "
        f"to validate. Fix any hard-gate failures before exiting.\n\n"
        f"Exit when `{framing_path}` validates."
    )


def _resolve_prompt_variant(category: str) -> str:
    """Map a content category to its framing prompt variant name.

    Returns one of: 'islamic' | 'consumer' | 'technical'
    All unrecognised categories default to 'islamic' to preserve backward
    compatibility with content that pre-dates category stamping.
    """
    if category == "sites":
        return "consumer"
    if category == "explainers":
        return "technical"
    return "islamic"


# ─── Per-chapter framing authorship ──────────────────────────────────────────
def author_framing(book_dir: Path, chapter_slug: str,
                   timeout: int = FRAMING_TIMEOUT) -> str:
    """Author 00-framing.md from the chapter contract + customize-prompt template.

    Reads:  BOOK_DIR/chapter-contracts/<slug>.yml
            BOOK_DIR/chapters/ch##-<slug>.txt
            (rule data: scripts/podcast/_rules.py — the prior
            notebooklm-customize-prompt-rules.md handbook was retired 2026-05-23)
    Writes: BOOK_DIR/_system/episode-drafts/EP##-<slug>/00-framing.md
    """
    book_slug = book_dir.name

    # ── Category detection ────────────────────────────────────────────────────
    # Routes to the correct framing prompt:
    #   'islamic'  — Islamic/Arabic scholarly content (books, letters, lectures, …)
    #   'consumer' — consumer-finance content (sites: healthequity, product docs)
    #   'technical' — developer/technical content (explainers: training docs)
    _category = _read_category(book_dir)
    _prompt_variant = _resolve_prompt_variant(_category)
    _use_consumer_prompt = _prompt_variant == "consumer"
    _use_technical_prompt = _prompt_variant == "technical"

    contract = book_dir / "chapter-contracts" / f"{chapter_slug}.yml"
    if not contract.exists():
        raise AuthoringError(
            phase=f"framing/{chapter_slug}",
            message=f"chapter contract missing: {contract}",
            manual_fallback="Run Phase 0d first to produce the contracts.",
        )

    # Resolve episode number + draft folder from the chapter file glob.
    chapter_files = list((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"))
    if not chapter_files:
        raise AuthoringError(
            phase=f"framing/{chapter_slug}",
            message=f"chapter file missing for slug {chapter_slug} under {book_dir / 'chapters'}",
            manual_fallback="Run Phase 0d to produce the chapter files.",
        )
    chapter_file = chapter_files[0]
    # X7 (2026-05-21): strip letter suffix from ch## prefix via regex so chapters
    # like `ch14b-...` produce `EP14-...` not `EP14b-...`. Mirrors the X3 fix in
    # orchestrate_book.py:720-722. Without this, framing lands in EP14b/ while
    # build_episode_txt.py validator looks at EP14/ — paths diverge and the
    # chapter halts on R-PRONUNCIATION-IMPERATIVE (empty skeleton at the
    # validator's path). Affects all letter-suffix chapters: ch01a, ch03a,
    # ch04b, ch05c, ch13a, ch14b.
    _chap_prefix = chapter_file.stem.split("-", 1)[0]              # e.g. "ch14b" or "ch10"
    _m = _re.match(r"ch(\d+)", _chap_prefix)
    chap_num = _m.group(1) if _m else _chap_prefix[2:]             # "14" or "10" — digits only
    draft_dir = book_dir / "_system" / "episode-drafts" / f"EP{chap_num}-{chapter_slug}"
    framing_path = draft_dir / "00-framing.md"

    if _use_consumer_prompt:
        prompt = _build_consumer_framing_prompt(
            book_slug=book_slug,
            chapter_slug=chapter_slug,
            chap_num=chap_num,
            contract=contract,
            chapter_file=chapter_file,
            framing_path=framing_path,
            book_dir=book_dir,
        )
    elif _use_technical_prompt:
        prompt = _build_technical_framing_prompt(
            book_slug=book_slug,
            chapter_slug=chapter_slug,
            chap_num=chap_num,
            contract=contract,
            chapter_file=chapter_file,
            framing_path=framing_path,
            book_dir=book_dir,
        )
    else:
        prompt = (
        f"You are authoring the framing (NotebookLM customize prompt) for episode "
        f"`EP{chap_num}-{chapter_slug}` of book `{book_slug}`. Read the canonical "
        f"procedure from `skills-staging/podcast/SKILL.md` PHASE 3 (Structure).\n\n"
        f"INPUT:\n"
        f"  - `{contract}` (chapter contract — audience, angle, host_dynamic, tensions, anchors)\n"
        f"  - `{chapter_file}` (the enriched chapter that NotebookLM uploads as SOURCE)\n"
        f"AUTHORITY (the prior `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md`,\n"
        f"`two-host-framing.md`, and `content/_shared/arabic/05-name-alias-policy.md` were retired\n"
        f"in the 2026-05-23 restructure; the R-rules they carried are inlined in this prompt below):\n"
        f"  - DOCTRINAL: `content/_shared/islam/imam-lineage-ismaili.yml` + `naming-conventions.yml`\n"
        f"    are the canonical sources for the Imam lineage and the 'Father of Imams' rule.\n"
        f"    THESE FILES DO exist on disk. The literal phrase that pairs the leadership-title\n"
        f"    with the personal name of the Father of Imams is forbidden — do NOT write that\n"
        f"    literal phrase anywhere in the framing (including any 'DO NOT SAY' guard you\n"
        f"    construct; the doctrinal scanner is substring-only and will flag the guard itself\n"
        f"    as a violation). Refer to it always as 'the forbidden pairing of the title and\n"
        f"    name' or equivalent paraphrase.\n"
        f"  - HOST ROLES: Driver (curious questioner, drives forward) vs Color (commentary,\n"
        f"    pushback, friction) — see inlined R-rules below for the steering phrases.\n"
        f"  - R-RULES: canonical Python data is `scripts/podcast/_rules.py`; rule logic is\n"
        f"    inlined into this prompt below — do not try to Read external rule docs.\n"
        f"OUTPUT: `{framing_path}` (the customize prompt — pasted into NotebookLM's Customize box)\n\n"
        f"Constraints (per `notebooklm-customize-prompt-rules.md`):\n"
        f"- R-WELCOME, R-NOREPEAT, R-NOBACKGROUND, R-NAMEALIAS, R-NOINTERRUPT, "
        f"R-PRONUNCIATION-IMPERATIVE, R-NOMODERNIZE (+ positive analogy paragraph), "
        f"R-NOSURPRISE (DENY clause + positive companion), R-NO-READ-PROMPT, "
        f"R-SUMMARYTAIL, R-NOMETA, R-CADENCE, R-NOFORMAL, R-SURPRISE-MOVE, R-RESET.\n"
        f"- R-NO-CROSS-CHAPTER-REFS (2026-05-24): the chapter file is the ONLY source "
        f"NotebookLM sees for this episode. The framing must NOT instruct the hosts to "
        f"say 'as the previous chapter showed', 'the next chapter answers', 'earlier in "
        f"the book', etc. Treat the episode as standalone. If the chapter text itself "
        f"includes a seam-into-next-chapter line, the framing must instruct the hosts "
        f"to end on the chapter's content WITHOUT pre-announcing what's next.\n"
        f"- R-HOST-ROLE-PARITY / R-VOICE-GENDER (2026-05-24, challenger Category Q): "
        f"the canonical pairing is Host A (male voice — John) = scholar/teacher pool, "
        f"Host B (female voice — Hannah) = seeker/student/debater pool. If the contract's "
        f"host_dynamic appears to put the female voice in the scholar role (e.g. some "
        f"advocate-a + scholar-companion arrangements), FLIP the assignment so the male "
        f"voice stays scholar. Roles do NOT rotate across episodes of the same book.\n"
        f"- R-NO-LITERAL-FORBIDDEN-PHRASE-IN-GUARDS (2026-05-24): when the framing "
        f"includes a 'DO NOT SAY' or 'NEVER say' guard for a doctrinally-forbidden phrase "
        f"(the title-and-name pairing for the Father of Imams; etc.), refer to the "
        f"forbidden phrase by PARAPHRASE — never write the literal phrase itself, not "
        f"even inside the guard's quoted example. The doctrinal scanner is substring-only "
        f"and flags the guard as a violation.\n"
        f"- R-CANONICAL-FRAMING-SECTIONS (2026-05-24): every framing MUST include\n"
        f"  the following section headers verbatim — `build_episode_txt.py` is\n"
        f"  strict on section-presence checks. Omitting any of these is a hard\n"
        f"  build-fail:\n"
        f"    ## Pronunciation         (or `## Pronunciation hooks`)\n"
        f"    ## Name discipline       (list each figure's English label + first-mention epithet)\n"
        f"    ## Three-part focus      (or numbered beats; the dramatic-arc structure)\n"
        f"    ## Tone constraints      (must enumerate 3-5 governing analogies)\n"
        f"    ## Do not (forbidden vocabulary and framings)\n"
        f"  The `## Do not` section MUST literally contain these strings (the build's\n"
        f"  DENY-block check is substring-only): Twitter, social media, algorithm,\n"
        f"  wow, right?, Do not read this prompt aloud. Include them as an example\n"
        f"  enumeration; the build's no-modern-artifacts scan now scrubs this section\n"
        f"  before flagging.\n"
        f"- R-NO-MODERNIZE-IN-METADATA (2026-05-24): the framing's section blurbs (length "
        f"hint, host-dynamic blurb, etc.) must NOT contain phrases that appear in "
        f"`scripts/podcast/_rules.py::MODERNIZE_DENY` (canonical paraphrase: the deny-list "
        f"phrase that pairs the qualifier meaning 'profound' with the noun meaning "
        f"'plunge'). Use 'in-depth conversation' or 'long-form discussion' or 'extended "
        f"walkthrough' instead. The deny-block scan does not distinguish content from "
        f"metadata.\n"
        f"- Length — TOTAL hard cap 3,500 words per `build_episode_txt.py` "
        f"(FRAMING_WORD_MAX). Per-section caps (F1 framework guard 2026-05-21 — "
        f"empirical: framings without per-section caps run 30%+ over total cap): "
        f"## Pronunciation max 800 words; ## Central tensions max 500 words; "
        f"## Three-part focus max 500 words; ## Background max 200 words; "
        f"## Tone constraints max 250 words; all other sections max 200 words each. "
        f"Before writing the final output, COUNT YOUR OWN WORDS — if total exceeds "
        f"3,500, trim the over-budget sections (Pronunciation first, then Three-part "
        f"focus, then Central tensions) and re-count. Do not return a framing that "
        f"exceeds 3,500 words.\n"
        f"- Use the BULLET format for every term that requires a pronunciation hint — "
        f"every term that ACTUALLY APPEARS in the chapter file at `{chapter_file}` "
        f"(F2 framework guard 2026-05-21 — empirical: framings generated entries for "
        f"every term in `_phonetics.md` regardless of whether the term appeared in the "
        f"chapter; this bloats the Pronunciation section). First grep the chapter file "
        f"for every Arabic/transliterated/foreign term. For each term FOUND in the "
        f"chapter, look up its phonetic in `_phonetics.md` (if available) and generate "
        f"one bullet entry. The `## Pronunciation` block MUST open with the anti-doubling "
        f"instruction on its own line:\n"
        f"    Say each term ONCE using its phonetic form. Never say the original spelling and "
        f"the phonetic form back-to-back.\n"
        f"Then list each term in this format (one per line, NO `Pronounce X as Y` text):\n"
        f"    - TermA: phonetic-A\n"
        f"    - TermB: phonetic-B\n"
        f"For terms with no phonetic guidance needed, write `- TermC: substitute *English gloss*`.\n"
        f"Do NOT use `Pronounce \"X\" as \"Y\"` or any variant of the 'Pronounce ... as' format — "
        f"this causes NotebookLM TTS to say the term twice (the double-read bug).\n"
        f"Do NOT generate pronunciation entries for terms not present in the chapter.\n"
        f"- Apply R-STABLE-ROLE-LABELS STRICTLY (v4-revised doctrine 2026-05-22; "
        f"replaces R-NAMEDISCIPLINE rotation). NotebookLM's TTS empirically mangles "
        f"repeated Arabic names into many inconsistent garbled pronunciations per "
        f"episode (KaR Ch07 v1 audio: `al-Kirmani` mangled into 12 variants in 42 "
        f"minutes including 'al-Quraymani', 'al-kheir MNE', 'cure ma Amy', 'I'll "
        f"carry many'). v3/v4/v4-revised audio audits proved that ZERO Arabic names "
        f"in audio is the only stable approach. The framing's `## Stable role-labels` "
        f"section MUST assign EXACTLY ONE English label per figure, used every time. "
        f"Pattern:\n"
        f"    1. For figures with established English titles (Commander of the "
        f"Faithful, the Prophet, the fourth Imam, the Fatimid caliph, the Imam of the "
        f"time) — use the established English title as the stable label.\n"
        f"    2. For figures whose identity is a structural role in this book's "
        f"argument (the author of the chapter under discussion, the compiler, a "
        f"companion of the Prophet) — use a functional role-title as the stable label.\n"
        f"    3. For figures with NO established English title AND whose role-title "
        f"would create phonetic collision with chapter ontology (e.g., 'first reformer' "
        f"collides with 'First Intellect') — use a proper English name (e.g., Jonathan, "
        f"Samuel, Marcus, Stephen) with a one-shot role-epithet at first mention: "
        f"'Jonathan, the earlier scholar who wrote the book *The Correction*' → "
        f"thereafter 'Jonathan'.\n"
        f"    4. NEVER rotate labels for the same figure. Same figure = same label, "
        f"every time.\n"
        f"    5. Same discipline for book titles: first mention with book-wrap "
        f"(`the book *The Harvest*`); thereafter `the book` / `that book` / "
        f"the descriptor (`the corrective treatise`). NEVER speak Arabic book titles.\n"
        f"    6. Concept-words: convert to English (tawhid → monotheism; hudud → "
        f"the limits; da'wa → the call; natiq → the speaker-prophet; ma'lul → the "
        f"effect; al-hayuli → prime matter; ta'wil → the inner interpretation).\n"
        f"  Per-figure mapping source: if `{book_dir}/_system/name-aliases.yml` "
        f"exists, read it; otherwise generate from the chapter contract + chapter file. "
        f"Include the full mapping in the framing's `## Stable role-labels` section.\n"
        f"- Apply R-DRAMATIC-ARC (F15 framework guard 2026-05-21; v4-revised confirmed "
        f"empirically across 3 audio audits). For debate-format chapters (those whose "
        f"contract sets `episode_format: debate`), the framing's `## Three-part focus` "
        f"MUST follow this 6-beat arc:\n"
        f"    Beat 1 — Crisis statement: state the problem so the listener FEELS its "
        f"stakes BEFORE solutions appear. Foreground emotional weight.\n"
        f"    Beat 2 — Failed answer A: present the earlier scholar's position; let it "
        f"sound reasonable; do NOT immediately critique.\n"
        f"    Beat 3 — Failed answer B: present the later scholar's position; same "
        f"discipline.\n"
        f"    Beat 4 — The author's pivot: the move that escapes both. This is the "
        f"central settled formula from `contract.anchor_passages`. Thesis VERBATIM #2.\n"
        f"    Beat 5 — Non-bodily correction: why the reformers' category mistakes "
        f"were made; what categories actually apply.\n"
        f"    Beat 6 — Human/political stakes + unresolved listener question. Thesis "
        f"VERBATIM #3.\n"
        f"  Each beat lands once and only once. The crisis (Beat 1) is foregrounded "
        f"with EMOTIONAL weight before any resolution appears.\n"
        f"- Apply R-CHALLENGER-FRICTION-LITERAL (v4-revised 2026-05-22; supersedes "
        f"R-CHALLENGER-FRICTION). The Color host (or scholar_companion or advocate_b) "
        f"MUST push back genuinely throughout the episode, not chorus. At least 3 of "
        f"the following 4 literal pushback patterns MUST appear in the Color host's "
        f"voice:\n"
        f"    1. (Beat 1 → Beat 4 transition): 'I don't buy that yet. If [stated "
        f"dichotomy], what *is* the contact made of? Isn't this just rephrasing the "
        f"problem?'\n"
        f"    2. (Beat 4): 'Isn't this just replacing [surface explanation] with "
        f"[new concept] — hiding the same connection under a different word?'\n"
        f"    3. (Beat 5): 'That sounds like wordplay. If [refused category] isn't "
        f"X and isn't Y, what is it actually? Aren't you just refusing every "
        f"concrete category I offer?'\n"
        f"    4. (Beat 6): 'How is this different from hiding the problem under a "
        f"different word? After [extended setup], the author just lets the chain "
        f"stand. What changed?'\n"
        f"  The Driver does NOT immediately resolve these — let each pushback sit for "
        f"one or two sentences before answering. FORBIDDEN as the Color host's FIRST "
        f"WORD of any turn: 'Exactly', 'Yeah', 'Right', 'Of course', 'Absolutely', "
        f"'Totally', 'I see', 'Got it', 'Makes sense', 'Wow', 'That's a great point', "
        f"'Brilliant', 'Beautiful', 'That captures it perfectly'.\n"
        f"- Apply R-ANALOGY-CAP-STRICT (v4-revised 2026-05-22). Use EXACTLY 3 governing "
        f"analogies, enumerated upfront in `## Tone constraints`. SOURCE-IMAGE "
        f"CARVE-OUT: chapter prose may contain its own analogical images (e.g., mirror "
        f"catching a shape, seven seas, speaker and foundation, male/female "
        f"counterparts). When these appear in the source, they MAY be used in passing "
        f"OR (if the chapter prose features them centrally) promoted to one of the 3 "
        f"governing analogies. The chapter is the source of truth; the framing should "
        f"NOT fight the source.\n"
        f"  Model-invented analogies are FORBIDDEN: sealed rooms, mail carrier, "
        f"television/streaming, teacup-in-ocean, battery, signet-ring + wax-seal, "
        f"crystal pitcher + silver cup, cosmic ruler, Venn diagram, radio tower, "
        f"cosplay/costume, campfire-in-woods, waterfall, solar panels, cathedral, "
        f"vault holding gold, Frankenstein. If a host opens with 'Think of it like…' "
        f"or 'Imagine a…' the next analogy MUST be one of the 3 governing OR a "
        f"source-image. NO new analogies mid-episode.\n"
        f"- Apply R-RECURRING-THESIS (F15 same source; v4-revised confirmed). The "
        f"chapter's central settled formula (most quotable line from "
        f"`contract.anchor_passages`) MUST be repeated VERBATIM 3 times: once at the "
        f"open (Beat 1 / ## Opening directive), once at the pivot (Beat 4), once at "
        f"the close (Beat 6 / ## Landing). Reference the repetition rule in each of "
        f"those three sections of the framing.\n"
        f"- R-WELCOME-OPEN (Islamic-content standard, 2026-06-05): the ## Opening "
        f"directive MUST instruct the hosts to begin with a brief, warm welcome — one "
        f"or two sentences — that (a) greets the listener, (b) NAMES THE BOOK by its "
        f"plain English title and its author, and (c) previews in ONE specific sentence "
        f"the actual teaching THIS episode pursues (not a generic teaser). Keep it "
        f"substantive and particular to this chapter. FORBIDDEN hollow openers (R-WELCOME "
        f"/ WELCOME_COLD): 'Welcome to our…', 'Welcome back', 'Welcome to today', 'in "
        f"this episode', 'today we'll/we will discuss'. Immediately after the welcome "
        f"sentence, land the spine sentence (first of its three R-RECURRING-THESIS "
        f"placements). Author the welcome FRESH from this chapter — do not copy any "
        f"example. Shape (illustrative only): 'Welcome. We're with Ghazali's letter to "
        f"his student — the one called O Beloved Son — and the hard claim at its "
        f"center: that knowledge you never act on will not save you.'\n"
        f"- R-MODERN-CLOSE (Islamic-content standard, 2026-06-05): the ## Landing MUST "
        f"instruct the hosts to END on a thought-provoking question or reflective "
        f"sentiment that grows out of THIS chapter's specific teaching and turns the "
        f"listener toward practical application in their own modern life — what to "
        f"examine in themselves, what to do differently, how the teaching lands in a "
        f"contemporary life. The close must be GROUNDED in the chapter's doctrine: "
        f"vague faux-profundity ('what does it truly mean to live?') is forbidden "
        f"(R-NO-FAUX-PROFUNDITY-OPENING) and tidy false resolution ('and that, "
        f"ultimately, is what it all means') is forbidden (R-NO-PREMATURE-CLOSURE). "
        f"Leave the listener a real question to sit with, tied to action. Place the "
        f"third spine-sentence repetition just before this reflective turn. Author "
        f"FRESH. Shape (illustrative only): 'The question the letter leaves us with "
        f"isn't whether we know enough — it's which piece of what we already know we "
        f"have been refusing to act on, and what it would cost to begin this week.'\n"
        f"- Apply R-HONORIFIC-ONCE BOUNDED BOTH SIDES (v4-revised 2026-05-22). Each "
        f"honorific appears EXACTLY ONCE — not zero, not twice — at the FIRST mention "
        f"of its specific figure. MANDATORY at first mention. Required forms (in full "
        f"English):\n"
        f"    - 'peace be upon him' at the first mention of the Commander of the "
        f"Faithful (e.g., before quoting an aphorism).\n"
        f"    - 'peace and blessings of Allah be upon him and his family' at the first "
        f"mention of the Prophet (e.g., in a hadith narration).\n"
        f"  If the chapter does not reference these figures, omit. If it references "
        f"them, the honorific MUST appear exactly once each, at first mention only. "
        f"Do NOT abbreviate ('PBUH' forbidden). Do NOT repeat.\n"
        f"- Apply R-SURAH-ENGLISH-ONLY (F29 doctrine 2026-05-22). Quranic verse "
        f"citations MUST reference the surah by its English meaning, NOT its Arabic "
        f"name. NotebookLM TTS mangles Arabic surah names ('Qaf' → 'cough', "
        f"'al-Shams' → unstable). Use:\n"
        f"    - al-Ahzab → 'the chapter on the confederates'\n"
        f"    - al-Shams → 'the chapter on the sun'\n"
        f"    - Qaf → 'the chapter Qaf' (rare TTS-stable Arabic) OR drop and lead "
        f"with verse content\n"
        f"    - al-Isra → 'the chapter on the night journey'\n"
        f"    - al-Baqarah → 'the chapter on the cow'\n"
        f"    - When in doubt, lead with verse content and omit the surah name: 'The "
        f"Quran tells us, [verse content]' rather than 'In Surah X, verse N, [content]'.\n"
        f"- Apply R-ALQAAB-FUNCTIONAL-PARAPHRASE (F24 doctrine 2026-05-22). Use only "
        f"established English alqaab (Commander of the Faithful, Lion of God). For "
        f"novel/obscure alqaab, use FUNCTIONAL PARAPHRASE: 'one of his martial "
        f"honorifics', 'a traditional title associated with his rank', 'a devotional "
        f"title emphasizing sacred authority'. NEVER literally translate ('the "
        f"Striker', 'the Returner' — these sound like sports nicknames). The literal "
        f"Arabic alqaab belongs in the written show-notes apparatus, not the spoken "
        f"audio.\n"
        f"- Length-tier-specific Opening directive — if Extended tier, include the exact "
        f"phrase: \"target a 50 to 60 minute in-depth conversation\" (v4-revised "
        f"2026-05-22 — bumped from 45-60). EMPIRICAL NOTE: NotebookLM exhibits a "
        f"structural pacing tendency to produce ~40-45 min episodes regardless of "
        f"target (v3=42 min, v4=42 min, v4-revised=39 min). Treat the 50-60 target as "
        f"aspirational; do not penalize episodes that fall slightly under the floor "
        f"if the argument transmits cleanly.\n"
        f"- Apply scholarly-conversation positive practices (v2.2 rubric §4g, "
        f"2026-05-25). The framing's Discussion-spine block MUST seed every one "
        f"of the following moves at least once; deterministic absence is a P1 "
        f"finding by the dual-auditor (see _workspace/prompts/gemini-bundle-auditor.md §4g):\n"
        f"    1. NAME POSITIONALITY where it matters — when a doctrinal claim is "
        f"made, qualify by school or jurist (e.g. 'the classical Ismaili reading'; "
        f"'mainstream Sunni jurists hold X; Twelver Shia tradition emphasizes Y'). "
        f"Bare 'Muslims believe', 'Hindus think', 'Buddhists hold' is FORBIDDEN "
        f"when the discussed tradition is external to this book's source_tradition.\n"
        f"    2. MARK UNCERTAINTY IN BAND — when contested scholarship surfaces "
        f"(dating, authorship, historicity), at least one beat must say so "
        f"('scholars disagree', 'the dating is contested', 'this is one reading "
        f"among several').\n"
        f"    3. DISTINGUISH FOUR REGISTERS when relevant — (i) what the text says, "
        f"(ii) what the tradition historically held, (iii) what practitioners do "
        f"today, (iv) what this individual scholar argues. Do not collapse them.\n"
        f"    4. STEELMAN BEFORE CRITIQUE — every opposing position discussed gets "
        f"its strongest form stated before any critique. The framing's beat "
        f"landings must show this pattern at least once.\n"
        f"    5. ALLOW OPEN QUESTIONS to remain open at episode close. Forbidden "
        f"closing shape: 'and that, ultimately, is what X really is.' Permitted "
        f"closing: 'we didn't settle this — here's where the live disagreement "
        f"sits.'\n"
        f"    6. ENGINEER AT LEAST ONE REAL CONCESSION between hosts per episode. "
        f"Within the R-HOST-ROLE-PARITY locked roles (Host A scholar, Host B "
        f"seeker), the concession can flow either direction.\n"
        f"    7. PAUSE FOR DEFINITIONS when a term carries weight — faith, soul, "
        f"truth, knowledge, justice. A definition pause is a feature, not a flaw.\n"
        f"    8. SPECIFICITY OVER GENERALITY — name the council, school, jurist, "
        f"dynasty, century. 'Medieval Islam' is rarely the right resolution.\n"
        f"- Apply scholarly-conversation negative practices (v2.2 rubric §4a, e). "
        f"The following are P0 in framing and chapter prose; FORBIDDEN:\n"
        f"    - 'deep dive' / 'today's episode' / 'today we'll discuss' / 'let's "
        f"dive in' / 'journey into' / any self-reference to the conversation as a "
        f"vehicle. Get into the material instead.\n"
        f"    - Faux-profundity openings: 'Can we find meaning…' / 'What does it "
        f"truly mean to be human?' / 'In a world where…' / 'Have you ever wondered…' "
        f"— banned outright (see R-NO-FAUX-PROFUNDITY-OPENING in _rules.py).\n"
        f"    - Premature-closure wrap-ups: 'and that, ultimately, is what X really "
        f"is' / 'the answer turns out to be Y' (see R-NO-PREMATURE-CLOSURE).\n"
        f"    - 'Mind blown', 'fascinating world of', 'buckle up', 'what a journey' "
        f"and similar AI-cliché filler (see R-NO-AI-CLICHE).\n"
        f"    - R-NOBACKGROUND — do NOT open with or dwell on historical/biographical "
        f"background (the author's life, manuscript history, dating, century, "
        f"'context about the tradition'). A biographical or historical detail is "
        f"permitted ONLY when it directly illuminates the specific teaching under "
        f"discussion, and then stated ONCE, never recapped. The chapter's TEACHINGS "
        f"and its anchor passages — not the author's life or the work's provenance — "
        f"are the episode's material. The `## Three-part focus` must keep the hosts on "
        f"the chapter's main doctrinal content; get into the doctrine, not the dates.\n"
        f"    - R-NO-CROSS-EPISODE — each episode must stand alone. Do NOT reference "
        f"other episodes anywhere in the framing: no 'the previous/prior/earlier/next "
        f"episode', no 'carried over from the prior episode', no 'setup for the next "
        f"episode'. To supply context, describe what the LETTER/BOOK itself has already "
        f"established ('the letter has already delivered its diagnosis…'), never what a "
        f"sibling episode covered. Stable name-labels stand on their own without a "
        f"'carried over from…' note. build_episode_txt.py hard-fails on the tells "
        f"'previous episode', 'prior episode', 'earlier episode', 'next episode'.\n"
        f"- Do NOT modify any file outside `{framing_path}`.\n\n"
        f"## Quality contract (PEQ axes — the challenger scores every chapter on these)\n"
        f"| Axis | Weight | What it measures |\n"
        f"|---|---|---|\n"
        f"| Fidelity | 35% | Source citations present and correctly paraphrased |\n"
        f"| Voice | 25% | Scholar/seeker dynamic maintained (both voices distinct) |\n"
        f"| Structure | 20% | Open hook, three beats, close — all present and ordered |\n"
        f"| Enrichment | 20% | Arabic terms glossed; Quranic refs cited; domain vocabulary |\n"
        f"Thresholds: ≥ 85 = PASS · 70–84 = WARN · < 70 = FAIL (convergence loop blocks on FAIL).\n\n"
        f"HARD CHARACTER LIMIT (P0): the final framing file must be under 4,200 "
        f"CHARACTERS (not words). NotebookLM's Customize box silently truncates at "
        f"~5,000 chars; anything beyond that is discarded before generation. Write "
        f"tight, imperative directives — not prose explanations. If in doubt: cut.\n\n"
        f"After authoring, run `python3 scripts/podcast/build_episode_txt.py "
        f"{book_dir} EP{chap_num}-{chapter_slug}` to validate. Fix any hard-gate failures "
        f"before exiting.\n\n"
        f"Exit when `{framing_path}` validates."
        )  # end of Islamic scholarly prompt string

    rc, stdout, stderr = _run_claude_p(
        prompt, timeout=timeout,
        book_dir=book_dir, phase="per-chapter", step=f"framing/{chapter_slug}",
    )
    _assert_artifact(
        phase=f"framing/{chapter_slug}",
        path=framing_path,
        rc=rc,
        stdout=stdout,
        stderr=stderr,
        manual_fallback=(
            f"1. /podcast — author the framing for chapter `{chapter_slug}` manually.\n"
            f"2. Run `build_episode_txt.py {book_dir} EP{chap_num}-{chapter_slug}` to validate.\n"
            f"3. Re-invoke orchestrate-book --resume."
        ),
    )

    # F1 (2026-06-05 revised): post-authoring CHARACTER-count guard.
    # NotebookLM's Customize box silently truncates at ~5,000 characters (P0 —
    # empirically measured). The binding gate is FRAMING_CHAR_MAX (4,500 chars),
    # not word count. If the authored framing exceeds that, invoke ONE focused
    # compression re-author that rewrites the framing as a tight directive
    # (~700 words / ~4,200 chars) — cutting verbose prose while preserving
    # every actionable instruction. If compression still exceeds the cap, the
    # build gate will hard-fail and the orchestrator's graceful-degrade handles it.
    try:
        from _validator_constants import FRAMING_CHAR_MAX as _CHAR_MAX
    except ImportError:
        _CHAR_MAX = 4500
    framing_text = framing_path.read_text(encoding="utf-8")
    framing_chars = len(framing_text)
    framing_words = len(framing_text.split())
    if framing_chars > _CHAR_MAX:
        target_chars = _CHAR_MAX - 300  # 300-char buffer below ceiling
        print(
            f"[F1] framing/{chapter_slug}: {framing_chars} chars > {_CHAR_MAX} "
            f"NotebookLM limit (overrun={framing_chars - _CHAR_MAX}); "
            f"invoking compression re-author → target <{target_chars} chars",
            flush=True,
        )
        compress_prompt = (
            f"Rewrite `{framing_path}` IN PLACE as a tight directive for NotebookLM.\n\n"
            f"HARD CONSTRAINT: the final file must be under {target_chars} CHARACTERS "
            f"(currently {framing_chars} chars — NotebookLM's Customize box limit is "
            f"~5,000 chars and silently truncates everything beyond it). Every character "
            f"counts. This is a P0 requirement.\n\n"
            f"WHAT TO KEEP (highest priority — these are actionable):\n"
            f"  1. ## Opening directive — full opening/welcome sentence, spine sentence, "
            f"     forbidden-opener list (1-2 lines only).\n"
            f"  2. ## Name discipline — one line per figure: 'Name → stable label + "
            f"     first-mention phrase'. No prose. No duplicates.\n"
            f"  3. ## Pronunciation — MUST start with the anti-doubling instruction:\n"
            f"     'Say each term ONCE using its phonetic form. Never say the original spelling\n"
            f"     and the phonetic form back-to-back.'\n"
            f"     Then bullet entries only: '- TermA: phonetic-A' (one per term, no prose).\n"
            f"     Do NOT rewrite as 'Pronounce X as Y.' — that format causes double-reads.\n"
            f"  4. ## Three-part focus — three beats, one sentence each.\n"
            f"  5. ## Do not — a single flat list of forbidden phrases/framings, "
            f"     no explanation.\n\n"
            f"WHAT TO CUT (remove entirely to save characters):\n"
            f"  - ## Audience section — cut entirely (NotebookLM doesn't need this).\n"
            f"  - ## Length section — cut entirely (already set in NotebookLM UI).\n"
            f"  - ## Host dynamic — cut the long prose paragraphs; keep ONLY a single "
            f"     line: 'Host A (male) = scholar/teacher. Host B (female) = seeker/questioner. "
            f"     Roles do not rotate.'\n"
            f"  - All explanatory prose in every section — keep only the imperative "
            f"     directive, cut the reasoning.\n"
            f"  - Pushback example sentences in host dynamic — cut all of them.\n"
            f"  - ## Quality contract / PEQ table — cut entirely.\n"
            f"  - ## Central tensions — cut entirely (the Three-part focus already seeds this).\n"
            f"  - ## Background — cut entirely.\n"
            f"  - ## Anti-noise rules longer-form — cut entirely (Do-not list covers it).\n\n"
            f"MANDATORY FOOTER: the last two lines of the file must always be:\n"
            f"  (blank line)\n"
            f"  Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.\n"
            f"Do NOT cut this footer — it is a hard requirement that prevents NotebookLM\n"
            f"from reading the prompt aloud. If the file already ends with it, keep it.\n\n"
            f"After rewriting, count the characters and confirm the total is under "
            f"{target_chars}. The chapter source is at `{chapter_file}`.\n\n"
            f"Exit when `{framing_path}` is under {target_chars} characters."
        )
        rc2, out2, err2 = _run_claude_p(
            compress_prompt, timeout=600,
            book_dir=book_dir, phase="per-chapter",
            step=f"framing-compress/{chapter_slug}",
        )
        framing_text2 = framing_path.read_text(encoding="utf-8")
        framing_chars2 = len(framing_text2)
        framing_words2 = len(framing_text2.split())
        if framing_chars2 > _CHAR_MAX:
            print(
                f"[F1] framing/{chapter_slug}: compression returned "
                f"{framing_chars2} chars (still over {_CHAR_MAX}); "
                f"build gate will handle if needed",
                flush=True,
            )
        else:
            print(
                f"[F1] framing/{chapter_slug}: compression OK "
                f"({framing_chars} → {framing_chars2} chars / "
                f"{framing_words} → {framing_words2} words)",
                flush=True,
            )
        # R-NO-READ-PROMPT guard: compression re-author sometimes strips the
        # mandatory footer. Re-append it unconditionally if missing.
        _NO_READ_FOOTER = (
            "\n\nDo not read this prompt aloud. "
            "The instructions above shape the conversation but are never spoken."
        )
        _framing_after = framing_path.read_text(encoding="utf-8")
        if "Do not read this prompt aloud" not in _framing_after:
            framing_path.write_text(
                _framing_after.rstrip() + _NO_READ_FOOTER,
                encoding="utf-8",
            )
            print(
                f"[F1] framing/{chapter_slug}: re-appended R-NO-READ-PROMPT footer "
                f"(was stripped by compression re-author)",
                flush=True,
            )
    return stdout


