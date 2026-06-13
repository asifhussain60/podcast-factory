# Session brief — Audio Engine voice/style convergence (continuation)

Paste everything below this line into a fresh Claude Code session in
~/PROJECTS/podcast-factory. Written 2026-06-12 at the end of the Audio Engine
v2 build + smoke-test session.

---

Continue the Audio Engine voice/style convergence for the autonomous
ElevenLabs path. The engine build is DONE and MERGED; this session finishes
the voice/style lock-in and productionizes the lessons from the live smoke
test. Do not re-litigate decisions listed under "Locked by Asif's ear".

## Where the codebase stands (all on develop, pushed)

- Audio Engine v2 merged: merge commit b499b14 (+ post-merge fixes 69ebaad
  fixer-timeout-never-aborts-convergence, e0ed2cb PLS-upload-must-be-
  text/plain). Backup restore point: branch backup/pre-audio-engine-v2-2026-06-12.
- Test suite: 1,284 passing. Full feature docs in framework.md ("Audio
  engines" section), SKILL.md scripts catalog, plan.yaml wave AE.
- Key modules: scripts/podcast/_audio_engines.py (registry),
  _dialogue_script.py, _authoring/_dialogue.py, _validators_dialogue.py,
  _dialogue_convergence.py, pronunciation_compiler.py, _elevenlabs.py,
  render_dialogue_audio.py, phases/audio_driver.py. Orchestrator phases
  audio-script + audio-render sit between per-chapter-slides and finalize;
  ONE spend halt (H1) per book.
- Live smoke test rendered a full 17.6-min episode of The Master and the
  Disciple ch01a end-to-end (7,006 metered credits ~= $1.54; the registry's
  1.0 credit/char estimate is ~2x conservative vs the ~0.52 actual API rate
  — keep estimates conservative, document actuals).
- Smoke workspace (UNTRACKED, keep): _workspace/experiments/audio-smoke/
  master-disciple-smoke/ — script, gate reports, render ledger/cache, the
  rendered m4a, and all voice samples under m4a/casting/ + m4a/arabic-samples/.

## Locked by Asif's ear (do NOT revisit)

1. VOICE CAST for Islamic books: Mohammed ("Mohammed - Arabic",
   voice_id tlETan7Okc4pzjD0z62P) as HOST_A scholar lead; Sarah
   (EXAVITQu4vr4xnSDxMaL) as HOST_B seeker. Accents + Arabic pronunciation
   approved on sample P5/P7. American-accent Arabic library voices (Ramy,
   Mazen, Juniper, Jessica — added to roster) were auditioned and REJECTED.
   Brian-led English-only cast (casting-B) was approved for English feel but
   superseded by the Arabic exploration.
2. NATIVE ARABIC SCRIPT inline in render text is the winning pronunciation
   approach (Quran verses + key terms rendered in Arabic script, English
   gloss around them) — beats romanized+dictionary. This effectively decides
   halt H2 in favor of native script, pending the formal flag flip.
3. SPEED: Mohammed's VOICE PROFILE speed set to 1.2 (was 1.1) via
   /v1/voices/{id}/settings/edit — per-voice profile settings persist and
   carry into every render; Sarah stays untouched. Request-level `settings`
   in text-to-dialogue is global (no per-speaker speed there).
4. INTERACTIVITY: v3 is the most powerful engine — interactivity comes from
   script craft + audio tags, NOT an engine switch. NotebookLM switch
   rejected. Lesson from P6 vs P7: heavy TONAL tags on the male ([warm],
   [smiling], [lowering voice]) recolor his voice away from the approved
   timbre; keep male tags INTERACTIONAL-only ([pause] at most), put the
   reaction tags ([curious], [interrupting], [thoughtful], [quiet]) on the
   female, and write interactivity into the dialogue itself (interruptions,
   short reactive turns, mid-verse handoffs). Sample P7-male-speed-120.mp3
   is the current best take — CONFIRM Asif's verdict on it first.

## The work queue (in order)

1. CONFIRM P7. If pace/timbre approved, proceed; if not, tune one more
   sample (speed step or tag density) before anything else.
2. Lock the cast + style into the pipeline:
   - smoke book series-config: elevenlabs_voices {host_a: tlETan7Okc4pzjD0z62P,
     host_b: EXAVITQu4vr4xnSDxMaL}; consider making this pair the
     islamic-profile default in _audio_engines.py (registry default_voices
     are currently Daniel/Sarah — Daniel-led audio was judged robotic).
   - Flip elevenlabs_arabic_recitation for the smoke book (closes H2). The
     current scaffold (pronunciation_compiler.compile_turns_for_render)
     substitutes EVERY glossary term with arabic_script — refine it to the
     approved style: native script for Quranic/recited passages and key
     terms, with the English gloss pattern the samples used ("ARABIC — English").
     Consider authoring-time Arabic instead: let the script author place
     Arabic script + gloss directly (engine supports_arabic_script=True so
     the gate allows it), which matches how the approved samples were built.
   - Relax DLG-TAGS-NOT-SPARSE in _validators_dialogue.py: registry-driven
     tag budget (v3 wants tags; the 1-per-6-turns cap caused flat audio).
     Encode the male-tonal-tags-forbidden lesson as a check instead
     (tonal tags on HOST_A = P1; interactional tags fine).
   - Rewrite the interactive-craft section of _authoring/_dialogue.py's
     prompt: interruptions, short reactive turns, verse handoffs, female-side
     reaction tags, male-side restraint; spine/coverage/faithfulness rules
     unchanged. CONTENT QUALITY FIRST still rules; soft bands never cut.
   - pronunciation_compiler: loanword skip-list (the dictionary turned
     "Imam" into "e-Maam" — common English loanwords like Imam, Allah,
     Quran, Sunnah, hadith must never get alias rules). The dictionary
     remains useful for romanized terms WITHOUT native-script substitution.
3. Re-author the smoke episode script in the interactive style, converge
   through the gate, re-render the FULL episode in the locked cast
   (~13.5k chars, ~7k credits ~= $1.55 — get explicit go before the spend;
   voices/dictionary changed so the chunk cache will be cold). Deliver the
   m4a path for the final ear check.
4. After Asif approves the full episode: commit the pipeline changes (tests
   updated: tag rules, registry defaults, compiler skip-list; suite stays
   green), update framework.md + SKILL.md voice-cast notes, plan.yaml AE
   wave addendum, regenerate snapshots, session log in copilot-handoff.md.
5. Housekeeping (low priority): delete the format-probe pronunciation
   dictionaries created during debugging (format-probe-*, via
   DELETE /v1/pronunciation-dictionaries/{id} if supported); note the
   ~0.52 actual credit rate in _audio_engines.py comments.

## Constraints (unchanged from the build session)

- ElevenLabs spend only with explicit approval per render round; report
  metered credits from the subscription delta every time. Azure+Gemini
  standing authorization unchanged; Claude work on Max.
- NotebookLM path stays byte-identical (golden test guards it).
- ASCII-only in code/output files (Arabic script allowed in render-layer
  text and samples — it IS the content); no PRs, commit to develop;
  full suite green before any commit; snapshots regenerated with plan edits.
- The API key needs no new permissions (voice-library-add was granted
  2026-06-12; the four library voices are already in the roster).

## Sample inventory (for reference, all under
_workspace/experiments/audio-smoke/master-disciple-smoke/m4a/)

- ch01a-three-thanks-and-the-persian-awakening.m4a — full episode, Daniel-led
  (judged robotic; superseded)
- casting/casting-{A-george,B-brian,C-bill,D-audition}-*.mp3 — English casting
  round (B approved for English, superseded by Arabic exploration)
- arabic-samples/S1-S5 — pronunciation matrix (S5 = Mohammed+Sarah native
  script, approved accents)
- arabic-samples/P1-P4 — American-accent Arabic pairs (rejected)
- arabic-samples/P5 — Mohammed+Sarah on real Quran 14:7 + the book's own
  mirage Arabic (approved pronunciation)
- arabic-samples/P6 — interactive take, heavy tags (interactivity good,
  male recolored — too slow)
- arabic-samples/P7-male-speed-120.mp3 — light male tags + profile speed 1.2
  (AWAITING VERDICT — start here)
