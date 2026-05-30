#!/usr/bin/env python3
"""transcribe_audio.py — WC8.6 audio intake (lecture video/audio -> text via Azure Speech).

The lecture videos are the spoken EXPLAINER / narrator source (an attributed additions layer).
This script extracts audio with ffmpeg (free, local) and transcribes it with Azure Speech
fast-transcription (metered). Azure-only — NO `claude -p` (Claude reasoning stays with the agent).

USAGE
    python3 scripts/podcast/transcribe_audio.py --slug ayyuhal-walad \\
        --video "_workspace/inbox/youtube/<file>.mp4" --out <path.txt> [--seconds N]

Cost is appended to the per-book ledger. `--seconds N` transcribes only the first N seconds
(cheap proof); omit for the full file.
"""
from __future__ import annotations
import argparse, subprocess, sys, tempfile, uuid, urllib.request, json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _azure  # noqa: E402
from _paths import REPO_ROOT, content_dir  # noqa: E402
from _cost_ledger import append_azure_stt_cost  # noqa: E402

def extract_wav(video: Path, seconds: int | None) -> tuple[Path, float]:
    # Compact mono mp3 (Azure Speech accepts it) so full ~1h lectures upload small.
    tmp = Path(tempfile.gettempdir()) / f"transcribe-{uuid.uuid4().hex}.mp3"
    cmd = ["ffmpeg", "-nostdin", "-i", str(video)]
    if seconds:
        cmd += ["-t", str(seconds)]
    cmd += ["-ac", "1", "-ar", "16000", "-codec:a", "libmp3lame", "-b:a", "48k", "-vn", "-y", str(tmp)]
    subprocess.run(cmd, check=True, capture_output=True)
    # duration in seconds
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(tmp)], capture_output=True, text=True)
    dur = float(probe.stdout.strip() or 0)
    return tmp, dur

def transcribe(wav: Path) -> str:
    c = _azure.load_speech_creds()
    host = c.endpoint if c.endpoint.startswith("http") else f"https://{c.region}.api.cognitive.microsoft.com"
    url = f"{host.rstrip('/')}/speechtotext/transcriptions:transcribe?api-version=2024-11-15"
    boundary = "b" + uuid.uuid4().hex
    def part(name, content, *, filename=None, ctype=None):
        h = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
        if filename: h += f'; filename="{filename}"'
        h += "\r\n" + (f"Content-Type: {ctype}\r\n" if ctype else "") + "\r\n"
        return h.encode() + content + b"\r\n"
    body = (part("audio", wav.read_bytes(), filename=wav.name, ctype="audio/mpeg")
            + part("definition", json.dumps({"locales": ["en-US"]}).encode(), ctype="application/json")
            + f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Ocp-Apim-Subscription-Key": c.key,
        "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    return " ".join(p.get("text", "") for p in d.get("combinedPhrases", []))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True); ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--seconds", type=int, default=None)
    a = ap.parse_args()
    wav, dur = extract_wav(Path(a.video), a.seconds)
    try:
        text = transcribe(wav)
    finally:
        wav.unlink(missing_ok=True)
    out = REPO_ROOT / a.out if not a.out.startswith("/") else Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text + "\n")
    append_azure_stt_cost(content_dir(a.slug), phase="wc8/transcribe",
                          step=Path(a.video).name, duration_seconds=dur)
    print(f"[done] {dur:.0f}s -> {len(text):,} chars -> {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
