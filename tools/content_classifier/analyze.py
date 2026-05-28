"""Round 1 KAHSKOLE taxonomy analysis.

Read-only. Computes:
  - Image dedup signals:
      * exact SHA-256 duplicates (already covered by image_dedupe.py but
        re-computed here for inline reporting)
      * perceptual-near duplicates via dHash (PIL + imagehash) — Hamming
        distance ≤ 8 over 64-bit dHash counts as "near-duplicate"
  - Topic content dedup signals:
      * exact SHA-256 duplicates of TopicDataUnicode (raw HTML)
      * exact SHA of normalized text (HTML stripped, whitespace collapsed)
      * near-duplicates: SequenceMatcher ratio ≥ 0.90 on normalized text
        (compared only within a binder-name-similar window to keep it tractable)
  - Quran-citation co-occurrence signals (which (surah,ayat) pairs appear
    in which topics).
  - Chapter-name signals to feed retitle proposal.

Outputs JSON at _workspace/plan/kashkole-taxonomy-r1-analysis.json.
The proposal document is composed in a separate step from that JSON.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from collections import defaultdict, Counter
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image
import imagehash

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from tools.source_extractor.db import query_json

EXTRACT_ROOT = REPO_ROOT / "_workspace" / "kashkole-corpus" / "extracted" / "kashkole"
OUT_DIR = REPO_ROOT / "_workspace" / "plan"
OUT_DIR.mkdir(parents=True, exist_ok=True)


HTML_TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
QURAN_WIDGET_RE = re.compile(r"\{\s*(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*\}")


def _normalize_text(html: str | None) -> str:
    if not html:
        return ""
    plain = HTML_TAG_RE.sub(" ", html)
    plain = WS_RE.sub(" ", plain).strip()
    return plain


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def pull_topic_corpus() -> list[dict]:
    """Pull every topic row from KAHSKOLE with binder + chapter context."""
    rows = query_json("KASHKOLE", """
SELECT bc.BinderID AS binder_id, b.BinderName AS binder_name,
       bc.ChapterID AS chapter_id, c.ChapterName AS chapter_name,
       ct.ChapterTopicOrder AS topic_order,
       t.TopicID AS topic_id, t.TopicName AS topic_name,
       t.TopicNameEnglish AS topic_name_en,
       td.TopicUnicode AS html
FROM BinderChapters bc
JOIN Binders b ON b.BinderID = bc.BinderID
JOIN Chapters c ON c.ChapterID = bc.ChapterID
JOIN ChapterTopics ct ON ct.ChapterID = bc.ChapterID
JOIN Topics t ON t.TopicID = ct.TopicID
LEFT JOIN TopicDataUnicode td ON td.TopicID = t.TopicID
ORDER BY bc.BinderID, ct.ChapterTopicOrder
FOR JSON PATH;""")
    return rows


def analyze_images() -> dict:
    """Compute SHA-256 and perceptual-hash (dHash) groupings across all PNGs."""
    pngs = sorted(EXTRACT_ROOT.glob("*/*/_system/source/images/*.png"))
    print(f"  PNGs scanned: {len(pngs)}", file=sys.stderr)

    sha_groups: dict[str, list[Path]] = defaultdict(list)
    dhash_groups: dict[str, list[Path]] = defaultdict(list)
    dhash_to_sha: dict[str, str] = {}

    for i, p in enumerate(pngs):
        if i % 50 == 0:
            print(f"    image {i}/{len(pngs)}", file=sys.stderr)
        b = p.read_bytes()
        sha = hashlib.sha256(b).hexdigest()[:16]
        sha_groups[sha].append(p)
        try:
            img = Image.open(p).convert("L").resize((9, 8))
            dh = str(imagehash.dhash(img))
            dhash_groups[dh].append(p)
            dhash_to_sha[dh] = sha
        except Exception as e:
            print(f"    dhash failed for {p.name}: {e}", file=sys.stderr)

    # Exact-byte clusters with >1 instance
    sha_dupes = {sha: [str(p.relative_to(EXTRACT_ROOT)) for p in ps]
                 for sha, ps in sha_groups.items() if len(ps) > 1}

    # Perceptual near-duplicates: group dhashes within Hamming distance ≤ 8
    # of each other; collapse into clusters.
    dhash_keys = list(dhash_groups.keys())
    dh_objs = {k: imagehash.hex_to_hash(k) for k in dhash_keys}
    seen: set[str] = set()
    perceptual_clusters: list[list[str]] = []
    for k in dhash_keys:
        if k in seen:
            continue
        cluster = [k]
        seen.add(k)
        for k2 in dhash_keys:
            if k2 in seen:
                continue
            if dh_objs[k] - dh_objs[k2] <= 8:
                cluster.append(k2)
                seen.add(k2)
        if len(cluster) > 1 or len(dhash_groups[k]) > 1:
            perceptual_clusters.append(cluster)

    # Convert dhash clusters to image-path clusters, dedup against SHA clusters
    perceptual_path_clusters: list[dict] = []
    for cluster in perceptual_clusters:
        all_paths = []
        all_shas = set()
        for k in cluster:
            for p in dhash_groups[k]:
                all_paths.append(str(p.relative_to(EXTRACT_ROOT)))
                all_shas.add(dhash_to_sha[k])
        # Only interesting if cluster spans more than one SHA (otherwise it's
        # already covered by SHA dedup)
        if len(all_shas) > 1:
            perceptual_path_clusters.append({
                "shas": sorted(all_shas),
                "size": len(all_paths),
                "paths": sorted(all_paths),
            })

    return {
        "total_pngs": len(pngs),
        "unique_shas": len(sha_groups),
        "exact_dupe_clusters": [
            {"sha": sha, "size": len(paths), "paths": sorted(paths)}
            for sha, paths in sha_dupes.items()
        ],
        "perceptual_near_dupe_clusters": perceptual_path_clusters,
    }


def analyze_topic_content(topics: list[dict]) -> dict:
    """SHA + near-duplicate analysis on TopicDataUnicode."""
    print(f"  topics: {len(topics)}", file=sys.stderr)

    sha_html: dict[str, list[dict]] = defaultdict(list)
    sha_norm: dict[str, list[dict]] = defaultdict(list)
    normalized_by_topic: dict[int, str] = {}

    for t in topics:
        html = t.get("html") or ""
        norm = _normalize_text(html)
        normalized_by_topic[int(t["topic_id"])] = norm
        # Skip empty content
        if not html.strip():
            continue
        sha_html[_sha(html)].append(t)
        if norm:
            sha_norm[_sha(norm)].append(t)

    exact_html_dupes = [
        {"sha": sha, "size": len(ts), "topics": [
            {"binder_id": int(t["binder_id"]), "chapter_id": int(t["chapter_id"]),
             "topic_id": int(t["topic_id"]), "topic_name": t.get("topic_name"),
             "binder_name": t.get("binder_name"), "chapter_name": t.get("chapter_name")}
            for t in ts
        ]} for sha, ts in sha_html.items() if len(ts) > 1
    ]

    exact_normalized_dupes = [
        {"sha": sha, "size": len(ts), "topics": [
            {"binder_id": int(t["binder_id"]), "chapter_id": int(t["chapter_id"]),
             "topic_id": int(t["topic_id"]), "topic_name": t.get("topic_name"),
             "binder_name": t.get("binder_name"), "chapter_name": t.get("chapter_name")}
            for t in ts
        ]} for sha, ts in sha_norm.items()
        if len(ts) > 1
        # Filter to not double-report already-caught exact HTML dupes
        and not any(_sha(t.get("html") or "") in {d["sha"] for d in exact_html_dupes} for t in ts)
    ]

    # Near-duplicates: SequenceMatcher ratio ≥ 0.90 on normalized text.
    # Comparing all 1337 × 1337 is 1.78M comparisons. To keep it tractable,
    # group topics into buckets by first 100 chars of normalized text, and
    # only compare within each bucket. This finds clusters where the opening
    # is similar (common case for content-derived dupes).
    buckets: dict[str, list[tuple[int, str]]] = defaultdict(list)
    nonempty_topics = [(int(t["topic_id"]), normalized_by_topic[int(t["topic_id"])])
                       for t in topics if normalized_by_topic[int(t["topic_id"])]]
    print(f"    non-empty topics for near-dupe analysis: {len(nonempty_topics)}",
          file=sys.stderr)
    for tid, norm in nonempty_topics:
        # Bucket by first 60 chars (after stripping); robust to whitespace
        head = norm[:60]
        buckets[head].append((tid, norm))

    # Within each bucket, pairwise compare
    near_clusters: list[set[int]] = []
    seen: set[int] = set()
    for head, members in buckets.items():
        if len(members) < 2:
            continue
        for i, (tid1, n1) in enumerate(members):
            if tid1 in seen:
                continue
            cluster = {tid1}
            for j in range(i + 1, len(members)):
                tid2, n2 = members[j]
                if tid2 in seen:
                    continue
                # Only compare if length is within 30%; avoids comparing
                # short fragments vs long ones
                if abs(len(n1) - len(n2)) > 0.3 * max(len(n1), len(n2)):
                    continue
                ratio = SequenceMatcher(None, n1, n2).quick_ratio()
                if ratio < 0.85:
                    continue
                ratio = SequenceMatcher(None, n1, n2).ratio()
                if ratio >= 0.90:
                    cluster.add(tid2)
                    seen.add(tid2)
            if len(cluster) > 1:
                near_clusters.append(cluster)
                seen.add(tid1)

    # Render near-clusters with context
    topic_by_id = {int(t["topic_id"]): t for t in topics}
    near_dupe_clusters = []
    seen_topic_ids: set[int] = set()
    # Skip near-dupes already in exact clusters
    exact_topic_ids = set()
    for d in exact_html_dupes + exact_normalized_dupes:
        for t in d["topics"]:
            exact_topic_ids.add(t["topic_id"])

    for cluster in near_clusters:
        if cluster.issubset(exact_topic_ids):
            continue
        topics_data = []
        for tid in sorted(cluster):
            if tid in topic_by_id:
                t = topic_by_id[tid]
                topics_data.append({
                    "binder_id": int(t["binder_id"]),
                    "chapter_id": int(t["chapter_id"]),
                    "topic_id": tid,
                    "topic_name": t.get("topic_name"),
                    "binder_name": t.get("binder_name"),
                    "chapter_name": t.get("chapter_name"),
                    "norm_len": len(normalized_by_topic[tid]),
                })
        if len(topics_data) > 1:
            near_dupe_clusters.append({
                "size": len(topics_data),
                "topics": topics_data,
            })

    return {
        "exact_html_dupe_clusters": exact_html_dupes,
        "exact_normalized_dupe_clusters": exact_normalized_dupes,
        "near_dupe_clusters": near_dupe_clusters,
    }


def quran_citation_overlap(topics: list[dict]) -> dict:
    """Co-occurrence: which (surah, ayat) pairs are cited in which topics."""
    citations: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for t in topics:
        html = t.get("html") or ""
        for m in QURAN_WIDGET_RE.finditer(html):
            surah = int(m.group(1))
            start = int(m.group(2))
            end = int(m.group(3)) if m.group(3) else start
            for ayat in range(start, end + 1):
                citations[(surah, ayat)].append({
                    "binder_id": int(t["binder_id"]),
                    "chapter_id": int(t["chapter_id"]),
                    "topic_id": int(t["topic_id"]),
                    "chapter_name": t.get("chapter_name"),
                })

    # Most-cited verses
    most_cited = sorted(citations.items(), key=lambda kv: -len(kv[1]))[:30]
    return {
        "total_unique_verses_cited": len(citations),
        "top_verses": [
            {"surah": s, "ayat": a, "occurrences": len(refs),
             "first_3_refs": refs[:3]}
            for (s, a), refs in most_cited
        ],
    }


def chapter_metadata(topics: list[dict]) -> dict:
    """Aggregate per-chapter info to inform retitle proposals."""
    by_chapter: dict[tuple[int, int], dict] = {}
    for t in topics:
        key = (int(t["binder_id"]), int(t["chapter_id"]))
        if key not in by_chapter:
            by_chapter[key] = {
                "binder_id": int(t["binder_id"]),
                "binder_name": t.get("binder_name"),
                "chapter_id": int(t["chapter_id"]),
                "chapter_name": t.get("chapter_name"),
                "topic_count": 0,
                "topic_labels": [],
                "topic_labels_en": [],
                "total_content_chars": 0,
            }
        c = by_chapter[key]
        c["topic_count"] += 1
        c["topic_labels"].append(t.get("topic_name"))
        c["topic_labels_en"].append(t.get("topic_name_en"))
        c["total_content_chars"] += len((t.get("html") or ""))
    return {"chapters": list(by_chapter.values())}


def main() -> None:
    print("[1/4] Pulling topic corpus from DB...", file=sys.stderr)
    topics = pull_topic_corpus()

    print("[2/4] Analyzing images (SHA + dHash)...", file=sys.stderr)
    image_analysis = analyze_images()

    print("[3/4] Analyzing topic content (SHA + near-dupe)...", file=sys.stderr)
    content_analysis = analyze_topic_content(topics)

    print("[4/4] Computing Quran-citation overlap + chapter metadata...",
          file=sys.stderr)
    quran_analysis = quran_citation_overlap(topics)
    chapter_meta = chapter_metadata(topics)

    out = {
        "version": 1,
        "kashkole_topic_count": len(topics),
        "images": image_analysis,
        "topic_content": content_analysis,
        "quran_citations": quran_analysis,
        "chapters": chapter_meta,
    }
    out_path = OUT_DIR / "kashkole-taxonomy-r1-analysis.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"\nWrote {out_path}", file=sys.stderr)
    print(f"  exact image dupes: {len(image_analysis['exact_dupe_clusters'])} clusters",
          file=sys.stderr)
    print(f"  perceptual near image dupes: "
          f"{len(image_analysis['perceptual_near_dupe_clusters'])} clusters",
          file=sys.stderr)
    print(f"  exact HTML content dupes: "
          f"{len(content_analysis['exact_html_dupe_clusters'])} clusters",
          file=sys.stderr)
    print(f"  exact normalized content dupes: "
          f"{len(content_analysis['exact_normalized_dupe_clusters'])} clusters",
          file=sys.stderr)
    print(f"  near content dupes (>=90%): "
          f"{len(content_analysis['near_dupe_clusters'])} clusters",
          file=sys.stderr)


if __name__ == "__main__":
    main()
