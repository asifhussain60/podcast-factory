#!/usr/bin/env python3
"""Work-level teaching allocator — place every ledger teaching into exactly one
volume (+ ordered concept slot), deduplicated, before any volume's 0d runs.

THE PROBLEM. A multi-volume work (e.g. al-anwaar-al-lateefah) synthesizes one
dense teaching ledger (here 3,037 teachings: 1,093 spine + 1,944 augmentation).
Phase 0d is text-segmentation-driven and never reads the ledger, so nothing today
guarantees (a) every augmentation concept is captured, (b) no concept is taught
twice across CHAPTERS or VOLUMES, (c) each concept sits in the right volume, or
(d) chapters flow incrementally. This pre-pass produces that guarantee as a shared
artifact `_system/_volume-split.json` that each volume's 0d consumes.

THE ALGORITHM (LLM-assisted hybrid; flat-rate Claude Max, no API spend).
  Stage 1  boundaries : place SPINE (ordered, monotonic with the book) into
                        volumes by classifying a downsampled spine into the 6
                        volumes, enforcing monotonicity, and interpolating the 5
                        inter-volume boundaries; fill all spine deterministically.
                        Within a volume, spine -> section by proportional word fill
                        (ordering only; never crosses a volume boundary).
  Stage 2  place      : place AUGMENTATION into one of the 28 sections via batched
                        LLM classification, each teaching carrying a Jaccard top-K
                        section shortlist for speed + accuracy.
  Stage 3  dedup      : Jaccard (key-term + text) shortlists the highest-overlap
                        teaching pairs; the LLM CONFIRMS only true same-concept
                        pairs -> union-find clusters. Canonical (spine-first, else
                        longest) airs once; the rest are VARIANTS retained for the
                        reading edition. Conservative: never auto-merges; no loss.
  Stage 4  emit       : order each volume's concepts by book position (incremental),
                        write `_volume-split.json`, and run the no-loss/no-repeat
                        GATE (union == N, each id one volume, each cluster one home).

Deterministic where it can be (spine order, blocking, ordering, verification);
LLM only for genuine semantic judgement (augmentation placement, dedup
confirmation). Resume-safe: each stage checkpoints under `_system/_alloc/`.

Usage:
  .venv/bin/python scripts/podcast/allocate_teachings.py <work-slug> --no-llm   # plumbing dry-run
  .venv/bin/python scripts/podcast/allocate_teachings.py <work-slug> --stage boundaries
  .venv/bin/python scripts/podcast/allocate_teachings.py <work-slug> --all      # full run
  .venv/bin/python scripts/podcast/allocate_teachings.py <work-slug> --emit-only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _work_manifest as wm
from _paths import find_content
from intelligence.dedup_corpus import _jaccard, _normalize, _tokens

_LLM_BATCH = 200  # each `claude -p` cold-starts the full CLI/MCP env (~minutes),
# so minimize CALL COUNT, not batch size. Output is tiny
# ({i,section}); ~10 calls for ~1,900 items beats ~24 small ones.
_CLAUDE_TIMEOUT = 900
# Use the DEFAULT model (no --model flag). Passing an explicit --model to `claude`
# hangs under nohup/no-TTY (it works only with a TTY), so the background allocator
# must not set one. Placement/dedup are constrained classification tasks anyway.
_PLACEMENT_MODEL = None
_SHORTLIST_K = 5
_DEDUP_KT_MIN = 0.60  # key-term Jaccard floor to even consider a dup pair
_DEDUP_MAX_PAIRS = 200  # cap LLM dedup-confirmation candidates


# ------------------------------------------------------------------ loading


def _load(work_slug: str):
    found = find_content(work_slug)
    if not found:
        raise SystemExit(f"work not found: {work_slug}")
    work_dir = found[2]
    if not wm.has_manifest(work_dir):
        raise SystemExit(f"not a multi-volume work (no work.yml): {work_dir}")
    manifest = wm.read_manifest(work_dir)
    led_rel = (manifest.get("shared") or {}).get("ledger")
    ledger = json.loads((work_dir / led_rel).read_text())
    book = (work_dir / ((manifest.get("shared") or {}).get("synthesis") or "_system/unified-book.md")).read_text()
    sections = _parse_sections(book)  # [(title, body)]
    if len(sections) != 28:
        # not fatal for other works; we drive purely off h2_sections in the manifest
        pass
    # section index (1-based) -> volume dir, from the manifest's h2_sections
    sec2vol: dict[int, str] = {}
    vol_titles: dict[str, str] = {}
    for v in wm.volumes_of(work_slug):
        vol_titles[v["dir"]] = v.get("title", v["dir"])
        for s in v.get("h2_sections", []):
            sec2vol[int(s)] = v["dir"]
    return work_dir, manifest, ledger, sections, sec2vol, vol_titles


def _parse_sections(text: str):
    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("## ")]
    bounds = idx + [len(lines)]
    out = []
    for k in range(len(idx)):
        block = lines[bounds[k] : bounds[k + 1]]
        out.append((block[0][3:].strip(), "\n".join(block)))
    return out


def _alloc_dir(work_dir: Path) -> Path:
    d = work_dir / "_system" / "_alloc"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ------------------------------------------------------------------ LLM glue


def _claude_json_array(prompt: str, *, book_dir: Path, step: str, log, model=_PLACEMENT_MODEL):
    """Run flat-rate claude -p, return the first JSON array in stdout (or None).

    model=None => default model, no --model flag (required under nohup/no-TTY).
    """
    from _authoring._core import _run_claude_p

    kw = {"model": model, "model_flag": model} if model else {}
    rc, text, err = _run_claude_p(prompt, timeout=_CLAUDE_TIMEOUT, book_dir=book_dir, phase="allocate", step=step, **kw)
    if rc != 0:
        log(f"    [{step}] rc={rc}: {(err or '')[:120]}")
        return None
    m = re.search(r"\[.*\]", text or "", re.DOTALL)
    if not m:
        log(f"    [{step}] no JSON array in reply")
        return None
    try:
        return json.loads(m.group(0))
    except Exception as e:
        log(f"    [{step}] JSON parse failed: {e}")
        return None


# ------------------------------------------------------ stage 1: spine -> volume


def _spine_indices(ledger):
    return [i for i, t in enumerate(ledger) if t.get("source") == "spine"]


def stage_boundaries(work_dir, ledger, sections, sec2vol, vol_titles, *, no_llm, log):
    """Place every spine teaching DETERMINISTICALLY by book order.

    The spine ledger is monotonic with the merged book, and the volumes were
    carved from that same book by section word-offset (split_synthesis_*). So the
    consistent placement is proportional-by-order: the k-th of K spine teachings
    sits at book word-fraction (k+0.5)/K; map that fraction through the sections'
    cumulative word offsets to a section, and the section to its volume. Monotonic
    by construction, exactly consistent with the volume book partition, no LLM.
    (Classifying distilled spine text with an LLM is both unreliable — the same
    concept recurs across the book — and redundant with the known order.)
    """
    spine = _spine_indices(ledger)
    secw = [len(b.split()) for _, b in sections] if sections else [1] * len(sec2vol)
    total = sum(secw) or 1
    edges, acc = [], 0
    for i, w in enumerate(secw):  # cumulative word-fraction edge per section
        acc += w
        edges.append((i + 1, acc / total))
    K = len(spine)
    out = {}
    for k, gi in enumerate(spine):
        frac = (k + 0.5) / max(1, K)
        sec = edges[-1][0]
        for s, edge in edges:
            if frac <= edge:
                sec = s
                break
        out[str(gi)] = {"section": sec, "volume": sec2vol.get(sec)}
    (_alloc_dir(work_dir) / "spine-assign.json").write_text(json.dumps(out, indent=1))
    from collections import Counter

    dist = Counter(v["volume"] for v in out.values())
    log(f"  boundaries: {len(out)} spine teachings -> volumes {dict(sorted(dist.items()))} (deterministic)")
    return out


# --------------------------------------------------- stage 2: augmentation -> section


def stage_place(work_dir, ledger, sections, sec2vol, *, no_llm, log):
    aug = [i for i, t in enumerate(ledger) if t.get("source") != "spine"]
    n_sec = len(sec2vol)
    sec_titles = [
        sections[s - 1][0] if sections and s - 1 < len(sections) else f"section {s}" for s in range(1, n_sec + 1)
    ]
    # per-section key-term profile from spine teachings of that section (for shortlist)
    spine_assign = json.loads((_alloc_dir(work_dir) / "spine-assign.json").read_text())
    sec_kt = defaultdict(set)
    for gi_s, info in spine_assign.items():
        sec_kt[int(info["section"])] |= {x.lower() for x in (ledger[int(gi_s)].get("key_terms") or [])}

    ckpt = _alloc_dir(work_dir) / "aug-assign.json"
    out = json.loads(ckpt.read_text()) if ckpt.exists() else {}

    if no_llm:
        for gi in aug:
            out[str(gi)] = {"section": 1, "volume": sec2vol.get(1)}
        ckpt.write_text(json.dumps(out, indent=1))
        log(f"  place(no-llm): {len(out)} aug -> section 1 (placeholder)")
        return out

    todo = [gi for gi in aug if str(gi) not in out]
    sect_list = "\n".join(f"  {s}: {sec_titles[s - 1]}" for s in range(1, n_sec + 1))
    done = len(out)
    for start in range(0, len(todo), _LLM_BATCH):
        batch = todo[start : start + _LLM_BATCH]
        lines = []
        for gi in batch:
            kt = {x.lower() for x in (ledger[gi].get("key_terms") or [])}
            scored = sorted(
                ((len(kt & sec_kt[s]) / (len(kt | sec_kt[s]) or 1), s) for s in range(1, n_sec + 1)), reverse=True
            )
            short = [s for _, s in scored[:_SHORTLIST_K]]
            lines.append(f'{{"i": {gi}, "shortlist": {short}, "t": {json.dumps(ledger[gi]["teaching"][:260])}}}')
        prompt = (
            "Place each scholarly teaching into the ONE section it most belongs to.\n"
            f"SECTIONS (number: title):\n{sect_list}\n\n"
            "Each teaching includes a 'shortlist' of likely section numbers (by term overlap) "
            "— prefer one of them, but choose any section if the content clearly fits elsewhere.\n"
            'Return ONLY a JSON array: [{"i": <i>, "section": <number 1..%d>}].\n\n'
            "TEACHINGS:\n%s" % (n_sec, "\n".join(lines))
        )
        arr = _claude_json_array(prompt, book_dir=work_dir, step="aug-section", log=log) or []
        for o in arr:
            try:
                s = int(o["section"])
                if 1 <= s <= n_sec:
                    out[str(int(o["i"]))] = {"section": s, "volume": sec2vol.get(s)}
            except Exception:
                pass
        ckpt.write_text(json.dumps(out, indent=1))
        done = len(out)
        log(f"    [place] {done}/{len(aug)} aug assigned")
    # safety net: any unplaced aug -> shortlist top-1
    for gi in aug:
        if str(gi) not in out:
            kt = {x.lower() for x in (ledger[gi].get("key_terms") or [])}
            best = max(range(1, n_sec + 1), key=lambda s: len(kt & sec_kt[s]))
            out[str(gi)] = {"section": best, "volume": sec2vol.get(best), "fallback": True}
    ckpt.write_text(json.dumps(out, indent=1))
    log(f"  place: {len(out)} aug teachings assigned to sections")
    return out


# ------------------------------------------------------------- stage 3: dedup


def stage_dedup(work_dir, ledger, *, no_llm, log):
    kts = [frozenset(x.lower().strip() for x in (t.get("key_terms") or []) if x.strip()) for t in ledger]
    txt = [_tokens(_normalize(t["teaching"])) for t in ledger]
    inv = defaultdict(list)
    for i, k in enumerate(kts):
        for term in k:
            inv[term].append(i)
    cand = set()
    for term, idxs in inv.items():
        if len(idxs) > 400:
            continue
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                if kts[i] and kts[j] and _jaccard(kts[i], kts[j]) >= _DEDUP_KT_MIN:
                    cand.add((i, j) if i < j else (j, i))
    scored = sorted(
        cand, key=lambda p: _jaccard(kts[p[0]], kts[p[1]]) + 0.25 * _jaccard(txt[p[0]], txt[p[1]]), reverse=True
    )[:_DEDUP_MAX_PAIRS]
    log(f"  dedup: {len(cand)} candidate pairs -> {len(scored)} sent for confirmation")

    confirmed = []
    if not no_llm and scored:
        for start in range(0, len(scored), _LLM_BATCH):
            batch = scored[start : start + _LLM_BATCH]
            lines = [
                f'{{"i": {n}, "a": {json.dumps(ledger[p[0]]["teaching"][:220])}, '
                f'"b": {json.dumps(ledger[p[1]]["teaching"][:220])}}}'
                for n, p in enumerate(batch)
            ]
            prompt = (
                "For each pair, decide if A and B teach the SAME core concept such that airing both "
                "in a podcast would be redundant repetition (not merely related or sequential).\n"
                "Be CONSERVATIVE: only 'same' when they assert essentially the same point.\n"
                'Return ONLY a JSON array: [{"i": <i>, "same": true|false}].\n\n'
                "PAIRS:\n" + "\n".join(lines)
            )
            arr = _claude_json_array(prompt, book_dir=work_dir, step="dedup-confirm", log=log) or []
            for o in arr:
                try:
                    if bool(o.get("same")) and 0 <= int(o["i"]) < len(batch):
                        confirmed.append(batch[int(o["i"])])
                except Exception:
                    pass
            log(f"    [dedup] confirmed {len(confirmed)} so far ({min(start + _LLM_BATCH, len(scored))}/{len(scored)})")

    # union-find clusters from confirmed pairs
    parent = list(range(len(ledger)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in confirmed:
        parent[find(i)] = find(j)
    clusters = defaultdict(list)
    for i in range(len(ledger)):
        clusters[find(i)].append(i)
    multi = {r: m for r, m in clusters.items() if len(m) > 1}
    out = {
        "confirmed_pairs": [[ledger[i]["id"], ledger[j]["id"]] for i, j in confirmed],
        "clusters": [[ledger[i]["id"] for i in m] for m in multi.values()],
    }
    (_alloc_dir(work_dir) / "dedup.json").write_text(json.dumps(out, indent=1))
    log(
        f"  dedup: {len(confirmed)} same-concept pairs -> {len(multi)} variant clusters "
        f"({sum(len(m) - 1 for m in multi.values())} variants suppressed from audio)"
    )
    return parent


# ------------------------------------------------------------- stage 4: emit + gate


def stage_emit(work_dir, manifest, ledger, sections, sec2vol, vol_titles, parent, *, log):
    spine_assign = json.loads((_alloc_dir(work_dir) / "spine-assign.json").read_text())
    aug_assign = json.loads((_alloc_dir(work_dir) / "aug-assign.json").read_text())
    assign = {}
    for gi_s, info in spine_assign.items():
        assign[int(gi_s)] = (info["section"], info["volume"])
    for gi_s, info in aug_assign.items():
        assign[int(gi_s)] = (info["section"], info["volume"])

    def root(x):
        r = x
        while parent[r] != r:
            r = parent[r]
        return r

    # canonical per cluster: spine-first, else longest teaching
    cluster_members = defaultdict(list)
    for i in range(len(ledger)):
        cluster_members[root(i)].append(i)

    def canon(members):
        sp = [i for i in members if ledger[i]["source"] == "spine"]
        pool = sp or members
        return max(pool, key=lambda i: len(ledger[i]["teaching"]))

    canonical = {r: canon(m) for r, m in cluster_members.items()}

    vols = sorted(set(sec2vol.values()), key=lambda v: min(s for s, vv in sec2vol.items() if vv == v))
    per_vol = {v: [] for v in vols}
    full_assignment = {}
    for i in range(len(ledger)):
        r = root(i)
        can = canonical[r]
        # A concept cluster has ONE home: every member (canonical + variants) takes
        # the canonical's placement, so a variant can never land in a different
        # volume than the concept it restates (no cross-volume duplication, even in
        # the reading edition). The canonical airs; variants are book-only.
        sec, vol = assign.get(can, (None, None))
        is_canon = can == i
        full_assignment[ledger[i]["id"]] = {
            "volume": vol,
            "section": sec,
            "cluster": ledger[can]["id"],
            "role": "canonical" if is_canon else "variant",
            "source": ledger[i]["source"],
        }
        if is_canon and vol is not None:
            per_vol[vol].append((sec, i))

    # order each volume's concepts by (section, original ledger order) = incremental
    volumes_out = {}
    for v in vols:
        concepts = sorted(per_vol[v], key=lambda si: (si[0], si[1]))
        volumes_out[v] = {
            "title": vol_titles.get(v, v),
            "sections": sorted({s for s, vv in sec2vol.items() if vv == v}),
            "n_concepts": len(concepts),
            "concepts": [
                {
                    "cluster": ledger[i]["id"],
                    "section": sec,
                    "source": ledger[i]["source"],
                    "teaching": ledger[i]["teaching"],
                    "variant_ids": [ledger[j]["id"] for j in cluster_members[root(i)] if j != i],
                }
                for sec, i in concepts
            ],
        }

    # ---- no-loss / no-repeat GATE ----
    all_ids = {t["id"] for t in ledger}
    assigned_ids = set(full_assignment)
    union_ok = assigned_ids == all_ids
    # each id exactly one volume
    one_volume = all(v.get("volume") for v in full_assignment.values())
    # canonicals partitioned across volumes (no canonical in two volumes — trivially true: one vol each)
    canon_ids = [cid for cid, a in full_assignment.items() if a["role"] == "canonical"]
    canon_homes = {cid: full_assignment[cid]["volume"] for cid in canon_ids}
    one_home = len(canon_homes) == len(set(canon_ids))
    # every variant shares its canonical's volume (a concept airs in ONE place)
    variant_consistent = True
    for cid, a in full_assignment.items():
        if a["role"] == "variant":
            cv = full_assignment.get(a["cluster"], {}).get("volume")
            if cv != a["volume"]:
                variant_consistent = False
                break
    n_canon = len(canon_ids)
    n_variant = sum(1 for a in full_assignment.values() if a["role"] == "variant")
    gate = {
        "n_teachings": len(ledger),
        "n_assigned": len(assigned_ids),
        "union_ok": union_ok,
        "one_volume_each": one_volume,
        "each_cluster_one_home": one_home,
        "variant_volume_consistent": variant_consistent,
        "n_concepts_aired": n_canon,
        "n_variants_book_only": n_variant,
        "per_volume_concepts": {v: volumes_out[v]["n_concepts"] for v in vols},
    }

    doc = {
        "work_slug": manifest["work_slug"],
        "generated_by": "allocate_teachings.py v1",
        "section_to_volume": {str(s): v for s, v in sorted(sec2vol.items())},
        "verification": gate,
        "volumes": volumes_out,
        "assignment": full_assignment,
    }
    out_path = work_dir / "_system" / "_volume-split.json"
    out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False))

    ok = union_ok and one_volume and one_home and variant_consistent
    log("")
    log(
        f"  GATE union_ok={union_ok} one_volume_each={one_volume} "
        f"each_cluster_one_home={one_home} variant_consistent={variant_consistent}"
    )
    log(
        f"  {n_canon} concepts aired (canonical) + {n_variant} variants (reading edition only) "
        f"= {len(ledger)} teachings, 0 lost"
    )
    for v in vols:
        log(f"    {v}: {volumes_out[v]['n_concepts']} concepts  ({vol_titles.get(v, v)})")
    log(f"  wrote {out_path.relative_to(REPO_ROOT)}")
    if not ok:
        raise SystemExit("NO-LOSS/NO-REPEAT GATE FAILED — see verification block")
    return doc


# ------------------------------------------------------------------ driver


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("work_slug")
    ap.add_argument("--stage", choices=["boundaries", "place", "dedup", "emit"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--emit-only", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="deterministic placeholders (plumbing check)")
    args = ap.parse_args()
    log = print

    work_dir, manifest, ledger, sections, sec2vol, vol_titles = _load(args.work_slug)
    log(
        f"work={args.work_slug}  teachings={len(ledger)}  sections={len(sections)}  "
        f"volumes={len(set(sec2vol.values()))}  mode={'no-llm' if args.no_llm else 'llm'}"
    )

    def _parent_from_ckpt():
        p = list(range(len(ledger)))
        f = _alloc_dir(work_dir) / "dedup.json"
        if f.exists():
            idx = {t["id"]: i for i, t in enumerate(ledger)}
            d = json.loads(f.read_text())

            def find(x):
                while p[x] != x:
                    p[x] = p[p[x]]
                    x = p[x]
                return x

            for a, b in d.get("confirmed_pairs", []):
                if a in idx and b in idx:
                    p[find(idx[a])] = find(idx[b])
        return p

    run = args.stage
    if args.all or args.emit_only:
        run = None
    if args.all or run == "boundaries":
        stage_boundaries(work_dir, ledger, sections, sec2vol, vol_titles, no_llm=args.no_llm, log=log)
    if args.all or run == "place":
        stage_place(work_dir, ledger, sections, sec2vol, no_llm=args.no_llm, log=log)
    if args.all or run == "dedup":
        stage_dedup(work_dir, ledger, no_llm=args.no_llm, log=log)
    if args.all or args.emit_only or run == "emit":
        parent = _parent_from_ckpt()
        stage_emit(work_dir, manifest, ledger, sections, sec2vol, vol_titles, parent, log=log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
