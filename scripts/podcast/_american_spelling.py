"""_american_spelling.py — one spelling standard across every deliverable.

These editions are published for an American readership, so the English is
American: honor not honour, center not centre, realize not realise, traveled not
travelled. The models that draft and re-voice chapters have no consistent
preference of their own, so without a deterministic pass a single book ends up
with both forms — sometimes in the same paragraph.

SCOPE — deliverables only. This normalizes prose the pipeline AUTHORS: the
reading edition (``book/book.md``), the NotebookLM chapter sources, the episode
framings, the slide-deck bundles. It must NEVER touch a source record: the OCR
extracts under ``_system/source/``, the shared source library, or third-party
research under ``research/``. Those are evidence, and the verbatim guarantee the
whole pipeline rests on means their words are not ours to respell.

TWO TIERS, deliberately separate:

``ORTHOGRAPHY`` is pure spelling — the same word, spelled the American way.
Mechanical and uncontroversial.

``USAGE`` is word choice that American style prefers (toward over towards, among
over amongst). It changes the prose slightly rather than only its spelling, so it
is kept in its own table where it can be reviewed — or switched off — without
touching the orthography rules.

Case is preserved: Honour -> Honor, HONOUR -> HONOR, honour -> honor.

Arabic script, transliterated terms, and anything inside a fenced block are left
alone — the substitutions are whole-word and ASCII, so they cannot fire inside a
transliteration, and fenced machine blocks are skipped outright.
"""

from __future__ import annotations

import re

# ── Tier 1: orthography ────────────────────────────────────────────────────
# -our/-or, -re/-er, -ise/-ize, -ce/-se, doubled-l, and the irregulars.
ORTHOGRAPHY: dict[str, str] = {
    # -our -> -or
    "honour": "honor",
    "honours": "honors",
    "honoured": "honored",
    "honouring": "honoring",
    "honourable": "honorable",
    "honourably": "honorably",
    "colour": "color",
    "colours": "colors",
    "coloured": "colored",
    "colouring": "coloring",
    "colourful": "colorful",
    "colourless": "colorless",
    "favour": "favor",
    "favours": "favors",
    "favoured": "favored",
    "favouring": "favoring",
    "favourite": "favorite",
    "favourites": "favorites",
    "favourable": "favorable",
    "favourably": "favorably",
    "behaviour": "behavior",
    "behaviours": "behaviors",
    "neighbour": "neighbor",
    "neighbours": "neighbors",
    "neighbouring": "neighboring",
    "neighbourhood": "neighborhood",
    "labour": "labor",
    "labours": "labors",
    "laboured": "labored",
    "labouring": "laboring",
    "labourer": "laborer",
    "labourers": "laborers",
    "endeavour": "endeavor",
    "endeavours": "endeavors",
    "endeavoured": "endeavored",
    "splendour": "splendor",
    "vigour": "vigor",
    "rigour": "rigor",
    "rigours": "rigors",
    "ardour": "ardor",
    "armour": "armor",
    "armoured": "armored",
    "saviour": "savior",
    "odour": "odor",
    "odours": "odors",
    "clamour": "clamor",
    "valour": "valor",
    "fervour": "fervor",
    "harbour": "harbor",
    "harbours": "harbors",
    "rumour": "rumor",
    "rumours": "rumors",
    "humour": "humor",
    "humoured": "humored",
    "demeanour": "demeanor",
    "succour": "succor",
    "candour": "candor",
    # -re -> -er
    "centre": "center",
    "centres": "centers",
    "centred": "centered",
    "centring": "centering",
    "theatre": "theater",
    "theatres": "theaters",
    "fibre": "fiber",
    "fibres": "fibers",
    "sombre": "somber",
    "lustre": "luster",
    "metre": "meter",
    "metres": "meters",
    "spectre": "specter",
    "sceptre": "scepter",
    "calibre": "caliber",
    "manoeuvre": "maneuver",
    # -ise -> -ize
    "realise": "realize",
    "realised": "realized",
    "realises": "realizes",
    "realising": "realizing",
    "realisation": "realization",
    "recognise": "recognize",
    "recognised": "recognized",
    "recognises": "recognizes",
    "recognising": "recognizing",
    "organise": "organize",
    "organised": "organized",
    "organises": "organizes",
    "organising": "organizing",
    "organisation": "organization",
    "organisations": "organizations",
    "apologise": "apologize",
    "apologised": "apologized",
    "emphasise": "emphasize",
    "emphasised": "emphasized",
    "emphasises": "emphasizes",
    "emphasising": "emphasizing",
    "summarise": "summarize",
    "summarised": "summarized",
    "criticise": "criticize",
    "criticised": "criticized",
    "criticises": "criticizes",
    "memorise": "memorize",
    "memorised": "memorized",
    "memorising": "memorizing",
    "civilise": "civilize",
    "civilised": "civilized",
    "characterise": "characterize",
    "characterised": "characterized",
    "specialise": "specialize",
    "specialised": "specialized",
    "authorise": "authorize",
    "authorised": "authorized",
    "minimise": "minimize",
    "minimised": "minimized",
    "maximise": "maximize",
    "maximised": "maximized",
    "symbolise": "symbolize",
    "symbolised": "symbolized",
    "analyse": "analyze",
    "analysed": "analyzed",
    "analyses": "analyzes",
    "analysing": "analyzing",
    "paralyse": "paralyze",
    "paralysed": "paralyzed",
    "catalogue": "catalog",
    "catalogues": "catalogs",
    # -ce -> -se
    "defence": "defense",
    "defences": "defenses",
    "offence": "offense",
    "offences": "offenses",
    "pretence": "pretense",
    "licence": "license",
    "practise": "practice",
    "practised": "practiced",
    "practising": "practicing",
    # doubled consonant
    "travelled": "traveled",
    "travelling": "traveling",
    "traveller": "traveler",
    "travellers": "travelers",
    "marvelled": "marveled",
    "marvelling": "marveling",
    "marvellous": "marvelous",
    "levelled": "leveled",
    "levelling": "leveling",
    "signalled": "signaled",
    "signalling": "signaling",
    "totalled": "totaled",
    "cancelled": "canceled",
    "cancelling": "canceling",
    "counselled": "counseled",
    "counsellor": "counselor",
    "counsellors": "counselors",
    "jewellery": "jewelry",
    "woollen": "woolen",
    # single -> doubled, and -ment
    "fulfil": "fulfill",
    "fulfils": "fulfills",
    "fulfilment": "fulfillment",
    "instalment": "installment",
    "instalments": "installments",
    "enrolment": "enrollment",
    "skilful": "skillful",
    "skilfully": "skillfully",
    "wilful": "willful",
    "wilfully": "willfully",
    "appal": "appall",
    "judgement": "judgment",
    "judgements": "judgments",
    "acknowledgement": "acknowledgment",
    "acknowledgements": "acknowledgments",
    "abridgement": "abridgment",
    "lodgement": "lodgment",
    # irregulars
    "grey": "gray",
    "greyish": "grayish",
    "plough": "plow",
    "ploughed": "plowed",
    "sceptic": "skeptic",
    "sceptics": "skeptics",
    "sceptical": "skeptical",
    "sceptically": "skeptically",
    "scepticism": "skepticism",
    "moustache": "mustache",
    "storey": "story",
    "storeys": "stories",
    "draught": "draft",
    "draughts": "drafts",
    "gaol": "jail",
    "kerb": "curb",
    "mould": "mold",
    "moulded": "molded",
    "moulding": "molding",
    "smoulder": "smolder",
    "smouldering": "smoldering",
    "sulphur": "sulfur",
    "tyre": "tire",
    "tyres": "tires",
    "aeroplane": "airplane",
    "programme": "program",
    "programmes": "programs",
}

# ── Tier 2: usage ──────────────────────────────────────────────────────────
# American style prefers these, but they are word choices rather than spellings,
# so they live apart and can be disabled on their own.
USAGE: dict[str, str] = {
    "towards": "toward",
    "amongst": "among",
    "whilst": "while",
    "backwards": "backward",
    "forwards": "forward",
    "upwards": "upward",
    "downwards": "downward",
    "onwards": "onward",
    "learnt": "learned",
    "spelt": "spelled",
    "burnt": "burned",
    "dreamt": "dreamed",
    "leapt": "leaped",
    "knelt": "kneeled",
}

# Machine fences and code blocks are not prose — skip them wholesale.
_FENCE_RE = re.compile(r"^\s*(```|~~~|:::)")


def _match_case(british: str, american: str) -> str:
    """Carry the source word's capitalization onto the replacement."""
    if british.isupper():
        return american.upper()
    if british[:1].isupper():
        return american[:1].upper() + american[1:]
    return american


def build_pattern(table: dict[str, str]) -> re.Pattern[str]:
    """One alternation over every key, longest first so plurals win."""
    keys = sorted(table, key=len, reverse=True)
    return re.compile(rf"\b({'|'.join(map(re.escape, keys))})\b", re.IGNORECASE)


_ORTHO_RE = build_pattern(ORTHOGRAPHY)
_USAGE_RE = build_pattern(USAGE)


def to_american(text: str, *, usage: bool = True) -> str:
    """Return *text* with British forms replaced by American ones.

    ``usage=False`` applies orthography only, leaving toward/towards and
    among/amongst as the author wrote them.
    """
    if not text:
        return text

    tables: list[tuple[re.Pattern[str], dict[str, str]]] = [(_ORTHO_RE, ORTHOGRAPHY)]
    if usage:
        tables.append((_USAGE_RE, USAGE))

    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        for pattern, table in tables:
            line = pattern.sub(lambda m: _match_case(m.group(1), table[m.group(1).lower()]), line)
        out.append(line)
    return "\n".join(out)


def findings(text: str, *, usage: bool = True) -> dict[str, int]:
    """Every British form present, with counts — for reporting, no mutation."""
    counts: dict[str, int] = {}
    for pattern in [_ORTHO_RE] + ([_USAGE_RE] if usage else []):
        for m in pattern.finditer(text):
            key = m.group(1).lower()
            counts[key] = counts.get(key, 0) + 1
    return counts
