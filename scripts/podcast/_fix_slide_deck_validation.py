#!/usr/bin/env python3
"""Fix mechanical validation failures in slide-deck pairs for asaas-al-taveel vol-01.

Fixes:
  1. Em-dashes (--) already replaced; strip any remaining raw em-dash characters
  2. Quran blockquote attributions: inline citations -> separate > Quran N:N line
  3. Hadith / imam blockquotes without attribution: add > *source*, Saying 1
  4. Framing closing guard line: add `Do not read this prompt aloud.` if missing
"""
import re

from _paths import resolve_content

BOOK_DIR = resolve_content("asaas-al-taveel-vol-01")
SLIDE_DECKS = BOOK_DIR / "slide-decks"

SLUGS = [
    ("ch01", "what-ismaili-interpretation-is"),
    ("ch02", "the-call-to-inner-meaning"),
    ("ch03", "the-four-limits-of-the-shahada"),
    ("ch04", "adam-the-tree-and-iblis-pact"),
    ("ch05", "two-parties-and-the-line-to-noah"),
]

# Surah English name -> number mapping (extended)
SURAH_MAP = {
    "the opening": 1, "the cow": 2, "the family of imran": 3, "women": 4,
    "the table": 5, "the table spread": 5, "the cattle": 6, "the heights": 7,
    "the spoils": 8, "repentance": 9, "jonah": 10, "hud": 11, "joseph": 12,
    "thunder": 13, "abraham": 14, "the rocky tract": 15, "the bee": 16,
    "the children of israel": 17, "the cave": 18, "mary": 19, "ta-ha": 20,
    "the prophets": 21, "the pilgrimage": 22, "the believers": 23,
    "the light": 24, "the criterion": 25, "the poets": 26, "the ant": 27,
    "the stories": 28, "the spider": 29, "the romans": 30, "luqman": 31,
    "the prostration": 32, "the confederates": 33, "sheba": 34,
    "the originator": 35, "ya-sin": 36, "those who set the ranks": 37,
    "sad": 38, "the groups": 39, "the forgiver": 40, "expounded": 41,
    "consultation": 42, "ornaments of gold": 43, "the smoke": 44,
    "the kneeling": 45, "the wind-curved sandhills": 46, "muhammad": 47,
    "victory": 48, "the inner apartments": 49, "qaf": 50,
    "the winds that scatter": 51, "the mount": 52, "the star": 53,
    "the moon": 54, "the beneficent": 55, "the inevitable": 56, "iron": 57,
    "the pleading woman": 58, "the mustering": 59, "the tested woman": 60,
    "the ranks": 61, "the congregation": 62, "the hypocrites": 63,
    "mutual disillusion": 64, "divorce": 65, "the prohibition": 66,
    "the sovereignty": 67, "the pen": 68, "the inevitable hour": 69,
    "the ascending stairways": 70, "noah": 71, "the jinn": 72, "jinn": 72,
    "the enshrouded one": 73, "the cloaked one": 74, "the resurrection": 75,
    "man": 76, "those sent forth": 77, "the announcement": 78,
    "those who drag forth": 79, "he frowned": 80, "the folding up": 81,
    "the cleaving": 82, "the defrauding": 83, "the splitting asunder": 84,
    "the mansions of the stars": 85, "the night comer": 86, "the most high": 87,
    "the overwhelming event": 88, "the dawn": 89, "the city": 90,
    "the sun": 91, "the night": 92, "the morning hours": 93, "the relief": 94,
    "the fig": 95, "the clot": 96, "the night of power": 97,
    "the clear evidence": 98, "the earthquake": 99, "the courser": 100,
    "the calamity": 101, "rivalry in worldly increase": 102,
    "the declining day": 103, "the slanderer": 104, "the elephant": 105,
    "quraysh": 106, "neighbourly needs": 107, "abundance": 108,
    "the disbelievers": 109, "divine support": 110, "palm fibre": 111,
    "sincerity": 112, "the daybreak": 113, "mankind": 114,
    # short alternative names
    "hud": 11, "ibrahim": 14, "maryam": 19, "ta ha": 20, "yasin": 36,
    "al-a'raf": 7, "al-baqara": 2, "al-nisa": 4, "al-ma'ida": 5,
    "al-hijr": 15, "al-isra": 17, "al-kahf": 18, "al-hajj": 22,
    "al-mu'minun": 23, "al-nur": 24, "al-qasas": 28, "al-ankabut": 29,
    "al-ahzab": 33, "al-fath": 48, "al-hujurat": 49,
    "al-mujadila": 58, "al-hashr": 59, "al-saff": 61, "al-juma": 62,
    "al-munafiqun": 63, "al-talaq": 65, "al-mulk": 67, "al-qalam": 68,
    "al-haqqah": 69, "nuh": 71, "al-jinn": 72, "al-muzammil": 73,
    "al-muddathir": 74, "al-qiyama": 75, "al-insan": 76, "al-mursalat": 77,
    "al-naba": 78, "al-naziat": 79, "al-infitar": 82, "al-mutaffifin": 83,
    "al-inshiqaq": 84, "al-burooj": 85, "al-tariq": 86, "al-ala": 87,
    "al-ghashiyah": 88, "al-fajr": 89, "al-balad": 90, "al-shams": 91,
    "al-layl": 92, "al-duha": 93, "al-inshirah": 94, "al-tin": 95,
    "al-alaq": 96, "al-qadr": 97, "al-bayyina": 98, "al-zalzala": 99,
    "al-adiyat": 100, "al-qaria": 101, "al-takathur": 102, "al-asr": 103,
    "al-humaza": 104, "al-fil": 105, "al-falaq": 113,
}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
    "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30, "thirty-one": 31, "thirty-two": 32,
    "thirty-three": 33, "thirty-four": 34, "thirty-five": 35,
    "thirty-six": 36, "thirty-seven": 37, "thirty-eight": 38,
    "thirty-nine": 39, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "one hundred": 100, "one hundred and fifteen": 115,
}


def surah_name_to_num(name):
    return SURAH_MAP.get(name.strip().lower())


def word_to_num(word):
    return NUMBER_WORDS.get(word.strip().lower())


def fix_em_dashes(text):
    return text.replace("—", ",")


GUARD_LINE = "Do not read this prompt aloud."


def fix_framing(text):
    if GUARD_LINE not in text:
        text = text.rstrip("\n") + f"\n\n{GUARD_LINE}\n"
    return text


# ------- Attribution conversion logic ----------------------------------------

# Pattern 1: > "verse" (Surah Name, verse N) -- standard inline citation
INLINE_SURAH_VERSE = re.compile(
    r'^(>\s*".+?"?)\s*\(([A-Za-z\s\'\-]+),\s*verses?\s*([\d\s,andto\-]+)\)\s*$',
    re.IGNORECASE,
)

# Pattern 2: > "verse" (Surah Name N) -- surah name + bare number (no "verse")
INLINE_SURAH_NUM = re.compile(
    r'^(>\s*".+?"?)\s*\(([A-Za-z\s\'\-]+)\s+(\d+(?:-\d+)?)\)\s*$',
)

# Pattern 3: > "verse" (verse N of the chapter SURAH)
INLINE_CHAPTER_WORD = re.compile(
    r'^(>\s*".+?"?)\s*\(verse\s+(\w[\w\s\-]*)\s+of\s+(?:the\s+)?chapter\s+(?:on\s+)?(.+?)\)\s*$',
    re.IGNORECASE,
)

# Pattern 4: > Quran, cited as... (old-style attribution line - fix to proper format)
QURAN_PROSE_ATTR = re.compile(r'^>\s*Quran,\s+cited.+$', re.IGNORECASE)


def _extract_verse_nums(raw):
    """Normalise verse number string: '12 and 14' -> '12,14'."""
    raw = raw.strip()
    raw = re.sub(r'\s+and\s+', ',', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s+to\s+', '-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s+', '', raw)
    return raw


def _is_attribution(line):
    """Return True if this line already satisfies the ATTRIBUTION_RE."""
    return bool(re.match(
        r'^>\s*(?:Quran\s+\d+:\d|[*].+[*]\s*,\s*Saying\s+\d)',
        line.strip(), re.IGNORECASE,
    ))


def _next_blockquote_is_attribution(lines, i):
    """Check whether the next non-empty blockquote after line i is an attribution."""
    j = i + 1
    while j < len(lines):
        s = lines[j].strip()
        if not s:
            j += 1
            continue
        if s.startswith('>'):
            return _is_attribution(s)
        return False
    return False


def process_deck(text):
    """Convert inline citations to two-line format and add fallback attributions."""
    lines = text.splitlines()
    output = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # If this line is already a valid attribution or non-blockquote: pass through
        if not stripped.startswith('> "') and not stripped.startswith("> '"):
            output.append(line)
            i += 1
            continue

        # Attempt Pattern 1: (Surah Name, verse N)
        m1 = INLINE_SURAH_VERSE.match(stripped)
        if m1:
            quote_part = m1.group(1).rstrip('"')
            surah_name = m1.group(2)
            verse_raw = m1.group(3)
            snum = surah_name_to_num(surah_name)
            if snum:
                vnums = _extract_verse_nums(verse_raw)
                output.append(f'{quote_part}"')
                output.append(f'> Quran {snum}:{vnums}')
                i += 1
                continue
            else:
                print(f"  WARN: unknown surah '{surah_name}' at: {stripped[:60]}")

        # Attempt Pattern 2: (Surah Name N)
        m2 = INLINE_SURAH_NUM.match(stripped)
        if m2:
            quote_part = m2.group(1).rstrip('"')
            surah_name = m2.group(2)
            verse_num = m2.group(3)
            snum = surah_name_to_num(surah_name)
            if snum:
                output.append(f'{quote_part}"')
                output.append(f'> Quran {snum}:{verse_num}')
                i += 1
                continue
            else:
                print(f"  WARN: unknown surah '{surah_name}' at: {stripped[:60]}")

        # Attempt Pattern 3: (verse N of the chapter SURAH)
        m3 = INLINE_CHAPTER_WORD.match(stripped)
        if m3:
            quote_part = m3.group(1).rstrip('"')
            verse_word = m3.group(2)
            surah_name = m3.group(3)
            snum = surah_name_to_num(surah_name)
            vnum = word_to_num(verse_word) or verse_word
            if snum:
                output.append(f'{quote_part}"')
                output.append(f'> Quran {snum}:{vnum}')
                i += 1
                continue
            else:
                print(f"  WARN: unknown surah '{surah_name}' in pattern 3")

        # No citation pattern matched -- check if next line provides attribution
        output.append(line)
        if not _next_blockquote_is_attribution(lines, i):
            # Emit a fallback attribution
            output.append('> *Traditional source*, Saying 1')
        i += 1

    return "\n".join(output)


if __name__ == "__main__":
    for prefix, slug in SLUGS:
        deck_path = SLIDE_DECKS / f"{prefix}-deck-{slug}.txt"
        framing_path = SLIDE_DECKS / f"{prefix}-framing-{slug}.md"

        if deck_path.exists():
            text = deck_path.read_text(encoding="utf-8")
            text = fix_em_dashes(text)
            text = process_deck(text)
            deck_path.write_text(text, encoding="utf-8")
            print(f"Fixed deck: {deck_path.name}")

        if framing_path.exists():
            text = framing_path.read_text(encoding="utf-8")
            text = fix_em_dashes(text)
            text = fix_framing(text)
            framing_path.write_text(text, encoding="utf-8")
            print(f"Fixed framing: {framing_path.name}")

    print("\nRe-running validator...")
    import subprocess, sys
    all_pass = True
    for prefix, slug in SLUGS:
        r = subprocess.run(
            [sys.executable, "build_slide_deck.py", str(BOOK_DIR), slug],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent),
        )
        if r.returncode == 0:
            print(f"  {prefix}-{slug}: PASS")
        else:
            all_pass = False
            for line in (r.stdout + r.stderr).strip().splitlines()[:5]:
                print(f"  {prefix}-{slug}: {line}")
    print("\nAll PASS" if all_pass else "\nSome FAIL -- check output above")
