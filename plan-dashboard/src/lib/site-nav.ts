export type ActivePage =
  | 'home'
  | 'overview'
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
  | 'studio-poc'
  | 'studio'
  | 'planner'
  | 'system-map'
  | 'intake';

export type NavSection = 'overview' | 'workspace' | 'library' | 'knowledge' | 'docs';

export interface NavLink {
  href: string;
  label: string;
  pages: ActivePage[];
}

export const TOP_NAV: Array<NavLink & { section: NavSection }> = [
  { href: '/', label: 'Home', section: 'overview', pages: ['home', 'overview'] },
  { href: '/workbench', label: 'Workspace', section: 'workspace', pages: ['workbench', 'studio', 'studio-poc', 'intake', 'annotation-ops'] },
  { href: '/library', label: 'Library', section: 'library', pages: ['library'] },
  { href: '/wisdom', label: 'Knowledge', section: 'knowledge', pages: ['wisdom', 'intelligence'] },
  { href: '/architecture', label: 'Docs', section: 'docs', pages: ['architecture', 'infrastructure', 'db-schema', 'security', 'system-map', 'quality', 'plan', 'dashboard', 'planner'] },
];

export const SUBNAV: Record<NavSection, NavLink[]> = {
  overview: [
    { href: '/', label: 'Factory tour', pages: ['home'] },
    { href: '/overview', label: 'Operations overview', pages: ['overview'] },
  ],
  workspace: [
    { href: '/workbench', label: 'Workbench', pages: ['workbench'] },
    { href: '/studio', label: 'Editor', pages: ['studio', 'studio-poc'] },
    { href: '/intake', label: 'New content', pages: ['intake'] },
    { href: '/annotation-ops', label: 'Annotations', pages: ['annotation-ops'] },
  ],
  library: [
    { href: '/library', label: 'Catalog', pages: ['library'] },
  ],
  knowledge: [
    { href: '/wisdom', label: 'Wisdom corpus', pages: ['wisdom'] },
    { href: '/intelligence', label: 'Intelligence', pages: ['intelligence'] },
  ],
  docs: [
    { href: '/architecture', label: 'Pipeline architecture', pages: ['architecture'] },
    { href: '/system-map', label: 'System map', pages: ['system-map'] },
    { href: '/infrastructure', label: 'Infrastructure', pages: ['infrastructure'] },
    { href: '/db-schema', label: 'Data model', pages: ['db-schema'] },
    { href: '/security', label: 'Security', pages: ['security'] },
    { href: '/quality', label: 'Quality', pages: ['quality'] },
    { href: '/plan', label: 'Roadmap', pages: ['plan', 'dashboard', 'planner'] },
  ],
};

export function getNavSection(active: ActivePage): NavSection {
  const match = TOP_NAV.find((item) => item.pages.includes(active));
  return match?.section ?? 'overview';
}

export function getSubnavLinks(active: ActivePage): NavLink[] {
  return SUBNAV[getNavSection(active)];
}
