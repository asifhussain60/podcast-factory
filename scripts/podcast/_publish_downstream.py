"""What happens AFTER a book's status flips to published.

Two deliveries, and they are together here because they share one property that
makes them different from everything in `publish_to_library.py`: they leave this
machine. Publishing itself is a change to files in this repo and either happens
or does not. These reach Google Drive and Cloudflare, which can be slow, offline,
or refuse — and neither failure may unwind a publish that already succeeded. So
both are NON-FATAL by construction, and each prints how to retry on its own.

Split out of `publish_to_library.py` when it crossed the module line-count gate,
along a seam that was already real: gates and state changes above, outbound
delivery here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent


def deliver(slug: str, args, *, info, warn) -> None:
    """Copy to Google Drive, then push to the Listener. Neither can fail the publish."""
    if not getattr(args, "skip_export", False):
        info("")
        info("=== Distribution export ===")
        try:
            from export_distribution import export as _dist_export

            out = Path(args.export_dir).expanduser() if getattr(args, "export_dir", None) else None
            _dist_export(slug, output_root=out, dry_run=False)
        except Exception as exc:
            warn(f"distribution export failed (publish succeeded): {exc}")

    # Always the asifhussain60@gmail.com Cloudflare account — the deploy script
    # resolves the token and REFUSES to run if it points anywhere else, so that
    # guarantee lives in one place rather than in every caller.
    #
    # It does not make the book visible. The script never writes
    # `content_unit.status` or `open_to_all`, so the book arrives complete and
    # unreadable until a human switches it on at /admin. `publication.status` in
    # this repo and visibility on the Listener are deliberately two decisions:
    # one says the work is finished, the other says people may see it.
    if getattr(args, "skip_listener", False):
        return

    info("")
    info("=== Listener (podcast-factory.safinaverse.com) ===")
    try:
        subprocess.run(["bash", str(HERE / "deploy_listener.sh"), slug], check=True)
    except Exception as exc:
        warn(f"listener deploy failed (publish succeeded): {exc}")
        warn(f"    retry on its own with: scripts/podcast/deploy_listener.sh {slug}")
