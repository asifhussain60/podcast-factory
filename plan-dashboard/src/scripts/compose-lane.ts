/**
 * compose-lane.ts — the Book Composer's lane switch (Reading edition ⇄ Podcast source).
 *
 * A book carries TWO English texts of the same Arabic source, and they are not
 * two views of one thing:
 *
 *   - The READING EDITION (`book/book.md`) — what the Composer edits, what
 *     becomes `book/book.pdf`.
 *   - The PODCAST SOURCE (`chapters/*.txt`) — what is uploaded to NotebookLM.
 *     Independently translated, differently segmented (this repo's first case:
 *     9 book chapters against 20 podcast chapters, non-corresponding titles),
 *     and deliberately carrying material the book does not: the leading italic
 *     narration framing, interleaved teaching commentary, and cited references.
 *
 * So this module flips WHICH TEXT the pane shows. It never mirrors an edit
 * between them: there is no chapter mapping to carry a positional edit along,
 * and copying articulated book prose over a chapter source would delete the
 * framing/commentary/citations that make it a NotebookLM source at all.
 *
 * The podcast lane is READ-ONLY, and that is enforced structurally rather than
 * by intent:
 *
 *   1. `setLane("podcast")` AWAITS the book lane's own leave hook first — the
 *      Composer's `leaveEditMode`, which flushes the debounced autosave and
 *      then destroys the TipTap editor. An edit typed a moment before the flip
 *      lands in book.md rather than racing it, and a leave the user declined
 *      ("Keep editing") aborts the flip with the book lane untouched.
 *   2. The podcast body is rendered into a host of its OWN — never the chapter
 *      body the editor seeds from — so no editable surface and no live autosave
 *      controller survives behind the toggle. Re-seeding one shared surface is
 *      what would let a single debounced keystroke write podcast prose into
 *      book.md AND freeze that chapter in `_system/composer-edits.json`, after
 *      which `_book_pipeline_v2.py` never regenerates it (RCA-001, but with
 *      prose from the wrong lane — see
 *      docs/rca/2026-07-22-composer-snapshots-froze-unarticulated-prose.md).
 *   3. The host is marked `contenteditable="false"` + `aria-readonly`, and
 *      `assertReadOnly()` re-checks that on every render.
 *
 * Rendering goes through `renderSourceMarkdown` — the same read-only path
 * `studio/[slug]/view.astro` uses for these files — so the lane reads exactly
 * as the existing chapter viewer does, and the bodies are fetched on demand
 * rather than shipped in the page (they are ~40% larger than the whole book).
 */
import { renderSourceMarkdown } from "../lib/reader/markdown";

export type Lane = "book" | "podcast";

/** One `chapters/*.txt` file, as the server listed it. Bodies are NOT included
 *  — see the header note on why they are fetched on demand. */
export interface PodcastChapterMeta {
  /** Basename inside `chapters/`, e.g. `ch01a-three-thanks.txt`. */
  file: string;
  /** The file's own `# ` heading, falling back to its filename. */
  title: string;
  /** The `chNN<letter>` ordinal the filename carries ('' if unparseable). */
  ordinal: string;
}

/** The book lane's side of the flip. Both hooks belong to the Composer, which
 *  owns the editing session; this module owns only the ORDER they run in. */
export interface BookLaneHooks {
  /**
   * Flush any pending autosave and tear the editing session down. Resolves
   * false when the user chose to keep editing (a save had failed) — the flip
   * is then abandoned and the book lane stays exactly as it was.
   *
   * The Composer's `leaveEditMode` may instead RELOAD the page (it does when
   * prose actually changed, so the preview re-renders from the authoritative
   * book.md). That is why the requested lane is stashed before the call: the
   * reload lands back here and `pendingLane()` restores the intent.
   */
  leave: () => Promise<boolean>;
  /** Restore the book lane and re-open its editing session. */
  enter: () => void;
}

export interface ComposeLaneOptions {
  slug: string;
  chapters: PodcastChapterMeta[];
  book: BookLaneHooks;
  /** `.composer` root — the lane attribute lands here for CSS to key off. */
  root: HTMLElement;
  /** Lane toggle buttons (`aria-pressed` is managed here). */
  bookBtn: HTMLButtonElement | null;
  podcastBtn: HTMLButtonElement | null;
  /** The podcast lane section, hidden while the book lane shows. */
  pane: HTMLElement;
  /** Read-only host the rendered chapter lands in. */
  body: HTMLElement;
  /** The podcast lane's OWN chapter picker — deliberately not the book's, whose
   *  change handler drives flush/reload machinery this lane must not touch. */
  select: HTMLSelectElement | null;
  /** Re-read the picker after this module sets `select.value` itself.
   *
   *  The Composer draws its chapter lists rather than using the OS dropdown (a
   *  native `<select>` paints its open panel through the window system, which
   *  dropped a grey system list out of an editorial control), so the element
   *  above is only the state holder and the visible list needs telling. Owned by
   *  the caller — this module stays independent of which picker widget is in use,
   *  and its tests need no widget at all. */
  syncSelect?: () => void;
  /** Status line (loading / error / which file is shown). */
  status: HTMLElement | null;
  /** Fetch one chapter's raw text. Injected in tests; defaults to the
   *  read-only `/api/library/file` route. */
  fetchChapterText?: (slug: string, file: string) => Promise<string>;
  /** Raw text → HTML. Defaults to the shared read-only renderer. */
  render?: (raw: string) => string;
}

export interface ComposeLane {
  lane: () => Lane;
  /** Flip lanes. Resolves the lane actually in effect when it settled. */
  setLane: (next: Lane) => Promise<Lane>;
  /** Show a specific podcast chapter (no-op outside the podcast lane). */
  showChapter: (file: string) => Promise<void>;
}

/** sessionStorage key holding a lane requested across a reload. Scoped per
 *  book so two Composer tabs on different books cannot inherit each other's. */
const laneKey = (slug: string) => `cx-restore-lane:${slug}`;

/** The lane the previous page requested before an autosave-triggered reload,
 *  consumed on read. Exported so the Composer can restore it on boot. */
export function pendingLane(slug: string): Lane | null {
  try {
    const raw = sessionStorage.getItem(laneKey(slug));
    sessionStorage.removeItem(laneKey(slug));
    return raw === "podcast" || raw === "book" ? raw : null;
  } catch {
    return null; // sessionStorage best-effort
  }
}

function stashLane(slug: string, lane: Lane): void {
  try {
    sessionStorage.setItem(laneKey(slug), lane);
  } catch {
    /* sessionStorage best-effort */
  }
}

function clearLane(slug: string): void {
  try {
    sessionStorage.removeItem(laneKey(slug));
  } catch {
    /* sessionStorage best-effort */
  }
}

/**
 * Read the podcast source through the same route the file viewer uses. GET
 * only, realpath-guarded to the book's own folder, and scoped here to
 * `chapters/<basename>` so nothing but a chapter file can be requested.
 */
async function defaultFetchChapterText(
  slug: string,
  file: string,
): Promise<string> {
  const url =
    `/api/library/file?slug=${encodeURIComponent(slug)}` +
    `&path=${encodeURIComponent(`chapters/${file}`)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`.trim());
  return res.text();
}

/**
 * The structural read-only guarantee, re-asserted rather than assumed.
 *
 * Throws if the podcast host is (or contains) an editable surface. A future
 * change that re-seeded the editor here — the exact mistake that would write
 * podcast prose into book.md — fails loudly at flip time instead of silently
 * on the next debounce tick.
 */
/**
 * Demote every heading in the rendered podcast chapter one level.
 *
 * The Composer page already owns the page's single `<h1>` (the book title in
 * its header), and the reading-edition lane's chapter title is an `<h2>` —
 * `.chapter-open h2`, the book renderer's own markup. A podcast chapter file
 * opens with `# `, so the shared source renderer hands back an `<h1>`: injected
 * as-is it would give the page a SECOND `<h1>` and skip a level (REQ-011,
 * REQ-049), and the two lanes would disagree about what a chapter title is.
 *
 * Only the element level changes — text, inline markup, ids and classes are
 * carried across untouched, so nothing about the source text is rewritten. The
 * visual treatment of the demoted levels is restored in book-composer.css
 * (`.cx-podcast-body h2/h3/h4`), so this is a semantic correction, not a
 * restyle.
 */
export function demoteHeadings(host: HTMLElement): void {
  const doc = host.ownerDocument;
  // Snapshot order matters: a heading created here is not in the list, so
  // nothing is demoted twice.
  for (const old of Array.from(host.querySelectorAll("h1, h2, h3, h4, h5"))) {
    const next = doc.createElement(`h${Number(old.tagName[1]) + 1}`);
    for (const attr of Array.from(old.attributes))
      next.setAttribute(attr.name, attr.value);
    next.innerHTML = old.innerHTML;
    old.replaceWith(next);
  }
}

export function assertReadOnly(host: HTMLElement): void {
  if (host.isContentEditable || host.getAttribute("contenteditable") === "true")
    throw new Error("podcast lane host is editable");
  if (host.querySelector('[contenteditable="true"], .ProseMirror, .cx-prose'))
    throw new Error("podcast lane host contains an editable surface");
}

export function createComposeLane(opts: ComposeLaneOptions): ComposeLane {
  const {
    slug,
    chapters,
    book,
    root,
    bookBtn,
    podcastBtn,
    pane,
    body,
    select,
    status,
  } = opts;
  const syncSelect = opts.syncSelect ?? (() => {});
  const fetchText = opts.fetchChapterText ?? defaultFetchChapterText;
  const render = opts.render ?? renderSourceMarkdown;

  let lane: Lane = "book";
  let shownFile = "";
  /** The flip in progress. `setLane("podcast")` awaits the book lane's leave
   *  hook, and `lane` is still "book" for that whole window — so a second click
   *  would sail past the same-lane guard and run leave() (and its flush) twice.
   *  Concurrent callers join the flip already running instead. */
  let flipping: Promise<Lane> | null = null;
  /** Bumped on every load so a slow fetch that lost the race cannot paint over
   *  a newer one (or paint into the book lane after a flip back). */
  let loadToken = 0;

  body.setAttribute("contenteditable", "false");
  body.setAttribute("aria-readonly", "true");

  function setStatus(message: string, isError = false): void {
    if (!status) return;
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  }

  function paintLane(): void {
    root.dataset.lane = lane;
    pane.hidden = lane !== "podcast";
    bookBtn?.setAttribute("aria-pressed", String(lane === "book"));
    podcastBtn?.setAttribute("aria-pressed", String(lane === "podcast"));
  }

  async function load(file: string): Promise<void> {
    const token = ++loadToken;
    setStatus("Loading…");
    let html: string;
    try {
      html = render(await fetchText(slug, file));
    } catch (err) {
      if (token !== loadToken || lane !== "podcast") return;
      body.replaceChildren();
      setStatus(`Couldn't read this chapter — ${(err as Error).message}`, true);
      return;
    }
    if (token !== loadToken || lane !== "podcast") return; // superseded
    body.innerHTML = html;
    demoteHeadings(body); // page keeps ONE <h1> — see the note on the helper
    assertReadOnly(body);
    shownFile = file;
    setStatus(`chapters/${file}`);
  }

  async function showChapter(file: string): Promise<void> {
    if (lane !== "podcast") return;
    if (!chapters.some((c) => c.file === file)) return; // not a listed chapter
    if (file === shownFile) return;
    await load(file);
  }

  async function flip(next: Lane): Promise<Lane> {
    if (next === lane) return lane;

    if (next === "podcast") {
      // Order matters and is the whole safety contract: the book lane's
      // pending save is flushed and its editor destroyed BEFORE any pane
      // swap, so nothing editable and no autosave controller is left behind
      // the toggle. Stash first — `leave()` may reload the page.
      stashLane(slug, "podcast");
      let left = false;
      try {
        left = await book.leave();
      } finally {
        if (!left) clearLane(slug);
      }
      if (!left) return lane; // user kept editing — book lane untouched
      clearLane(slug);
      lane = "podcast";
      paintLane();
      const file = select?.value || chapters[0]?.file || "";
      if (file) {
        if (select && select.value !== file) {
          select.value = file;
          syncSelect();
        }
        await load(file);
      } else {
        setStatus("This book has no podcast chapter sources.", true);
      }
      return lane;
    }

    // Back to the book. Drop the rendered podcast prose rather than leaving it
    // in the DOM behind a hidden pane, so nothing can later be mistaken for
    // (or serialized as) chapter content.
    loadToken += 1;
    lane = "book";
    shownFile = "";
    body.replaceChildren();
    setStatus("");
    paintLane();
    book.enter();
    return lane;
  }

  /** Serialize flips: one at a time, in the order they were asked for. */
  async function setLane(next: Lane): Promise<Lane> {
    const run = (flipping ?? Promise.resolve(lane)).then(() => flip(next));
    flipping = run.catch(() => lane);
    return run;
  }

  bookBtn?.addEventListener("click", () => void setLane("book"));
  podcastBtn?.addEventListener("click", () => void setLane("podcast"));
  select?.addEventListener("change", () => void showChapter(select.value));

  paintLane();

  return { lane: () => lane, setLane, showChapter };
}
