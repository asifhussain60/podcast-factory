/**
 * studio-picker.ts — the Studio landing page's behaviour: three filter facets
 * and three view modes.
 *
 * This file is the DOM half only. The filtering RULES — what a facet matches,
 * and what a chip's number means — live in `lib/reader/studio-filters.ts` and
 * are unit-tested there, because both have been wrong in ways only a real
 * browser caught. Keep it that way: a rule added here instead of there is a
 * rule no test can state.
 *
 * THREE FACETS, single-select, narrowing together. Category and status ask
 * where a book is in the pipeline; track asks what it is about. Each starts
 * unnarrowed, each has its own clear in its caption, and Reset in the header
 * clears all three.
 *
 * This replaced a multi-select model in which every chip started ON, so a click
 * SUBTRACTED: pressing "Published" hid the published books, and the pressed
 * styling drew the chip you had just switched off as the prominent one, so the
 * interface confirmed the wrong reading.
 */
import {
  ALL,
  FACETS,
  contextualCount,
  isWideOpen,
  matches,
  wideOpen,
  type Chosen,
  type Facet,
  type FilterUnit,
} from "../lib/reader/studio-filters";

const STORAGE_KEY = "pf-studio-filters";
const VIEW_KEY = "pf-studio-view";

/** How each facet's chips are found, and how a card declares its value. */
const GROUPS: Record<Facet, { chip: string; attr: string }> = {
  bucket: { chip: ".studio-bucket-chip", attr: "bucketFilter" },
  status: { chip: ".studio-filter-chip", attr: "statusFilter" },
  track: { chip: ".studio-track-chip", attr: "trackFilter" },
};

/**
 * A card, read as the plain data the rules operate on.
 *
 * The bucket comes from the card's SHELF, not the card — the shelf is the
 * group — which is the one piece of DOM knowledge the rules module is
 * deliberately kept free of.
 */
const unitOf = (card: HTMLElement): FilterUnit => ({
  bucket: card.closest<HTMLElement>(".studio-shelf")?.dataset.bucket ?? "",
  status: card.dataset.status ?? "",
  track: card.dataset.track ?? "",
});

const chipsIn = (facet: Facet) =>
  Array.from(document.querySelectorAll<HTMLButtonElement>(GROUPS[facet].chip));

const valueOf = (facet: Facet, chip: HTMLButtonElement) =>
  chip.dataset[GROUPS[facet].attr] ?? ALL;

const allCards = () =>
  Array.from(document.querySelectorAll<HTMLElement>(".studio-shelf-card"));

const chosen: Chosen = wideOpen();

function restore(): void {
  let saved: unknown;
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
  } catch {
    return; // Unreadable or unavailable storage just means the defaults.
  }
  if (!saved || typeof saved !== "object") return;
  for (const facet of FACETS) {
    const want = (saved as Record<string, unknown>)[facet];
    if (typeof want !== "string") continue;
    // Only restore a choice this page can still honour: a track whose books
    // have all been republished elsewhere, or a bucket that no longer has a
    // shelf, would otherwise restore an empty screen with no way back except
    // finding a chip that is not there.
    const chip = chipsIn(facet).find((c) => valueOf(facet, c) === want);
    if (chip && !chip.disabled) chosen[facet] = want;
  }
}

function persist(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chosen));
  } catch {
    /* Private browsing or a full quota — the filters still work this visit. */
  }
}

function paintChips(): void {
  for (const facet of FACETS) {
    for (const chip of chipsIn(facet)) {
      chip.setAttribute(
        "aria-pressed",
        valueOf(facet, chip) === chosen[facet] ? "true" : "false",
      );
    }
  }
}

/**
 * Recount every chip AGAINST THE OTHER FACETS' CURRENT CHOICES.
 *
 * A chip reports what pressing it WOULD show given everything else already
 * chosen, and a chip that would show nothing is disabled — so the number and
 * the outcome come from the same predicate over the same cards rather than
 * from two computations that can drift.
 */
function recount(): void {
  const units = allCards().map(unitOf);
  for (const facet of FACETS) {
    for (const chip of chipsIn(facet)) {
      const value = valueOf(facet, chip);
      const n = contextualCount(units, chosen, facet, value);
      const slot = chip.querySelector<HTMLElement>("[class$='-count']");
      if (slot) slot.textContent = String(n);
      // The CHOSEN chip is never disabled even at zero — it is the one that
      // got you to an empty shelf, and disabling it would take away the
      // control you need to leave. Everything else at zero goes flat.
      chip.disabled = n === 0 && value !== chosen[facet];
    }
  }
}

function apply(): void {
  document.querySelectorAll<HTMLElement>(".studio-shelf").forEach((shelf) => {
    let visible = 0;
    shelf
      .querySelectorAll<HTMLElement>(".studio-shelf-card")
      .forEach((card) => {
        const show = matches(unitOf(card), chosen);
        card.hidden = !show;
        // A deck's card is its `<summary>`, but the stacked-sheet shell drawn
        // around it is the `<details>`. Hiding only the summary left that shell
        // holding a grid cell as an empty bordered panel — visible the moment the
        // track facet arrived, since a track is the first facet that can hide one
        // deck while its shelf-mates stay.
        const deck = card.closest<HTMLElement>(".studio-series-deck");
        if (deck) deck.hidden = !show;
        if (show) visible += 1;
      });
    // Volume rows inside an open deck follow the same rules, so a facet narrows
    // what the deck lists rather than leaving stale rows on screen. They DO
    // carry their own status, unlike the deck summary above them.
    shelf.querySelectorAll<HTMLElement>(".studio-series-vol").forEach((row) => {
      row.hidden = !matches(unitOf(row), chosen);
    });
    shelf.hidden = visible === 0;
    const count = shelf.querySelector<HTMLElement>(".studio-shelf-count");
    if (count)
      count.textContent = `${visible} ${visible === 1 ? "work" : "works"}`;
  });

  const shown = document.querySelectorAll<HTMLElement>(
    ".studio-shelf-card:not([hidden])",
  ).length;

  // The find bar's own count. Visual only — the live region below is what is
  // announced, and doing both would say the same number twice.
  const headCount = document.getElementById("studio-findbar-count");
  if (headCount)
    headCount.textContent = `${shown} ${shown === 1 ? "work" : "works"}`;

  // Said out loud, because filtering happens with no page change: without it a
  // screen-reader user presses a chip and is told nothing at all.
  const status = document.getElementById("studio-filter-status");
  if (status) {
    status.textContent = isWideOpen(chosen)
      ? `Showing all ${shown} works.`
      : `Showing ${shown} ${shown === 1 ? "work" : "works"}.`;
  }
}

const clearButtons = () =>
  Array.from(
    document.querySelectorAll<HTMLButtonElement>(".studio-facet-clear"),
  );

function refresh(): void {
  paintChips();
  recount();
  apply();
  persist();
  // The reset control appears only while something is narrowed, and each
  // group's own clear only while THAT group is.
  const reset = document.getElementById("studio-findbar-reset");
  if (reset) reset.hidden = isWideOpen(chosen);
  for (const btn of clearButtons()) {
    const facet = btn.dataset.clearFacet as Facet | undefined;
    btn.hidden = !facet || chosen[facet] === ALL;
  }
}

for (const facet of FACETS) {
  for (const chip of chipsIn(facet)) {
    chip.addEventListener("click", () => {
      // Pressing the chip you are already on clears that facet, so a group can
      // always be undone from inside itself without reaching for the caption's
      // control — the same way a pressed toggle releases.
      const value = valueOf(facet, chip);
      chosen[facet] = chosen[facet] === value ? ALL : value;
      refresh();
    });
  }
}

// The per-group clear in each caption. It clears ONLY ITS OWN facet — the
// "clear everything" job belongs to Reset in the header. Three controls that
// each wiped all three groups would make Reset redundant and make "clear the
// category filter" do something its label does not say.
for (const btn of clearButtons()) {
  btn.addEventListener("click", () => {
    const facet = btn.dataset.clearFacet as Facet | undefined;
    if (!facet || !(facet in GROUPS)) return;
    chosen[facet] = ALL;
    refresh();
  });
}

document
  .getElementById("studio-findbar-reset")
  ?.addEventListener("click", () => {
    for (const facet of FACETS) chosen[facet] = ALL;
    refresh();
  });

/**
 * View mode — cards / compact / list.
 *
 * One data attribute on the picker; the stylesheet does the rest. Kept apart
 * from the facets because it answers a different question: they decide WHICH
 * books are on screen, this decides how much of each is drawn. Remembered
 * separately for the same reason.
 */
const VIEWS = ["cards", "compact", "list"] as const;
type View = (typeof VIEWS)[number];

const picker = document.querySelector<HTMLElement>(".studio-picker");
const viewButtons = Array.from(
  document.querySelectorAll<HTMLButtonElement>(".studio-view-btn"),
);

function setView(view: View, save: boolean): void {
  if (picker) picker.dataset.view = view;
  for (const b of viewButtons) {
    b.setAttribute(
      "aria-pressed",
      b.dataset.viewMode === view ? "true" : "false",
    );
  }
  if (!save) return;
  try {
    localStorage.setItem(VIEW_KEY, view);
  } catch {
    /* Storage unavailable — the choice still holds for this visit. */
  }
}

for (const b of viewButtons) {
  b.addEventListener("click", () => {
    const view = b.dataset.viewMode as View | undefined;
    if (view && (VIEWS as readonly string[]).includes(view))
      setView(view, true);
  });
}

let savedView: string | null = null;
try {
  savedView = localStorage.getItem(VIEW_KEY);
} catch {
  /* see above */
}
setView(
  (VIEWS as readonly string[]).includes(savedView ?? "")
    ? (savedView as View)
    : "cards",
  false,
);

restore();
refresh();
