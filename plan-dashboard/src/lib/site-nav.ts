export type ActivePage =
  | 'home'
  | 'overview'
  | 'about'
  | 'architecture'
  | 'intelligence'
  | 'infrastructure'
  | 'db-schema'
  | 'security'
  | 'dashboard'
  | 'workbench'
  | 'plan'
  | 'library'
  | 'wisdom'
  | 'quality'
  | 'annotation-ops'
  | 'studio'
  | 'planner'
  | 'system-map'
  | 'intake'
  | 'corpus';

/**
 * Four domains (locked 2026-06-01 IA redesign):
 *   studio  — the content pipeline (one book, sequential: intake → review → edit → publish)
 *   library — the produced catalog + reading
 *   corpus  — the reference storehouse (Wisdom + the DB sources)
 *   system  — read-only docs about the factory
 * Home is reached via the brand link, not a top section.
 */
export type NavSection = 'studio' | 'library' | 'corpus' | 'system';

export interface NavLink {
  href: string;
  label: string;
  pages: ActivePage[];
}

export const TOP_NAV: Array<NavLink & { section: NavSection }> = [
  { href: '/studio', label: 'Studio', section: 'studio', pages: ['studio', 'workbench', 'intake'] },
  { href: '/library', label: 'Library', section: 'library', pages: ['library'] },
  { href: '/corpus', label: 'Corpus', section: 'corpus', pages: ['corpus', 'wisdom', 'db-schema'] },
  { href: '/architecture', label: 'System', section: 'system', pages: ['architecture', 'intelligence', 'system-map', 'infrastructure', 'security', 'quality', 'plan', 'dashboard', 'planner', 'overview', 'about', 'annotation-ops'] },
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
    { href: '/corpus', label: 'Storehouse', pages: ['corpus'] },
    { href: '/wisdom', label: 'Wisdom shelf', pages: ['wisdom'] },
    { href: '/db-schema', label: 'Data model', pages: ['db-schema'] },
  ],
  system: [
    { href: '/architecture', label: 'Pipeline architecture', pages: ['architecture'] },
    { href: '/intelligence', label: 'Intelligence pipeline', pages: ['intelligence'] },
    { href: '/system-map', label: 'System map', pages: ['system-map'] },
    { href: '/infrastructure', label: 'Infrastructure', pages: ['infrastructure'] },
    { href: '/security', label: 'Security', pages: ['security'] },
    { href: '/quality', label: 'Quality', pages: ['quality'] },
    { href: '/plan', label: 'Roadmap', pages: ['plan', 'dashboard', 'planner'] },
    { href: '/annotation-ops', label: 'Annotations', pages: ['annotation-ops'] },
    { href: '/overview', label: 'Operations', pages: ['overview'] },
    { href: '/about', label: 'About & Help', pages: ['about'] },
  ],
};

export function getNavSection(active: ActivePage): NavSection {
  const match = TOP_NAV.find((item) => item.pages.includes(active));
  return match?.section ?? 'studio';
}

export function getSubnavLinks(active: ActivePage): NavLink[] {
  return SUBNAV[getNavSection(active)];
}
