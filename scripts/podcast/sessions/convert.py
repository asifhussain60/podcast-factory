"""The authored HTML of a session -> the markdown the reading edition renders.

WHAT SURVIVES AND WHY

The transcripts were written in Froala inside the KSESSIONS admin, so the markup
mixes three unrelated things and only one of them is content:

  content     the verse cards, hadith, poetry, anecdotes, inline Arabic and Urdu
              Asif marked deliberately — `content/_shared/source-library/README.md`
              calls these protected and says never to treat them as noise
  layout      Bootstrap grid (`col-xs-12`, `row`) that positioned the editor's
              own panes and means nothing outside it
  chrome      Froala's artifacts (`fr-*`) and the admin's own buttons —
              `delete-hadees-btn`, `poetry-restore-btn froala-only-btn`. One of
              them says `froala-only-btn` in its own class list.

Chrome is dropped whole, layout is unwrapped, content is translated.

WHY THE OUTPUT CARRIES NO CLASSES

A quotation in this repo is a plain markdown blockquote: the Arabic, a blank
quoted line, then the translation. `renderMarkdown` tags `.ar`/`.tr` itself, adds
the `quran` class when the Arabic matches the canonical mushaf, and otherwise
classifies the block as hadith, verse or saying. Emitting our own classes would
be a second opinion about the same paragraph, which is the one thing the reader
contract is built to prevent — so a verse card and a hadith widget both become
the same blockquote, and the renderer decides what they are.

CASING IS NOT A DETAIL

`inlineArabic` in one session, `InlineArabic` in two others, both authored by
hand years apart. Every class test here folds case; matching exactly loses a
third of the Arabic in Love Of The Prophet alone.
"""

from __future__ import annotations

import html as html_mod
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

# Wholesale drops: an element carrying any of these is chrome, and its children go
# with it. `froala-only-btn` is self-describing; the rest are the admin's buttons.
_CHROME = ("btn", "froala-only", "delete-hadees", "poetry-restore", "ks-ahadees-delete")

# Unwrapped: the element disappears, its children stay. Editor layout, not content.
_LAYOUT = ("col-", "row", "container", "fr-draggable", "clearfix")

# Blocks that become blockquotes. The renderer decides which KIND afterwards.
_QUOTED = ("ayah-card", "hadees-widget", "ks-ahadees-container", "poetry-section", "poetry-couplet")

# Arabic/Urdu inline spans — kept as text; the reader styles by script, not class.
_SCRIPT = ("inlinearabic", "amiricrimson", "urdunastaleeq", "ayah-arabic", "ayah-translation")

_BLOCK = {"p", "div", "section", "article", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br"}


@dataclass
class Converted:
    markdown: str
    images: list[str] = field(default_factory=list)  # src values, as authored
    external_images: list[str] = field(default_factory=list)  # http(s) — cannot be localised
    dropped_chrome: int = 0
    dropped_badges: int = 0  # third-party verse-number graphics
    quotes: int = 0  # blocks promoted to blockquotes for the renderer to classify


def _classes(attrs: list[tuple[str, str | None]]) -> str:
    for key, value in attrs:
        if key.lower() == "class" and value:
            return value.lower()
    return ""


def _is(classes: str, needles: tuple[str, ...]) -> bool:
    return any(n in classes for n in needles)


# Third-party verse-number badges hotlinked from myislam.sfo3.digitaloceanspaces.com.
# Dropped rather than downloaded: they are somebody else's decorative numerals, the
# reader already renders a citation chip for the verse from the text itself, and
# hotlinking them would make an offline page depend on another site staying up.
_BADGE_SRC = re.compile(r"/ayat/ayah-\d+\.\w+$", re.I)


class _Walker(HTMLParser):
    """Emit markdown while tracking which enclosing element we are inside."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.images: list[str] = []
        self.external: list[str] = []
        self.badges_dropped = 0
        self.quotes = 0
        self.chrome_dropped = 0
        self._skip_depth = 0  # >0 while inside dropped chrome
        self._depth = 0  # open non-void elements, so a quote knows its own close
        self._quote_at: int | None = None  # depth the current quoted block opened at
        self._buf: list[str] = []  # captures a quoted block's text
        self._part: str | None = None  # "ar" | "tr" inside a verse card
        self._parts: dict[str, list[str]] = {"ar": [], "tr": []}
        self._list_stack: list[str] = []
        self._emphasis = 0

    # -- helpers ----------------------------------------------------------
    def _emit(self, text: str) -> None:
        if self._skip_depth:
            return
        if self._quote_at is not None:
            (self._parts[self._part] if self._part else self._buf).append(text)
            return
        self.out.append(text)

    def _newblock(self) -> None:
        target = self._buf if self._quote_at is not None else self.out
        if target and not "".join(target[-2:]).endswith("\n\n"):
            self._emit("\n\n")

    def _close_quote(self) -> None:
        """Flush the captured block as a blockquote and resume normal output."""
        self._emphasis = 0
        arabic = _tidy("".join(self._parts["ar"]))
        translation = _tidy("".join(self._parts["tr"]))
        loose = _tidy("".join(self._buf))
        if arabic or translation:
            body = "\n\n".join(p for p in (arabic, translation) if p)
        else:
            body = loose
        self._quote_at, self._part = None, None
        self._parts = {"ar": [], "tr": []}
        self._buf = []
        # Froala leaves tags crossed — `<h3><strong>x</h3>` appears in several
        # hadith widgets — so a `**` can open inside the block and never close.
        # Balanced here rather than at the tag, because the closer belongs to
        # whichever part the text actually landed in.
        if body.count("**") % 2:
            body += "**"
        if body:
            self.quotes += 1
            if self.out and not "".join(self.out[-2:]).endswith("\n\n"):
                self.out.append("\n\n")
            self.out.append(_blockquote(body))
            self.out.append("\n\n")

    # -- parser hooks -----------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = _classes(attrs)

        if self._skip_depth or (tag not in ("br", "img") and _is(classes, _CHROME)):
            if _is(classes, _CHROME) and not self._skip_depth:
                self.chrome_dropped += 1
            self._skip_depth += 1
            return

        if tag == "img":
            src = next((v for k, v in attrs if k.lower() == "src" and v), "")
            if not src:
                return
            if _BADGE_SRC.search(src):
                self.badges_dropped += 1
                return
            if src.startswith(("http://", "https://")):
                self.external.append(src)
            else:
                self.images.append(src)
            alt = next((v for k, v in attrs if k.lower() == "alt" and v), "") or ""
            self._newblock()
            self._emit(f"![{alt}]({src})")
            self._newblock()
            return

        if tag == "br":
            self._emit("\n")
            return

        self._depth += 1

        if self._quote_at is None and _is(classes, _QUOTED):
            self._quote_at = self._depth
            return
        if self._quote_at is not None:
            if "ayah-arabic" in classes:
                self._part = "ar"
            elif "ayah-translation" in classes:
                self._part = "tr"

        if tag in ("strong", "b"):
            self._emphasis += 1
            self._emit("**")
        elif tag in ("em", "i"):
            self._emphasis += 1
            self._emit("*")
        elif tag in ("ul", "ol"):
            self._list_stack.append(tag)
            self._newblock()
        elif tag == "li":
            marker = "1." if (self._list_stack and self._list_stack[-1] == "ol") else "-"
            self._emit("\n" + "  " * (len(self._list_stack) - 1) + marker + " ")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            # The session's own name is the chapter's `##`. Everything the author
            # marked as a heading inside it is therefore a section beneath that,
            # never a sibling — a promoted h1 would split one lecture into two
            # chapters at publish time.
            #
            # Inside a quoted block a heading is dropped to plain text: several
            # hadith widgets open with an <h3> naming the speaker, and `> ###`
            # renders as a heading floating inside a quotation.
            self._newblock()
            if self._quote_at is None:
                self._emit("### ")
        elif tag in _BLOCK and not _is(classes, _LAYOUT):
            self._newblock()

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in ("img", "br"):
            return

        if tag in ("strong", "b") and self._emphasis:
            self._emphasis -= 1
            self._emit("**")
        elif tag in ("em", "i") and self._emphasis:
            self._emphasis -= 1
            self._emit("*")
        elif tag in ("ul", "ol") and self._list_stack:
            self._list_stack.pop()
            self._newblock()
        elif tag in _BLOCK:
            self._newblock()

        if self._quote_at is not None:
            if self._part and self._depth <= self._quote_at + 1:
                self._part = None
            if self._depth <= self._quote_at:
                self._close_quote()
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data.strip():
            if data.strip() == "":
                self._emit(" " if self.out and not self.out[-1].endswith(("\n", " ")) else "")
            return
        self._emit(re.sub(r"[ \t]+", " ", data))


def _blockquote(text: str) -> str:
    """Prefix every line of a paragraph group with `> `."""
    return "\n".join(("> " + line) if line.strip() else ">" for line in text.split("\n"))


def _tidy(markdown: str) -> str:
    md = html_mod.unescape(markdown)
    md = md.replace(" ", " ")
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]{2,}", " ", md)
    return md.strip()


def convert(session_html: str) -> Converted:
    """Authored HTML -> markdown, with the images and chrome it carried reported."""
    if not session_html.strip():
        return Converted(markdown="")

    walker = _Walker()
    walker.feed(session_html)
    walker.close()

    body = _tidy("".join(walker.out))

    # Quote-block promotion is done on the flattened text rather than inside the
    # walker: a verse card nests <p>s, and prefixing during the walk produced
    # `> ` on the opening line only.
    blocks = []
    for block in body.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        blocks.append(stripped)

    return Converted(
        markdown="\n\n".join(blocks),
        images=walker.images,
        external_images=walker.external,
        dropped_chrome=walker.chrome_dropped,
        dropped_badges=walker.badges_dropped,
        quotes=walker.quotes,
    )


IMAGE_SRC_RE = re.compile(r"Resources/IMAGES/(\d+)/([0-9a-fA-F-]{36})\.(\w+)", re.I)


def localise_images(markdown: str, slug: str) -> tuple[str, list[tuple[str, str]]]:
    """Rewrite `Resources/IMAGES/<sid>/<guid>.jpg` to the book's own asset path.

    Returns the rewritten markdown and the (session_id, filename) pairs it wants,
    so the caller can copy exactly those out of the Drive folder and report any it
    cannot find rather than shipping a broken image.
    """
    wanted: list[tuple[str, str]] = []

    def _swap(match: re.Match[str]) -> str:
        session_id, guid, ext = match.group(1), match.group(2).lower(), match.group(3).lower()
        wanted.append((session_id, f"{guid}.{ext}"))
        return f"images/{session_id}/{guid}.{ext}"

    return IMAGE_SRC_RE.sub(_swap, markdown), wanted
