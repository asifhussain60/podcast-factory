"""_translation_chunk.py — one source chunk through the faithful composer.

DR-005 split (2026-08-03), the fourth cut out of ``_translation_edition``: the
config/contract predicates went to ``_translation_contract``, the deterministic
text post-processing to ``_translation_text``, the prompt to
``_translation_prompts``, and now the per-chunk `claude -p` orchestration lands
here. What remains in the parent is the ASSEMBLY — which chunks exist, which are
cached, where the source's own opening goes, how the parts become book.md.

Moved verbatim, and re-exported by the parent under its original private name
(the ``_azure.py`` pattern), so importers and — the reason it matters here — the
test patch target ``_translation_edition._compose_one`` keep working unchanged.

The retries are the module's whole substance and each was earned:

  short output      a first answer under 55% of the source's length is asked
                    again, once, with a longer timeout.
  integrity         a failed gate is retried with THE ACTUAL FINDINGS named. It
                    used to assert "process commentary or model-owned headings"
                    whatever the gate found, so a retry for a lost enumeration
                    re-ran the model with instructions about a defect it did not
                    have, and failed the same way.
  Arabic coverage   an output that dropped too much of the ground truth's quoted
                    Arabic is retried with the dropped spans named. Non-fatal and
                    keep-best: a residual shortfall never blocks a book.

A chunk that is still too compressed, or still fails the integrity gate, raises.
Persisting model commentary as a chapter of somebody's book is not a trade this
pipeline makes.
"""

from __future__ import annotations

from pathlib import Path

from _arabic_coverage import arabic_coverage_shortfall, arabic_run_spans
from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _translation_prompts import _compose_prompt
from _translation_text import _translation_long_enough, normalize_translation_prose, translation_output_findings

_COMPOSE_TIMEOUT = 900
_RETRY_TIMEOUT = 1350


def _compose_one(
    title: str,
    body: str,
    previous_tail: str,
    book_dir: Path,
    label: str,
    log,
    *,
    arabic_src: str = "",
    quran_anchor: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    prompt = _compose_prompt(
        title,
        body,
        previous_tail,
        arabic_src=arabic_src,
        quran_anchor=quran_anchor,
        frame=frame,
        narrator=narrator,
    )
    rc, out, err = _run_claude_p_with_retry(
        prompt,
        timeout=_COMPOSE_TIMEOUT,
        book_dir=book_dir,
        phase="0book-compose",
        step=f"translation-{label}",
        log=log,
    )
    out = (out or "").strip()
    if rc != 0:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: translation edition compose failed rc={rc}: {err[:300]}",
            manual_fallback="Re-run the translation edition path; completed chunks are skipped.",
        )
    source_words = len(body.split())
    if source_words >= 200 and len(out.split()) < 0.55 * source_words:
        log(f"      {label}: short ({len(out.split())}/{source_words}w) - retry")
        rc2, out2, _ = _run_claude_p_with_retry(
            prompt + "\n\nYour previous attempt was too compressed. Rewrite faithfully, preserving the full teaching.",
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"translation-{label}-retry",
            log=log,
        )
        if rc2 == 0 and len((out2 or "").split()) > len(out.split()):
            out = (out2 or "").strip()
    findings = translation_output_findings(
        out, expected_title=title, frame=frame, narrator_subject=narrator, source=body
    )
    if findings:
        log(f"      {label}: invalid translation output ({'; '.join(findings[:3])}) - retry")
        # Name the ACTUAL failures. This retry used to assert "process commentary
        # or model-owned headings" no matter what the gate found, so a retry for
        # a lost enumeration (or any non-commentary finding) re-ran the model
        # with instructions about a defect it did not have — and failed again.
        retry_prompt = (
            prompt
            + "\n\nYour previous answer failed these integrity checks: "
            + "; ".join(findings[:5])
            + ". Rewrite now as clean chapter prose only, correcting exactly those failures. "
            "Do not mention instructions, options, source mismatch, inability, the title "
            "selection, or the prompt. Do not emit Markdown headings."
        )
        rc2, out2, err2 = _run_claude_p_with_retry(
            retry_prompt,
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"translation-{label}-integrity-retry",
            log=log,
        )
        if rc2 == 0:
            candidate = (out2 or "").strip()
            if not translation_output_findings(
                candidate, expected_title=title, frame=frame, narrator_subject=narrator, source=body
            ):
                out = candidate
            else:
                out = candidate or out
        else:
            log(f"      {label}: integrity retry failed rc={rc2}: {err2[:160]}")
        findings = translation_output_findings(
            out, expected_title=title, frame=frame, narrator_subject=narrator, source=body
        )
    if findings:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: translation edition output failed integrity gate: " + "; ".join(findings),
            manual_fallback=(
                "Re-run 0book-design/0book-compose after inspecting the source range; "
                "the pipeline refused to persist model commentary or generated headings."
            ),
        )
    # Arabic-coverage safety net (see _arabic_coverage): when the output drops too
    # much of the ground truth's quoted Arabic, retry ONCE with the specific spans
    # named. Non-fatal and keep-best — a residual shortfall never blocks the book,
    # and an empty suffix (no Arabic source, or coverage already adequate) skips it.
    arabic_retry = arabic_coverage_shortfall(out, arabic_src)
    if arabic_retry:
        log(f"      {label}: Arabic coverage low - retrying with the dropped spans named")
        rc3, out3, _err3 = _run_claude_p_with_retry(
            prompt + arabic_retry,
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"translation-{label}-arabic-retry",
            log=log,
        )
        cand = (out3 or "").strip()
        if (
            rc3 == 0
            and cand
            and not translation_output_findings(
                cand, expected_title=title, frame=frame, narrator_subject=narrator, source=body
            )
            and len(arabic_run_spans(cand)) > len(arabic_run_spans(out))
            and _translation_long_enough(cand, source_words)
        ):
            out = cand
        else:
            log(f"      {label}: Arabic-coverage retry did not improve - keeping best attempt")
    if not _translation_long_enough(out, source_words):
        raise AuthoringError(
            phase="0book-compose",
            message=(
                f"{label}: translation edition output is too compressed ({len(out.split())}/{source_words} words)"
            ),
            manual_fallback="Re-run after reducing chapter/window size or inspect the source range.",
        )
    return normalize_translation_prose(out, title=title)
