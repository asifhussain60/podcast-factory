"""intake_launch.py — launch PREP for the intake cockpit (Phase 6, Q10).

``prepare_launch`` does everything that must happen BEFORE the pipeline runs, and
NOTHING that spends: it commits the staged files into the canonical ``_source/``
(atomic — Screen-1 staging → real tree only here), writes ``series-config.yaml``
from the smart-form settings, upserts the ``work.yml`` volume entry for a
multi-volume work, scaffolds ``orchestrator-state.json`` at ``phase=preflight``,
and returns the resolved slug + branch + the launch argv. It does NOT spawn the
orchestrator — the endpoint does that DETACHED, and the user's confirm IS the
Tier-2 spend gate. Keeping prep separate makes it fully unit-testable with no LLM.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402
import _work_manifest as wm  # noqa: E402
import intake_staging as staging  # noqa: E402
from _rules import bucket_for_profile  # noqa: E402

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise ImportError("intake_launch requires PyYAML") from exc

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prepare_launch(
    *,
    title: str,
    settings: dict[str, Any],
    staging_token: str,
    slug: str | None = None,
    work_slug: str | None = None,
    volume: int | None = None,
) -> dict[str, Any]:
    """Stage → canonical commit + config + state scaffold for a single book OR a
    multi-volume work volume. Returns {slug, branch, target, sources, launch}.

    Exactly one of ``slug`` (single book) or (``work_slug`` + ``volume``) must be given.
    """
    profile = settings.get("content_profile") or "islamic_scholarly"
    is_work = bool(work_slug)
    if is_work == bool(slug):
        raise ValueError("provide either slug (single book) OR work_slug+volume")
    if is_work and volume is None:
        raise ValueError("work launch needs a volume number")

    bucket = bucket_for_profile(profile)

    if is_work:
        work_dir = _paths.content_dir(work_slug, profile=profile)
        vol_dir_name = f"vol-{volume:02d}"
        composite = wm.composite_slug(work_slug, vol_dir_name)
        book_dir = work_dir / vol_dir_name
        resolved_slug = composite
    else:
        book_dir = _paths.content_dir(slug, profile=profile)
        resolved_slug = slug

    _paths.ensure_book_skeleton(book_dir)

    # Atomic commit: staged files → canonical _source/ (role validation enforced).
    sources = staging.commit(staging_token, book_dir / "_source")
    primary = next((s for s in sources if s["role"] == "primary_source"), None)

    _write_series_config(book_dir, resolved_slug, title, settings, volume if is_work else None)

    # Multi-volume: upsert this volume into the parent work.yml.
    if is_work:
        manifest = wm.read_manifest(work_dir) or {
            "work_slug": work_slug, "title": title,
            "content_profile": profile, "bucket": bucket, "volumes": [],
        }
        rel_sources = [{"path": f"{vol_dir_name}/_source/{s['path']}", "role": s["role"]} for s in sources]
        entry = {
            "order": volume, "slug": composite, "dir": vol_dir_name,
            "title": settings.get("volume_title") or f"Volume {volume}",
            "source_pdf": (f"{vol_dir_name}/_source/{primary['path']}" if primary else None),
            "sources": rel_sources, "status": "draft",
        }
        others = [v for v in manifest.get("volumes", []) if v.get("dir") != vol_dir_name]
        manifest["volumes"] = sorted(others + [entry], key=lambda v: v.get("order", 0))
        wm.write_manifest(work_dir, manifest)

    branch = _branch_for(resolved_slug, work_slug, profile)
    _write_state(book_dir, resolved_slug, work_slug, volume, profile, primary, branch)

    launch = _launch_argv(is_work, work_slug, resolved_slug, primary, book_dir)
    return {
        "slug": resolved_slug, "branch": branch, "is_work": is_work,
        "target": _paths.relative_to_repo(book_dir),
        "sources": sources, "launch": launch,
    }


def _branch_for(resolved_slug: str, work_slug: str | None, profile: str) -> str:
    from _branching import branch_for_work
    return branch_for_work(work_slug or resolved_slug, profile=profile)


def _write_series_config(book_dir: Path, slug: str, title: str,
                         settings: dict[str, Any], volume: int | None) -> None:
    from _rules import (
        audio_engine_default_for_profile, default_voice_cast_for_profile,
    )

    profile = settings.get("content_profile") or "islamic_scholarly"
    video_style = settings.get("video_style") or "scenic"
    # Audio engine: explicit operator choice (from the voice/engine picker) wins;
    # otherwise the per-profile NEW-book default (islamic_scholarly -> notebooklm,
    # locked 2026-06-13; ElevenLabs is quarantined/dormant — chosen only explicitly).
    audio_engine = (settings.get("audio_engine")
                    or audio_engine_default_for_profile(profile))
    cfg: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "content_profile": profile,
        "source_language": settings.get("source_language") or "en",
        "episode_planning_mode": settings.get("episode_planning_mode") or "chronological",
        "audience_profile": settings.get("audience_profile") or "traditional",
        "conversation_style": settings.get("host_dynamic") or "deep_dive",
        "length_tier": settings.get("length_tier") or "extended",
        "enable_video": video_style != "none",
        "video_style": video_style,
        "audio_engine": audio_engine,
    }
    # Voice cast (library names) — only meaningful on the autonomous engine.
    # The picker sends flat string keys voice_cast_host_a / voice_cast_host_b
    # (matching the Record<string,string> settings shape); a nested voice_cast
    # dict is also accepted. Operator selection wins; else the profile default.
    if audio_engine == "elevenlabs":
        nested = settings.get("voice_cast") if isinstance(settings.get("voice_cast"), dict) else {}
        host_a = settings.get("voice_cast_host_a") or (nested or {}).get("host_a")
        host_b = settings.get("voice_cast_host_b") or (nested or {}).get("host_b")
        if not (host_a and host_b):
            d = default_voice_cast_for_profile(profile)
            host_a, host_b = d.get("host_a"), d.get("host_b")
        if host_a and host_b:
            cfg["voice_cast"] = {"host_a": host_a, "host_b": host_b}
        # Arabic recitation: ElevenLabs pronounces Arabic correctly, so an
        # Islamic book recites verses (from KQur) + key terms (from the glossary)
        # in native Arabic at render. Deterministic, verified-source — safe to
        # default ON. Per-book flag retained (set false to keep phonetic).
        if profile == "islamic_scholarly":
            cfg["elevenlabs_arabic_recitation"] = True
    if volume is not None:
        cfg["volume"] = volume
    (book_dir / "_system" / "series-config.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def _write_state(book_dir: Path, slug: str, work_slug: str | None, volume: int | None,
                profile: str, primary: dict | None, branch: str) -> None:
    state = {
        "schema_version": 1,
        "book_slug": slug,
        "work_slug": work_slug,
        "volume": volume,
        "source_path": (f"{_paths.relative_to_repo(book_dir)}/_source/{primary['path']}"
                        if primary else None),
        "source_kind": "intake-upload",
        "phase": "preflight",
        "phase_status": "pending",
        "last_completed_phase": None,
        "last_error": None,
        "content_profile": profile,
        "branch": branch,
        "status": "draft",
        "started": _now(),
        "updated": _now(),
        "phases": {},
        "intake_via": "intake cockpit (Screen 4)",
    }
    (book_dir / "_system" / "orchestrator-state.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )


def _launch_argv(is_work: bool, work_slug: str | None, slug: str,
                primary: dict | None, book_dir: Path) -> dict[str, Any]:
    """The command the endpoint spawns DETACHED. Work → sequencer; single → orchestrator."""
    if is_work:
        return {"script": "orchestrate_work.py", "args": [work_slug]}
    src = f"{_paths.relative_to_repo(book_dir)}/_source/{primary['path']}" if primary else ""
    return {"script": "orchestrate_book.py", "args": ["--start", src, "--slug", slug]}


def main(argv: list[str] | None = None) -> int:
    """CLI for the endpoint: prep only, prints JSON {ok, result}. Never spawns."""
    import argparse

    p = argparse.ArgumentParser(description="intake launch prep (no spawn)")
    p.add_argument("--title", required=True)
    p.add_argument("--settings", required=True, help="JSON of smart-form settings")
    p.add_argument("--staging-token", required=True)
    p.add_argument("--slug")
    p.add_argument("--work")
    p.add_argument("--volume", type=int)
    args = p.parse_args(argv)
    try:
        result = prepare_launch(
            title=args.title,
            settings=json.loads(args.settings),
            staging_token=args.staging_token,
            slug=args.slug,
            work_slug=args.work,
            volume=args.volume,
        )
    except (ValueError, KeyError) as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    print(json.dumps({"ok": True, "result": result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
