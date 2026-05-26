"""
Class-aware HTML → markdown converter for KAHSKOLE Urdu content.

Strips ALL HTML to clean markdown. Preserves semantic class signals as
text-level markers so downstream phases (Phase 0c phonetics, Phase 0b
refinement, translation) can find them:

  ⟪ar:…⟫       — inline Arabic (was <span class="ArabicFont">…)
  ⟪ar-quote:…⟫ — KAHSKOLE Arabic quote with Urdu translation following

Inline base64 images are NOT processed here — they're left as
{{IMG:<placeholder>}} tokens that the prepare stage replaces after it
decodes and saves the image bytes.
"""
from __future__ import annotations
import re
from bs4 import BeautifulSoup, NavigableString, Tag


def _has_class(tag: Tag, name: str) -> bool:
    classes = tag.get("class") or []
    return name in classes


def _has_any_class(tag: Tag, *names: str) -> bool:
    classes = set(tag.get("class") or [])
    return any(n in classes for n in names)


def _txt(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()

    # KAHSKOLE Quran table widget — caller may handle differently;
    # here we render as best-effort inline blockquote with no validated citation
    # (the Quran validation pass picks this up via TopicAyats / HQAyats matching).
    if name == "table" and node.find(class_="Quran_Shell") is not None:
        return _render_kahskole_quran_inline(node)

    # Images get a placeholder — prepare.py replaces this with {{IMG:NNN}}
    # after it indexes the image data URI into a numbered slot.
    if name == "img":
        src = node.get("src") or ""
        if src.startswith("data:image"):
            return "{{IMG:__INLINE__}}"
        return f"{{{{IMG_URL:{src}}}}}"

    # Drop legacy embeds
    if name in ("object", "embed", "param"):
        return ""

    # Inline Arabic markers — wrap so Phase 0c can find them
    if name == "span" and _has_any_class(node, "ArabicFont", "inlineArabic"):
        inner = "".join(_txt(c) for c in node.children).strip()
        return f"⟪ar:{inner}⟫" if inner else ""

    # KAHSKOLE arabic quote + urdu translation pair
    if name == "span" and _has_class(node, "CKArabicQuote"):
        inner = "".join(_txt(c) for c in node.children).strip()
        return f"⟪ar-quote:{inner}⟫"
    if name == "span" and _has_class(node, "CKUrduTranslation"):
        inner = "".join(_txt(c) for c in node.children).strip()
        return f" *{inner}*"

    # Red/highlight emphasis
    if name == "span" and _has_any_class(node, "RedHighlight", "highlight", "BlueHighlight"):
        inner = "".join(_txt(c) for c in node.children).strip()
        return f"**{inner}**" if inner else ""

    # KAHSKOLE inline heading marker (RedHeading inside flowing text)
    if name == "span" and _has_class(node, "RedHeading"):
        inner = "".join(_txt(c) for c in node.children).strip()
        return f"\n\n### {inner}\n\n" if inner else ""

    # Standard inline tags
    if name in ("strong", "b"):
        inner = "".join(_txt(c) for c in node.children).strip()
        return f"**{inner}**" if inner else ""
    if name in ("em", "i"):
        inner = "".join(_txt(c) for c in node.children).strip()
        return f"*{inner}*" if inner else ""

    if name == "br":
        return "\n"
    if name == "hr":
        return "\n\n---\n\n"

    return "".join(_txt(c) for c in node.children)


def _render_kahskole_quran_inline(widget: Tag) -> str:
    """KAHSKOLE inline Quran table — emit as marked blockquote; finalize pass
    will validate against HQAyats and add proper citation."""
    arabic_el = widget.find(class_="Quran_ArabicAyatUnicode")
    arabic = arabic_el.get_text(" ", strip=True) if arabic_el else ""
    surah_name_el = widget.find(class_="QuranTD_SurahName")
    surah_num_el = widget.find(class_="Quran_SurahNumber")
    ayat_num_el = widget.find(class_="QuranDIV_AyatNumberShell")
    translation_el = widget.find(class_="QuranTD_Translation")

    parts = []
    if surah_name_el:
        parts.append(surah_name_el.get_text(" ", strip=True))
    if surah_num_el:
        parts.append(surah_num_el.get_text(" ", strip=True))
    if ayat_num_el:
        parts.append(ayat_num_el.get_text(" ", strip=True))
    citation = ", ".join(p for p in parts if p)

    translation = translation_el.get_text(" ", strip=True) if translation_el else ""

    out = []
    if arabic:
        out.append(f"> ⟪ar:{arabic}⟫")
    if translation:
        out.append(f"> {translation}")
    if citation:
        out.append(f"> — *(Quran: {citation} — to be validated)*")
    return "\n" + "\n".join(out) + "\n" if out else ""


BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "ul", "ol", "li",
              "blockquote", "pre", "table", "tr", "td", "th"}


def _walk_blocks(node, out: list[str]) -> None:
    if isinstance(node, NavigableString):
        s = str(node)
        if s.strip():
            out.append(s)
        return
    if not isinstance(node, Tag):
        return

    name = node.name.lower()

    if name == "div" and _has_any_class(node, "row", "InpageBlock"):
        for c in node.children:
            _walk_blocks(c, out)
        return
    if name == "div" and any(c.startswith("col-") for c in (node.get("class") or [])):
        for c in node.children:
            _walk_blocks(c, out)
        return

    if name == "table" and node.find(class_="Quran_Shell") is not None:
        out.append(_txt(node))
        return

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        inner = "".join(_txt(c) for c in node.children).strip()
        if inner:
            out.append(f"\n{'#' * level} {inner}\n")
        return

    if name == "p":
        inner = "".join(_txt(c) for c in node.children).strip()
        if inner:
            out.append(f"\n{inner}\n")
        return

    if name == "ul":
        for li in node.find_all("li", recursive=False):
            inner = "".join(_txt(c) for c in li.children).strip()
            out.append(f"- {inner}\n")
        out.append("\n")
        return
    if name == "ol":
        for i, li in enumerate(node.find_all("li", recursive=False), 1):
            inner = "".join(_txt(c) for c in li.children).strip()
            out.append(f"{i}. {inner}\n")
        out.append("\n")
        return

    if name == "blockquote":
        inner = "".join(_txt(c) for c in node.children).strip()
        if inner:
            for line in inner.split("\n"):
                out.append(f"> {line}\n")
            out.append("\n")
        return

    if name == "table":
        rows = node.find_all("tr")
        if not rows:
            return
        rendered_rows = []
        for tr in rows:
            cells = tr.find_all(["td", "th"])
            cell_texts = ["".join(_txt(c) for c in cell.children).strip().replace("\n", " ")
                          for cell in cells]
            rendered_rows.append(cell_texts)
        if rendered_rows and all(len(r) == len(rendered_rows[0]) for r in rendered_rows):
            width = len(rendered_rows[0])
            out.append("\n")
            out.append("| " + " | ".join(rendered_rows[0]) + " |\n")
            out.append("| " + " | ".join(["---"] * width) + " |\n")
            for row in rendered_rows[1:]:
                out.append("| " + " | ".join(row) + " |\n")
            out.append("\n")
        else:
            for row in rendered_rows:
                out.append(" · ".join(row) + "\n")
        return

    if name == "div":
        for c in node.children:
            _walk_blocks(c, out)
        out.append("\n")
        return

    out.append(_txt(node))


def html_to_md(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    out: list[str] = []
    root = soup.body if soup.body else soup
    for child in root.children:
        _walk_blocks(child, out)
    md = "".join(out)

    md = re.sub(r"\n[ \t]+", "\n", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = md.strip() + "\n"
    return md
