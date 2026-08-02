/**
 * composer.ts — loader for the Book Composer (Book Pipeline v2).
 *
 * The Composer is where a human curates how the decoupled visual candidates
 * (book/visuals/index.json) are placed in the reading edition. It reads three
 * things and projects them for the view:
 *   - book.md            -> chapters (anchor + title + rendered body)
 *   - visuals/index.json -> the candidate asset palette
 *   - visual-layout.json -> the current curated placements (may be absent)
 *
 * The human's edits are saved back to book/visual-layout.json via
 * /api/studio/visual-layout (PUT); the renderer (render-book-pdf.mjs) consumes
 * that contract. Read-only here — persistence is the API route's job.
 */
import { open, readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { anchorKey } from "../../../scripts/lib/anchor-key.mjs";
import { fingerprints } from "../../../scripts/lib/para-blocks.mjs";
import { articulationWarningsFrom } from "./articulation";
import { editionIntroDelta } from "./book-fences";
import { findContent } from "../content-paths";
import { loadGlossary, loadGlossaryAll, type GlossaryEntry } from "./glossary";
import { renderEditSeed } from "./markdown";
// The PDF's own renderer. Importing it here (rather than re-implementing the
// book-craft layer in TypeScript) is what makes the Composer's read mode and
// the printed page ONE code path — the same consolidation render-book-pdf.mjs
// and the Studio Preview already share. Node-only module; this loader runs
// server-side, so the fs reads inside it are fine.
import {
  renderMd,
  readCrosswalk,
  readCitationFamily,
  readTranslationFont,
  readArabicFont,
  readArabicSize,
  readArabicInk,
  readQuranicRuns,
} from "../../../scripts/lib/book-html.mjs";

export interface ComposerCitation {
  ar: string; // Arabic-script line (plain text)
  tr: string; // translation / following line (plain text; '' if none)
}

export interface ComposerChapter {
  anchor: string; // the raw "## N. Title" heading — the placement anchor
  key: string; // normalized comparable key (mirrors visual-layout anchorKey)
  title: string; // display title, without the leading number
  /** The chapter's own number as the SOURCE heading gives it ("1", "2", …), or
   *  null for unnumbered front matter like the reader's preface. Taken from the
   *  heading rather than counted by position, so the preface never becomes
   *  "chapter 1" and a renumbered book stays truthful. */
  ordinal: string | null;
  /** READ mode. Rendered by the SAME renderMd() the PDF uses (scripts/lib/
   *  book-html.mjs), so the chapter on screen is the chapter that prints:
   *  chapter-open page, drop cap, mushaf verses, source range. Never feed this
   *  to the editor — see editHtml. */
  html: string;
  /** EDIT mode seed ONLY. The plain reader render, whose element set is exactly
   *  what the TipTap StarterKit schema round-trips back to markdown. The rich
   *  read-mode HTML above must NEVER seed the editor: TipTap silently drops
   *  what its schema doesn't know (asides, figures, verse dividers, the
   *  chapter-open section), so the next save would write that loss into
   *  book.md. Keeping the two strings separate is what makes the read surface
   *  print-faithful WITHOUT putting the source file at risk. */
  editHtml: string;
  paras: number; // prose-paragraph count (for the anchor_para position control)
  /** A stable name for each prose paragraph, in order — the key the Arabic-source
   *  alignment is stored under. Computed from the RAW markdown by the same shared
   *  splitter the Python aligner uses, so the two cannot disagree about which
   *  blocks a chapter has. Lines up one-to-one with the read view's top-level
   *  `<p>` elements; the Composer asserts that at runtime and disables the reveal
   *  rather than trusting it. */
  paraKeys: string[];
  citations: ComposerCitation[]; // Arabic-bearing verses/hadith detected in this chapter
}

/** Pull the Arabic-bearing quotation blocks out of rendered chapter HTML.
 *  markdown.ts tags them as `<blockquote class="quran"><p class="ar">…<p class="tr">…`,
 *  so the Citations tab can list a chapter's verses without a new data artifact. */
function extractCitations(html: string): ComposerCitation[] {
  const out: ComposerCitation[] = [];
  const strip = (s: string) =>
    s
      .replace(/<[^>]+>/g, "")
      .replace(/\s+/g, " ")
      .trim();
  const blocks =
    html.match(/<blockquote class="quran">[\s\S]*?<\/blockquote>/g) ?? [];
  for (const b of blocks) {
    const ar = strip(
      (b.match(/<p class="ar"[^>]*>([\s\S]*?)<\/p>/) ?? ["", ""])[1],
    );
    const tr = strip(
      (b.match(/<p class="tr"[^>]*>([\s\S]*?)<\/p>/) ?? ["", ""])[1],
    );
    if (ar) out.push({ ar, tr });
  }
  return out;
}

export interface ComposerVisual {
  id: string;
  type: string;
  caption: string;
  file: string; // basename in book/visuals/
  src: string; // servable URL
  suggested_anchor: string;
  chapter: string; // resolved chapter key (for the palette's chapter filter); '' = unassigned
  cleaned: boolean;
  embedded_title: string;
}

export interface ComposerPlacement {
  visual_id: string;
  anchor: string;
  anchor_para: number | null;
  align: "left" | "center" | "right";
  flow: "wrap" | "standalone";
  width_pct: number;
  caption: string;
  page_fit: "avoid" | "before" | "isolate-plate";
}

/**
 * One `chapters/*.txt` file — the NotebookLM upload source, listed for the
 * Composer's read-only Podcast lane.
 *
 * Deliberately METADATA ONLY. The podcast lane is a different English text of
 * the same source, independently segmented (a book can have 9 chapters against
 * 20 podcast chapters) and typically LARGER than the whole reading edition —
 * shipping those bodies in the compose page would roughly double its prose
 * payload for a pane most visits never open. The lane fetches the one chapter
 * it is showing through the read-only /api/library/file route instead.
 */
export interface ComposerPodcastChapter {
  /** Basename inside `chapters/`. */
  file: string;
  /** The file's own `# ` heading, falling back to its filename. */
  title: string;
  /** The `chNN<letter>` ordinal the filename carries ('' if unparseable). */
  ordinal: string;
}

/** Bytes read per chapter file to find its `# ` heading. The heading is the
 *  first line the pipeline writes, so a small window always contains it; this
 *  used to be a full `readFile`, which meant 336 KB of I/O across 20 files on
 *  every SSR render of the compose page to extract 20 short strings. */
const HEADING_PROBE_BYTES = 2048;

/** Read the chapter sources' titles without reading — or shipping — their
 *  bodies. Sorted by filename, which is how the pipeline numbers them
 *  (`ch01a`, `ch02b`, …). */
async function loadPodcastChapters(
  dir: string,
): Promise<ComposerPodcastChapter[]> {
  let names: string[];
  try {
    names = (await readdir(join(dir, "chapters")))
      .filter((n) => n.endsWith(".txt"))
      .sort();
  } catch {
    return []; // no chapters/ — this book has no podcast lane
  }
  return Promise.all(
    names.map(async (file) => {
      let heading = "";
      let handle;
      try {
        handle = await open(join(dir, "chapters", file), "r");
        const buf = Buffer.alloc(HEADING_PROBE_BYTES);
        const { bytesRead } = await handle.read(buf, 0, HEADING_PROBE_BYTES, 0);
        // Decode only whole lines: a multi-byte character could straddle the
        // window's end, and the heading is never the truncated last line.
        const head = buf.subarray(0, bytesRead).toString("utf-8");
        const whole = head.slice(0, head.lastIndexOf("\n") + 1) || head;
        heading = (whole.match(/^#\s+(.+)$/m)?.[1] ?? "").trim();
      } catch {
        /* unreadable file still lists, under its filename */
      } finally {
        await handle?.close();
      }
      const ordinal = /^ch(\d+[a-z]?)-/.exec(file)?.[1] ?? "";
      return {
        file,
        title: heading || file.replace(/\.txt$/, ""),
        ordinal,
      };
    }),
  );
}

export interface ComposerView {
  slug: string;
  title: string;
  chapters: ComposerChapter[];
  /** The read-only Podcast lane's chapter list — see ComposerPodcastChapter. */
  podcastChapters: ComposerPodcastChapter[];
  visuals: ComposerVisual[];
  placements: ComposerPlacement[];
  hasBook: boolean;
  /** The book-wide citation/quote family from book/citation-style.json, chosen
   *  in the Citations tab. The PDF applies it as a `style-<family>` body class
   *  (buildBookHtml); read mode applies the SAME class to the chapter container,
   *  so picking a style visibly restyles the chapter you are looking at instead
   *  of only the swatch in the tab. '' = unset (the scholarly default). */
  citationFamily: string;
  /** The book's English-rendering face for Arabic quotations, from the same
   *  artifact (`translation_font`). Stamped beside the family as `tr-<font>`,
   *  which sets --q-tr-face (quote-typography.css). '' = unset -> EB Garamond. */
  translationFont: string;
  /** The NON-Qur'anic Arabic face; '' falls back to Scheherazade New. */
  arabicFont: string;
  /** How large the book sets its Arabic, and in what ink (`arabic_size` /
   *  `arabic_ink`). Stamped as `ars-<size>` / `ari-<ink>`, which move
   *  --q-ar-size, --q-ar-inline-size and --q-maroon (quote-typography.css).
   *  '' for the DEFAULT as well as for unset — the default is the `:root`
   *  declaration, so there is no class to add. */
  arabicSize: string;
  arabicInk: string;
  // Arabic-script glossary — needed by the Refinement tab's term curation and
  // by the chapter editor's Arabic overlay decorations. Same source Edit &
  // Enrich reads (_system/glossary.yml); glossary = arabic_script-confirmed
  // entries only, glossaryAll = every entry including those awaiting one.
  glossary: GlossaryEntry[];
  glossaryAll: GlossaryEntry[];
  /** RCA-001 AI-3 — chapters whose CURRENT prose never passed articulation,
   *  keyed by chapter key, valued with a plain-language reason. The Composer
   *  warns (advisory confirm, never a block) before a save freezes one of
   *  these as a durable human edit. Empty when the book has no fluency report
   *  (the articulation contract does not apply) or every chapter is safe. */
  articulationWarnings: Record<string, string>;
}

// anchorKey is re-exported, not redefined: it had four byte-identical copies and
// a divergence in any one of them silently orphans a saved Composer edit. The
// single implementation is imported at the top of this file.
export { anchorKey };

async function readJson<T>(path: string, fallback: T): Promise<T> {
  try {
    return JSON.parse(await readFile(path, "utf-8")) as T;
  } catch {
    return fallback;
  }
}

export async function loadComposer(slug: string): Promise<ComposerView | null> {
  const ref = await findContent(slug);
  if (!ref) return null;

  let md: string;
  try {
    md = await readFile(join(ref.dir, "book", "book.md"), "utf-8");
  } catch {
    return {
      slug,
      title: slug,
      chapters: [],
      // No reading edition composed yet, so the page renders its empty state
      // and never mounts the lane switch — an unusable list would be noise.
      podcastChapters: [],
      visuals: [],
      placements: [],
      hasBook: false,
      citationFamily: "",
      translationFont: "",
      arabicFont: "",
      arabicSize: "",
      arabicInk: "",
      glossary: [],
      glossaryAll: [],
      articulationWarnings: {},
    };
  }

  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : slug;

  // Book-craft inputs the PDF renderer reads, so read mode can match it exactly.
  // The crosswalk supplies each chapter's "Arabic source pp. x–y" line; the
  // citation family is the book-wide quote skin. Both are best-effort — a book
  // without either renders exactly as the PDF would without either.
  const crosswalk = readCrosswalk(ref.dir) as { index?: number | string }[];
  const crosswalkByIndex = new Map(
    crosswalk.map((item) => [Number(item.index), item]),
  );
  const citationFamily = String(
    readCitationFamily(join(ref.dir, "book")) ?? "",
  );
  const translationFont = String(
    readTranslationFont(join(ref.dir, "book")) ?? "",
  );
  const arabicFont = String(readArabicFont(join(ref.dir, "book")) ?? "");
  const arabicSize = String(readArabicSize(join(ref.dir, "book")) ?? "");
  const arabicInk = String(readArabicInk(join(ref.dir, "book")) ?? "");
  // Which Arabic runs the audit resolved against the canonical mushaf — read ONCE
  // per page load and shared by every chapter's render.
  const quranicRuns = readQuranicRuns(ref.dir) as Set<string>;

  // Split into chapters on "## " headings.
  const chapters: ComposerChapter[] = [];
  // Lowercased raw bodies keyed by chapter — used to resolve a visual whose
  // suggested_anchor is a passage phrase (slides) rather than a heading (diagrams).
  const bodyByKey: { key: string; lc: string }[] = [];
  const parts = md.split(/^(##\s+.+)$/m);
  // Running edition-intro depth: the introduction's `## Introduction` heading
  // lives INSIDE its fenced span, and it is apparatus, not a chapter. Offering
  // it here made it editable — and an edit of it can never survive, because the
  // pipeline strips and re-authors the introduction on every compose.
  let introDepth = editionIntroDelta(parts[0] ?? "");
  for (let i = 1; i < parts.length; i += 2) {
    const heading = parts[i].trim();
    const body = (parts[i + 1] ?? "").trim();
    const insideIntro = introDepth > 0;
    introDepth +=
      editionIntroDelta(parts[i]) + editionIntroDelta(parts[i + 1] ?? "");
    if (insideIntro) continue; // the edition's front matter — not an editable chapter
    const numbered = /^##\s+(\d+)\.\s*/.exec(heading);
    const ordinal = numbered ? numbered[1] : null;
    const displayTitle = heading.replace(/^##\s+\d*\.?\s*/, "").trim();
    // Prose-paragraph count: blank-line-separated blocks that aren't a blockquote,
    // heading, or HTML block — mirrors what applyLayout counts as a paragraph.
    // The rule now lives in scripts/lib/para-blocks.mjs, shared with the Python
    // aligner (`_para_blocks.py`) under pinned fixtures, so "which blocks does this
    // chapter have" is answered in one place rather than three.
    const paraKeys = fingerprints(body);
    const paras = paraKeys.length;
    const key = anchorKey(heading);
    // READ: the PDF's renderer, on this chapter's heading + body. `sawH2` is
    // seeded true for every chapter after the first so a later unnumbered
    // heading is treated as an in-flow section heading, exactly as it would be
    // in the whole-book pass. Guarded by the parity test in
    // scripts/lib/book-html.test.mjs.
    const html = String(
      renderMd(`${heading}\n\n${body}`, crosswalkByIndex, {
        sawH2: chapters.length > 0,
        // Same provenance the PDF uses, so read mode sets scripture in the
        // Uthmanic face and everything else in Scheherazade exactly as it prints.
        quranicRuns,
      }),
    );
    // EDIT: the byte-faithful render — the TipTap-safe seed (see editHtml).
    // Never the default profile: its display-only transliteration fold ate
    // leading straight apostrophes, and a seed loss becomes a book.md loss on
    // the first autosave (see renderEditSeed in markdown.ts).
    const editHtml = renderEditSeed(body);
    chapters.push({
      anchor: heading,
      key,
      title: displayTitle,
      ordinal,
      html,
      editHtml,
      paras,
      paraKeys,
      // Citations are extracted from the READ render so the Citations tab lists
      // exactly the verses the printed page will show.
      citations: extractCitations(html),
    });
    bodyByKey.push({ key, lc: body.toLowerCase() });
  }

  // A visual's chapter: a diagram anchors by heading (direct key match); a slide
  // anchors by a quoted passage phrase, so fall back to the chapter whose body
  // contains that phrase. '' means unassigned (e.g. a book-level title slide).
  const chapterKeys = new Set(chapters.map((c) => c.key));
  function resolveChapter(suggested: string): string {
    const k = anchorKey(suggested);
    if (!k) return "";
    if (chapterKeys.has(k)) return k;
    const needle = suggested.trim().toLowerCase().slice(0, 60);
    if (!needle) return "";
    return bodyByKey.find((b) => b.lc.includes(needle))?.key ?? "";
  }

  const indexData = await readJson<{ visuals?: ComposerVisual[] }>(
    join(ref.dir, "book", "visuals", "index.json"),
    {},
  );
  const visuals: ComposerVisual[] = (indexData.visuals ?? []).map((v) => ({
    id: v.id,
    type: v.type ?? "diagram",
    caption: v.caption ?? "",
    file: v.file,
    src: `/api/studio/visual-asset?slug=${encodeURIComponent(slug)}&file=${encodeURIComponent(v.file)}`,
    suggested_anchor: v.suggested_anchor ?? "",
    // The producer stamps `chapter` (bare heading text) at emit time — it is
    // the only side that can resolve a slide-deck anchor, whose needle quotes
    // the deck narration rather than book.md (the flood-every-chapter bug).
    // The needle fallback stays for pre-stamp index files.
    chapter:
      resolveChapter(v.chapter ?? "") ||
      resolveChapter(v.suggested_anchor ?? ""),
    cleaned: v.cleaned ?? true,
    embedded_title: v.embedded_title ?? "",
  }));

  const layoutData = await readJson<{ placements?: ComposerPlacement[] }>(
    join(ref.dir, "book", "visual-layout.json"),
    {},
  );
  const placements: ComposerPlacement[] = layoutData.placements ?? [];

  const [glossary, glossaryAll, podcastChapters] = await Promise.all([
    loadGlossary(slug),
    loadGlossaryAll(slug),
    loadPodcastChapters(ref.dir),
  ]);

  // RCA-001 AI-3 — read the articulation pass's own report so the Composer can
  // warn before a save freezes a chapter whose base is still machine text. The
  // crosswalk (already read above) marks the translation route: there, a book
  // with NO report has not been articulated at all and every chapter warns;
  // off it, the articulation contract does not apply and nothing warns.
  const fluencyReport = await readJson<unknown>(
    join(ref.dir, "_system", "book-fluency-report.json"),
    null,
  );
  const articulationWarnings = articulationWarningsFrom(
    fluencyReport,
    chapters.map((c) => c.key),
    { translationRoute: crosswalk.length > 0 },
  );

  return {
    slug,
    title,
    chapters,
    podcastChapters,
    visuals,
    placements,
    hasBook: true,
    citationFamily,
    translationFont,
    arabicFont,
    arabicSize,
    arabicInk,
    glossary,
    glossaryAll,
    articulationWarnings,
  };
}
