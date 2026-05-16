#!/usr/bin/env python3
"""
detect_user_delta.py — Identifies paragraphs and sentences the user edited since the last
agent revision, with explicit reporting of:
  - Punctuation-only changes
  - Paragraph splits and merges
  - Translation changes (when a parenthetical English gloss has been changed)

Usage:
    python detect_user_delta.py <chapter_file>
    python detect_user_delta.py <chapter_file> <snapshot_file>

Output (stdout): Human-readable delta report for the agent.
Output (stderr): Full JSON report for programmatic use.

Protection levels:
    PARAGRAPH_SPLIT     — user broke one paragraph into shorter ones; never merge back.
    PARAGRAPH_MERGE     — user merged multiple paragraphs into one; preserve as-is.
    PARAGRAPH           — entire paragraph changed or added; preserve verbatim.
    SENTENCE            — specific sentence(s) changed; preserve those sentences verbatim.
    PUNCTUATION         — punctuation-only change; preserve and register as stylistic choice.
    TRANSLATION_CHANGE  — parenthetical English translation of a non-English word was changed
                          by the user. NEW TRANSLATION becomes canonical. Must be applied to
                          all chapters and recorded in references/translations-glossary.md.

If no snapshot exists, all content is available for revision (first run).
"""

import sys
import os
import re
import json
import difflib
import string


# ---------------------------------------------------------------------------
# Text splitting helpers
# ---------------------------------------------------------------------------

def get_snapshot_path(chapter_path):
    """Snapshots live under the sibling _system/snapshots/ of the chapter dir."""
    chapter_dir = os.path.dirname(os.path.abspath(chapter_path))
    base = os.path.splitext(os.path.basename(chapter_path))[0]
    ext  = os.path.splitext(chapter_path)[1]
    book_dir = os.path.dirname(chapter_dir)
    snapshots_dir = os.path.join(book_dir, '_system', 'snapshots')
    os.makedirs(snapshots_dir, exist_ok=True)
    return os.path.join(snapshots_dir, f"{base}-snapshot{ext}")


def split_paragraphs(text):
    """Split text into paragraphs on blank lines."""
    paragraphs = []
    current_lines = []
    for line in text.split('\n'):
        if line.strip() == '':
            if current_lines:
                paragraphs.append('\n'.join(current_lines))
                current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        paragraphs.append('\n'.join(current_lines))
    return paragraphs


def split_sentences(text):
    """
    Split paragraph text into sentences.
    Handles: .  !  ?  ...  !?  ?!  multiple punctuation marks.
    Keeps the sentence-ending punctuation attached to the sentence it closes.
    """
    pattern = r'(?<=[.!?])\s+(?=[A-Z\"])'
    parts = re.split(pattern, text.strip())
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Punctuation analysis
# ---------------------------------------------------------------------------

PUNCTUATION_CHARS = set('.,;:!?\'"-()[]{}…')


def strip_punctuation(s):
    """Return the text with all punctuation and whitespace removed, lowercased."""
    return re.sub(r'[^\w\s]', '', s).strip().lower()


def is_punctuation_only_change(s1, s2):
    """Return True if s1 and s2 differ only in punctuation/spacing, not in words."""
    return strip_punctuation(s1) == strip_punctuation(s2) and s1 != s2


def describe_punctuation_change(s_old, s_new):
    """Produce a short human-readable description of what punctuation changed."""
    diffs = list(difflib.ndiff(s_old, s_new))
    removed = ''.join(c[2] for c in diffs if c.startswith('- ') and c[2] in PUNCTUATION_CHARS)
    added   = ''.join(c[2] for c in diffs if c.startswith('+ ') and c[2] in PUNCTUATION_CHARS)
    if removed and added:
        return f"punctuation changed: '{removed}' → '{added}'"
    elif removed:
        return f"punctuation removed: '{removed}'"
    elif added:
        return f"punctuation added: '{added}'"
    else:
        return "punctuation/spacing adjusted"


# ---------------------------------------------------------------------------
# Translation change detection
# ---------------------------------------------------------------------------

# Pattern: one or more words followed by a parenthetical gloss
# Matches: "nikah (Islamic marriage contract)" → word="nikah", gloss="Islamic marriage contract"
# Also matches multi-word terms: "Dr. Sahab (Doctor, sir)"
TRANSLATION_PATTERN = re.compile(
    r'([A-Za-z][A-Za-z\s\'\-\.]{0,40}?)\s*\(([^)]{2,80})\)'
)


def extract_translations(text):
    """
    Return a dict of {term: gloss} for every word(gloss) pattern found in text.
    Keys are lowercased for comparison.
    """
    return {
        m.group(1).strip().lower(): m.group(2).strip()
        for m in TRANSLATION_PATTERN.finditer(text)
    }


def find_translation_changes(snapshot_sentence, current_sentence):
    """
    Compare parenthetical translations between two versions of a sentence.
    Returns a list of dicts:
      {
        "word":            str,   # the non-English term (lowercased)
        "old_translation": str or None,
        "new_translation": str,
        "kind":            "changed" | "added"
      }
    Only returns entries where the translation actually changed or was newly added.
    Does NOT return entries where the translation was removed (deletion is not a new canonical).
    """
    old_trans = extract_translations(snapshot_sentence)
    new_trans = extract_translations(current_sentence)
    changes = []

    for word, new_gloss in new_trans.items():
        old_gloss = old_trans.get(word)
        if old_gloss is None:
            # Translation newly added for this word
            changes.append({
                "word": word,
                "old_translation": None,
                "new_translation": new_gloss,
                "kind": "added"
            })
        elif old_gloss != new_gloss:
            # Translation wording was changed
            changes.append({
                "word": word,
                "old_translation": old_gloss,
                "new_translation": new_gloss,
                "kind": "changed"
            })

    return changes


# ---------------------------------------------------------------------------
# Sentence-level diffing within a paragraph
# ---------------------------------------------------------------------------

def diff_paragraph_sentences(snapshot_para, current_para):
    """
    Diff two versions of a paragraph at the sentence level.
    Returns a list of sentence-level change records:
      {
        "sentence_index":      int,
        "change_type":         "punctuation_only" | "word_change" |
                               "translation_change" | "sentence_added",
        "snapshot_sentence":   str or None,
        "current_sentence":    str,
        "description":         str,
        "translation_changes": list  # populated when change_type == "translation_change"
      }
    """
    snap_sents    = split_sentences(snapshot_para)
    current_sents = split_sentences(current_para)
    changes = []

    matcher = difflib.SequenceMatcher(None, snap_sents, current_sents, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue

        if tag == 'replace':
            for offset in range(max(i2 - i1, j2 - j1)):
                s_idx = j1 + offset
                i_idx = i1 + offset
                s_sent = current_sents[s_idx] if s_idx < j2 else None
                o_sent = snap_sents[i_idx]    if i_idx < i2 else None

                if s_sent is None:
                    continue  # sentence deleted

                if o_sent is None:
                    # New sentence — check if it introduces translations
                    trans = find_translation_changes('', s_sent)
                    changes.append({
                        "sentence_index":      s_idx,
                        "change_type":         "sentence_added",
                        "snapshot_sentence":   None,
                        "current_sentence":    s_sent,
                        "description":         "sentence added by user",
                        "translation_changes": trans
                    })
                elif is_punctuation_only_change(o_sent, s_sent):
                    changes.append({
                        "sentence_index":      s_idx,
                        "change_type":         "punctuation_only",
                        "snapshot_sentence":   o_sent,
                        "current_sentence":    s_sent,
                        "description":         describe_punctuation_change(o_sent, s_sent),
                        "translation_changes": []
                    })
                else:
                    # Word change — check for translation updates
                    trans = find_translation_changes(o_sent, s_sent)
                    change_type = "translation_change" if trans else "word_change"
                    desc = (
                        f"translation updated: " +
                        ", ".join(
                            f"'{t['word']}' "
                            + (f"({t['old_translation']}) → ({t['new_translation']})"
                               if t['kind'] == 'changed'
                               else f"→ ({t['new_translation']}) [newly added]")
                            for t in trans
                        )
                        if trans else "sentence rewritten by user"
                    )
                    changes.append({
                        "sentence_index":      s_idx,
                        "change_type":         change_type,
                        "snapshot_sentence":   o_sent,
                        "current_sentence":    s_sent,
                        "description":         desc,
                        "translation_changes": trans
                    })

        elif tag == 'insert':
            for idx in range(j1, j2):
                trans = find_translation_changes('', current_sents[idx])
                changes.append({
                    "sentence_index":      idx,
                    "change_type":         "sentence_added",
                    "snapshot_sentence":   None,
                    "current_sentence":    current_sents[idx],
                    "description":         "sentence added by user",
                    "translation_changes": trans
                })

    return changes


# ---------------------------------------------------------------------------
# Paragraph structure change detection
# ---------------------------------------------------------------------------

def classify_structural_change(snap_count, cur_count):
    """
    Given the number of snapshot paragraphs and current paragraphs in a replace block,
    return a reason string.
    """
    if cur_count > snap_count:
        return "paragraph_split"
    elif cur_count < snap_count:
        return "paragraph_merge"
    else:
        return "user_edited"


# ---------------------------------------------------------------------------
# Main delta detection
# ---------------------------------------------------------------------------

def detect_delta(chapter_path, snapshot_path=None):
    if snapshot_path is None:
        snapshot_path = get_snapshot_path(chapter_path)

    if not os.path.exists(snapshot_path):
        return {
            "has_snapshot": False,
            "protected_count": 0,
            "punctuation_change_count": 0,
            "paragraph_split_count": 0,
            "translation_changes": [],
            "protected_paragraphs": [],
            "message": (
                "No snapshot found. First agent revision of this chapter. "
                "All paragraphs available for refinement. "
                "Run save_snapshot.py after saving the revised chapter."
            )
        }

    with open(chapter_path, 'r', encoding='utf-8') as f:
        current_text = f.read()
    with open(snapshot_path, 'r', encoding='utf-8') as f:
        snapshot_text = f.read()

    if current_text.strip() == snapshot_text.strip():
        return {
            "has_snapshot": True,
            "protected_count": 0,
            "punctuation_change_count": 0,
            "paragraph_split_count": 0,
            "translation_changes": [],
            "protected_paragraphs": [],
            "message": "No user changes detected. All paragraphs available for refinement."
        }

    current_paras  = split_paragraphs(current_text)
    snapshot_paras = split_paragraphs(snapshot_text)

    matcher = difflib.SequenceMatcher(None, snapshot_paras, current_paras, autojunk=False)

    protected = []
    total_punct_changes = 0
    total_splits = 0
    all_translation_changes = []  # flat list across the whole chapter

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            snap_count   = i2 - i1
            cur_count    = j2 - j1
            block_reason = classify_structural_change(snap_count, cur_count)

            if block_reason == "paragraph_split":
                total_splits += 1

            for offset in range(cur_count):
                cur_idx  = j1 + offset
                snap_idx = i1 + offset
                cur_para  = current_paras[cur_idx]
                snap_para = snapshot_paras[snap_idx] if snap_idx < i2 else None

                sentence_changes = []
                punct_changes    = []
                para_trans       = []

                if snap_para:
                    sentence_changes = diff_paragraph_sentences(snap_para, cur_para)
                    punct_changes    = [c for c in sentence_changes
                                        if c["change_type"] == "punctuation_only"]
                    total_punct_changes += len(punct_changes)

                    # Collect translation changes from this paragraph
                    for sc in sentence_changes:
                        for tc in sc.get("translation_changes", []):
                            # Deduplicate by word (last occurrence wins)
                            existing = next(
                                (x for x in all_translation_changes if x["word"] == tc["word"]),
                                None
                            )
                            if existing:
                                existing.update(tc)
                            else:
                                all_translation_changes.append(dict(tc))
                            para_trans.append(tc)

                split_meta = None
                if block_reason == "paragraph_split":
                    split_meta = {
                        "split_from_count": snap_count,
                        "split_into_count": cur_count,
                        "piece_index": offset + 1
                    }
                elif block_reason == "paragraph_merge":
                    split_meta = {
                        "merged_from_count": snap_count,
                        "merged_into_count": cur_count
                    }

                protected.append({
                    "paragraph_index":     cur_idx,
                    "reason":              block_reason,
                    "content":             cur_para,
                    "sentence_changes":    sentence_changes,
                    "punctuation_changes": punct_changes,
                    "translation_changes": para_trans,
                    "structural_meta":     split_meta
                })

        elif tag == 'insert':
            for idx in range(j1, j2):
                # Scan newly inserted paragraphs for translations
                cur_para = current_paras[idx]
                inserted_trans = []
                for sc in diff_paragraph_sentences('', cur_para):
                    for tc in sc.get("translation_changes", []):
                        existing = next(
                            (x for x in all_translation_changes if x["word"] == tc["word"]),
                            None
                        )
                        if existing:
                            existing.update(tc)
                        else:
                            all_translation_changes.append(dict(tc))
                        inserted_trans.append(tc)

                protected.append({
                    "paragraph_index":     idx,
                    "reason":              "user_added",
                    "content":             cur_para,
                    "sentence_changes":    [],
                    "punctuation_changes": [],
                    "translation_changes": inserted_trans,
                    "structural_meta":     None
                })

        # 'equal'  → unchanged, safe to refine
        # 'delete' → user removed; do not restore

    tc_count = len(all_translation_changes)
    return {
        "has_snapshot":             True,
        "protected_count":          len(protected),
        "punctuation_change_count": total_punct_changes,
        "paragraph_split_count":    total_splits,
        "translation_changes":      all_translation_changes,
        "protected_paragraphs":     protected,
        "message": (
            f"{len(protected)} paragraph(s) protected "
            f"({total_splits} paragraph split(s), "
            f"{tc_count} translation change(s) detected). "
            f"{total_punct_changes} punctuation change(s). "
            f"All protected content must be preserved verbatim. "
            + (
                f"TRANSLATION UPDATES REQUIRED: update translations-glossary.md "
                f"and apply new translations across all chapters."
                if tc_count > 0 else ""
            )
        )
    }


# ---------------------------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------------------------

def print_readable_report(result):
    print("\n--- USER DELTA REPORT ---")
    print(f"Snapshot exists      : {result['has_snapshot']}")
    print(f"Protected paragraphs : {result['protected_count']}")
    print(f"Paragraph splits     : {result['paragraph_split_count']}")
    print(f"Punctuation changes  : {result['punctuation_change_count']}")
    print(f"Translation changes  : {len(result['translation_changes'])}")
    print(f"Message              : {result['message']}")

    # Translation changes get their own prominent section
    if result['translation_changes']:
        print("\n*** TRANSLATION UPDATES (CANONICAL — APPLY ACROSS ALL CHAPTERS) ***")
        print("Asif has changed how these words are translated. These are now the canonical")
        print("forms. Update references/translations-glossary.md and replace every occurrence")
        print("of the old translation in all chapter files.\n")
        for tc in result['translation_changes']:
            word = tc['word']
            new_t = tc['new_translation']
            old_t = tc.get('old_translation')
            if tc['kind'] == 'changed':
                print(f"  {word!r:30s}  ({old_t})  →  ({new_t})")
            else:
                print(f"  {word!r:30s}  [new]  →  ({new_t})")
        print()

    if result['protected_paragraphs']:
        print("PROTECTED CONTENT")
        print("(Preserve every protected paragraph EXACTLY — no rewording, no restructuring,")
        print(" no punctuation changes, not even spacing. These are Asif's choices.)")
        if result['paragraph_split_count'] > 0:
            print(" CRITICAL: paragraph splits indicate Asif prefers shorter paragraphs.")
            print(" NEVER merge split paragraphs back into one. Preserve each break as written.")
        print()

        for p in result['protected_paragraphs']:
            idx    = p['paragraph_index']
            reason = p['reason']

            if reason == "paragraph_split":
                meta  = p['structural_meta']
                label = (
                    f"PARAGRAPH SPLIT — piece {meta['piece_index']} of {meta['split_into_count']} "
                    f"(user broke 1 paragraph into {meta['split_into_count']})"
                )
            elif reason == "paragraph_merge":
                meta  = p['structural_meta']
                label = (
                    f"PARAGRAPH MERGE — user combined {meta['merged_from_count']} paragraphs into 1"
                )
            elif reason == "user_added":
                label = "user_added"
            else:
                label = "user_edited"

            print(f"  [Paragraph {idx} — {label}]")
            preview = p['content'][:140].replace('\n', ' ')
            if len(p['content']) > 140:
                preview += '...'
            print(f"  Content: \"{preview}\"")

            if p.get('translation_changes'):
                print(f"  TRANSLATION CHANGES in this paragraph:")
                for tc in p['translation_changes']:
                    if tc['kind'] == 'changed':
                        print(f"    '{tc['word']}': ({tc['old_translation']}) → ({tc['new_translation']})")
                    else:
                        print(f"    '{tc['word']}': [newly added] → ({tc['new_translation']})")

            if p['punctuation_changes']:
                print(f"  PUNCTUATION CHANGES in this paragraph:")
                for pc in p['punctuation_changes']:
                    print(f"    Sentence {pc['sentence_index']}: {pc['description']}")
                    print(f"      Before: \"{pc['snapshot_sentence']}\"")
                    print(f"      After : \"{pc['current_sentence']}\"")

            elif p['sentence_changes']:
                non_trans = [sc for sc in p['sentence_changes']
                             if sc['change_type'] not in ('translation_change',)]
                if non_trans:
                    print(f"  Sentence-level changes: {len(non_trans)}")
                    for sc in non_trans:
                        print(f"    Sentence {sc['sentence_index']} ({sc['change_type']}): {sc['description']}")

            print()

    print("--- END DELTA REPORT ---\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python detect_user_delta.py <chapter_file> [snapshot_file]")
        sys.exit(1)

    chapter_path  = sys.argv[1]
    snapshot_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = detect_delta(chapter_path, snapshot_path)
    print_readable_report(result)

    # Full JSON on stderr for programmatic consumption
    print(json.dumps(result, indent=2), file=sys.stderr)
