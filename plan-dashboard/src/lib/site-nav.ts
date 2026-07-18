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
  | "library"
  | "wisdom"
  | "quality"
  | "annotation-ops"
  | "studio"
  | "planner"
  | "system-map"
  | "corpus"
  | "pronunciation"
  | "pipeline-paths"
  | "pre-upload";

/**
 * Four domains (locked 2026-06-01 IA redesign):
 *   studio  — the content pipeline (one book, sequential: intake → review → edit → publish)
 *   library — the produced catalog + reading
 *   corpus  — the reference storehouse (Wisdom + the DB sources)
 *   system  — read-only docs about the factory
 * Home is reached via the brand link, not a top section.
 */
export type NavSection = "studio" | "library" | "corpus" | "system";

export interface NavLink {
  href: string;
  label: string;
  pages: ActivePage[];
}

export const TOP_NAV: Array<NavLink & { section: NavSection }> = [
  // Pronunciation + Pre-Upload Review are working tools in the book workflow,
  // so they highlight Studio (the pipeline domain), not the read-only System docs.
  // Studio is the single books hub: it lists every book (grouped by bucket) and
  // hosts the per-book content reader at /studio/<slug>. The former 'Library'
  // top-nav entry + catalog were retired 2026-06-15; /library/* now redirects here.
  {
    href: "/studio",
    label: "Studio",
    section: "studio",
    pages: ["studio", "library", "pronunciation", "pre-upload"],
  },
  {
    href: "/corpus",
    label: "Corpus",
    section: "corpus",
    pages: ["corpus", "wisdom", "db-schema"],
  },
  {
    href: "/architecture",
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
    ],
  },
];

export const SUBNAV: Record<NavSection, NavLink[]> = {
  // Studio's secondary navigation is the pipeline STEPPER, rendered by the
  // Studio shell — so the generic subnav is intentionally empty here.
  studio: [],
  // Library is breadcrumb-driven (Catalog → Book → Chapter); no flat subnav.
  library: [],
  // Corpus = the reference storehouse: the consolidated 3-source store, the
  // live Wisdom shelf, and the store's data model. (The intelligence-pipeline
  // diagram is "how it works" docs and lives under System.)
  corpus: [
    { href: "/corpus", label: "Storehouse", pages: ["corpus"] },
    { href: "/wisdom", label: "Wisdom shelf", pages: ["wisdom"] },
    { href: "/db-schema", label: "Data model", pages: ["db-schema"] },
  ],
  // Consolidated 2026-06-09 (13 → 8). System map, Pipeline paths, and
  // Annotations live under Architecture (linked from that page and still
  // routable); Pronunciation + Pre-Upload Review moved to the Studio domain.
  system: [
    { href: "/overview", label: "Overview", pages: ["overview"] },
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
};

export function getNavSection(active: ActivePage): NavSection {
  const match = TOP_NAV.find((item) => item.pages.includes(active));
  return match?.section ?? "studio";
}

export function getSubnavLinks(active: ActivePage): NavLink[] {
  return SUBNAV[getNavSection(active)];
}
