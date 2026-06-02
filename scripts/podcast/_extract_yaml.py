"""_extract_yaml.py — Minimal YAML reader for the podcast extract pipeline.

Split from _extract_helpers.py (DR-005 — files must stay under 600 lines).
Imported by _extract_contract.py; re-exported via _extract_helpers.py.
"""

from __future__ import annotations

from typing import Any


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s == "" or s.lower() == "null" or s == "~":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p) for p in inner.split(",")]
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        if not inner:
            return {}
        out: dict[str, Any] = {}
        for pair in inner.split(","):
            if ":" not in pair:
                raise ValueError(f"bad inline map entry: {pair!r}")
            k, v = pair.split(":", 1)
            out[k.strip()] = _parse_scalar(v)
        return out
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def load_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset → dict. Raises ValueError on unsupported constructs."""
    lines = text.splitlines()

    def parse_block(start: int, indent: int) -> tuple[Any, int]:
        # Decide if the block is a list (lines start with '- ') or a mapping.
        j = start
        while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("#")):
            j += 1
        if j >= len(lines):
            return None, j
        first = lines[j]
        first_indent = len(first) - len(first.lstrip())
        if first_indent < indent:
            return None, j

        if first.lstrip().startswith("- "):
            items: list[Any] = []
            k = j
            while k < len(lines):
                ln = lines[k]
                if not ln.strip() or ln.lstrip().startswith("#"):
                    k += 1
                    continue
                ln_indent = len(ln) - len(ln.lstrip())
                if ln_indent < indent:
                    break
                if ln_indent == indent and ln.lstrip().startswith("- "):
                    item_text = ln.lstrip()[2:]
                    if ":" in item_text and not item_text.startswith("'") and not item_text.startswith('"'):
                        # nested mapping inside a list item
                        sub: dict[str, Any] = {}
                        key, _, val = item_text.partition(":")
                        if val.strip():
                            sub[key.strip()] = _parse_scalar(val)
                        # consume further indented lines as part of this mapping
                        k += 1
                        nested, k = parse_block(k, indent + 4)
                        if isinstance(nested, dict):
                            sub.update(nested)
                        items.append(sub)
                        continue
                    items.append(_parse_scalar(item_text))
                    k += 1
                else:
                    break
            return items, k

        # Mapping
        m: dict[str, Any] = {}
        k = j
        while k < len(lines):
            ln = lines[k]
            if not ln.strip() or ln.lstrip().startswith("#"):
                k += 1
                continue
            ln_indent = len(ln) - len(ln.lstrip())
            if ln_indent < indent:
                break
            if ln_indent > indent:
                k += 1
                continue
            if ":" not in ln:
                raise ValueError(f"line {k+1}: expected `key: value`, got: {ln!r}")
            key, _, val = ln.partition(":")
            key = key.strip()
            val = val.rstrip()
            if val.strip() == "":
                # Block scalar coming on next lines
                k += 1
                child, k = parse_block(k, indent + 2)
                m[key] = child
                continue
            if val.strip() == ">":
                # Folded scalar — collect indented lines until dedent
                k += 1
                buf: list[str] = []
                while k < len(lines):
                    nxt = lines[k]
                    if not nxt.strip():
                        buf.append("")
                        k += 1
                        continue
                    nxt_indent = len(nxt) - len(nxt.lstrip())
                    if nxt_indent <= indent:
                        break
                    buf.append(nxt.strip())
                    k += 1
                folded = " ".join(s for s in buf if s).strip()
                m[key] = folded
                continue
            m[key] = _parse_scalar(val.lstrip())
            k += 1
        return m, k

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        return {}
    return parsed
