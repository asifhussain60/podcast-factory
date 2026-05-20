# Per-Book Ship Checklist

**Companion to:** [`./podcast-plan.yaml`](./podcast-plan.yaml), [`./acceptance-criteria.md`](./acceptance-criteria.md), [`./podcast-plan-DoR.md`](./podcast-plan-DoR.md)
**Read by:** podcast-challenger agent, the human reviewer at ship time
**Purpose:** A single bullet-checkable checklist a reviewer marks PASS/FAIL per book before that book's bundle ships to NotebookLM. Consolidates three authoritative sources:

1. **podcast-challenger 30-check catalog** — [`infra/claude-agents/podcast-challenger.md`](../../infra/claude-agents/podcast-challenger.md) §"Check catalog", to migrate to `.github/agents/podcast-challenger.agent.md` in P8.8.
2. **Handbook NORMATIVE R-rules** — [`content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md`](../../content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md) (chapter rules) + [`...notebooklm-customize-prompt-rules.md`](../../content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md) (framing rules).
3. **`P9.per_book_ship_gate`** — [`podcast-plan.yaml` P9 block](./podcast-plan.yaml).

> **Ship rule:** every bullet below MUST be PASS (or documented as a deliberate exception in the book's `_system/challenger-report.md`) before merging the book's branch into `develop`. P0 failures BLOCK ship outright. P1 failures may ship with caution + sidecar note. P2 = polish.

---

## Section A — Source bundle completeness *(P0)*

Every chapter-as-source under `BOOK_DIR/chapters/chNN-<slug>.txt` AND every framing under `BOOK_DIR/_system/episode-drafts/EP##-<slug>/00-framing.md` must exist and match by slug.

- [ ] **A1** Chapter file exists for every episode in the book registry — `ls BOOK_DIR/chapters/` count equals episode count
- [ ] **A2** Framing file exists for every chapter — 1:1 slug parity between `chapters/chNN-<slug>.txt` and `_system/episode-drafts/EP##-<slug>/00-framing.md` *(challenger F1)*
- [ ] **A3** Final episode txt exists at `BOOK_DIR/episodes/EP##-<slug>.txt` (rebuilt by `build_episode_txt.py`)
- [ ] **A4** Source-integrity sidecars present: `_system/source/text/{refined-english,_phonetics,raw-extract,_lexicon}.md`
- [ ] **A5** Per-book `_system/challenger-report.md` exists with verdict `SHIP-READY` or `SHIP-WITH-CAUTION` (never `BLOCKED`)
- [ ] **A6** If P4 numeric/symbolic source: `_system/source/text/numeric-disambiguation-register.md` present and all entries either RESOLVED or NEEDS HUMAN REVIEW (never invented)

---

## Section B — Citation authenticity & verbatim integrity *(challenger Category A, all P0)*

- [ ] **B1** Every Quranic verse cites `(Quran <Surah>:<Verse>)` or `(<Surah Name> <Surah>:<Verse>)` *(A1)*
- [ ] **B2** Every hadith cites collection + book + number + narrator *(A1)*
- [ ] **B3** Every Imam Ali saying cites `(Nahj al-Balagha, Sermon/Letter/Aphorism <N>)` or `(Ghurar al-Hikam, <N>)` *(A1)*
- [ ] **B4** No `[VERIFY CITATION]` markers in any chapter; no fabricated hadith numbers; no `da'if`/`mawdu'` cited as authoritative *(A2)*
- [ ] **B5** Quranic translations name the translator on first occurrence per chapter (Yusuf Ali, Asad, Pickthall, Sahih International) *(A3)*
- [ ] **B6** Scripture and hadith blockquotes are **verbatim**, not paraphrased *(A4)*
- [ ] **B7** No source-shifting — prose around quotes doesn't twist accepted scholarly meaning *(A5)*
- [ ] **B8** No cross-tradition collision — Sunni hadith and Shia/Ismaili tradition cited adjacently are annotated as parallel traditions, never collapsed *(A6)*

---

## Section C — NotebookLM literalness *(challenger Category B, all P0)*

- [ ] **C1** No meta-prose tells (build script's `META_PROSE_TELLS` + `META_PROSE_REGEX_TELLS` clean; semantic equivalents flagged) *(B1)*
- [ ] **C2** No cross-episode references — zero `EP\d\d`, "previous episode", "earlier episode" *(B2; R-CROSSREF)*
- [ ] **C3** No file-length self-references ("in a few thousand words", "this chapter has") *(B3)*
- [ ] **C4** No translator-apparatus prefixes ("the translator notes", "the square brackets are") *(B4)*
- [ ] **C5** No em-dashes in chapter prose *(B5; R-NOEMDASH)*
- [ ] **C6** No invented dialogue, fictionalized scenes, or fabricated quotes *(B6; R-NOFABRIC)*
- [ ] **C7** No HTML comments in chapter file *(R-NOHTML)*
- [ ] **C8** No meta-prose describing the chapter itself *(R-NOMETAPROSE)*

---

## Section D — Pronunciation discipline *(challenger Category C, P1)*

- [ ] **D1** Every italicized Arabic term has an inline phonetic guide on first chapter occurrence; lookup order: (a) `content/_shared/arabic/03-arabic-english-manifest.md`, then (b) `_system/source/text/_lexicon.md` *(C1)*
  - **OR**: phonetic guides are absent because the imperative-pronunciation pivot is active — see Section H.
- [ ] **D2** Lexicon parity — every phonetic in chapter matches the shared manifest where present; same term same phonetic across chapters *(C2)*
- [ ] **D3** Honorific discipline — PBUH / AS / RA at first mention only per chapter, never on every line *(C3; R-HONORIFIC-ONCE)*
- [ ] **D4** Substitution policy — every term flagged in `content/_shared/arabic/04-common-term-substitutions.md` §2 either substituted to English OR justified in framing's Pronunciation hooks *(C4; R-SUBSTITUTION)*

---

## Section E — Enrichment & depth *(challenger Category D, P1; R-ENRICH60, R-MULTITIER, R-NOSTACK)*

- [ ] **E1** Multi-tier enrichment — chapter draws on ≥3 distinct whitelist tiers (Tier 1–7); not a monoculture *(D1)*
- [ ] **E2** Enrichment ratio ≤ 60% — outside material does not exceed 60% of chapter word count *(D2)*
- [ ] **E3** Tradition coherence over breadth — citations cluster around the chapter's named tensions, not scattered *(D3)*
- [ ] **E4** No quote-stacking — no ≥3 consecutive blockquotes without integrating prose ≥30 words between *(D4)*
- [ ] **E5** No `[CONTEXT NEEDED]` markers anywhere *(D5; bumped to P0 per build script)*

---

## Section F — Articulation & shape *(challenger Category E, P1; R-WORDBAND)*

- [ ] **F1** Word-count band — chapter 1,500–4,500 words; framing 200–2,000 (default tier) OR 200–3,500 (Extended tier, `contract.length_target == "extended"`) *(E1)*
- [ ] **F2** One-sentence summarizability — the listener can summarize the episode in one sentence *(E2)*
- [ ] **F3** Beginning / middle / end arc — chapter has hook open, pressure-building middle, landed close *(E3)*
- [ ] **F4** No verbal filler / cheerful filler ("Well, you know…", "It's interesting that…", "wow", "amazing") *(E4)*
- [ ] **F5** No translation-residue awkward phrasings — no leftover Urdu→English calques *(E5)*

---

## Section G — Chapter opens correctly *(P0/P1; R-OPENFRAME, H1)*

- [ ] **G1** Chapter opens with one-paragraph contextual frame (≤120 words) *(R-OPENFRAME)*
- [ ] **G2** Welcome clause present in framing's Opening directive *(H1; R-WELCOME)*
- [ ] **G3** Episode-summary clause present — 2–3 sentence summary names source + tension + landing question *(H2; R-WELCOME)*
- [ ] **G4** Closing landing — Three-part focus → Landing forbids recap; closes on unresolved tension / question / sharp line *(H3; R-SUMMARYTAIL)*

---

## Section H — Framing integrity *(challenger Category F, P1)*

- [ ] **H1** Framing four-part structure — opening directive, three-part focus, pronunciation hooks, anti-noise rules *(F2)*
- [ ] **H2** Audience named concretely — not "general audience"; names a concrete profile *(F3)*
- [ ] **H3** 2–4 specific tensions named in `## Central tensions` — not generic themes *(F4)*
- [ ] **H4** Discussion-spine 6–12 beats in `04-discussion-spine.md` *(F5)*
- [ ] **H5** ≥1 canonical NotebookLM steering phrase from `two-host-framing.md` ("Slow down on…", "Treat X as the central tension…", "End on a question…") *(F6, P2)*

---

## Section I — Imperative-pronunciation pivot *(challenger Category N, P0; R-PHONETICS-OUT, R-PRONUNCIATION-IMPERATIVE)*

- [ ] **I1** Chapter contains zero inline phonetic parens — patterns `*Term* (PHO-NE-TIC;...)` and post-transliteration phonetic lines are forbidden *(N1)*
- [ ] **I2** Framing's `## Pronunciation` block uses imperative form — every non-blank line begins `Pronounce "..."` or `Do not...` *(N2)*
- [ ] **I3** Every transliterated Arabic term in chapter has a matching `Pronounce "..."` line in framing *(N3)*
- [ ] **I4** Framing ends with the no-read-aloud guard — `Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.` *(N4; R-NO-READ-PROMPT)*
- [ ] **I5** (Transcript empirical, post-publication) Zero parenthetical-phonetic doublings — no adjacent identical-or-near-identical tokens within 3 words *(N5, P1)*

---

## Section J — Name aliasing *(challenger Category J, P1; R-NAMES, R-NAMEALIAS)*

- [ ] **J1** Name discipline block in framing's Pronunciation hooks lists every long name in chapter with alias from `content/_shared/arabic/05-name-alias-policy.md` *(J1)*
- [ ] **J2** Chapter applies alias after first mention — every long name appears full ONCE then alias subsequently *(J2)*
- [ ] **J3** Alias spelling matches canonical phonetic in `03-arabic-english-manifest.md` exactly *(J3, P0)*

---

## Section K — Anti-repetition + no-irrelevant-background *(challenger Category I, P1; R-NOREPEAT, R-NOBACKGROUND)*

- [ ] **K1** Anti-repetition clause present in framing's Anti-noise section — forbids restating thesis >2×, re-citing quotes, summarizing what was just said *(I1)*
- [ ] **K2** No-irrelevant-background clause present — instructs hosts to stay on main content; biographical/historical context only when pertinent, only once *(I2)*
- [ ] **K3** Chapter does not state the same point in two adjacent movements *(I3)*
- [ ] **K4** Biographical material about author/translator/century appears at most once and ≤ 10% of chapter word count *(I4)*

---

## Section L — Host-dynamic discipline *(challenger Category K, P1; R-NOINTERRUPT)*

- [ ] **L1** Interruption-avoidance clause present — Host dynamic or Anti-noise has "Conversation discipline" forbidding mid-sentence interjections *(K1)*
- [ ] **L2** Filler-injection words named in Host dynamic — "yeah", "right", "exactly" explicitly listed *(K2)*

---

## Section M — Modernization + surprise-noise audit *(challenger Category M, P0/P1; R-NOMODERNIZE, R-NOSURPRISE)*

- [ ] **M1** Framing carries DENY-modernize block in `## Do not` — names at minimum: Twitter, X, social media, algorithm, content creator, internet troll, reply guy, YouTube comment, TikTok, deep dive, "21st century", "in our modern world", quote-tweet, cognitive behavioral therapy *(M1, P0)*
- [ ] **M2** Framing carries DENY-surprise block in `## Do not` — names: "wow", "that's so interesting", "it's chilling", "it's devastating", "it's terrifying", "right?", "exactly", "no way" *(M2, P0)*
- [ ] **M3** (Post-publication) Transcript has ≤1 injected modernization *(M3, P1)*
- [ ] **M4** (Post-publication) Transcript surprise-loop density ≤ 1 per 1,000 words *(M4, P1)*

---

## Section N — Numeric / symbolic disambiguation *(challenger Loop N, P0/P1; P4 deliverable)*

- [ ] **N1** Every "N X" claim in the chapter has either an enumeration in the per-chapter scaffolding OR an explicit NEEDS HUMAN REVIEW flag in `03-source-integrity-notes.md`
- [ ] **N2** No enumeration is repeated across episodes — one-time enumeration rule
- [ ] **N3** Any abjad-encoded sequence has either a sourced decoding OR a NEEDS HUMAN REVIEW flag
- [ ] **N4** Every anachronistic gloss has both period referent AND modernization labeled, with explicit on-air host instruction
- [ ] **N5** **NO INVENTED ENUMERATION** — any unsourced count is **P0 BLOCKED**; ship is refused

---

## Section O — Honorific + abbreviation discipline *(challenger Category O, P0/P1; R-NO-ABBREVIATION)*

- [ ] **O1** Honorific discipline — see D3 (R-HONORIFIC-ONCE)
- [ ] **O2** No abbreviation of major work names — full title on every appearance (e.g., "Nahj al-Balagha", not "NaB"); first ~3 occurrences include source-tradition tag

---

## Section P — Extract Mode contracts *(challenger Category G, P0/P1; only when `BOOK_DIR/chapter-contracts/` is populated)*

- [ ] **P1** Contract present per chapter — every `chapters/chNN-<slug>.txt` has matching `chapter-contracts/<slug>.yml` *(G1)*
- [ ] **P2** Contract validates — `python3 scripts/podcast/extract_chapter.py <ref> --force` exits 0 *(G2)*
- [ ] **P3** Contract passes meta-prose lint — no `EP##` refs / next-episode prose / Phase-04..08 leaks / translator-apparatus prefixes *(G3)*
- [ ] **P4** `derived_from:` lineage valid — referenced source exists; siblings point at the same source *(G4)*
- [ ] **P5** Derivative slug discipline — kebab-case single-noun English; no `-v2`, `-part-a`, `-half-one` *(G5)*
- [ ] **P6** Source not stale relative to derivative — derivative mtime ≥ `derived_from:` source mtime *(G6)*

---

## Section Q — Arabic / RTL hygiene *(implicit; verified by build script + manifest)*

- [ ] **Q1** No mojibake — chapter renders Arabic UTF-8 cleanly in a NotebookLM-rendering preview
- [ ] **Q2** No `?? ?? ??` placeholder runs anywhere
- [ ] **Q3** Phonetic guides preserve liaison/gemination per `content/_shared/arabic/01-tts-pronunciation-key.md`
- [ ] **Q4** Quranic verses preserve original Arabic UTF-8 alongside transliteration where used

---

## Section R — Learning loop closure *(P9 per_book_ship_gate; P-9 invariant)*

- [ ] **R1** Cost-ledger row appended for every `claude -p` call during this book's pipeline *(P6.1)*
- [ ] **R2** ≥1 finding row in `_learning/findings.jsonl` OR documented zero-findings rationale in `_system/challenger-report.md` *(LL2)*
- [ ] **R3** `_learning/health/<book-slug>.json` written; row appended to `BOOK_DIR/_system/health-trend.md` *(LL3)*
- [ ] **R4** Trainer ran; outcome ∈ {PROMOTED, ARCHIVED} — **never NEVER_RAN** unless explicitly documented *(R7 risk; per_book_ship_gate)*
- [ ] **R5** `python3 scripts/podcast/test_challenger.py` exits 0 after any trainer commit (no fixture regressed) *(LL3 invariant)*
- [ ] **R6** If trainer promoted a rule on this book: `CHALLENGER_VERSION` bumped by 0.1 in `_rules.py` in the same commit *(LL7)*
- [ ] **R7** If new check shipped: ≥1 fixture lands in `_learning/fixtures/` in the same commit (P-9 / LL9)

---

## Section S — Cost & resource guardrails *(P6.3, P10.1)*

- [ ] **S1** Book cost within tier budget (soft warn $20, hard cap $50 by default) — no `cost_cap_hard_breach` event in events.jsonl
- [ ] **S2** Predicted cost from P10.1 cost-eta was within ±25% of actual at ship time
- [ ] **S3** No `claude -p` retry storm — total retries across the run ≤ 10% of total invocations
- [ ] **S4** Azure spend itemized per adapter (post-P17.1) OR per phase (pre-P17.1) in `cost-ledger.jsonl`

---

## Section T — Cross-skill boundary *(framework.md governance; P1, P-6, P-7)*

- [ ] **T1** Zero writes from `scripts/podcast/` to `content/babu-memoir/**`, `content/_shared/**` (except whitelisted `06-abjad-numerals.md`), `scripts/memoir/**`, `scripts/site/**` *(P1.1 / `_boundary_check.py`)*
- [ ] **T2** Any `proposed-library-entries.md` written carries `schema_version: 1` frontmatter *(P1.2)*
- [ ] **T3** Manual library handoff documented — journal-side promotion is a separate human step *(P-7)*

---

## Section U — Show-note resolvability *(challenger ad-hoc; post-publication)*

- [ ] **U1** Every external URL in the book's framing or chapter shows-notes resolves (HTTP 200 + content-type sane); broken-link audit run within 30 days of publication
- [ ] **U2** Cited primary sources (PDFs, scholar pages, IIS / Iranica) tracked in `enrichment-sources.md`; no link rot since last audit

---

## How to use this checklist

1. **Before merging a book branch to `develop`**: walk every bullet. For each, mark `- [x]` if PASS or note the exception path inline (e.g., `- [x] P0 deferred — see _system/challenger-report.md §"Section M ship-with-caution rationale"`).
2. **Bullet-citation discipline**: every PASS that's not auto-verified by a script must cite the evidence — a file:line, an output snippet, or the challenger-report row id.
3. **One UNKNOWN = not ready** (CORE-068 convergence gate). UNKNOWN means "I haven't checked." That's a blocker for merge.
4. **Section R is non-negotiable** — the P-9 learning-loop invariant. A book that ships without triggering learning-loop activity is suspicious and surfaces a P1 warning band on the dashboard.

## Provenance — where each bullet is grounded

| Section | Source-of-truth file |
|---|---|
| A — Source bundle | [`skills-staging/podcast/SKILL.md`](../../skills-staging/podcast/SKILL.md) §10 ("In `BOOK_DIR/`") |
| B — Citation authenticity | [`infra/claude-agents/podcast-challenger.md`](../../infra/claude-agents/podcast-challenger.md) §"Category A" + [`content/podcast/.skill/handbook/enrichment-sources.md`](../../content/podcast/.skill/handbook/enrichment-sources.md) |
| C — NotebookLM literalness | [`infra/claude-agents/podcast-challenger.md`](../../infra/claude-agents/podcast-challenger.md) §"Category B" + `scripts/podcast/build_episode_txt.py:META_PROSE_TELLS` |
| D — Pronunciation discipline | [`...handbook/notebooklm-source-chapter-rules.md`](../../content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md) R-PHONETICS-OUT, R-HONORIFIC-ONCE, R-SUBSTITUTION |
| E — Enrichment & depth | [`...handbook/enrichment-sources.md`](../../content/podcast/.skill/handbook/enrichment-sources.md) + R-ENRICH60, R-MULTITIER, R-NOSTACK |
| F — Articulation & shape | R-WORDBAND + [`...handbook/episode-architecture.md`](../../content/podcast/.skill/handbook/episode-architecture.md) |
| G — Chapter opens correctly | R-OPENFRAME, R-WELCOME, R-SUMMARYTAIL |
| H — Framing integrity | [`...handbook/two-host-framing.md`](../../content/podcast/.skill/handbook/two-host-framing.md) + [`...handbook/notebooklm-best-practices.md`](../../content/podcast/.skill/handbook/notebooklm-best-practices.md) §5 |
| I — Imperative pronunciation | R-PHONETICS-OUT + R-PRONUNCIATION-IMPERATIVE (challenger Loop N) |
| J — Name aliasing | [`content/_shared/arabic/05-name-alias-policy.md`](../../content/_shared/arabic/05-name-alias-policy.md) + R-NAMES + R-NAMEALIAS |
| K — Anti-repetition / no-bg | R-NOREPEAT + R-NOBACKGROUND |
| L — Host-dynamic discipline | R-NOINTERRUPT + [`...handbook/two-host-framing.md`](../../content/podcast/.skill/handbook/two-host-framing.md) |
| M — Modernization + surprise | R-NOMODERNIZE + R-NOSURPRISE (challenger Loop M; empirical-transcript loop) |
| N — Numeric / symbolic | [`./numeric-symbolic-disambiguation-plan.md`](./numeric-symbolic-disambiguation-plan.md) + [`...handbook/numeric-symbolic-disambiguation.md`](../../content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md) (P4) + [`content/_shared/arabic/06-abjad-numerals.md`](../../content/_shared/arabic/06-abjad-numerals.md) |
| O — Honorific + abbreviation | R-HONORIFIC-ONCE + R-NO-ABBREVIATION |
| P — Extract Mode contracts | [`...handbook/extract-capability.md`](../../content/podcast/.skill/handbook/extract-capability.md) + [`scripts/podcast/extract_chapter.py`](../../scripts/podcast/extract_chapter.py) |
| Q — Arabic / RTL hygiene | [`content/_shared/arabic/01-tts-pronunciation-key.md`](../../content/_shared/arabic/01-tts-pronunciation-key.md) + manifest |
| R — Learning loop closure | [`podcast-plan.yaml`](./podcast-plan.yaml) `P9.per_book_ship_gate` + `LL1..LL15` block |
| S — Cost & resource | `podcast-plan.yaml` P6.3 + P10.1 |
| T — Cross-skill boundary | [`framework.md`](../../framework.md) §"Cowork-Canonical-Writes" + `podcast-plan.yaml` P-6/P-7 |
| U — Show-note resolvability | `enrichment-sources.md` tier discipline |

---

## Reconciliation note

Where the three authoritative sources overlap, this checklist defers to:
1. **podcast-challenger 30-check catalog** for severity (P0/P1/P2) and detection method.
2. **Handbook NORMATIVE files** for the canonical R-rule definition.
3. **`P9.per_book_ship_gate`** for the structural pipeline check (cost ledger, findings, health, trainer outcome, regression-green).

If a future drift creates conflicting wording across the three, **reconcile in this file FIRST** (CORE-064 sweep completeness), then update the source-of-truth file to match.
