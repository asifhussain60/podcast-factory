# Journal Workflow v2: File-First Model
# AUTHORITATIVE: This file completely replaces SKILL.md Sections 1-10.
# When SKILL.md conflicts with this file, THIS FILE WINS.
# Nomenclature: the memoir is "What I Wish Babu Taught Me." Asif's
#   father is "Babu." Any "Dad" reference in the read-only SKILL.md
#   or its references is stale. Read it as "Babu."
#
# CORTEX Challenger Framework v1 governance: as of 2026-05-16, /journal
# operates under the framework defined at
# `reference/cortex-challenger-framework.md`, with skill-specific
# compliance recorded at
# `reference/skill-overlays/journal-cortex-overlay.md`.
# Severity tiers (P0-P3), DoR gate, voice-rewrite convergence loop, and
# applicable CORE rules are all defined there. When this workflow
# document and the overlay are both authoritative on a topic, the
# overlay wins for severity and gate behavior; this document wins for
# memoir-specific craft and content rules.
#
# Last updated: 2026-05-16 (CORTEX framework integration added)

============================================================
SECTION 1: SESSION START PROTOCOL
============================================================

Before doing ANY work, read these files in this order:

1. JOURNAL_DIR/content/babu-memoir/_system/memoir-rules-supplement.txt
2. JOURNAL_DIR/content/babu-memoir/_system/master-context.md (synthesized cross-chapter
   intelligence; replaces reading every chapter individually)
3. JOURNAL_DIR/content/babu-memoir/_system/voice-deep-analysis.md
4. JOURNAL_DIR/content/babu-memoir/_system/voice-fingerprint.md  (Babu-correct override)
5. JOURNAL_DIR/content/babu-memoir/_system/craft-techniques.md  (Babu-correct override)
6. JOURNAL_DIR/content/babu-memoir/_system/thematic-arc.md  (Babu-correct override)
7. JOURNAL_DIR/content/babu-memoir/_system/biographical-context.md + supplement Bio Context
8. JOURNAL_DIR/content/babu-memoir/_system/locked-paragraphs.md
9. JOURNAL_DIR/content/babu-memoir/_system/quotes-library.txt
10. JOURNAL_DIR/content/babu-memoir/_system/incident-bank.md
11. JOURNAL_DIR/content/babu-memoir/_system/quotes-workflow.md  (extraction + weaving protocol)
12. JOURNAL_DIR/content/babu-memoir/_system/translations-glossary.md  (canonical translations)
13. JOURNAL_DIR/content/babu-memoir/_system/chapter-status.md  (current state of every chapter)
14. JOURNAL_DIR/content/_shared/arabic/00-README.md  (cross-skill Arabic reference index)
15. JOURNAL_DIR/content/_shared/arabic/03-arabic-english-manifest.md  (canonical Arabic to English to phonetic lookup; translations-glossary wins for memoir-specific glosses)
16. JOURNAL_DIR/content/_shared/arabic/04-common-term-substitutions.md  (substitution policy for nafs, shaytan, ruh, etc.; memoir voice choices already shipped override per its Section 4)
17. JOURNAL_DIR/content/_shared/arabic/05-name-alias-policy.md  (long-name to short-alias policy: Ghazali, Haatim, Junaid, etc.; applied when memoir introduces a long Islamic name for the first time)

NOTE: Steps 4-7 read the writable JOURNAL_DIR/content/babu-memoir/_system/ versions
rather than the read-only SKILL_DIR/references/ originals. The writable
copies carry the Babu nomenclature override and any session-specific
edits. Do not fall back to SKILL_DIR/references/ unless the writable
copy is missing.

Then run delta detection:
  python3 <JOURNAL_DIR>/scripts/memoir/auto_delta.py <JOURNAL_DIR>/content/babu-memoir/chapters

Read the full delta report before touching any file. (Legacy SKILL_DIR
location at ~/Library/Application Support/Claude/.../skills/journal/scripts/
still works but the in-repo copy at scripts/memoir/ is canonical.)

============================================================
SECTION 2: FOLDER STRUCTURE
============================================================

JOURNAL_DIR/
  content/
    babu-memoir/
      _system/                     All reference + working state
        master-context.md          Synthesized cross-chapter intelligence
        journal-workflow-v2.md     THIS FILE (authoritative workflow)
        memoir-rules-supplement.txt
        voice-deep-analysis.md
        locked-paragraphs.md
        quotes-library.txt
        incident-bank.md
        temporal-guardrail.md
        snapshots/                 Delta snapshots (date-stamped)
        scratchpad/                Working files (one per chapter)
          scratch-love.txt         Active working file
      chapters/                    Final chapter files only
        preface.txt
        ch00-intro.txt
        ch01-man.txt
        ch02-love.txt
        ch03-marriage.txt

Rules:
  - One active scratchpad per chapter at a time.
  - Naming: scratch-{chapter-name}.txt (under content/babu-memoir/_system/scratchpad/)
  - No version files. Git handles all history.
  - After finalization, scratchpad file is deleted.
  - scratchpad/ folder stays clean between sessions.

============================================================
SECTION 3: CHAPTER WORKFLOW. FILE-FIRST MODEL.
============================================================

The work happens in the scratchpad file. Asif reads the file directly
in his filesystem. Chat is for feedback by section number and for
confirming what changed. Chapter prose never gets dumped into chat.
If you find yourself about to paste prose into chat, stop. Update the
file, present the link, report what changed in one or two sentences,
and wait for the section-by-section feedback.

### PHASE 1: ASSEMBLY & DRAFT

When Asif says "/journal work on chapter N" with optional brief
direction (1-2 sentences), the skill:

  1. Runs the full Session Start Protocol (Section 1 above)
  2. Reads the existing chapter file (if any) from chapters/
  3. Pulls ALL incidents tagged for this chapter from incident-bank.md
  4. Reads master-context.md for cross-chapter context, character
     tracker, threads, and callback candidates
  5. Scans master-context.md for themes relevant to this chapter that
     could be mined for new incident bank entries. If found, suggest
     to Asif before drafting.
  6. Checks quotes-library.txt for unused quotes fitting this chapter
  7. Writes the FULL chapter into content/babu-memoir/_system/scratchpad/scratch-{name}.txt:
     - Holistic write following the arc: experience → ownership → wisdom
     - Three-phase balance: Experiences ~50-60%, Learnings ~20-30%,
       Babu's Advice ~15-20%
     - ALL of Asif's existing sentences kept intact
     - Language refined: tighter phrasing, stronger words, better
       articulation
     - Transitions improved using documented bridge patterns
     - Humor added where natural using 6 documented patterns
     - Emotional pacing strengthened
     - Every scene tested: does it TURN something?
     - Sections divided by narrative beats:
       === SECTION N: Title ===
  8. Git-commits the scratchpad: "scratch-{name}: initial draft"
  9. OPENS BOTH FILES for Asif to review:
     - Present scratchpad file: content/babu-memoir/_system/scratchpad/scratch-{name}.txt
     - Present chapter file: content/babu-memoir/chapters/ch{NN}-{name}.txt (if exists)
     Use computer:// links so Asif can click to open them directly.
  10. Reports in chat: section count, readiness score, any incident
      suggestions. NEVER dumps text into chat.

For NEW chapters (no existing file): assemble from the incident bank,
biographical context, thematic arc, and whatever brief direction
Asif gave. If anything is ambiguous, ask ONE qualifying question
before drafting. Never invent. Better one smart question than the
wrong scene written confidently.

### PHASE 2: INTERACTIVE REVIEW

Asif reads the scratchpad file directly and gives feedback in chat
by section number:
  - "Section 3, add the skipping meds detail"
  - "Section 5 is good"
  - "Add [new incident] to section 2"
  - "Move section 4 before section 3"
  - "Section 7 needs more humor"

After EVERY edit:
  1. Apply the change directly in the scratchpad file
  2. Run the Challenger on the modified section
  3. Git-commit with descriptive message
  4. OPEN the updated scratchpad file for Asif using computer:// link
  5. Report in chat: what changed + any Challenger flags
  6. Do NOT dump section text into chat. Asif reads the file.

When Asif provides new content, his words are delta-protected. They
are content-locked. The only changes allowed are:
  - Grammar fixes that do not touch rhythm
  - A more precise emotional word he would have reached for
  - Articulation or flow refinements that say the same thing better
  - Relocation to a better position in the chapter

What is not allowed on his content:
  - Rewriting sentences, even if you think yours is better. They are
    not yours.
  - Changing facts, ages, places, dialogue, or details
  - Adding or removing sentences
  - Restructuring
  - Merging paragraphs he split

Section numbering stays stable. New sections get sub-numbers (3a)
rather than renumbering everything.

### PHASE 2a: QUALIFYING QUESTIONS

When Asif shares a new incident needing context, ask ONE smart
question rather than a survey. If clear enough, skip and draft.
After context gathered, insert into file and add to incident-bank.md.

### PHASE 3: FULL-CHAPTER CHALLENGER GATE

Once ALL sections reviewed and approved:

  1. SEAM CHECK: Read full scratchpad end-to-end. Check bridges
     between every section pair. Fix seams in file.
  2. Run FULL CHALLENGER (Section 4 below) across entire chapter.
     Iterative, up to 5 passes, fixing issues in the file each time.
  3. Report findings in chat ONLY (no report files).
  4. Approval gate opens ONLY when Challenger issues APPROVED.

### PHASE 4: FINALIZATION

When Challenger approves:
  1. Strip section headers from scratchpad
  2. Write clean content to content/babu-memoir/chapters/ch{NN}-{name}.txt
  3. OPEN the finalized chapter file for Asif using computer:// link:
     content/babu-memoir/chapters/ch{NN}-{name}.txt
  4. Lock new/modified paragraphs in locked-paragraphs.md
  4. Update quotes-library.txt usage markers
  5. Update incident-bank.md placement status
  6. Update temporal-guardrail.md if timeline affected
  7. Update master-context.md with new chapter synthesis
  8. Run full compliance scan
  9. Snapshot: python3 <JOURNAL_DIR>/scripts/memoir/auto_delta.py
     <JOURNAL_DIR>/chapters --save
  10. Git-commit final: "ch{NN}-{name}: finalized"
  11. Delete scratchpad file (history in git)
  12. Update voice-deep-analysis.md with new patterns

============================================================
SECTION 4: THE CHALLENGER. ENFORCEMENT ENGINE.
============================================================

Runs at TWO levels:
  1. SECTION-LEVEL: After every edit during Phase 2
  2. FULL-CHAPTER: Before finalization (Phase 3), iterative up to 5 passes

Severity:
  CRITICAL: must fix, no override
  MAJOR: should fix, Asif can explicitly override
  ADVISORY: flagged, non-blocking

### LOOP 1: VOICE INTEGRITY
  C1. Every sentence sounds like Asif? Test against voice-deep-analysis.md.
      Flag AI-sounding sentences. [CRITICAL]
  C2. Humor: only 6 documented patterns. No sitcom, no comedy. [MAJOR]
  C3. Emotional register: pain flat, interiority through questions, anger
      behind a wall, tenderness through specificity. [CRITICAL]
  C4. Banned word scan (AUTOMATED): trauma, toxic, narcissist, boundaries,
      triggered, journey (non-geographic), growth, healing, incredibly,
      absolutely, literally, em dashes, semicolons. [CRITICAL]
  C5. Contractions: formal when serious, casual when relaxed. [ADVISORY]
  C6. Sentence openers: flag 3+ consecutive "I" openers. [MAJOR]
  C7. Paragraph length: 2-5 sentences. Flag longer unless user delta. [MAJOR]
  C8. Voice calibration: test 3 random sentences against calibration lines
      in voice-fingerprint.md. Revise if they don't belong. [CRITICAL]

### LOOP 2: NARRATIVE ARCHITECTURE
  C9. Emotional arc: damage → search → discovery → wisdom. All four phases
      present. Flag missing/underweight. [CRITICAL]
  C10. Scene earns its place: turns something, or flag for removal. [MAJOR]
  C11. Three-phase balance: ~50-60% / ~20-30% / ~15-20%. [MAJOR]
  C12. Phase transitions: organic, not mechanical. [ADVISORY]
  C13. Narrative Constant: no victim framing, no accusation. [CRITICAL]
  C14. Babu's Advice: advises younger self, not lectures about parents.
       Only references events/people from same chapter's narrative. [CRITICAL]

### LOOP 3: CRAFT & PACING
  C15. Emotional moments slow, transitions fast. [MAJOR]
  C16. Bridge pattern variety: no two consecutive same-type. [MAJOR]
  C17. Reader fatigue: flag 3+ consecutive high-intensity sections without
       breathing moment. [MAJOR]
  C18. Insight from memory/contradiction, not stated directly. [CRITICAL]
  C19. No em dashes. No markdown. No semicolons. [CRITICAL]
  C20. No therapy jargon, self-help, corporate, academic, literary
       affectation, melodrama. [CRITICAL]

### LOOP 4: GOVERNANCE COMPLIANCE
  C21. Ali (AS) everywhere. Full honorific on first use per chapter. [CRITICAL]
  C22. Temporal guardrail: no forward references. [CRITICAL]
  C23. Atif: max 2 mentions per chapter (Ch01 exempt). [MAJOR]
  C24. Translation rule: single words never translated. Multi-word get
       parenthetical gloss. ABD = "slave" exception. [MAJOR]
  C25. Sacred quotes: max 1-2 sentences, no expansion, no lecture. [MAJOR]
  C26. Quote once-only: AUTOMATED check against quotes-library.txt. [CRITICAL]
  C27. Locked paragraphs: character-for-character. [CRITICAL]
  C28. Delta protection: only grammar/emotion/articulation/relocation. [CRITICAL]

### LOOP 5: DUPLICATION & REPETITION ENFORCEMENT
  C29. WITHIN-CHAPTER sentence duplication: flag any sentence or construction
       appearing twice, even with minor word changes. Identical meaning +
       identical structure = duplication. [CRITICAL]
  C30. CROSS-CHAPTER duplication: via master-context.md, flag any sentence,
       phrase, or construction duplicated from another chapter. [CRITICAL]
  C31. Incident re-telling: one primary chapter tells in full. Others may
       REFERENCE briefly (1-2 sentences max) but NEVER re-tell. [CRITICAL]
  C32. Thematic echo style: if a theme/image recurs across chapters, the
       style, register, or angle MUST be completely different. Flag same
       phrasing, structure, or approach. [CRITICAL]
  C33. Babu's Advice originality: flag verbatim narrative phrasing in Babu's
       section. Must offer different lens/elevation. [MAJOR]
  C34. Repetition balance: intentional craft (triads, callbacks, parallel
       structure) is allowed. Accidental/clumsy repetition flagged. If Asif
       restored something removed, his choice stands. [MAJOR]

### LOOP 6: REFLECTION & QUOTE INTEGRITY
  C35. Reflections: first person ("I") only. Split between realization
       bridges and Babu's Advice setup bridges. [CRITICAL]
  C36. Reflections modifiable into voice DNA. Quotes A/B immutable. [CRITICAL]
  C37. Sacred quotes exact. Invisible quotes paraphrased, meaning intact. [CRITICAL]

### LOOP 7: CROSS-CHAPTER CONTINUITY
  C38. Character consistency: master-context.md tracker. No new characters
       in Babu's Advice not in narrative. Atif count enforced. [MAJOR]
  C39. Incident bank reconciliation: every tagged incident placed or
       explicitly deferred. Flag orphans. [MAJOR]
  C40. Thread depth: recurring themes must deepen, not repeat. [MAJOR]

### LOOP 8: VOICE EXTRACTION
  C41. Extract new voice patterns from this session's work. [ADVISORY]
  C42. Update voice-deep-analysis.md. [ADVISORY]
  C43. Update master-context.md key phrases if new callbacks created. [ADVISORY]

### READINESS SCORE (reported after Phase 1)
Score 0-100 based on:
  - Incident coverage (tagged incidents placed?)
  - Quote placement (woven, not dropped?)
  - Voice match (sample sentences pass calibration?)
  - Arc completeness (all 4 phases present and weighted?)
  - Bridge variety (no consecutive same-type?)
  - Duplication clean (no cross-chapter duplicates?)
  - Reader fatigue (breathing moments present?)

============================================================
SECTION 5: GIT VERSIONING
============================================================

All scratchpad history tracked via git commits:
  - Phase 1 draft: "scratch-{name}: initial draft"
  - Each edit: "scratch-{name}: Section N refined per feedback"
  - Challenger fixes: "scratch-{name}: Challenger pass {N}"
  - Finalization: "ch{NN}-{name}: finalized"

Commands:
  - History: git log --oneline content/babu-memoir/_system/scratchpad/scratch-{name}.txt
  - Diff: git diff HEAD~1 content/babu-memoir/_system/scratchpad/scratch-{name}.txt
  - Rollback: git checkout HEAD~1 -- content/babu-memoir/_system/scratchpad/scratch-{name}.txt

No file copies. Git is sole version control.

============================================================
SECTION 6: OUTPUT RULES
============================================================

- Chapter text: plain text for Day One. No markdown.
- No em dashes, no semicolons.
- Commas after introductory adverbial phrases.
- Scratchpad: === SECTION N: Title === headers (stripped on finalization).
- NEVER dump chapter text into chat.
- ALWAYS present file links after ANY update to scratchpad or chapter:
  [View scratchpad](computer://<JOURNAL_DIR>/content/babu-memoir/_system/scratchpad/scratch-{name}.txt)
  [View chapter](computer://<JOURNAL_DIR>/content/babu-memoir/chapters/ch{NN}-{name}.txt)
  Where <JOURNAL_DIR> is Asif's mounted journal folder. In Cowork
  sessions this resolves to /Users/asifhussain/PROJECTS/journal. Use
  the user-facing path, not the sandbox session path. The user
  cannot navigate to /sessions/<id>/mnt/... links.
  This is how Asif reads the work. He clicks the link and opens the
  file directly. Without these links, he cannot see what changed.
- Chat is for: section counts, readiness scores, Challenger findings,
  confirming changes, receiving feedback by section number.

============================================================
SECTION 7: CLEANUP PROTOCOL
============================================================

After finalization:
  - Scratchpad file: deleted (history in git)
  - master-context.md: updated with new chapter synthesis
  - voice-deep-analysis.md: updated with new patterns
  - incident-bank.md: all placements updated
  - quotes-library.txt: all usage markers updated
  - locked-paragraphs.md: new paragraphs locked
  - temporal-guardrail.md: timeline updated if needed
  - No orphan files. No report files. Folder stays clean.

============================================================
SECTION 8: REFERENCE FILE INDEX
============================================================

A. Skill Directory (SKILL_DIR/references/). READ-ONLY, FROZEN.
   These are the original "Dad"-flavored references. Do not read
   them directly. Every memoir-relevant one has a writable Babu
   override at JOURNAL_DIR/content/babu-memoir/_system/. Listed here only so the
   agent knows what exists in the plugin folder.

   voice-fingerprint.md, craft-techniques.md, thematic-arc.md,
   biographical-context.md, chapter-status.md, quotes-workflow.md,
   translations-glossary.md

B. Journal Directory (JOURNAL_DIR/content/babu-memoir/_system/). WRITABLE, AUTHORITATIVE.

   B1. Always read at session start (in this order):
       memoir-rules-supplement.txt, master-context.md, voice-deep-analysis.md,
       voice-fingerprint.md, craft-techniques.md, thematic-arc.md,
       biographical-context.md, locked-paragraphs.md, quotes-library.txt,
       incident-bank.md, quotes-workflow.md, translations-glossary.md,
       chapter-status.md, journal-workflow-v2.md (this file)

   B2. On-demand references (read when the work touches them):
       temporal-guardrail.md   chronological map; consult before
                               adding any temporal claim
       clinic-library.txt       clinical signs library for ADHD,
                               dyslexia, depression, anxiety, sleep.
                               Read when an incident hinges on a
                               cognitive or mental-health symptom.

   B3. Cross-skill artifacts (NOT for memoir writing, leave alone):
       voice-fingerprint-light.md   used by Babu app orchestrators
                                    (highlights, short labels)

C. Scratchpad (JOURNAL_DIR/content/babu-memoir/_system/scratchpad/). TEMPORARY.
   scratch-{chapter-name}.txt   active chapter working file
   scratch-incidents.txt        active incident draft batch
   .gitkeep                     keeps folder tracked when empty
   Files here are deleted after finalization (history in git).

D. Chapters (JOURNAL_DIR/content/babu-memoir/chapters/)
   ch00-intro.txt, ch01-man.txt, ch02-love.txt, ch03-marriage.txt,
   preface.txt, snapshots/{base}-snapshot.txt (delta baseline)

E. Scripts (JOURNAL_DIR/scripts/memoir/). IN-REPO, STANDALONE.
   Pure stdlib Python. No external dependencies. Canonical location.
   The legacy SKILL_DIR/scripts/ copies (in Claude desktop's
   skills-plugin install) are identical mirrors — leave them alone
   but don't rely on them. The in-repo copies travel with the repo
   and survive uninstall of the desktop skill.

   auto_delta.py            delta CHECK + SAVE for all chapters
                            usage: python3 scripts/memoir/auto_delta.py chapters
                                   python3 scripts/memoir/auto_delta.py chapters --save
   detect_user_delta.py     core delta engine (called by auto_delta)
   save_snapshot.py         save single-file snapshot
   refresh_all_snapshots.py reset all snapshots to current state
