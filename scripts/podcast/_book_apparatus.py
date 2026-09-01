"""_book_apparatus.py — the deterministic tail of a book compose.

Everything `compose_book_v2` does AFTER its model passes: the Composer-edit
replay, then the house-style and Arabic apparatus, the audits, the comprehension
bridges, the honorific convention and the paragraph alignment. No model writes
prose here. Two steps still call a model for a JUDGMENT that is then persisted
and never re-asked (the annotation policy and the etymology atoms), and both are
idempotent — once the answer is in `glossary.yml` they are free forever.

Split out of `_book_pipeline_v2` on 2026-08-02, for a reason the compose path
alone could not serve: the apparatus was reachable ONLY by running the whole
compose, whose earlier stages DO re-run models over the prose. That made
"bring this book's Arabic up to the current rules" cost a full re-composition —
which for `the-master-and-the-disciple` would have rewritten eight of nine
chapters of an approved reference edition, and for `al-anwaar-al-lateefah` and
`asaas-al-taveel` would have run the fluency pass under a narrative frame neither
book declares, rewriting both into the wrong grammatical person.

ONE DEFINITION, TWO CALLERS. `compose_book_v2` calls this as its own tail, and
`apply_book_apparatus.py` calls it standalone over a book already on disk. There
is no second copy of the sequence, so the two cannot drift; a test pins the
delegation.

Every step is idempotent by construction — each undoes its own previous output
before re-deriving — so a standalone run over an already-apparatus'd book is a
no-op rather than a doubling.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# The step vocabulary and its recorder live in `_apparatus_steps`: the review gate
# needs the LIST and nothing else, and that list is a contract shared by this module,
# `_compose_skips`' page-altering/advisory classification, and the gate. Both names are
# re-exported here because callers and tests already reach for them at this path.
from _apparatus_steps import APPARATUS_STEPS as APPARATUS_STEPS  # noqa: PLC0414
from _apparatus_steps import record_ok as _ok
from _book_reports import run_defect_scan, run_report_steps
from _compose_skips import record_skip as _record_skip


def apply_book_apparatus(
    book_dir: Path,
    *,
    log=print,
    force: bool = False,
    stages: dict | None = None,
) -> Path:
    """Run the deterministic tail over ``book/book.md``. Returns that path.

    ``stages`` carries the per-stage Arabic counts the model passes stamped, so
    the audit can name the stage a quotation went missing in. A standalone run
    has no model stages and passes nothing; the audit then reports the final
    count alone, which is the honest answer for a run that changed no prose.
    """
    book_dir = Path(book_dir).resolve()
    stages = {} if stages is None else stages
    book_md = book_dir / "book" / "book.md"

    # 5a-replay. Replay durable Book Composer edits, and stamp the per-chapter
    #     fingerprints the Composer quotes back on its next save.
    #
    #     Since 2026-07-21 the model stages above SKIP any chapter carrying a
    #     Composer edit, so this is normally a confirming pass rather than a rescue.
    #     It stays because it is what makes the guarantee unconditional: under
    #     `--force`, and for any stage that grows a new path to book.md, the
    #     author's chapter is restored here and the overwrite is reported.
    #
    #     It runs BEFORE the deterministic house-style passes below, not after.
    #     After was wrong and cost the authored chapters their inline Arabic: the
    #     script pass ran, annotated the human's terms, and then the replay wrote
    #     the raw saved body back over the annotations, so exactly the chapters
    #     someone cared enough to author printed with no Arabic beside their terms
    #     — and gate B3 counts Arabic runs book-wide, so nothing noticed. Replaying
    #     first means transliteration, script, spelling and honorifics all see the
    #     final text, the author's chapters included, instead of a version of it.
    #     Idempotent and anchored by heading — see _book_edits.py.
    #
    #     The replay must also keep the pass reports honest (RCA-001): fluency
    #     and voice wrote "adapted" BEFORE this step, so a replayed edit landing
    #     on an adapted chapter — under `--force`, or from a save that arrived
    #     mid-run — makes that claim stale in the same compose that wrote it,
    #     and in July 2026 exactly that report waved 8 discarded chapters
    #     through every gate. The reconcile re-stamps those chapters
    #     'adapted-then-overwritten', and the discard is announced here, loudly,
    #     because it means model spend bought prose the book does not carry.
    from _book_edits import apply_composer_edits
    from _book_pass_reports import reconcile_reports_after_replay

    _replay_report = None
    try:
        _replay_report = apply_composer_edits(book_dir, log=log, force=force)
        book_md = book_dir / "book" / "book.md"
        _ok(book_dir, "composer-edits")
    except Exception as e:  # a bad sidecar must never destroy a good compose
        _record_skip(book_dir, "composer-edits", e, log)

    # The reconcile gets its OWN guard, deliberately not shared with the replay's.
    # Sharing one try block meant a reconcile failure was recorded as a
    # "composer-edits" skip — telling the operator their edits were dropped when
    # the replay had in fact applied them — while ALSO suppressing the discard
    # warning and leaving the stale "adapted" in place: the one failure mode this
    # step exists to end, hidden behind a false skip record.
    if _replay_report is not None:
        try:
            _discarded = reconcile_reports_after_replay(book_dir, _replay_report, log=log)
            if _discarded:
                log(
                    f"    WARNING: composer-edit replay DISCARDED adapted prose in {_discarded} chapter(s) — "
                    "the pass reports now read 'adapted-then-overwritten'; that model spend bought text "
                    "the book does not carry"
                )
            _ok(book_dir, "report-reconcile", changed=int(_discarded or 0))
        except Exception as e:  # a truth-teller must never fail the compose it describes
            _record_skip(book_dir, "report-reconcile", e, log)

    # 5c. Take the machine preface OUT (Asif, 2026-08-03 — no book needs one; they
    #     begin with the actual content chapters). This slot used to AUTHOR that
    #     preface; the authoring path is retired in `_book_frontmatter` and only
    #     the cleanup remains.
    #
    #     The position is unchanged and still forced, for a reason that survives
    #     the reversal: AFTER the Composer replay. A fence written while the old
    #     path was live can sit inside a saved Composer edit — it does in
    #     `degrees-of-excellence` — so the replay puts it back into book.md on
    #     every run, and a cleanup placed before the replay would report a preface
    #     removed from a file that ends the compose still carrying one.
    #
    #     Costs nothing and claims nothing: a book that never had a preface, or has
    #     already been cleaned, is left byte-identical.
    from _book_frontmatter import clear_introduction

    try:
        clear_introduction(book_dir, log=log)
        _ok(book_dir, "front-matter")
    except Exception as e:  # apparatus is never worth a finished translation
        _record_skip(book_dir, "front-matter", e, log)

    # 5d. Fold what remains of the front matter — the SOURCE's own opening — into
    #     chapter 1, so the edition begins on the book.
    #
    #     The assembly in `_translation_edition` folds too, and this is not a
    #     duplicate of it: that path only runs when a book is COMPOSED, and for a
    #     book already written a compose is a re-translation. On 2026-08-03 taking
    #     that route on `ayyuhal-walad` — whose front matter was the only thing
    #     meant to change — cost 615 words of teaching and 38 quotation-length
    #     Arabic runs, the closing supplication of chapter 9 among them, with no
    #     gate failing. Both paths are idempotent and neither can double, because
    #     each looks for a front-matter section the other has already removed.
    #
    #     STRICTLY AFTER the clear above: the retired machine preface sits INSIDE
    #     that section, so folding first would carry into chapter 1 the one text
    #     this change exists to delete.
    from _book_opening import apply_opening_fold

    try:
        apply_opening_fold(book_dir, log=log)
        _ok(book_dir, "opening-fold")
    except Exception as e:  # apparatus is never worth a finished translation
        _record_skip(book_dir, "opening-fold", e, log)

    # 5e. The edition's introduction (Asif, 2026-08-03): short, honestly titled
    #     `## Introduction to the Book`, unnumbered, and written in the SAME
    #     articulation register as the chapters so it does not read as a different
    #     hand. Applies to EVERY PDF route, which is why it lives here rather than
    #     on one composer — the apparatus is the one tail all routes share.
    #
    #     AFTER the fold, necessarily. The fold moves the front-matter section into
    #     chapter 1, and an introduction injected first would be inside the section
    #     being moved — carried into chapter 1 with the author's own words, which
    #     is the exact confusion the retired preface created.
    #
    #     BEFORE every house-style step below, which is the 2026-08-02 lesson kept:
    #     run after them and the introduction goes to press as the one part of the
    #     book no house rule has touched — no transliteration fold, no surah-named
    #     citations, no glossary overlay, no vowelling, no American spelling.
    #     Costs one model call per book, ever: the text is cached and the cache is
    #     the idempotency marker.
    from _book_frontmatter import apply_introduction

    try:
        apply_introduction(book_dir, log=log, force=force)
        _ok(book_dir, "introduction")
    except Exception as e:  # apparatus is never worth a finished translation
        _record_skip(book_dir, "introduction", e, log)

    # 5a-translit. Fold scholarly transliteration to the plain house form, AFTER
    #     the model passes. The base composer already does this at the end of its
    #     own run (_translation_edition), but the fluency and augment passes come
    #     later and write whatever spelling they please — a rebuild on 2026-07-21
    #     came out of them carrying Shu'ayb, Ka'b, ta'wil, du'at and Ma'mur again,
    #     apostrophes and all. That is not only the wrong house style: the
    #     inline-Arabic pass below matches glossary terms against this text, so an
    #     un-folded "Bayt al-Ma'mur" silently matches nothing and the term loses
    #     its script. Folding here is what makes the two steps below reliable.
    from _translit import simplify_transliteration

    try:
        _md = book_dir / "book" / "book.md"
        if _md.exists():
            _before = _md.read_text(encoding="utf-8")
            _after = simplify_transliteration(_before)
            if _after != _before:
                _md.write_text(_after, encoding="utf-8")
                log("    translit: folded to plain transliteration")
        _ok(book_dir, "translit")
    except Exception as e:  # never worth a finished translation
        _record_skip(book_dir, "translit", e, log)

    # 5a-quran. Put the Arabic of every cited Qur'anic verse onto the page. Zero
    #     model spend and zero model judgment: the EXTENT comes from the source
    #     scan (what the author actually quoted) and the LETTERS come from the
    #     canonical mushaf in content/knowledge-base/mirror.db, so no model is ever
    #     asked to recall scripture.
    #
    #     POSITION IS FORCED, from four directions. After every LLM pass and after
    #     the Composer replay, for the same reason 5a-arabic is (nothing may
    #     romanize the script away afterwards). BEFORE 5a-arabic, so the glossary
    #     overlay sees the verse already on the page and its "script is already
    #     here" suppression fires — otherwise a chapter prints `Adam (آدم)` two
    #     lines under a verse containing آدم. Before step 6, so the audit resolves
    #     these runs as canonical-mushaf and the reading edition sets them in the
    #     Uthmanic face. And before steps 10-11, because align_book fingerprints
    #     paragraphs and inserting blocks after it would describe a document that
    #     no longer exists.
    try:
        from _book_quran import inject_book as _inject_quran

        _inject_quran(book_dir, log=lambda m: log(f"    {m}"))
        _ok(book_dir, "quran-arabic")
    except Exception as e:  # a missing verse must never fail a finished translation
        _record_skip(book_dir, "quran-arabic", e, log)

    # 5a-citations. Name the surah in every citation (Asif, 2026-08-01): `(2:24)`
    #     becomes `(Al-Baqarah: 24)`. A bare number is a lookup key, not a
    #     reference — it asks a reader who does not read Arabic to already know
    #     which surah 2 is. Every printed translation names it.
    #
    #     IMMEDIATELY AFTER 5a-quran, and that order is load-bearing in one
    #     direction only. The injection above reads citations to decide which
    #     verse to set, and `_book_citations.find_citations` reads BOTH the
    #     numeric and the named form precisely so a re-compose of an
    #     already-renamed book still finds its 23 cited verses. Running the
    #     rename first would therefore still work — it is placed second because
    #     the numeric form is what every upstream pass and report speaks, and the
    #     house form is the last word before the page.
    try:
        from _book_citations import rename_book as _name_surahs

        _name_surahs(book_dir, log=lambda m: log(f"    {m}"))
        _ok(book_dir, "citation-names")
    except Exception as e:  # a citation's spelling must never fail a translation
        _record_skip(book_dir, "citation-names", e, log)

    # 5a-glossary-harvest. Teach the glossary the vocabulary the book already
    #     teaches, and give those terms their Arabic. THE ROOT FIX for a book whose
    #     script never reaches the page, and it belongs HERE — before the policy
    #     classifies the terms and long before `5a-arabic` annotates them.
    #
    #     Everything downstream that puts Arabic on the page is glossary-driven, and
    #     the glossary's own generator has been dead since 2026-06-08:
    #     `build_glossary` reads `_system/source/text/_phonetics.md`, which nothing
    #     writes any more, so every book created since then falls through to a
    #     hard-coded thirty-term list. `degrees-of-excellence` matched none of them
    #     and had ELEVEN entries against the 177 terms its own prose glosses; both
    #     Mukhtasar volumes have no glossary at all. `harvest_gloss_terms` existed
    #     to fix exactly this and was never wired into anything — the only importer
    #     was the ship gate, which MEASURED the starvation without curing it. So
    #     every book composed after the fix reproduced the fault it diagnosed.
    #
    #     The book is its own missing input: a scholarly edition teaches its
    #     vocabulary in parentheses — `the ranks (hudud)` — so reading those back
    #     out recovers the source's own apparatus rather than inventing one.
    #     Naturalized English (`imam`, `quran`, prophet names) is excluded by
    #     `_gloss_terms.absorbed_english`, per the 2026-08-02 scope: the rule is
    #     about Arabic VOCABULARY, not about words English has already absorbed.
    #
    #     Harvest is deterministic and free. The Arabic fill is gated on the harvest
    #     having actually ADDED rows, which is the difference between filling new
    #     terms once and re-asking a model on every compose about the handful whose
    #     script the scan does not contain — those stay empty, stay romanized, and
    #     are reported by gate B7 rather than invented from recall.
    from harvest_gloss_terms import MARKER as _HARVEST_MARKER
    from harvest_gloss_terms import apply as _apply_harvest
    from harvest_gloss_terms import harvest as _harvest

    try:
        if (book_dir / "_system" / _HARVEST_MARKER).exists() and not force:
            log("    glossary-harvest: already harvested — skipped")
        else:
            _plan = _harvest(book_dir)
            if _plan.get("error"):
                log(f"    glossary-harvest: {_plan['error']}")
            else:
                _added = _apply_harvest(book_dir, _plan)
                log(
                    f"    glossary-harvest: {_plan['candidates']} glossed term(s) in the prose · "
                    f"{_plan['known']} already known · {_added} added"
                )
                if _added:
                    # The CLI, not an imported function: its logic lives in `main()`
                    # and pulling it apart is a refactor this step does not need.
                    # Exit codes are documented, and it is idempotent — a row that
                    # already has script is never refilled without --force.
                    _fill = subprocess.run(
                        [
                            sys.executable,
                            str(Path(__file__).parent / "fill_glossary_arabic.py"),
                            "--book-dir",
                            str(book_dir),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=900,
                    )
                    for _line in (_fill.stderr or "").strip().splitlines()[-4:]:
                        log(f"    glossary-fill: {_line.strip()}")
                    if _fill.returncode != 0:
                        log(f"    glossary-fill: rc={_fill.returncode} — new terms stay romanized until filled")
        _ok(book_dir, "glossary-harvest")
    except Exception as e:  # a starved glossary must never cost a finished book
        _record_skip(book_dir, "glossary-harvest", e, log)

    # 5a-policy. Classify the glossary's annotation policy — ONCE per book. Which
    #     terms deserve an inline annotation is a judgment call, so a model makes
    #     it, and it is durable: proposals land in glossary.yml where a human can
    #     override any line, and entries already carrying a class are never
    #     touched again, so this is a no-op (and zero cost) on every compose
    #     after the first. Per the learning-loop rule, suggestions are pre-applied
    #     and visible (_system/annotation-policy-report.json), never silent.
    from _annotation_policy import propose_annotation_policy

    try:
        propose_annotation_policy(book_dir, log=log)
        _ok(book_dir, "annotation-policy")
    except Exception as e:  # a policy miss must never cost a finished book
        _record_skip(book_dir, "annotation-policy", e, log)

    # 5a-etymology. Root-level etymology atoms for the book's key Arabic terms —
    #     grounded in the Quranic morphology corpus (real roots + derived
    #     families, see _etymology.load_morphology_reference) and gated by the
    #     deterministic veto + adversarial verify before anything persists.
    #     ONCE per book: the report is the idempotency marker (delete
    #     _system/etymology-report.json to re-run), so recomposes never re-spend
    #     the two claude -p calls. Glossary-gated — only 0c books (Islamic
    #     scholarly) carry one, so fiction/technical routes skip at zero cost.
    from _etymology import build_etymology_atoms

    try:
        _ety_report = book_dir / "_system" / "etymology-report.json"
        if not (book_dir / "_system" / "glossary.yml").exists():
            log("    etymology: no glossary — skipped")
        elif _ety_report.exists():
            log("    etymology: report already present — skipped (delete _system/etymology-report.json to re-run)")
        else:
            build_etymology_atoms(book_dir, log=log)
        _ok(book_dir, "etymology")
    except Exception as e:  # an apparatus miss must never cost a finished book
        _record_skip(book_dir, "etymology", e, log)

    # 5a-glossary-vowel. Mark the GLOSSARY's Arabic, and do it BEFORE the overlay
    #     below — the overlay inserts whatever the glossary holds, so a bare
    #     glossary prints bare terms however well the quotations are vowelled.
    #     Order matters in one direction only, and it is not negotiable: changing
    #     the glossary AFTER an overlay exists leaves `_normalize_annotations`
    #     unable to recognise the annotation it already wrote (it keys on the old
    #     script), so it annotates on top of it — measured on 2026-07-29 as
    #     `Tur (اَلطُّور), الطور)`, a doubled parenthetical in live prose.
    #     See vowel_glossary.py.
    from vowel_glossary import vowel_glossary

    try:
        vowel_glossary(book_dir, log=lambda m: log(f"    {m}"))
        _ok(book_dir, "glossary-vowelling")
    except Exception as e:  # marks are never worth a finished book
        _record_skip(book_dir, "glossary-vowelling", e, log)

    # 5a-arabic. Put the Arabic script back beside inline terms. AFTER every
    #     LLM text pass, so no model can romanize the script away again, and AFTER
    #     the Composer replay, so it annotates the author's chapters too — before
    #     the replay it annotated them and the replay wrote the raw saved body back
    #     over its work. BEFORE the audits, so the Arabic audit judges exactly what
    #     prints. Deterministic and glossary-driven — no model, no cost, nothing
    #     recalled. See _book_inline_arabic.py.
    from _book_inline_arabic import apply_inline_arabic

    try:
        apply_inline_arabic(book_dir, log=lambda m: log(f"    {m}"))
        book_md = book_dir / "book" / "book.md"
        _ok(book_dir, "inline-arabic")
    except Exception as e:  # an overlay is never worth a finished translation
        _record_skip(book_dir, "inline-arabic", e, log)

    # 5a-shape. A cited book under its English name; every Arabic quotation a
    #     blockquote holding its own rendering. AFTER 5a-arabic — the overlay is
    #     also the strip pass, and both read what it leaves. See _book_shape.py.
    from _book_shape import apply_book_shape

    try:
        apply_book_shape(book_dir, log=lambda m: log(f"    {m}"))
        _ok(book_dir, "text-shape")
    except Exception as e:  # a printed shape is never worth a finished book
        _record_skip(book_dir, "text-shape", e, log)

    # 5a-vowelling. Put the vowel marks on the Arabic (Asif, 2026-07-29 — this
    #     reverses the rule that a model may never supply tashkeel). AFTER the
    #     inline-Arabic overlay, so glossary script inserted there is marked too,
    #     and after every prose pass, so nothing rewrites a run once it is
    #     vowelled. BEFORE the audits, so what they judge is what prints.
    #     Qur'anic runs are skipped — the canonical mushaf already vowels them —
    #     and every answer must come back with a byte-identical consonantal
    #     skeleton or it is refused and recorded. See vowel_book.py.
    from vowel_book import vowel_book

    try:
        vowel_book(book_dir, log=lambda m: log(f"    {m}"))
        book_md = book_dir / "book" / "book.md"
        _ok(book_dir, "vowelling")
    except Exception as e:  # marks are never worth a finished book
        _record_skip(book_dir, "vowelling", e, log)

    # 5a-substitute. Romanization OUT, script IN — the third operation, and the
    #     one that finishes Asif's 2026-08-02 rule: "zero English transliteration
    #     of Arabic terms in book.md". `_book_inline_arabic` CONVERTS a bracket the
    #     author wrote and ANNOTATES a term he did not, but neither reaches a term
    #     the prose simply uses in romanization (`the *mawaddah*`), nor collapses
    #     the appended shape it produced itself (`amal (عَمَل)` -> `عَمَل`).
    #
    #     AFTER 5a-vowelling on purpose: the script this puts into running prose
    #     is the glossary's, and the glossary is marked by 5a-glossary-vowel, so
    #     what lands is already vowelled — which is the whole reason the rule is
    #     readable rather than hostile to a reader without Arabic.
    #
    #     Reversible by sidecar rather than by inference: substitution removes the
    #     romanization that `_normalize_annotations` uses as its anchor, so the
    #     pre-substitution body is stored per chapter and restored before each
    #     re-derivation. Deterministic, glossary-driven, no model, no cost.
    #     See _book_substitution.py.
    from _book_substitution import apply_arabic_substitution

    try:
        apply_arabic_substitution(book_dir, log=lambda m: log(f"    {m}"))
        book_md = book_dir / "book" / "book.md"
        _ok(book_dir, "arabic-substitution")
    except Exception as e:  # a script swap is never worth a finished book
        _record_skip(book_dir, "arabic-substitution", e, log)

    # 5a-spelling + 5a-opening. The typographic pair — one spelling standard, and
    #     a capital at the head of every chapter. Both change how the book is SET
    #     and not what it says, both need the final wording, and both were lifted
    #     into _book_typography (2026-08-31) when the line cap forced a split.
    #     Same position in the sequence, same order within it.
    from _book_typography import run_typography_steps

    run_typography_steps(book_dir, log=log)

    # 6-7. The report-only tail — Arabic provenance audit, duplicated-passage sweep,
    #      visual policy. Lifted into _book_reports (2026-08-08): all three are
    #      ADVISORY in _compose_skips and none alters the page, so this was the one
    #      group whose extraction could not change a printed book. Same position in
    #      the sequence, same order within it.
    run_report_steps(book_dir, log=log, stages=stages)

    # 8. Comprehension bridges — LAST, so a fix from a prior review round survives
    #    this compose. Idempotent (strips its own previous output first), so a
    #    convergence loop that re-enters compose many times never accumulates
    #    duplicate bridges. Read-only over the sidecar: only the reviewer writes it.
    from _book_bridges import apply_bridges

    try:
        apply_bridges(book_dir, log=log)
        _ok(book_dir, "bridges")
    except Exception as e:
        _record_skip(book_dir, "bridges", e, log)

    # 9. Honorifics — introduce each in full, then abbreviate. Genuinely LAST,
    #    after the introduction and the bridges, because "first use" is a property
    #    of the whole book AS THE READER MEETS IT and both of those are prose a
    #    reader reads. Run before them, an abbreviation in the introduction sat
    #    ahead of its own expansion — the exact confusion this pass exists to end.
    #    The Arabic audit above therefore counts the abbreviated form; that is the
    #    same limitation bridges already have, and both are report-only.
    #    Deterministic, book-scoped and idempotent; see _honorifics.py.
    #    Unwrap a doubled bracket FIRST, so the first-use scan below reads the
    #    honorific rather than the outer pair around it — and so a book that
    #    nested every occurrence cannot have its introduction "already spelled
    #    out" by a form the reader never sees as one.
    from _honorifics import expand_first_honorific_use, unwrap_nested_honorifics

    try:
        _md = book_dir / "book" / "book.md"
        if _md.exists():
            _before = _md.read_text(encoding="utf-8")
            _text, _unwrapped = unwrap_nested_honorifics(_before)
            _after, _n = expand_first_honorific_use(_text)
            if _unwrapped or _n:
                _md.write_text(_after, encoding="utf-8")
            if _unwrapped:
                log(f"    honorifics: {_unwrapped} doubly-bracketed honorific(s) collapsed to one pair")
            if _n:
                log(f"    honorifics: {_n} first-use honorific(s) spelled out in full")
        _ok(book_dir, "honorifics")
    except Exception as e:  # a convention is never worth a finished book
        _record_skip(book_dir, "honorifics", e, log)

    # 10. Which SOURCE paragraph each English paragraph came from, so the Composer
    #     can show the Arabic behind a passage on demand. GENUINELY last, and the
    #     position is forced rather than chosen: bridges (8) and honorifics (9) both
    #     rewrite book.md after the audits, and this step fingerprints the
    #     paragraphs it aligns. Run any earlier and it would name paragraphs the
    #     shipped book no longer contains, and every pairing would silently miss.
    #
    #     Incremental: a chapter whose block fingerprints are unchanged is skipped
    #     outright, so a re-compose costs nothing. Only a chapter whose prose
    #     actually moved is re-aligned, and only the residue the deterministic pass
    #     cannot settle goes to a model. Skips silently for a book with no Arabic
    #     source or no translation-edition crosswalk.
    from align_arabic_paragraphs import align_book

    try:
        align_book(book_dir, log=lambda m: log(f"    {m}"), apply=True)
        _ok(book_dir, "arabic-alignment")
    except Exception as e:  # an alignment is never worth a finished book
        _record_skip(book_dir, "arabic-alignment", e, log)

    # 11. MIRROR THE PARAGRAPHING onto the Arabic's (Asif, 2026-07-30).
    #
    #     A translation edition's paragraphing belongs to its source. Articulation
    #     splits a long Arabic paragraph into several readable English ones and
    #     splits a speech tag off from the speech, so `قال الغلام: …` — one
    #     paragraph in the source — printed as "The boy said:" on a line of its own
    #     with the quotation beneath. Consecutive English paragraphs from one Arabic
    #     paragraph are merged back into one.
    #
    #     AFTER the alignment, necessarily: the merge is driven by the pairing, and
    #     it rewrites that pairing itself rather than leaving fingerprints naming
    #     paragraphs the merge has just replaced. No model is called — the grouping
    #     is already known exactly. A chapter the human authored in the Composer is
    #     skipped: its paragraphing is a choice, not an artefact.
    from mirror_paragraphs import mirror_book

    try:
        mirror_book(book_dir, log=lambda m: log(f"    {m}"), apply=True)
        _ok(book_dir, "paragraph-mirror")
    except Exception as e:  # paragraphing is never worth a finished book either
        _record_skip(book_dir, "paragraph-mirror", e, log)

    # 11b. Scan the FINISHED page for the five reading-edition defects Asif found by
    #      eye in shipped editions, every one of them after each automatic gate here
    #      had passed the book (2026-08-09). Report-only: the repair is prose, and prose
    #      bound for the PDF belongs to the Book Composer, not to a compose step.
    #
    #      HERE and not with the other three report steps, which run at 6-7. Two of
    #      these checks read what the steps between then and now WRITE — the honorific
    #      convention is applied at 9, the paragraph mirror rewrites quotations at 11 —
    #      so scanning up there would report the honorifics of a page that never reaches
    #      disk. Placed after 11 and before 12, which alters no text.
    run_defect_scan(book_dir, log=log)

    # 12. Re-stamp the substitution sidecar from the FINISHED page, exactly as
    #     5a-replay stamps `composer-base.json`. A fingerprint is only useful if
    #     it names the text the NEXT run will find, and 5a-substitute stamps its
    #     own output with four page-altering steps still to come — spelling at
    #     5a-spelling, the bridges at 8, the honorifics at 9, the paragraph mirror
    #     at 11. So the stored number described a chapter that never reached disk,
    #     every later compose read a mismatch, and the pre-substitution English —
    #     the only copy of it anywhere, since substitution deletes the anchor
    #     `_normalize_annotations` would need — was dropped from the sidecar.
    #
    #     LAST, necessarily and by definition: anything that rewrites book.md
    #     after this point stales the stamp again.
    from _substitution_record import restamp_from_final_book

    try:
        restamp_from_final_book(book_dir, log=lambda m: log(f"    {m}"))
        _ok(book_dir, "substitution-restamp")
    except Exception as e:  # a stamp is never worth a finished book
        _record_skip(book_dir, "substitution-restamp", e, log)

    return book_md
