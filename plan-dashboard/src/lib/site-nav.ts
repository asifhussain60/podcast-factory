export type ActivePage =
  | "home"
  | "overview"
  | "about"
  | "architecture"
  | "intelligence"
  | "infrastructure"
  | "db-schema"
  | "security"
  | "plan"
  | "snag-list"
  | "claude-plans"
  | "library"
  | "wisdom"
  | "quality"
  | "annotation-ops"
  | "studio"
  // The per-book Studio pages (/studio/<slug>/…). Split out of "studio" on
  // 2026-08-15 so the Studio section could gain a subnav row WITHOUT that row
  // appearing above every book's work surface — see NO_SECTION_SUBNAV below.
  | "studio-book"
  | "planner"
  | "system-map"
  | "corpus"
  | "corpus-morphology"
  | "pronunciation"
  | "pipeline-paths"
  | "how-it-works"
  | "pre-upload"
  | "intake";

/**
 * Four domains (locked 2026-06-01 IA redesign):
 *   studio  — the content pipeline (one book, sequential: intake → review → edit → publish)
 *   library — the produced catalog + reading
 *   corpus  — the reference storehouse (Wisdom + the DB sources)
 *   system  — read-only docs about the factory
 * Home is reached via the brand link, not a top section.
 */
export type NavSection =
  | "studio"
  | "library"
  | "corpus"
  | "system"
  | "snaglist"
  | "claudeplans"
  | "intake";

export interface NavLink {
  href: string;
  label: string;
  pages: ActivePage[];
}

export const TOP_NAV: Array<NavLink & { section: NavSection }> = [
  // Intake leads the row (Asif, 2026-08-30). The order is the shape of the
  // work: commission a piece of content, then produce it in Studio, with the
  // reference and read-only domains after. It is also the only tab reached to
  // START something, so it should not sit last behind four tabs about work
  // already under way.
  //
  // Naming: the per-book pipeline stepper also has a step called Intake. The
  // tab keeps the word (Asif's choice); the page's own h1 is "Commission new
  // content", so the two read differently wherever they appear together.
  {
    href: "/intake",
    label: "Intake",
    section: "intake",
    pages: ["intake"],
  },
  // Pronunciation + Pre-Upload Review are working tools in the book workflow,
  // so they highlight Studio (the pipeline domain), not the read-only System docs.
  // Studio is the single books hub: it lists every book (grouped by bucket) and
  // hosts the per-book content reader at /studio/<slug>. The former 'Library'
  // top-nav entry + catalog were retired 2026-06-15; /library/* now redirects here.
  {
    href: "/studio",
    label: "Studio",
    section: "studio",
    pages: ["studio", "studio-book", "library", "pronunciation", "pre-upload"],
  },
  {
    href: "/corpus",
    label: "Corpus",
    section: "corpus",
    pages: ["corpus", "corpus-morphology", "wisdom", "db-schema"],
  },
  {
    href: "/overview",
    label: "System",
    section: "system",
    pages: [
      "architecture",
      "intelligence",
      "system-map",
      "infrastructure",
      "security",
      "quality",
      "plan",
      "planner",
      "overview",
      "about",
      "annotation-ops",
      "pipeline-paths",
      "how-it-works",
    ],
  },
  // Promoted out of System's subnav to its own top-level tab, right after
  // System (Asif, 2026-08-08) — it's an actively-used work list, not read-only
  // factory documentation, so it earns a first-class spot rather than being
  // buried a click deep.
  {
    href: "/snag-list",
    label: "Snag List",
    section: "snaglist",
    pages: ["snag-list"],
  },
  // Same promotion logic as Snag List (Asif, 2026-08-08): the plans Claude
  // Code writes for this repo are an actively-read work surface, not
  // read-only docs, so they get their own top-level tab too.
  {
    href: "/claude-plans",
    label: "Plans",
    section: "claudeplans",
    pages: ["claude-plans"],
  },
];

export const SUBNAV: Record<NavSection, NavLink[]> = {
  // Studio's hub row (2026-08-15). Pre-Upload Review and Pronunciation used to
  // be reachable ONLY from a sentence of instructions on the Studio picker;
  // when that prose was removed, both pages became URL-only. They are workflow
  // tools in the book pipeline, so they belong in the Studio section's own
  // chrome rather than in a paragraph that any layout tidy can delete.
  //
  // This row does NOT render on the per-book pages — those are "studio-book"
  // and are listed in NO_SECTION_SUBNAV below, because /studio/<slug>/<step>
  // already fills the same slot with the pipeline STEPPER and its siblings
  // would gain a second chrome row above the work surface for no gain.
  studio: [
    { href: "/studio", label: "Books", pages: ["studio", "library"] },
    {
      href: "/pre-upload",
      label: "Pre-Upload Review",
      pages: ["pre-upload"],
    },
    {
      href: "/pronunciation",
      label: "Pronunciation",
      pages: ["pronunciation"],
    },
  ],
  // Library is breadcrumb-driven (Catalog → Book → Chapter); no flat subnav.
  library: [],
  // Corpus = the reference storehouse: the consolidated 3-source store, the
  // live Wisdom shelf, and the store's data model. (The intelligence-pipeline
  // diagram is "how it works" docs and lives under System.)
  corpus: [
    { href: "/corpus", label: "Storehouse", pages: ["corpus"] },
    {
      href: "/corpus/morphology",
      label: "Morphology",
      pages: ["corpus-morphology"],
    },
    { href: "/wisdom", label: "Wisdom shelf", pages: ["wisdom"] },
    { href: "/db-schema", label: "Data model", pages: ["db-schema"] },
  ],
  // Consolidated 2026-06-09 (13 → 8). System map, Pipeline paths, and
  // Annotations live under Architecture (linked from that page and still
  // routable); Pronunciation + Pre-Upload Review moved to the Studio domain.
  system: [
    { href: "/overview", label: "Overview", pages: ["overview"] },
    { href: "/how-it-works", label: "How it works", pages: ["how-it-works"] },
    {
      href: "/architecture",
      label: "Architecture",
      pages: ["architecture", "system-map", "pipeline-paths", "annotation-ops"],
    },
    { href: "/intelligence", label: "Intelligence", pages: ["intelligence"] },
    {
      href: "/infrastructure",
      label: "Infrastructure",
      pages: ["infrastructure"],
    },
    { href: "/security", label: "Security", pages: ["security"] },
    { href: "/quality", label: "Quality", pages: ["quality"] },
    { href: "/plan", label: "Roadmap", pages: ["plan", "planner"] },
    { href: "/about", label: "About & Help", pages: ["about"] },
  ],
  // Its own top-level tab (2026-08-08) with no second-row subnav — a single page.
  snaglist: [],
  // Same shape: one page, its own tab, no subnav.
  claudeplans: [],
  // Likewise — one page, and the wizard's own rail is its navigation.
  intake: [],
};

export function getNavSection(active: ActivePage): NavSection {
  const match = TOP_NAV.find((item) => item.pages.includes(active));
  return match?.section ?? "studio";
}

/**
 * Pages that belong to a section but deliberately render NO section subnav.
 *
 * The per-book Studio pages are the only members. `/studio/<slug>/<step>` fills
 * Base's `subnav` slot with the pipeline stepper, and its siblings (the book
 * overview, Compose, view, preview) sit beside it — giving them the section row
 * would push every book's work surface down by a row and, on the stepper page,
 * stack two navigation bars. They carry their own ActivePage, so this is a
 * lookup rather than a pathname test.
 */
const NO_SECTION_SUBNAV: ReadonlySet<ActivePage> = new Set<ActivePage>([
  "studio-book",
]);

export function getSubnavLinks(active: ActivePage): NavLink[] {
  if (NO_SECTION_SUBNAV.has(active)) return [];
  return SUBNAV[getNavSection(active)];
}
