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
_CHROME = (
    "btn",
    "froala-only",
    "delete-hadees",
    "poetry-restore",
    "ks-ahadees-delete",
    # The one-letter category badge on the lecture guide's index chips — 214 of
    # them, `W`, `I`, `R`, `Q`. A glyph that means nothing without a legend
    # nobody has, and it sits immediately before the chip's label with no
    # separator, so the two ran together into "WWALEE" and "IANS" on the page.
    #
    # THE BADGE ONLY. The chip itself stays, and that correction cost a run:
    # dropping `sessionguide` and `box-hub` wholesale — which read as obviously
    # right, they are the admin's own furniture — took 36 of Surah Al-Fateha's
    # 63 illustrations with them. The `sessionGuide-desc` span holds the label
    # AND the diagram it labels: `<span …>A vs THE<img src="…"></span>`. The
    # label is a caption, not chrome.
    "sessionguide-letter",
)

# Font Awesome. 508 of them, 496 being the `fa-ban` on the admin's own row-delete
# control — every one an EMPTY element, and every one matched by the emphasis rule
# below because Font Awesome's tag of choice is `<i>`. An empty `<i>` emits `*`
# open and `*` close with nothing between, so the page carried 133 stray `**` in
# Surah Al-Fateha and 16 in Love Of The Prophet, which is live on the site today.
#
# Matched on WHOLE class tokens rather than by substring, unlike everything else
# here: `fa` is two letters and appears inside ordinary words.
_ICON_TOKEN = re.compile(r"(?:^|\s)(?:fa|fas|far|fab|fal|glyphicon)(?:-[\w-]+)?(?=\s|$)")

# Unwrapped: the element disappears, its children stay. Editor layout, not content.
_LAYOUT = ("col-", "row", "container", "fr-draggable", "clearfix")

# Blocks that become blockquotes. The renderer decides which KIND afterwards.
_QUOTED = (
    "ayah-card",
    "hadees-widget",
    "ks-ahadees-container",
    "poetry-section",
    "poetry-couplet",
    # The Quran widget — 370 of them, and the reason this matters most on a book
    # about a surah. It carries the verse in Arabic, the ayah number and the
    # English underneath, exactly the shape `ayah-card` carries; unlisted, all
    # three fell out as loose paragraphs and the page showed scripture set like
    # ordinary prose.
    "quranwidget",
)

# Arabic/Urdu inline spans — kept as text; the reader styles by script, not class.
_SCRIPT = ("inlinearabic", "amiricrimson", "urdunastaleeq", "ayah-arabic", "ayah-translation")

_BLOCK = {"p", "div", "section", "article", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br"}


@dataclass
class Converted:
    markdown: str
    images: list[str] = field(default_factory=list)  # src values, as authored
    # Corpus images the author wrote with a host in front of them. Counted apart
    # from `images` only so the report can say how many were recovered that way —
    # they are the same files and they localise identically.
    hosted_images: list[str] = field(default_factory=list)
    external_images: list[str] = field(default_factory=list)  # http(s) — genuinely somewhere else
    # Relative srcs that name no file in the corpus. Reported, never emitted: an
    # `<img>` that cannot resolve is a broken icon in a reading edition.
    unmappable_images: list[str] = field(default_factory=list)
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


def _is_chrome(classes: str) -> bool:
    """The editor's furniture, dropped whole — including its icons."""
    return _is(classes, _CHROME) or _ICON_TOKEN.search(classes) is not None


# Third-party verse-number badges hotlinked from myislam.sfo3.digitaloceanspaces.com.
# Dropped rather than downloaded: they are somebody else's decorative numerals, the
# reader already renders a citation chip for the verse from the text itself, and
# hotlinking them would make an offline page depend on another site staying up.
_BADGE_SRC = re.compile(r"/ayat/ayah-\d+\.\w+$", re.I)


# THE ONE SHAPE A SESSION ILLUSTRATION IS FILED UNDER, wherever the reference to
# it happens to have been typed: `Resources/IMAGES/<session>/<guid>.<ext>`.
#
# The tail is anchored and the head is not, which is the whole point. The same
# picture is referenced three ways in these transcripts, because the admin was
# authored over ten years on whatever machine was in front of Asif:
#
#     Resources/IMAGES/87/<guid>.jpg                      relative
#     https://session.kashkole.com/Resources/IMAGES/…     the live admin
#     http://localhost:786/Resources/IMAGES/…             his own dev server
#
# All three name the SAME file in `Resources Images/`, and 47 of the corpus's
# image references across the seven ingestable groups are one of the last two.
# Reading the host as meaningful is what made them "external, cannot be
# localised" — a description of where the editor's browser once fetched a
# picture from, mistaken for where the picture lives.
_CORPUS_IMAGE_RE = re.compile(r"(?:.*/)?Resources/IMAGES/(\d+)/([0-9a-fA-F-]{36})\.(\w+)$", re.I)

_SCHEME_HOST_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://[^/]*", re.I)


def corpus_ref(src: str) -> tuple[str, str] | None:
    """The `(session folder, filename)` a reference names, or None if it names none.

    The single answer to "which file is this?", asked by the classifier when the
    HTML is read and again by `localise_images` when the markdown is rewritten.
    One function because they must never disagree: a src the classifier counts as
    an image and the rewriter does not recognise is copied to disk, uploaded to
    R2, given a database row — and then pointed at by nothing.

    Case is folded into the returned name, so a `.JPG` written in 2016 and a
    `.jpg` written in 2021 are one file rather than two.
    """
    path = src.split("?", 1)[0].split("#", 1)[0]
    match = _CORPUS_IMAGE_RE.match(_SCHEME_HOST_RE.sub("", path))
    if match is None:
        return None
    return match.group(1), f"{match.group(2).lower()}.{match.group(3).lower()}"


class _Walker(HTMLParser):
    """Emit markdown while tracking which enclosing element we are inside."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.images: list[str] = []
        self.hosted: list[str] = []
        self.external: list[str] = []
        self.unmappable: list[str] = []
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

        if self._skip_depth or (tag not in ("br", "img") and _is_chrome(classes)):
            if _is_chrome(classes) and not self._skip_depth:
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
            if corpus_ref(src) is None:
                # Nothing in `Resources Images/` answers to this reference. It is
                # recorded by name and NOT emitted, because the alternative is a
                # broken-image icon in a printed reading edition — and, when the
                # src carries a host, a reader's browser reaching out to somebody
                # else's server from inside a chapter they were granted access to.
                # Same argument the verse badges above are dropped under.
                target = self.external if _SCHEME_HOST_RE.match(src) else self.unmappable
                target.append(src)
                return
            if _SCHEME_HOST_RE.match(src):
                self.hosted.append(src)
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
            # Translation FIRST: `quran-ayat-translation` contains `quran-ayat`,
            # so asking about the Arabic first would file every English gloss in
            # the widget as Arabic and the card would come out with no
            # translation at all.
            if "ayah-translation" in classes or "quran-ayat-translation" in classes:
                self._part = "tr"
            elif "ayah-arabic" in classes or "quran-ayat" in classes:
                self._part = "ar"

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
        hosted_images=walker.hosted,
        external_images=walker.external,
        unmappable_images=walker.unmappable,
        dropped_chrome=walker.chrome_dropped,
        dropped_badges=walker.badges_dropped,
        quotes=walker.quotes,
    )


# A markdown image, matched WHOLE. The rewrite below replaces the entire target,
# never a substring of it.
#
# Substituting on the path fragment alone is what turned
# `https://session.kashkole.com/Resources/IMAGES/87/<guid>.jpg` into
# `https://session.kashkole.com/images/87/<guid>.jpg` — a URL that has never
# existed on that host, on a page whose file was sitting correctly in the bucket
# the whole time. The file was copied, uploaded and given a row; only the src
# still pointed at the internet.
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*(\S+?)\s*\)")


def localise_images(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Point every illustration at the book's own asset folder.

    Returns the rewritten markdown and the `(session_id, filename)` pairs it
    wants, so the caller copies exactly those out of the Drive folder and reports
    any it cannot find rather than shipping a broken image.

    The path written is `images/<sid>/<file>`, relative to `book/`, which is where
    the print edition is built and therefore resolves for the PDF as written. The
    site has no such folder, so `_listener_book._media_image_srcs` rewrites the
    rendered `<img src>` a second time onto the gated `/media/<slug>/image/…`
    route. Those two are pinned against each other by a test, because between
    them they are the only reason a picture appears on the page.
    """
    wanted: list[tuple[str, str]] = []

    def _swap(match: re.Match[str]) -> str:
        ref = corpus_ref(match.group(2))
        if ref is None:
            return match.group(0)
        session_id, filename = ref
        wanted.append((session_id, filename))
        return f"![{match.group(1)}](images/{session_id}/{filename})"

    return _MD_IMAGE_RE.sub(_swap, markdown), wanted
