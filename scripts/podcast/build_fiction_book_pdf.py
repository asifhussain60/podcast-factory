"""build_fiction_book_pdf.py — Illustrated reading-edition PDF for fiction books.

Three steps:
  1. Compose book/book.md from refined-english.md (chapter headings + prose)
  2. Generate one Imagen3 illustration per chapter → book/images/ch-NN.jpg
     and insert as base64 <figure> blocks → book/book-illustrated.md
  3. Render book/book-illustrated.md → book/book.pdf via Playwright

Usage:
  python3 build_fiction_book_pdf.py <book-slug>
  python3 build_fiction_book_pdf.py journey-to-the-west-vol-1
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO_ROOT  # noqa: E402
from _cost_ledger import append_gemini_cost  # noqa: E402
from _secrets import get_gemini_key  # noqa: E402

IMAGE_MODEL = "gemini-3.1-flash-image"
IMAGE_COST_USD = 0.04

# Per-chapter illustration prompts for Journey to the West Vol 1.
# Keyed by sc_index (1-based). Style: epic classical Chinese brushwork meets
# cinematic drama; atmospheric mist, jewel tones, dynamic composition.
# Canonical chapter titles for JtW Vol 1 — used when source-toc.json has only
# a partial entry set (e.g. when TOC was trimmed to N episodes for podcast work).
_JTW_TITLES: dict[int, str] = {
    1:  "The Stone Egg of Flower-Fruit Mountain and the Magical Monkey King",
    2:  "The Secret Word at the Third Watch",
    3:  "The Four Seas and a Thousand Mountains Bow in Submission",
    4:  "A Stable-Keeper's Title Cannot Content Him; The Great Sage Raises Heaven's Banner",
    5:  "The Great Sage Plunders the Peaches and Steals the Elixir",
    6:  "Guanyin Comes to the Feast and Asks the Cause; The Little Sage Subdues the Great Sage",
    7:  "The Great Sage Escapes the Eight-Trigrams Furnace; The Buddha Subdues the Mind-Monkey",
    8:  "The Buddha Forges the Scriptures, and Guanyin Seeks the Pilgrim",
    9:  "The River-Float Monk and the Long Road to Vengeance",
    10: "The Old Dragon King's Reckless Scheme Breaks Heaven's Law",
    11: "The Emperor's Soul Journeys Through the Underworld",
    12: "The Borrowed Body and the Bodhisattva's Sign",
    13: "Into the Tiger's Pit, and the Mountain Lord's Aid",
    14: "The Mind-Monkey Returns to the Right, and the Demon is Slain",
    15: "The Hawk-Grief Gorge and the Dragon-Horse",
    16: "The Monks of Guanyin Temple Scheme for the Treasure",
    17: "The Black Wind Mountain and the Bear Who Stole the Treasure Coat",
    18: "The Tang Monk Escapes His Trouble at Guanyin Mountain",
    19: "The Cloud-Ladder Cave, Where Wukong Wins the Heart of the Pig",
    20: "The Yellow Wind Ridge and the Tiger Vanguard",
    21: "The Wind Demon and the Healing Salve",
    22: "The Sands That Swallow Men — Friar Sand Joins the Quest",
    23: "The Four Saints Test a Pilgrim's Heart",
    24: "The Mountain of Ten Thousand Years and the Stone of Life-Prolonging",
    25: "The Immortal Zhenyuan Pursues the Pilgrims, and the Ginseng Tree",
    26: "The Three Isles and the Sweet Dew of Mercy",
    27: "The Corpse-Demon Thrice Deceives the Tang Monk",
    28: "The Demons Gather at the Mountain of Flowers and Fruit",
    29: "A Letter Carried Out of Sorrow, and a Monk Who Plays the Tiger",
    30: "The Demon Profanes the True Law; the Dragon-Horse Transforms",
    31: "The Brotherly Bond, and the Cunning Capture of the Golden Helmet Demon",
    32: "The Spirit of the Day Brings Warning on Flat-Top Mountain",
    33: "The False Way Beguiles the True Nature; the Princess Steals the Elixir",
}

_STYLE = (
    "Epic classical Chinese fantasy illustration. Painterly brushwork meets "
    "cinematic drama. Deep jewel tones — jade green, vermilion, midnight blue, "
    "burnished gold. Atmospheric mist and dynamic composition. No text."
)

_JTW_PROMPTS: dict[int, str] = {
    1:  "A stone egg atop Flower-Fruit Mountain cracks open in a blaze of golden light; a magical monkey king emerges from the rock, his eyes blazing with twin rays that pierce the heavens.",
    2:  "Sun Wukong kneeling reverently before the ancient white-bearded Patriarch Subodhi inside a candlelit cave at twilight, receiving forbidden wisdom inscribed on glowing scrolls.",
    3:  "Sun Wukong brandishing the massive iron pillar — the Pillar That Steadies the Sea — inside the Dragon King's luminous crystal palace beneath the waves, sea creatures recoiling in awe.",
    4:  "Sun Wukong strutting through jade corridors of the Heavenly Palace in a celestial official's robe, celestial horses watching nervously from gilded stables behind him.",
    5:  "Sun Wukong in the Jade Emperor's peach garden at night under paper lanterns, gleefully stuffing golden peaches into his sleeves while celestial fairies scatter in alarm.",
    6:  "Erlang Shen and Sun Wukong locked in titanic combat on a cloud-swept mountain peak, their bodies mid-transformation — one a giant hawk, the other a cormorant — lightning crackling between them.",
    7:  "Sun Wukong pinned beneath a colossal mountain by the Buddha's golden seal, only one arm reaching upward through the rocks toward a distant sky.",
    8:  "Guanyin Bodhisattva riding lotus clouds above a misty jade-green landscape, staff of willow in hand, serenely surveying the mortal realm far below in golden afternoon light.",
    9:  "A tiny infant in a carved wooden chest floating silently down a moonlit river at night, distant figures of grieving monks watching from the shadow-draped bank.",
    10: "The Dragon King of the Jing River confronting the imperial minister Wei Zheng in a fever-dream — the dragon's scales shimmering silver-blue as the executioner's sword descends in a nightmare courtroom.",
    11: "The Tang Emperor Taizong's robed soul standing before Yama's underworld courtroom, enormous demon scribes recording sins in towering black ledgers, spectral lanterns casting eerie green light.",
    12: "Tang Sanzang in his monk's robe kneeling before Guanyin, receiving a gleaming golden kasaya robe and begging bowl, with the vast western mountains glowing at dawn behind them.",
    13: "Tang Sanzang alone on horseback on a narrow mountain trail at midnight, lantern in hand, surrounded by invisible roars and glowing eyes in the darkness of an ancient forest.",
    14: "Sun Wukong emerging from beneath Five Elements Mountain, the golden headband tightening on his brow as he kneels before Tang Sanzang on a barren stone hillside at sunrise.",
    15: "A luminous white dragon exploding out of a jade waterfall gorge, mid-transformation into a white horse, the water frozen in a cascade of glittering droplets around him.",
    16: "A great temple burning at midnight, flames shooting into the darkness, monks scrambling in terror as a black bear demon hovers above on a cloud clutching a stolen golden robe.",
    17: "A massive bear demon in dark armour standing triumphant on a pine-forested mountaintop, clutching a monk's embroidered kasaya robe, the horizon glowing orange behind him.",
    18: "Sun Wukong in disguise as a Taoist — gold-ringed staff hidden — at the entrance to the bear demon's cave, face set in cunning confidence as the mountains loom behind him.",
    19: "Zhu Bajie with his nine-toothed rake kneeling on muddy ground before Tang Sanzang, his pig-face contrite, at the entrance to a misty cave carved into a dark mountain.",
    20: "A tiger-headed wind demon riding roiling yellow storm clouds across a barren plateau, his jade flute raised, sending hurricane winds scattering travellers and horses on the road below.",
    21: "Sun Wukong in fierce aerial combat with the three-headed six-armed Wind Demon above a mist-filled valley, their staffs clashing in showers of sparks against a stormy sky.",
    22: "Sha Wujing rising menacingly from the turbulent Flowing Sands River, his robe of skulls dripping water, staff raised, as the four pilgrims face him from the muddy bank.",
    23: "Four celestial beauties in glittering gowns presenting trays of gold and silk to the four pilgrims in a luxurious mountain manor, testing the monks' resolve to resist temptation.",
    24: "The legendary ginseng fruit tree towering in mist, its golden fruit shaped like human infants hanging from jade branches, with the immortal grounds glowing in soft otherworldly light.",
    25: "The ancient Earth Immortal Zhenyuan flying through golden clouds, his sleeve expanding magically to capture the fleeing pilgrims below in a billowing net of brocaded fabric.",
    26: "Guanyin kneeling beside the shattered stump of the ginseng tree, sprinkling sweet dew from a white jade vase, the tree visibly regrowing its branches in luminous green light.",
    27: "The White Bone Demoness in her third guise — a trembling old man — approaching Tang Sanzang on a mist-shrouded mountain road, her true skeleton form faintly visible as a ghostly overlay.",
    28: "Sun Wukong back at Flower-Fruit Mountain rallying an army of demon generals beneath his banner, the mountain peaks jagged and red with sunset behind the assembled forces.",
    29: "Zhu Bajie flying alone through dark storm clouds at night, a letter clutched in one trotter, his pig silhouette barely visible against lightning-lit thunderheads over a black landscape.",
    30: "A golden-horned and silver-horned demon lord seated on a throne of carved bone in a cavernous mountain lair, the captured pilgrims bound and kneeling before their enormous figures.",
    31: "Sun Wukong and Zhu Bajie fighting in fierce tandem against the twin demon kings, iron staff and nine-toothed rake clashing against celestial swords under a stormy amber sky.",
    32: "The Spirit of the Day appearing as a tiny luminous figure before Sun Wukong on a windswept plateau, pointing ominously toward a dark mountain range on the horizon.",
    33: "A strikingly beautiful female demon queen in phoenix-embroidered scarlet robes, her face identical to a mortal princess, standing imperiously before a trembling Tang Sanzang in her palace.",
}


def _chapter_titles() -> dict[int, str]:
    """Read chapter titles from source-toc.json (all 34 entries cover 33 source chapters)."""
    toc_paths = list((REPO_ROOT / "content").glob(
            "*/journey-to-the-west-vol-1/_system/source/text/_chunks/0d/source-toc.json"
        ))
    if not toc_paths:
        return {}
    toc = json.loads(toc_paths[0].read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for sc in toc["source_chapters"]:
        idx = sc["sc_index"]
        title = sc["source_title"]
        # Drop part suffixes (e.g. " — Part One") — use only first encounter per sc_index
        if idx not in out:
            out[idx] = re.sub(r"\s*—\s*Part (One|Two|Three)$", "", title).strip()
    return out


def compose_book_md(book_dir: Path) -> Path:
    """Step 1: assemble book/book.md from refined-english.md."""
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not refined.exists():
        sys.exit(f"ERROR: {refined} not found — run Phase 0b first.")

    print("  compose · reading refined-english.md …")
    raw = refined.read_text(encoding="utf-8")
    lines = raw.splitlines()

    # Find <!-- chapter N --> markers
    marker_re = re.compile(r"<!--\s*chapter\s+(\d+)\s*-->", re.IGNORECASE)
    breaks: list[tuple[int, int]] = []  # (line_index, ch_num)
    for i, line in enumerate(lines):
        m = marker_re.search(line)
        if m:
            breaks.append((i, int(m.group(1))))

    if not breaks:
        sys.exit("ERROR: no <!-- chapter N --> markers found in refined-english.md")

    titles = _chapter_titles()
    print(f"  compose · found {len(breaks)} chapter markers, {len(titles)} titles")

    chapters: list[tuple[int, str]] = []
    for k, (start_line, ch_num) in enumerate(breaks):
        end_line = breaks[k + 1][0] if k + 1 < len(breaks) else len(lines)
        # Skip the marker line itself; find first non-empty line for the body
        body_lines = lines[start_line + 1 : end_line]
        # Remove any leading heading that duplicates the marker (e.g. # Chapter 1: ...)
        while body_lines and (body_lines[0].strip() == "" or body_lines[0].startswith("#")):
            body_lines = body_lines[1:]
        body = "\n".join(body_lines).strip()
        title = titles.get(ch_num) or _JTW_TITLES.get(ch_num, f"Chapter {ch_num}")
        chapters.append((ch_num, title, body))

    # Write book.md
    book_dir_out = book_dir / "book"
    book_dir_out.mkdir(exist_ok=True)
    out_md = book_dir_out / "book.md"

    parts = ["# Journey to the West: Volume One\n"]
    for ch_num, title, body in chapters:
        parts.append(f"\n## Chapter {ch_num}: {title}\n")
        parts.append(body)
        parts.append("")  # blank line between chapters

    out_md.write_text("\n".join(parts), encoding="utf-8")
    print(f"  compose · wrote {out_md} ({out_md.stat().st_size // 1024}KB, {len(chapters)} chapters)")
    return out_md


def illustrate_book(book_dir: Path, book_md: Path) -> Path:
    """Step 2: generate Imagen3 illustrations + produce book-illustrated.md."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("ERROR: google-genai not installed. Run: pip3 install google-genai")

    api_key = get_gemini_key()
    client = genai.Client(api_key=api_key)

    images_dir = book_dir / "book" / "images"
    images_dir.mkdir(exist_ok=True)

    md = book_md.read_text(encoding="utf-8")

    # Split on H2 chapter headings to inject figures after each heading
    chapter_re = re.compile(r"(^## Chapter (\d+): .+$)", re.MULTILINE)
    parts = chapter_re.split(md)
    # parts alternates: [pre-H2-text, full-heading, ch_num, body, full-heading, ch_num, body, ...]

    out_parts: list[str] = []
    i = 0
    # First element is the H1 title block (before first chapter)
    if parts:
        out_parts.append(parts[0])
        i = 1

    total_chapters = len([x for x in parts if re.match(r"^\d+$", x.strip())])
    generated = 0
    skipped = 0

    while i < len(parts):
        if i + 2 >= len(parts):
            out_parts.append(parts[i])
            i += 1
            continue

        heading = parts[i]      # e.g. "## Chapter 1: The Stone Egg..."
        ch_num_str = parts[i + 1]  # e.g. "1"
        body = parts[i + 2]     # chapter text
        i += 3

        ch_num = int(ch_num_str)
        img_path = images_dir / f"ch-{ch_num:02d}.jpg"

        # Generate or reuse
        if img_path.exists():
            print(f"  illustrate · ch {ch_num:02d} image already exists, reusing")
            image_bytes = img_path.read_bytes()
            skipped += 1
        else:
            prompt = _JTW_PROMPTS.get(ch_num, f"Epic scene from Journey to the West chapter {ch_num}.")
            full_prompt = f"{prompt} {_STYLE}"
            print(f"  illustrate · ch {ch_num:02d} generating image … ", end="", flush=True)
            try:
                resp = client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["image", "text"],
                    ),
                )
                image_bytes = None
                for part in resp.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        image_bytes = part.inline_data.data
                        break
                if not image_bytes:
                    print("FAILED (no image in response) — skipping illustration")
                    out_parts.append(heading + "\n" + body)
                    continue
                img_path.write_bytes(image_bytes)
                print(f"saved ({len(image_bytes) // 1024}KB)")
                generated += 1
                append_gemini_cost(
                    book_dir=book_dir, phase="0book-illustrate",
                    step=f"image/ch{ch_num:02d}",
                    model=IMAGE_MODEL,
                    in_chars=len(full_prompt),
                    out_chars=len(image_bytes) // 4,  # rough char estimate for image bytes
                )
            except Exception as exc:
                print(f"FAILED ({exc}) — skipping illustration")
                out_parts.append(heading + "\n" + body)
                continue

        # Embed as base64 data URI so the PDF renderer doesn't need file serving
        b64 = base64.b64encode(image_bytes).decode("ascii")
        ch_title = heading.lstrip("# ").strip()
        figure = (
            f'<figure class="book-illustration">\n'
            f'<img src="data:image/jpeg;base64,{b64}" alt="{ch_title}" style="width:100%;max-height:480px;object-fit:cover;display:block;margin:0 auto;">\n'
            f'<figcaption>{ch_title.split(": ", 1)[-1] if ": " in ch_title else ch_title}</figcaption>\n'
            f'</figure>'
        )
        out_parts.append(heading + "\n\n" + figure + "\n" + body)

    print(f"  illustrate · {generated} generated, {skipped} reused of {total_chapters} chapters")

    illustrated_md = book_dir / "book" / "book-illustrated.md"
    illustrated_md.write_text("".join(out_parts), encoding="utf-8")
    print(f"  illustrate · wrote {illustrated_md} ({illustrated_md.stat().st_size // 1024}KB)")
    return illustrated_md


def render_pdf(book_dir: Path, illustrated_md: Path) -> Path:
    """Step 3: render book-illustrated.md → book.pdf via Playwright."""
    out_pdf = book_dir / "book" / "book.pdf"
    print(f"  render · {illustrated_md.name} → book.pdf (Playwright) …")
    render_script = REPO_ROOT / "plan-dashboard" / "scripts" / "render-book-pdf.mjs"
    theme_css = REPO_ROOT / "plan-dashboard" / "src" / "styles" / "theme.css"
    result = subprocess.run(
        ["node", str(render_script), str(illustrated_md), str(out_pdf), str(theme_css)],
        cwd=REPO_ROOT / "plan-dashboard",
        capture_output=True, text=True,
    )
    if result.stdout:
        print(" ", result.stdout.strip())
    if result.stderr:
        print("  [stderr]", result.stderr.strip()[:300])
    if result.returncode == 3:
        sys.exit(
            "ERROR: Playwright chromium not installed.\n"
            "  Run: cd plan-dashboard && npx playwright install chromium"
        )
    if result.returncode != 0:
        sys.exit(f"ERROR: render-book-pdf.mjs exited {result.returncode}")

    print(f"  render · wrote {out_pdf} ({out_pdf.stat().st_size // 1024}KB)")

    # Copy to Google Drive
    gdrive = Path(
        "~/Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com"
        "/My Drive/podcast factory"
    ).expanduser()
    if gdrive.exists():
        import shutil
        dest = gdrive / "Journey to the West Vol 1.pdf"
        shutil.copy2(out_pdf, dest)
        print(f"  render · copied to Google Drive: {dest.name}")

    return out_pdf


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(__doc__)
        return 2

    slug = args[0]
    # Locate the book directory
    matches = list((REPO_ROOT / "content").glob(f"*/{slug}"))
    if not matches:
        sys.exit(f"ERROR: book slug '{slug}' not found under content/")
    book_dir = matches[0]
    print(f"\nbuild_fiction_book_pdf · {slug}")
    print(f"  book_dir: {book_dir}")

    book_md = compose_book_md(book_dir)
    illustrated_md = illustrate_book(book_dir, book_md)
    out_pdf = render_pdf(book_dir, illustrated_md)

    print(f"\nDone. PDF: {out_pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
