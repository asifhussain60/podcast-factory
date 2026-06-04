#!/usr/bin/env python3
"""transcribe_all_lectures.py — WC8.6 batch: transcribe all Ayyuhal Walad lecture videos.

Loops the 12 local lecture MP4s through transcribe_audio.py (ffmpeg + Azure Speech), writing one
transcript per lecture to _system/source/lectures/lecNN-<title>.txt. Idempotent (skips done files).
Azure-only — NO claude -p. Run in the background; cost accrues to the per-book ledger.

USAGE
    python3 scripts/podcast/transcribe_all_lectures.py --slug ayyuhal-walad
"""
from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import REPO_ROOT, content_dir  # noqa: E402

INBOX = REPO_ROOT / "_workspace" / "inbox" / "youtube"

def slug_for(name: str) -> str:
    m = re.search(r'\b(\d{2})\s*-\s*(.+?)\s*-\s*Ghazali', name)
    if not m:
        m2 = re.match(r'\d+\.\s*(\d{2})', name)
        if m2:
            return f"lec{m2.group(1)}"
        # Use the sanitized filename as slug rather than a fixed "lec00" that
        # would collide if multiple videos fail both patterns.
        safe = re.sub(r'[^a-z0-9]+', '-', Path(name).stem.lower()).strip('-')[:60]
        return f"lec-{safe}"
    n, title = m.group(1), m.group(2)
    t = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return f"lec{n}-{t}"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    a = ap.parse_args()
    out_dir = content_dir(a.slug) / "_system" / "source" / "lectures"
    out_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(INBOX.glob("*.mp4"), key=lambda p: int(re.match(r'(\d+)\.', p.name).group(1)) if re.match(r'(\d+)\.', p.name) else 0)
    if not videos:
        print(f"No videos in {INBOX}"); return 1
    print(f"[batch] {len(videos)} lectures -> {out_dir.relative_to(REPO_ROOT)}")
    for i, v in enumerate(videos, 1):
        out = out_dir / f"{slug_for(v.name)}.txt"
        if out.exists() and out.stat().st_size > 0:
            print(f"[{i}/{len(videos)}] cached {out.name}"); continue
        print(f"[{i}/{len(videos)}] transcribing {v.name[:50]}…", flush=True)
        rel = out.relative_to(REPO_ROOT)
        r = subprocess.run([sys.executable, str(SCRIPT_DIR / "transcribe_audio.py"),
                            "--slug", a.slug, "--video", str(v), "--out", str(rel)],
                           capture_output=True, text=True)
        print("   " + (r.stdout.strip() or r.stderr.strip()[-300:]), flush=True)
    print("[batch] done")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
