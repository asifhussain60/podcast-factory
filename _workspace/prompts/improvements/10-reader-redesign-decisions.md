# 10 — Podcast chapter-reader redesign — CONVERGED decisions (2026-05-29)

> Per-view redesign discussion (Asif, 2026-05-29), folded into the intelligence-pipeline
> session. The reader is the convergence surface for the source-intake decisions
> ([09-source-intake-decisions.md](09-source-intake-decisions.md)): the Intake Review /
> source-budget panel (SI-6), divergence markers (SI-4), and corpus-verified annotation
> markers (D10). Current-state map: a mature editorial-modern MVP (external CSS, machine-
> agnostic paths, serif-first, themed) whose core problem is that consumption + editorial
> tooling are fused into one dense surface. Cortex HTML View standard applies to any build.
> Plan-first gate: these become a plan entry + snapshot + approval BEFORE any code.

| # | Decision |
|---|---|
| **R-1 — Two modes on the same chapter: Read + Studio.** | **Read** = clean, audience-grade, distraction-free (the eventual public-facing experience). **Studio** = Asif's editorial cockpit (annotations, AI tools, divergence markers, Intake Review/source-budget, source layers). One-click in-context toggle on the same chapter; nothing removed, just placed in the right mode. Resolves the consumption-vs-editorial tension at the root. |
| **R-2 — Studio uses a single contextual inspector, not stacked rails.** | One right-side panel whose content FOLLOWS FOCUS. Nothing selected → chapter/book context (source budget, section summaries, divergence overview, mini-TOC). Paragraph selected → that paragraph's tags, notes, divergent source renderings, reference markers, AI actions. Replaces the current competing widget stack (workbench + TOC + AI + Q&A + summaries). Makes annotations/divergences prominent; absorbs new surfaces without new rails; surfacing is context-gated, not crammed (honours ui-max-surfacing without clutter). |
| **R-3 — Read mode = reading + subtle verified markers + audio + Arabic; zero editorial chrome.** | Renders only the CANONICAL reconciled text. Corpus-verified Quran/hadith/term markers stay but rendered RESTRAINED + tappable for popovers (not the bright editorial highlight). Inline AUDIO player (NotebookLM/m4a Audio Overview) — the headline missing feature. Arabic toggle stays. Tags, AI, divergence markers, source layers are absent (Studio-only). The audience sees the clean result; Asif reviews divergences in Studio. |

| **R-4 — Divergences: inline indicator + side-by-side inspector.** | Quiet per-paragraph margin glyph ("N sources differ") preserves reading flow; selecting it opens the inspector side-by-side: canonical vs each source version, color-coded by role, span-level diff highlighting, keep/accept/flag controls. Doubles as the Anwaar Urdu-vs-English transcript comparison surface (SI-2). Two jobs (locate / compare) → two treatments. |
| **R-5 — Audio: persistent docked player + sync-when-available.** | Slim player docked to the reading column, persists on scroll, scoped to the chapter's episode; karaoke text-sync when timestamps exist, graceful plain player otherwise; available in both modes. Headline missing feature; degrades cleanly. |
| **R-6 — Chapter/episode: explicit mapping; Read=episode, Studio=chapter.** | Formalize one-episode↔one-or-more-chapters mapping; unify into one reader where Read mode is episode-centric (assembled text + synced audio) and Studio is chapter/source-centric (editorial). Retires the separate pages; makes audio-scoping + listen-along work; models the locked content-aware boundary reconfiguration. |
| **R-7 — Studio = the pipeline's single human-review cockpit.** | Not a reader with edit features bolted on — a purpose-built review workbench where ALL human review happens as raw source flows through the pipeline (source budget, divergence reconciliation, refined-source review, annotation, AI-assisted edits). Maximum tooling for fast scanning / marking / identifying / editing; richest-UI default ([[ui-max-surfacing]]). |
| **R-8 — Engine: TipTap (ProseMirror) for Studio; Read stays static.** | ProseMirror decorations = non-destructive annotations / markers / divergence highlights; mature extensions for comments, suggestions/track-changes, marks, find-replace, keyboard nav; real transactions + undo/redo; collaboration-ready (y.js) later. React-island friendly. Read mode = fast server-rendered prose + audio player. Add `jsdiff` for side-by-side; keep `floating-ui`. Asif authorized installing libraries; prefers richer UI. |

| **R-9 — Studio capability set = FULL package.** | Scan: keyboard nav + document minimap/scrollbar heatmap (markers/divergences/unreviewed at a glance) + find-replace. Mark: one-keystroke marking palette (tag chips + reference markers), color-coded decorations, legend. Identify: side-by-side divergence diff (jsdiff, accept/reject per span) + inline verified reference markers. Edit: tracked inline suggestions (accept/reject, real undo/redo) + accept/reject AI rewrite (never auto-applied). Capture: contextual-inspector feedback hub + review-queue + per-paragraph reviewed-state + chapter progress + one-click stage approval (writes the gate flag). One coherent confidence-sweep cockpit. |
| **R-10 — Mobile = DESKTOP-ONLY for now.** | Ship both modes desktop-first; defer all mobile/responsive optimization (incl. mobile-first Read polish). Studio's editorial tooling is the priority and is desktop-bound; revisit mobile Read later. (Deviation from the recommended Read-mobile-first split — Asif chose desktop-only.) |

## MUST-PRESERVE from the existing ChapterEditor (Asif 2026-05-29, verified in code)
The TipTap rebuild MUST carry these forward:
- **Change-tracking redline ("stays green").** Per-block original/current/deleted snapshots +
  WORD-LEVEL diff; changed paragraphs highlighted in `--edit-highlight` (emerald/green default,
  switchable amber/sky/rose/violet); per-block hover chips (↺ Revert / ✕ Delete / ✦ Rewrite);
  changes summary/export. On TipTap → ProseMirror change-decorations (transaction-based, more
  robust). Source: ChapterEditor.tsx (renderDiffHtml, edit-block-changed, --edit-highlight).
- **Per-paragraph token tags.** `data-para-idx` on every p/h2/h3; tag chips (5 defaults:
  esoteric/reality/sharia/mark-for-deletion/mark-for-improvement, colour+icon, extensible);
  persisted via annotation_tags + paragraph_annotations + /api/annotations; coloured paragraph
  mark. On TipTap → paragraph node attributes rendered as the same chips, same persistence.
  Source: ParagraphAnnotationBar.tsx + lib/db/annotations.ts.

## Next-iteration build set (Asif-selected 2026-05-29) — spike → real Studio (WC8.5)
Verse hover (Radix HoverCard + existing Quran detector + /api/quran/verse → wisdom MCP/corpus
per D13 + surah-name→number map) · click-to-jump + scrollbar minimap/heatmap · ⌘K palette
(cmdk) + TipTap find/replace · PLUS the two MUST-PRESERVE capabilities above.

## Learning loop (CORE PRINCIPLE, Asif 2026-05-29)
Every manual enhancement (reference marks, paragraph tags, edits) is training signal: the
intelligence learns it and the pipeline PRE-APPLIES it on the next chapter/book BEFORE Asif
reviews — confirm/refine, never start blank. Chapter→chapter, book→book (flywheel). TIERED:
deterministic (corpus-verified reference markers) AUTO-APPLIED; judgment (esoteric/reality/sharia
tags, prose edits) PRE-MARKED as accept/reject suggestions, never silent (mirrors D12). Build
implication: the editor EMITS actions as learnable signal; the pre-mark phase CONSUMES + applies
tiered. See plan.yaml WC8.co_development_model.learning_loop + memory `learning-loop`.

## All reader points RESOLVED (R-1..R-10).
Lower-priority audit items still unscheduled: citation/export, persistent margin notes, server-side edit history, selectable Quran translation. (In-chapter search is folded into R-9 find.)

> **Next: consolidate [09](09-source-intake-decisions.md) + this doc into a single plan.yaml entry + snapshot for approval (plan-first gate) before any code.** This is a real re-platforming of Studio onto TipTap + the intake/reconciliation pipeline work — scope it as a wave with sub-steps.

---

## Feel-check feedback — Slice-0 TipTap PoC (Asif, 2026-05-29)

First live feel-check of the throwaway PoC (`/studio-poc`, one Ayyuhal chapter). Feedback
captured verbatim-in-intent and routed to PIPELINE / PODCAST / INTELLIGENCE / UI. These
refine the R-decisions; nothing here is built until the consolidated plan is approved.

| # | Asif's feedback | Resolution + where it lands |
|---|---|---|
| **FC-1 — Verse hover: works, but CSS not applied + z-index wrong; and DON'T reuse the heavy gold Quran panel inline.** | Replace the inline treatment: instead of highlighting the whole "Surah Az-Zalzalah, verses 7 to 8" prose run, render a **compact `chapter:verse` label** (e.g. `99:7–8`) in small script, clear enough to read, **styled like a label/chip**. Keep a hover detail panel but FIX it (external CSS, correct stacking context, raised z-index). Revises R-3 + the step-2 "reuse QuranPopover" decision. **UI (WC8.5 cleanup).** The label text comes from the surah-name→number map (PIPELINE/INTELLIGENCE supply the full 114 + verified verse data via the corpus per D13). |
| **FC-2 — Inspector marker list (item 4): value unclear; only "QURAN 11" visible, no Hadith/Works.** | Two parts. (a) **Explain the value or remove** — the marker list is the chapter's *reference inventory / verification queue*: every scripture & source reference the chapter cites, deduped, at a glance, so coverage is verifiable and each ref is jump-to-able; in the learning loop it becomes the **review queue of corpus-verified vs unverified citations**. Asif to decide keep/remove once value is clear. (b) Hadith/Works groups were empty because the regex matched none in THIS chapter (not a bug) — but the regex detector is a stopgap; **real detection = corpus lookup (INTELLIGENCE), not patterns.** Ties R-9 (inline verified markers) + the knowledge slice. |
| **FC-3 — Redline: green works but change not visible after leaving the paragraph; paragraph hover/select wrong; want Microsoft-Word track-changes visuals.** | Three fixes. (a) **Word-level track changes** — render insertions/deletions inline Word-style (strikethrough deletions + underlined/coloured insertions) via **jsdiff (already installed)**, not whole-paragraph green; this completes the MUST-PRESERVE "word-level diff" that the PoC only stubbed at block level. (b) **Per-paragraph affordance** — hovering ANY paragraph shows a hover state; clicking selects/highlights ONLY that paragraph. (c) Persisted change visibility regardless of cursor position. **UI (WC8.5), with EDITOR emitting each edit as learning signal.** |
| **FC-4 — Arabic toggle (as in the podcast viewer): ON swaps Arabic-derived English words to Arabic script — modern clean Arabic font, distinct colour to stand out.** | Reuse the existing `ArabicToggle.tsx` + the per-book **glossary overlay** (`_system/glossary.yml`, phonetic↔Arabic-script, baked in Phase 0c). Render swapped tokens in a clean modern Arabic webfont (font asset only — e.g. Amiri / Noto Naskh) with a distinct colour. **UI (WC8.5) + INTELLIGENCE (glossary must cover the chapter's terms) + PIPELINE (glossary bake already exists; ensure Ayyuhal has it).** Available in BOTH Read and Studio. |
| **FC-5 — Reevaluate libraries; don't create sprawl.** | Current footprint is already lean: `@tiptap/*` (one engine), `@floating-ui/react`, `diff` (jsdiff). **Decision: add NO new JS libraries for this set.** Verse hover/label → `@floating-ui/react` (drop the previously-noted Radix HoverCard). Word-style redline → `jsdiff` (drop any track-changes lib; TipTap Pro is paid). ⌘K palette (cmdk) → **deferred**, not added now. Only possible new dependency = a self-hosted Arabic **font** (asset, not logic). Supersedes the "Radix HoverCard + cmdk" note in the next-iteration build set. |

> **Net effect on the build set:** the WC8.5 capability work now leads with these five
> corrections; library policy is frozen to tiptap + floating-ui + jsdiff (+ one optional
> font). The PoC's regex marker detector and block-level green are explicitly interim,
> superseded by corpus-verified markers (INTELLIGENCE) and jsdiff word-level redline (UI).

### FC-1 clarification — NotebookLM audio is unaffected; spoken verse form is a framing choice (Asif, 2026-05-29)
The compact `chapter:verse` chip is a **Studio editor decoration only**. It is appended
AFTER the natural-language reference and the chapter prose is NEVER mutated, so the source
NotebookLM ingests still reads "The Quran, in Surah Az-Zalzalah, verses 7 to 8". NotebookLM
never sees the chip. Confirmed: the chip cannot break or alter audio generation.
SEPARATELY — Asif wants the hosts to SAY the numeric form, e.g. "As Allah says in the Quran,
chapter 4, verse 44". That is a **PODCAST/PIPELINE framing-text phrasing requirement**, not a
UI concern: the episode framing `.txt` (and/or the chapter prose the pipeline emits) should
render Quran references as "chapter N, verse M" (numeric) so NotebookLM speaks them that way.
Routes to the authoring/framing step (PIPELINE + PODCAST). Recorded as a standing preference.

### Feel-check round 2 — icon-first affordances (Asif, 2026-05-29)
- **THROWAWAY confirmed.** `/studio-poc` is a functionality/feel spike only — NOT the final
  editor. The real Studio is built fresh in WC8.5 (Read + Studio modes, editorial-modern
  design, full capability package). The PoC exists solely to lock behaviour before that build.
- **FC-6 active-paragraph ring.** The full-editor focus outline (wrapped the whole panel) is
  removed; the active paragraph alone gets a glowing ring that persists while the caret is in it.
- **FC-7 icon-first tagging (Asif is a visual worker).** Token tags are ICONS, not colour-only:
  a floating icon palette anchored to the active block's top-left (tap to tag, tooltips name
  each), and persistent icon marks on tagged-but-inactive blocks so marked paragraphs are
  scannable. Inspector shows a tag key + the Arabic toggle moved to the top.
- **FC-8 visual-enhancement MENU (Asif asked "what other icon-based enhancements?").** Candidate
  affordances to layer into the real Studio (WC8.5 / R-9), to be picked per-page:
  1. Document minimap / heatmap strip — coloured ticks for tags / edits / references /
     unreviewed, click-to-jump (the R-9 scan tool).
  2. Per-paragraph status gutter — reviewed ✓, has-edits ✎, has-reference 📖, has-divergence ⇄.
  3. Reference source-type icons — Quran 📖 / hadith 🕌 / work 📚 on each marker instead of text.
  4. Confidence stars on verified references (★★★ corpus-verified vs ⚠ unverified) — ties the
     learning loop's auto/suggest tiers to a glance.
  5. Always-visible colour+icon legend.
  6. Divergence margin glyph (⇄ "N sources differ") opening the side-by-side inspector (R-4).
  7. Per-paragraph reviewed-state toggle (one click marks a block reviewed; chapter progress bar).
  These route to WC8.5 (UI) + the knowledge/learning slices (data behind icons 3/4/6).

### Feel-check round 3 (Asif, 2026-05-29)
- **FC-9 Arabic toggle scope = ALL scripture/poetry, not just glossary terms.** Toggling Arabic
  must also swap the **Quran verses, hadith, and poems** quoted in the chapter to their Arabic
  script — not only inline terms (Ghazali, Quran, Surah…). This is the PAYOFF of the
  multi-source unification (WC8.1): the **Arabic original is one of the sources**, aligned
  segment-by-segment to the English, so each quoted passage carries its Arabic rendering as an
  attributed layer. Quran/hadith Arabic also come VERIFIED from the corpus (INTELLIGENCE); poems
  come from the aligned Arabic source captured at intake (PIPELINE). Routing: PIPELINE (intake
  attaches Arabic per segment) + INTELLIGENCE (corpus supplies verified Quran/hadith Arabic) +
  UI (toggle swaps term AND quote layers). **PoC status:** single-source English fixture + seed
  glossary ⇒ terms-only today; full-quote swap activates once the Arabic source layer lands.
- **FC-10 hover = pointer cursor** (signals "nothing selected yet"). Done in PoC.
- **FC-11 active paragraph = dark thick border + padding + slight zoom** to stand off the page
  (the prior thin ring hugged the text). Done in PoC.
- **FC-12 icon row contrast + top separation** — its own surface/border and a real gap above so
  it never blends into the text behind it. Done in PoC.

## Voice normalization — global house style (Asif, 2026-05-29)
A new pipeline capability + its editor review surface, decided before building the Slice-0
stage-aware write-back loop. Routes to PIPELINE (the stage) + INTELLIGENCE (the style guide +
learning loop) + UI (the Normalized tab + diff).

- **SN-1 House voice = editorial-modern, accessible.** The Stripe / MIT-Press register already
  locked for the reader ([[podcast-reader-aesthetic]]): warm, clear, dignified, flowing; general
  reader without dumbing down.
- **SN-2 Latitude = moderate.** Reflow sentences, smooth transitions, unify tense/POV, fix
  translationese — preserve ALL meaning. HARD RULE: Quran verses, hadith, and poetry are kept
  VERBATIM; only the narration/exposition around them is normalized.
- **SN-3 Application = auto-applied, spot-checked.** Runs automatically and emits a distinct
  stage artifact; the Studio shows it as the Normalized tab beside Source with a diff = the
  spot-check surface. Meaning-drift guards (because auto-applied interpretive rewrite on
  doctrinal text is the risk point): (a) scripture verbatim, (b) source+diff tab always
  available, (c) podcast-challenger doctrinal-fidelity check on the normalized stage, (d)
  learning loop flags recurring risky rewrites. (Asif chose auto-applied over suggest-only;
  these guards keep it safe without a per-paragraph gate.)
- **SN-4 Consistency = ONE global house voice.** A single style guide the normalizer follows
  and the learning loop refines, applied to every book / source / genre — the whole library
  reads as one voice.
- **SN-5 Placement = a stage between clean-core and augment.** Stage/tab order:
  Source -> Denoised -> Core -> Normalized -> Augmented. Each is a tab in the Studio (the FC
  stage-tabs ask). Tabs fill in as the slices produce each stage.
- **SN-6 Input-adaptive, output-uniform.** The normalizer detects the incoming register
  (classical translationese / third-person scholarly / lecture transcript / teaching story) and
  maps each TO the single house voice.
