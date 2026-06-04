/**
 * Ref-category registry.
 *
 * Adding a new category (e.g. etymology, dates, place-names) requires:
 *   1. Create `src/lib/ref-categories/builtin/<id>.ts` exporting a RefCategory.
 *   2. Import it here and add to BUILT_IN.
 *   3. (Nothing else.)
 *
 * Consumers (HighlightRenderer, ReaderControls, search filters, TOC counts)
 * iterate over `getEnabledCategories()` — no consumer hard-codes an id.
 */

import type { RefCategory, RegistryValidationIssue } from './types';
import { quran } from './builtin/quran';
import { hadith } from './builtin/hadith';
import { arabicTranslit } from './builtin/arabic-translit';

export const BUILT_IN: RefCategory[] = [quran, hadith, arabicTranslit];

export interface CategoryPrefs {
  /** Per-category enabled toggles. Missing key → use category.enabledByDefault. */
  enabled?: Record<string, boolean>;
}

export function getAllCategories(): RefCategory[] {
  return BUILT_IN;
}

export function getEnabledCategories(prefs: CategoryPrefs = {}): RefCategory[] {
  return BUILT_IN.filter((c) => {
    if (prefs.enabled && c.id in prefs.enabled) return prefs.enabled[c.id];
    return c.enabledByDefault;
  });
}

export function getCategoryById(id: string): RefCategory | undefined {
  return BUILT_IN.find((c) => c.id === id);
}

/**
 * Validate the registry at startup. Surfaces duplicate IDs, duplicate
 * keyboard shortcuts, etc. Run once on module load; throw on errors.
 */
export function validateRegistry(): RegistryValidationIssue[] {
  const issues: RegistryValidationIssue[] = [];
  const seenIds = new Set<string>();
  const seenShortcuts = new Map<string, string>();
  for (const c of BUILT_IN) {
    if (seenIds.has(c.id)) {
      issues.push({ level: 'error', message: `Duplicate category id: ${c.id}` });
    }
    seenIds.add(c.id);
    for (const key of [c.shortcuts.next, c.shortcuts.prev]) {
      if (seenShortcuts.has(key)) {
        issues.push({
          level: 'warn',
          message: `Shortcut "${key}" used by both ${seenShortcuts.get(key)} and ${c.id}`,
        });
      }
      seenShortcuts.set(key, c.id);
    }
  }
  return issues;
}

// Run validation eagerly so problems surface at module-load, not at first render.
const _issues = validateRegistry();
for (const issue of _issues) {
  if (issue.level === 'error') {
    throw new Error(`[ref-categories] ${issue.message}`);
  }
  // eslint-disable-next-line no-console
  console.warn(`[ref-categories] ${issue.message}`);
}
