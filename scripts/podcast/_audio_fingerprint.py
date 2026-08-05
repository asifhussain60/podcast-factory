#!/usr/bin/env python3
"""_audio_fingerprint.py — measurable speaking-style fingerprint + gold-standard score.

The tracked production form of the style-match experiment
(`_workspace/experiments/audio-smoke/style-match/style_metrics.py`, promoted
2026-06-13). The DSP is ported verbatim — it is proven against the NotebookLM
corpus — and given a clean library surface plus a genre-keyed gold standard.

WHAT IT MEASURES
Fingerprints a two-host (male+female) podcast m4a with no speaker labels: per-
frame autocorrelation pitch (f0) separates the hosts by register (male < 150 Hz,
female > 175 Hz). The eight metrics are the ones that define the NotebookLM
"interactive" feel:

    wpm              words per minute (needs a word count — from the transcript)
    switches_per_min speaker alternation rate (turn-taking energy)
    run_med_s        median continuous same-speaker run (turn length proxy)
    share_male       fraction of voiced time held by the male host
    pause_per_min    pauses > 0.4 s per minute (dead-air rate)
    pause_med_ms     median pause length
    st_sd_male       pitch variance of the male in SEMITONES (monotone gauge)
    st_sd_female     same for the female

THE GOLD STANDARD
`content/_shared/audio-style/<profile>.json` is the tracked, versioned per-genre
reference, built from a real NotebookLM corpus by build_audio_gold_standard.py.
Each metric stores a median `center`, a relative tolerance `tol_rel`, and the raw
`p10`/`p90` spread for auditability. `score_against_profile` scores a fingerprint
against that reference; `load_gold_standard` resolves the asset by content
profile (islamic_scholarly fallback), mirroring _rules.bucket_for_profile.

NO SPEND: pure local DSP over ffmpeg-decoded audio. Used by the post-render
style gate (render_dialogue_audio) and the corpus builder.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

# ── DSP constants (ported verbatim — do not retune without a corpus rebuild) ──
SR = 16000
FRAME = int(0.04 * SR)  # 40 ms
HOP = int(0.02 * SR)  # 20 ms
SILENCE_RMS = 0.015
MALE_MAX_HZ = 150.0
FEMALE_MIN_HZ = 175.0
PAUSE_MIN_S = 0.40
BRIDGE_FRAMES = 12  # bridge gaps < 240 ms inside a speaker run

# Metric weights + relative tolerances for scoring. The tolerance here is the
# FLOOR; a per-profile gold standard may widen any band to the real corpus
# spread (build_audio_gold_standard) but never tightens below this.
SCORE_SPEC: dict[str, tuple[float, float]] = {
    "wpm": (3.0, 0.18),
    "switches_per_min": (2.5, 0.55),
    "run_med_s": (1.5, 0.60),
    "share_male": (1.0, 0.35),
    "pause_per_min": (1.5, 0.60),
    "pause_med_ms": (1.0, 0.60),
    "st_sd_male": (2.0, 0.45),
    "st_sd_female": (1.5, 0.45),
}

METRIC_KEYS: tuple[str, ...] = tuple(SCORE_SPEC)

GOLD_STANDARD_DIR = "audio-style"  # under content/_shared/


# ── audio decode + pitch ──────────────────────────────────────────────────────


def decode(path: Path, start: float | None = None, dur: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-loglevel", "error"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(path)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-f", "s16le", "-ac", "1", "-ar", str(SR), "-"]
    pcm = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float64) / 32768.0


def frames_f0(x: np.ndarray) -> list[tuple[float, float]]:
    """[(time_s, f0_hz or 0=silence / -1=unvoiced)] per 20 ms hop."""
    out = []
    lo, hi = int(SR / 350), int(SR / 70)
    for s in range(0, len(x) - FRAME, HOP):
        fr = x[s : s + FRAME]
        t = s / SR
        if np.sqrt(np.mean(fr**2)) < SILENCE_RMS:
            out.append((t, 0.0))
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, "full")[FRAME - 1 :]
        if hi >= len(ac):
            out.append((t, -1.0))
            continue
        peak = lo + int(np.argmax(ac[lo:hi]))
        out.append((t, SR / peak if ac[peak] / (ac[0] + 1e-9) >= 0.30 else -1.0))
    return out


def speaker_labels(fr) -> list[str]:
    """Per-frame label: M / F / ? (voiced-unclear) / _ (silence)."""
    lab = []
    for _, f0 in fr:
        if f0 == 0.0:
            lab.append("_")
        elif f0 < 0:
            lab.append("?")
        elif f0 <= MALE_MAX_HZ:
            lab.append("M")
        elif f0 >= FEMALE_MIN_HZ:
            lab.append("F")
        else:
            lab.append("?")
    return lab


def speaker_runs(lab, min_run_s: float = 0.6) -> list[tuple[str, int, int]]:
    """Monotonic (speaker, frame0, frame1) runs — bridges short gaps."""
    runs: list[tuple[str, int, int]] = []
    cur, i0 = None, 0
    for i, l in enumerate(lab):
        if l in ("M", "F"):
            if cur == l:
                continue
            if cur is None and runs and runs[-1][0] == l and i - runs[-1][2] <= BRIDGE_FRAMES:
                _, j0, _ = runs.pop()
                cur, i0 = l, j0
                continue
            if cur is not None:
                runs.append((cur, i0, i))
            cur, i0 = l, i
        elif l == "_" and cur is not None:
            j = i
            while j < len(lab) and lab[j] == "_":
                j += 1
            if j - i > BRIDGE_FRAMES:
                runs.append((cur, i0, i))
                cur = None
    if cur is not None:
        runs.append((cur, i0, len(lab)))
    return [(s, a, b) for s, a, b in runs if (b - a) * HOP / SR >= min_run_s]


# ── fingerprint ─────────────────────────────────────────────────────────────


def fingerprint(path: Path, words: int | None = None, start: float | None = None, dur: float | None = None) -> dict:
    x = decode(path, start, dur)
    total_s = len(x) / SR
    fr = frames_f0(x)
    lab = speaker_labels(fr)
    runs = speaker_runs(lab)

    switches = sum(1 for k in range(1, len(runs)) if runs[k][0] != runs[k - 1][0])
    run_lens = [(b - a) * HOP / SR for _, a, b in runs]
    m_time = sum((b - a) for s, a, b in runs if s == "M") * HOP / SR
    f_time = sum((b - a) for s, a, b in runs if s == "F") * HOP / SR

    sil = []
    i = 0
    first_voice = next((k for k, l in enumerate(lab) if l in "MF"), 0)
    last_voice = len(lab) - next((k for k, l in enumerate(reversed(lab)) if l in "MF"), 0)
    while i < len(lab):
        if lab[i] == "_" and first_voice < i < last_voice:
            j = i
            while j < len(lab) and lab[j] == "_":
                j += 1
            span = (j - i) * HOP / SR
            if span >= PAUSE_MIN_S:
                sil.append(span)
            i = j
        else:
            i += 1

    def st_sd(spk):
        f0s = np.array([f0 for (t, f0), l in zip(fr, lab) if l == spk and f0 > 0])
        if len(f0s) < 10:
            return 0.0
        med = np.median(f0s)
        return float(np.std(12 * np.log2(f0s / med)))

    prof = {
        "file": str(path),
        "window": [start or 0, dur or total_s],
        "total_s": round(total_s, 1),
        "switches_per_min": round(switches / total_s * 60, 2) if total_s else 0,
        "run_med_s": round(float(np.median(run_lens)), 2) if run_lens else 0,
        "share_male": round(m_time / max(m_time + f_time, 1e-9), 3),
        "pause_per_min": round(len(sil) / total_s * 60, 2) if total_s else 0,
        "pause_med_ms": round(float(np.median(sil)) * 1000) if sil else 0,
        "st_sd_male": round(st_sd("M"), 2),
        "st_sd_female": round(st_sd("F"), 2),
    }
    if words:
        prof["wpm"] = round(words / total_s * 60, 1) if total_s else 0
    return prof


def word_count(text: str) -> int:
    """Spoken-word count for wpm: strip [tags] + speaker labels, count tokens.

    Mirrors the experiment's norm_tokens so stage directions and HOST_x labels
    never inflate the rate.
    """
    text = re.sub(r"\[[^\]]+\]", " ", text)  # [tags] are not speech
    text = re.sub(r"(?im)^\s*host_[ab]\s*:", " ", text)  # speaker labels
    return len(re.sub(r"[^a-z' ]+", " ", text.lower()).split())


def fingerprint_m4a(path: Path, *, transcript: Path | None = None, words: int | None = None) -> dict:
    """Fingerprint an m4a; derive the word count from a transcript when given.

    *words* (explicit) wins; else *transcript* is read and counted; else wpm is
    omitted from the profile (score() simply skips a metric absent on either side).
    """
    if words is None and transcript is not None and Path(transcript).exists():
        words = word_count(Path(transcript).read_text(encoding="utf-8"))
    return fingerprint(Path(path), words=words)


# ── gold standard ─────────────────────────────────────────────────────────────


def _gold_standard_path(profile: str) -> Path:
    from _paths import REPO_ROOT

    return Path(REPO_ROOT) / "content" / "_shared" / GOLD_STANDARD_DIR / f"{profile}.json"


def load_gold_standard(profile: str | None) -> dict | None:
    """The tracked per-profile gold standard, or None when absent.

    Unknown / absent profiles fall back to islamic_scholarly (the historical
    default), matching _rules.bucket_for_profile discipline.
    """
    for candidate in (profile or "", "islamic_scholarly"):
        if not candidate:
            continue
        p = _gold_standard_path(candidate)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
    return None


def score(cand: dict, ref_metrics: dict) -> dict:
    """Weighted similarity score (0-100) of a fingerprint vs a reference.

    *ref_metrics* maps metric -> {"center": .., "tol_rel": ..} (gold-standard
    form) OR metric -> scalar (a raw reference profile). A metric absent from
    either side is skipped (e.g. wpm when no transcript was available).
    """
    rows, wsum, total = [], 0.0, 0.0
    for m, (w, tol_floor) in SCORE_SPEC.items():
        if m not in cand:
            continue
        spec = ref_metrics.get(m)
        if spec is None:
            continue
        if isinstance(spec, dict):
            center = spec.get("center")
            tol = spec.get("tol_rel") or tol_floor
        else:
            center, tol = spec, tol_floor
        if not center:
            continue
        rel = abs(cand[m] - center) / (abs(center) * tol)
        sub = max(0.0, 1.0 - rel)
        rows.append({"metric": m, "ref": center, "cand": cand[m], "sub": round(sub * 100)})
        total += w * sub
        wsum += w
    return {"score": round(total / wsum * 100, 1) if wsum else 0.0, "breakdown": rows}


def score_against_profile(fp: dict, profile: str | None) -> dict:
    """Score a fingerprint against a profile's gold standard.

    Returns {score, breakdown, threshold, passed, profile} — or
    {score: None, ...} when no gold standard exists for the profile (the style
    gate then treats the episode as un-scored and never blocks).
    """
    gold = load_gold_standard(profile)
    if not gold:
        return {
            "score": None,
            "breakdown": [],
            "threshold": None,
            "passed": True,
            "profile": profile,
            "note": "no gold standard for profile",
        }
    metrics = gold.get("metrics") or {}
    result = score(fp, metrics)
    threshold = float(gold.get("pass_threshold", 70))
    return {
        "score": result["score"],
        "breakdown": result["breakdown"],
        "threshold": threshold,
        "passed": result["score"] >= threshold,
        "profile": gold.get("profile", profile),
        "gold_version": gold.get("version"),
    }
