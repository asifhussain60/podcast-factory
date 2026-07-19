"""render.py — step 7. units.json + source record → the facing-column PDF.

Shells out to plan-dashboard/scripts/render-supplication-pdf.mjs, which owns the
Playwright/print mechanics. That renderer is a SIBLING of render-book-pdf.mjs;
neither it nor book-print.css is touched by this lane.

The payload handed to the renderer is built by schema.render_payload, which
derives every `source` string from the immutable OCR record — units.json is
never the source of source text.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from .schema import SourceRecord, SupplicationError, UnitsDoc, render_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
RENDERER = REPO_ROOT / "plan-dashboard" / "scripts" / "render-supplication-pdf.mjs"


def output_path(book_dir: Path, slug: str) -> Path:
    return book_dir / "book" / f"{slug}.pdf"


def run(book_dir: Path, doc: UnitsDoc, record: SourceRecord, *, out: Path | None = None) -> Path:
    if not RENDERER.is_file():
        raise SupplicationError(f"renderer not found: {RENDERER}")

    out = out or output_path(book_dir, doc.slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = render_payload(doc, record)

    # The renderer reads a self-contained document; write it to a temp file so
    # the derived-source payload is never persisted next to units.json (where a
    # later reader might mistake it for editable source of truth).
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as fh:
        json.dump(payload, fh, ensure_ascii=False)
        tmp = Path(fh.name)
    try:
        proc = subprocess.run(
            ["node", str(RENDERER), str(tmp), str(out)],
            cwd=REPO_ROOT / "plan-dashboard",
            capture_output=True,
            text=True,
        )
    finally:
        tmp.unlink(missing_ok=True)

    if proc.returncode == 3:
        raise SupplicationError(
            "chromium unavailable — run `npx playwright install chromium` in plan-dashboard/, then retry.\n"
            + proc.stderr.strip()
        )
    if proc.returncode != 0:
        raise SupplicationError(f"renderer failed (rc={proc.returncode}):\n{proc.stderr.strip()}")
    if not out.is_file():
        raise SupplicationError(f"renderer reported success but {out} does not exist")
    return out
