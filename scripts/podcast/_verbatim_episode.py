"""Phase 0d's verbatim-episode writer: proofread and Arabic-restore, never author.

Split out of `_authoring/_chapter_design.py` (2026-08-30, DR-005): that file is
a grandfathered over-limit module — "split, never grow" — and this function
was the growth. It belongs on its own regardless: `_chapter_design.py` is the
per-source-chapter AUTHORING loop, and this is the thing that runs INSTEAD of
authoring for a book with `episode_voice: verbatim`.

See `_pipeline_flags.episode_voice` for the knob, and `_verbatim_correct` for
the proofread/Arabic-restore pair this calls.
"""

from __future__ import annotations

from pathlib import Path


def write_verbatim_chapter(
    book_dir: Path,
    *,
    book_slug: str,
    sc_idx: int,
    sc_title: str,
    slice_text: str,
    chapter_path: Path,
    contract_path: Path,
    ep_num: int,
    audience_profile: str,
    log,
) -> tuple[int, int]:
    """Phase 0d, verbatim mode: proofread and Arabic-restore, never author.

    Added 2026-08-30 (`purification-of-the-heart`): the normal per-source-chapter
    path hands the slice to a full episode-authoring prompt — concept sections,
    an opening hook, a word-count target — and the model does exactly what that
    asks, which is rewrite. This path never calls that prompt. It reuses the
    same proofread-and-restore pair the Sessions lane uses for exactly this
    reason (`_verbatim_correct.correct`/`restore_script`): fix transcription
    noise, put the Arabic back, change nothing else. `correct` reverts any
    window that drops below 90% of the speaker's own vocabulary, so a window it
    cannot safely touch is left as the raw transcription rather than lost.

    ONE FILE PER SOURCE CHAPTER, always — a verbatim book's `episode_count` is
    forced to 1 before this is ever called (see the caller's loop), regardless
    of what phase 0d's own TOC step planned. The TOC step's session/topic
    boundaries are real chapter-design work and are kept; splitting ONE
    continuous session into several episode-length files is a production
    decision about how long a podcast episode should run, which is exactly the
    kind of judgment call this mode exists to not make.

    Returns (windows_reverted, arabic_runs_restored) for the caller's log line.
    """
    from _verbatim_correct import correct as _vc_correct
    from _verbatim_correct import restore_script as _vc_restore_script

    label = f"sc-{sc_idx:03d}"
    corrected, correct_warnings = _vc_correct(book_dir, slice_text, phase="0d", label=label, log=log)
    corrected, arabic_resolutions = _vc_restore_script(
        book_dir, corrected, phase="0d", label=label, book_title=book_slug, log=log
    )
    chapter_path.write_text(corrected.strip() + "\n", encoding="utf-8")

    restored_count = sum(1 for r in arabic_resolutions if r.ok)
    contract = {
        "chapter_ref": chapter_path.stem,
        "slug": chapter_path.stem.split("-", 1)[-1] if "-" in chapter_path.stem else chapter_path.stem,
        "source_type": "lecture",
        "book_slug": book_slug,
        "source_chapter_ref": sc_idx,
        "episode_number": ep_num,
        "title": sc_title[:60],
        "audience": audience_profile or "General listeners.",
        "angle": "faithful_narrative",
        "angle_note": (
            "Verbatim session — proofread only (spelling, punctuation, paragraph "
            "breaks, obviously dropped words), never rewritten. No angle is "
            "chosen; the recording sets its own."
        ),
        "episode_format": "monologue",
        "format_rationale": "One continuous recorded session, presented as delivered — no hosts, no discussion format.",
        "essential": "core",
        "essential_rationale": "A session of the source recording.",
        "host_dynamic": "verbatim",
        "host_dynamic_rationale": "No hosts — this is the speaker's own recorded words.",
        "length_target": f"{len(corrected.split()):,}",
        "key_tensions": ["None — presented as the speaker recorded it, with no editorial angle imposed."],
        "tone_constraints": [],
        "anchor_passages": [],
        "adaptation_mode": "faithful",
        "phonetic_overrides": [],
        "show_notes": [],
        "thesis_relevance": "Part of the recorded series.",
        "sermon": {"present": False},
    }
    import yaml as _yaml

    contract_path.write_text(_yaml.safe_dump(contract, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return len(correct_warnings), restored_count


def _audience_profile(book_dir: Path) -> str:
    try:
        import yaml as _yaml

        cfg = _yaml.safe_load((book_dir / "_system" / "series-config.yaml").read_text(encoding="utf-8")) or {}
        return str(cfg.get("audience_profile") or "")
    except Exception:
        return ""


def _chapter_concepts(chapter_path: Path, book_slug: str) -> list[str]:
    """Concept-section H2 titles, for the cross-chapter doctrine-dedup ledger
    (R-NO-DOCTRINE-REPEAT) `_chapter_design.py` threads through every source
    chapter, authored or verbatim alike — same deterministic extraction that
    module uses, called here rather than passed in as a closure."""
    try:
        from chapter_density_audit import audit_chapter

        return [s.title.strip() for s in audit_chapter(chapter_path, book_slug, "").concept_sections if s.title]
    except Exception:
        return []


def handle_verbatim_source_chapter(
    book_dir: Path,
    sc_idx: int,
    sc_title: str,
    slice_text: str,
    chapter_path: Path,
    contract_path: Path,
    ep_num: int,
    plan_sessions,
    done_marker: Path,
    taught_concepts: list,
    log,
) -> None:
    """`write_verbatim_chapter` plus every bit of loop bookkeeping the caller
    does identically for an authored chapter: session-group stamping, the
    done-marker checkpoint, the doctrine-dedup ledger, and the log line —
    moved here too so the (grandfathered, may-shrink-never-grow) caller stays
    a single short call.
    """
    book_slug = book_dir.name
    reverted, restored = write_verbatim_chapter(
        book_dir,
        book_slug=book_slug,
        sc_idx=sc_idx,
        sc_title=sc_title,
        slice_text=slice_text,
        chapter_path=chapter_path,
        contract_path=contract_path,
        ep_num=ep_num,
        audience_profile=_audience_profile(book_dir),
        log=log,
    )
    if plan_sessions:
        from _sessions import session_for_episode, stamp_contract

        session = session_for_episode(plan_sessions, ep_num)
        if session is not None:
            stamp_contract(contract_path, session, ep_num)
    done_marker.write_text(
        f"sc_index={sc_idx}\nsource_title={sc_title}\nepisode_count=1\nverbatim=true\n", encoding="utf-8"
    )
    taught_concepts.extend(_chapter_concepts(chapter_path, book_slug))
    log(
        f"    sc {sc_idx:03d} · verbatim · {reverted} window(s) reverted to raw "
        f"transcription · {restored} Arabic run(s) restored to script"
    )
