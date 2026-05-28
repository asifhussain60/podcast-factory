/**
 * Status badge class mappings — single source of truth.
 * Used by DashboardTabs, PlanDesign, and any other component rendering step rows.
 */

/** CSS class for the pill/badge element itself (background colour). */
export const STATUS_PILL: Record<string, string> = {
  complete:    'is-ok',
  in_progress: 'is-flight',
  ready:       'is-ready',
  blocked:     'is-blocked',
  failed:      'is-blocked',
  pending:     'is-future',
};

/** Human-readable label for the step status. */
export const STATUS_LABEL: Record<string, string> = {
  complete:    'Done',
  in_progress: 'In progress',
  ready:       'Ready to start',
  blocked:     'Blocked',
  failed:      'Failed',
  pending:     'Up next',
};

/** CSS class for section/header row background. */
export const STATUS_HEADER: Record<string, string> = {
  complete:    'is-complete',
  in_progress: 'is-processing',
  blocked:     'is-failed',
  failed:      'is-failed',
};

/** CSS class for the inline status dot. */
export const STATUS_DOT: Record<string, string> = {
  complete:    'is-ok',
  in_progress: 'is-flight',
  blocked:     'is-fail',
  failed:      'is-fail',
  ready:       'is-ready',
  pending:     'is-idle',
};
