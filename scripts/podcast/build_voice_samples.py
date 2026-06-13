#!/usr/bin/env python3
"""build_voice_samples.py — render one short sample clip per approved voice.

Produces the "hear them speak" clips the Astro intake voice picker links
(plan-dashboard/public/voice-samples/<name>.mp3, the `sample` field in
voice-library.yaml). One short line per voice, rendered with the SAME engine
the books use (eleven_v3), so the demo matches production timbre.

SPEND: ElevenLabs, ~one short line per voice (8 voices ≈ a few hundred
characters total — tiny, one-time). Requires --confirm; reports the metered
credit delta. Skips voices whose clip already exists unless --force.

USAGE
    python3 scripts/podcast/build_voice_samples.py --dry-run     # plan only, no spend
    python3 scripts/podcast/build_voice_samples.py --confirm     # render missing clips
    python3 scripts/podcast/build_voice_samples.py --confirm --force   # re-render all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _voice_library import pools  # noqa: E402
from _audio_engines import get_engine, ENGINE_ELEVENLABS  # noqa: E402

# A short, neutral line in the two-host register — long enough to hear timbre +
# pace, short enough to keep the spend trivial. ASCII only.
SAMPLE_LINE = ("Gratitude is not a feeling you keep to yourself. It is a debt "
               "you repay with how you live.")

OUTPUT_DIR_REL = "plan-dashboard/public/voice-samples"
OUTPUT_FORMAT = "mp3_44100_128"


def _output_dir() -> Path:
    from _paths import REPO_ROOT
    return Path(REPO_ROOT) / OUTPUT_DIR_REL


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="authorize the ElevenLabs spend")
    ap.add_argument("--force", action="store_true", help="re-render clips that already exist")
    ap.add_argument("--dry-run", action="store_true", help="list what would render; no spend")
    args = ap.parse_args()

    engine = get_engine(ENGINE_ELEVENLABS)
    out_dir = _output_dir()
    entries: list[dict] = pools()["males"] + pools()["females"]

    todo: list[dict] = []
    for v in entries:
        sample = v.get("sample") or f"{str(v.get('name', '')).lower()}.mp3"
        dest = out_dir / sample
        if dest.exists() and not args.force:
            continue
        todo.append({**v, "_sample": sample, "_dest": dest})

    print(f"Voice sample clips -> {out_dir}")
    print(f"  voices in library : {len(entries)}")
    print(f"  to render         : {len(todo)} ({'all (force)' if args.force else 'missing only'})")
    for v in todo:
        print(f"    - {v['name']:<10} {v['voice_id']}  -> {v['_sample']}")
    approx_chars = len(SAMPLE_LINE) * len(todo)
    print(f"  approx characters : {approx_chars:,} (~{approx_chars:,} credits at v3 rate)")

    if not todo:
        print("Nothing to render — all clips present.")
        return 0
    if args.dry_run or not args.confirm:
        print("\nDRY RUN — pass --confirm to render (ElevenLabs spend).")
        return 0

    from _elevenlabs import ElevenLabsClient
    client = ElevenLabsClient()
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        meter_start = int(client.subscription().get("character_count"))
    except Exception:  # noqa: BLE001
        meter_start = None

    for v in todo:
        audio = client.text_to_dialogue(
            [{"text": SAMPLE_LINE, "voice_id": v["voice_id"]}],
            model_id=engine.model_id, output_format=OUTPUT_FORMAT)
        v["_dest"].write_bytes(audio)
        print(f"  wrote {v['_dest'].name}")

    if meter_start is not None:
        try:
            import time
            time.sleep(5)
            metered = int(client.subscription().get("character_count")) - meter_start
            print(f"\nMetered credits this run: {metered:,}")
        except Exception as e:  # noqa: BLE001
            print(f"(credit metering failed: {e})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
