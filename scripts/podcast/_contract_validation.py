"""_contract_validation.py — single source of truth for chapter-contract validation.

FIX 14 (2026-06-11): contract validation used to be fragmented across three
layers with three different coverage sets:

  smoke gate ($0)  <  extract (validate_contract)  <  pipeline_lint (post-authoring)

so a defective contract burned progressively more time/money the deeper its
defect sat. Three real failure classes from the-master-and-the-disciple run:
  (a) episode_format=debate with no `debate:` block — caught only at extract,
      after the $0 pre-loop smoke gate had already passed the book;
  (b) slug/chapter_ref renamed without the chapter file — caught at extract;
  (c) debate.host_a/host_b.role outside the R-HOST-ROLE-PARITY enums — caught
      only by pipeline_lint AFTER an ~11-minute framing authoring, because
      extract checked role non-emptiness but not the enum.

This module is the ONE validator. Four gates call it:

  1. phases/preflight_chapter.smoke_check_chapter — $0 pre-loop smoke gate
  2. _extract_contract.validate_contract          — extract time (sys.exit wrapper)
  3. pipeline_lint.lint_chapter_and_framing       — deterministic post-authoring lint
  4. phases/initial_driver `_run_0d` post-write gate — fail 0d BEFORE 0e spend

`validate_contract_full()` RETURNS findings (list[str]) and never raises or
sys.exits; each gate decides its own failure surface ((ok, reason) tuple,
sys.exit, P0 finding dict, AuthoringError). Add new contract rules HERE so
every gate inherits them at once — never inline a contract check in a caller.

Import layering (no cycles): this module imports _rules, _validators and
_extract_yaml only. _extract_contract imports THIS module (not vice versa).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _rules import ALLOWED_CATEGORIES, EPISODE_FORMAT_ALLOWED
from _validator_constants import CH_PATTERN
from _validators import validate_host_role_parity
from _extract_yaml import load_yaml

# ─────────────────────────────────────────────────────────────────────────────
# Canonical enums (moved verbatim from _extract_contract.validate_contract so
# extract/lint/smoke/0d-gate all enforce the same sets).
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ["chapter_ref", "slug", "source_type", "title", "audience", "angle",
                   "host_dynamic", "key_tensions"]

VALID_ANGLES = {
    # Islamic scholarly angles (R-ANGLE family)
    "faithful_exposition", "personal_application",
    "critical_dialectical", "comparative",
    # Fiction / narrative angles
    "faithful_narrative",
}

VALID_ADAPTATION_MODES = {"faithful", "bridge", "modern_paraphrase"}

VALID_SOURCE_TYPES = {"book-chapter", "article", "document", "lecture",
                      "interview", "letter",
                      "synthesized-explainer", "explainer-doc"}

SOURCE_TYPE_TO_CATEGORY = {
    "book-chapter": "books",
    "article":      "articles",
    "document":     "documents",
    "lecture":      "lectures",
    "interview":    "interviews",
    "letter":       "letters",
    "synthesized-explainer": "explainers",
    "explainer-doc": "explainers",
}

VALID_DEBATE_RESOLUTIONS = {"synthesis", "open", "host_a_concedes",
                            "host_b_concedes", "historical_division"}


# ─────────────────────────────────────────────────────────────────────────────
# The one validator
# ─────────────────────────────────────────────────────────────────────────────

def _find_chapter_file(chapters_dir: Path, slug: str) -> tuple[Path | None, str | None]:
    """Resolve chapters/ch*-<slug>.txt by EXACT slug match. Never raises.

    Returns (path, finding). Exactly one of the two is non-None, except the
    (None, finding) case where no/multiple files match.
    """
    candidates: list[Path] = []
    if chapters_dir.is_dir():
        for f in sorted(chapters_dir.glob("*.txt")):
            m = CH_PATTERN.match(f.name)
            if m and m.group(2) == slug:
                candidates.append(f)
    if not candidates:
        return None, (
            f"contract.slug {slug!r} has no chapter file "
            f"(expected chapters/ch*-{slug}.txt). If the slug/chapter_ref was "
            f"renamed, rename the chapter .txt file in the same change — the "
            f"1:1 chapter ↔ episode mapping (SKILL.md §0) requires them to match."
        )
    if len(candidates) > 1:
        return None, (
            f"multiple chapter files match contract.slug {slug!r}: "
            f"{[c.name for c in candidates]}. Resolve the duplicate."
        )
    return candidates[0], None


def _validate_debate_block(contract: dict[str, Any]) -> list[str]:
    """Full debate-block schema + R-HOST-ROLE-PARITY role enums."""
    findings: list[str] = []
    debate = contract.get("debate")
    if not isinstance(debate, dict) or not debate:
        findings.append(
            "contract.episode_format is 'debate' but contract.debate is null/missing. "
            "Required fields: debate.proposition, debate.host_a, debate.host_b, "
            "debate.resolution. See debate-framing.md §Framing structure."
        )
        return findings

    for required in ("proposition", "host_a", "host_b", "resolution"):
        if not debate.get(required):
            findings.append(
                f"contract.debate.{required} is missing or empty. "
                f"See debate-framing.md §Vocabulary for what each field means."
            )

    prop = debate.get("proposition")
    if isinstance(prop, str) and prop.strip().endswith("?"):
        findings.append(
            f"contract.debate.proposition must be a debatable STATEMENT, not a "
            f"question: {prop.strip()[:120]!r}. Rephrase as the position host_a defends."
        )

    resolution = debate.get("resolution")
    if resolution and resolution not in VALID_DEBATE_RESOLUTIONS:
        findings.append(
            f"contract.debate.resolution {resolution!r} not in {VALID_DEBATE_RESOLUTIONS}."
        )

    for host_key in ("host_a", "host_b"):
        host = debate.get(host_key)
        if host is None:
            continue  # already flagged by the required-keys loop above
        if not isinstance(host, dict):
            findings.append(
                f"contract.debate.{host_key} must be a mapping with role + position + source_moves."
            )
            continue
        for sub in ("role", "position"):
            if not host.get(sub):
                findings.append(f"contract.debate.{host_key}.{sub} is missing or empty.")
        moves = host.get("source_moves")
        if not isinstance(moves, list) or not [m for m in moves if str(m or "").strip()]:
            findings.append(
                f"contract.debate.{host_key}.source_moves must be a non-empty list of "
                f"source-grounded argumentative moves."
            )

    # R-HOST-ROLE-PARITY (Q4) — exact role enums (HOST_A_ROLES_SCHOLAR /
    # HOST_B_ROLES_SEEKER). Reuses the SAME check pipeline_lint always ran, so
    # a descriptive label like 'advocate — voices Salih' now fails at every
    # gate instead of only after an authored framing (failure class (c)).
    findings.extend(validate_host_role_parity(contract))
    return findings


def validate_contract_full(
    contract: dict[str, Any],
    chapter_path: Path | None,
    book_dir: Path,
    *,
    contract_path: Path | None = None,
) -> list[str]:
    """Validate a chapter contract end-to-end. Returns findings; raises nothing.

    Args:
      contract:      the parsed contract mapping.
      chapter_path:  the chapter .txt this contract belongs to, when the caller
                     has already resolved it; None → resolved here from
                     `book_dir/chapters/ch*-<slug>.txt` (a resolution failure is
                     itself a finding — failure class (b)).
      book_dir:      the book directory (parent of chapters/ + chapter-contracts/).
      contract_path: the on-disk contract file. None for stub-generated
                     contracts — title placeholder/uniqueness checks are skipped
                     for stubs, matching the historical extract behaviour.
    """
    if not isinstance(contract, dict) or not contract:
        return ["contract is not a YAML mapping"]
    findings: list[str] = []

    # 1. Required fields.
    missing = [k for k in REQUIRED_FIELDS if contract.get(k) in (None, "", [])]
    if missing:
        findings.append(
            f"missing required fields: {', '.join(missing)}. "
            f"See scripts/podcast/extract_chapter.py::stub_contract() for the canonical schema."
        )

    # 2. slug ↔ chapter-file match (failure class (b)).
    slug = str(contract.get("slug") or "").strip()
    resolved = chapter_path
    if resolved is None and slug:
        resolved, resolve_finding = _find_chapter_file(Path(book_dir) / "chapters", slug)
        if resolve_finding:
            findings.append(resolve_finding)
    if resolved is not None:
        m = CH_PATTERN.match(resolved.name)
        file_slug = m.group(2) if m else None
        if slug and file_slug and slug != file_slug:
            findings.append(
                f"contract.slug ({slug!r}) does not match chapter slug ({file_slug!r}). "
                f"Under the 1:1 chapter ↔ episode mapping (SKILL.md §0), these must match exactly."
            )
        chapter_ref = str(contract.get("chapter_ref") or "").strip()
        # Normalize: chapter_ref may carry a path prefix and/or .txt suffix.
        ref_stem = chapter_ref.rsplit("/", 1)[-1]
        if ref_stem.endswith(".txt"):
            ref_stem = ref_stem[: -len(".txt")]
        if ref_stem and ref_stem != resolved.stem:
            findings.append(
                f"contract.chapter_ref ({chapter_ref!r}) does not match the chapter "
                f"file stem ({resolved.stem!r}). Rename one side so they agree."
            )

    # 3. Title discipline (INVARIANT 6) — on-disk contracts only (stubs carry
    #    [TODO] placeholders by design).
    if contract_path is not None:
        title = contract.get("title")
        if isinstance(title, str):
            stripped = title.strip()
            if not stripped or stripped.startswith("[TODO]"):
                findings.append(
                    "contract.title is a TODO placeholder. Set a real concise title "
                    "(≤ 60 chars; ≤ 6 words; unique within the book) before extracting."
                )
            elif len(stripped) > 60:
                findings.append(
                    f"contract.title is {len(stripped)} chars (>60). "
                    f"Per SKILL.md INVARIANT 6, chapter titles must be concise."
                )
            else:
                collisions: list[str] = []
                for sibling in sorted(contract_path.parent.glob("*.yml")):
                    if sibling == contract_path:
                        continue
                    try:
                        other = load_yaml(sibling.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    other_title = str((other or {}).get("title") or "").strip()
                    if other_title and other_title.lower() == stripped.lower():
                        collisions.append(f"{sibling.name}: {other_title!r}")
                if collisions:
                    findings.append(
                        f"contract.title {stripped!r} duplicates another chapter in this book: "
                        + "; ".join(collisions)
                        + ". Per SKILL.md INVARIANT 6, every chapter must have a unique title."
                    )

    # 4. Enum fields.
    angle = contract.get("angle")
    if angle not in VALID_ANGLES:
        findings.append(f"contract.angle {angle!r} not in {VALID_ANGLES}.")

    mode = contract.get("adaptation_mode")
    if mode not in VALID_ADAPTATION_MODES:
        findings.append(f"contract.adaptation_mode {mode!r} not in {VALID_ADAPTATION_MODES}.")

    episode_format = contract.get("episode_format") or "deep_dive"
    if episode_format not in EPISODE_FORMAT_ALLOWED:
        findings.append(
            f"contract.episode_format {episode_format!r} not in {EPISODE_FORMAT_ALLOWED}. "
            f"See infra/claude-agents/podcast-challenger.md Category P for the debate spec; "
            f"_rules.EPISODE_FORMAT_ALLOWED is the current allowed set."
        )

    # 5. Debate block — full schema + role enums (failure classes (a) + (c)).
    if episode_format == "debate":
        findings.extend(_validate_debate_block(contract))

    # 6. source_type enum + library/<category>/ folder coupling.
    source_type = contract.get("source_type")
    if source_type not in VALID_SOURCE_TYPES:
        findings.append(f"contract.source_type {source_type!r} not in {VALID_SOURCE_TYPES}.")
    elif resolved is not None:
        try:
            actual_category = resolved.parents[2].name
        except IndexError:
            actual_category = None
        expected_category = SOURCE_TYPE_TO_CATEGORY[source_type]
        if actual_category in ALLOWED_CATEGORIES and actual_category != expected_category:
            findings.append(
                f"contract.source_type {source_type!r} requires the chapter to live under "
                f"<root>/{expected_category}/<book-slug>/, but the chapter resolved to a path "
                f"under .../{actual_category}/ ({resolved}). Fix: move the chapter to the "
                f"{expected_category}/ category, or change contract.source_type to match."
            )

    return findings


# ─────────────────────────────────────────────────────────────────────────────
# Book-level sweep (Phase-0d post-write gate + ad-hoc audits)
# ─────────────────────────────────────────────────────────────────────────────

def validate_book_contracts(book_dir: Path) -> list[tuple[str, list[str]]]:
    """Validate every chapter-contracts/*.yml in a book. Never raises.

    Returns [(contract_slug, findings), ...] for contracts with ≥1 finding;
    an empty list means every contract would pass extract AND pipeline_lint.
    """
    failures: list[tuple[str, list[str]]] = []
    contracts_dir = Path(book_dir) / "chapter-contracts"
    for cpath in sorted(contracts_dir.glob("*.yml")):
        try:
            contract = load_yaml(cpath.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — parse failure is a finding, not a crash
            failures.append((cpath.stem, [f"contract parse error: {type(e).__name__}: {e}"]))
            continue
        findings = validate_contract_full(contract, None, book_dir, contract_path=cpath)
        if findings:
            failures.append((cpath.stem, findings))
    return failures
