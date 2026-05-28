/**
 * Shared types for plan data structures — sourced from dashboard-snapshot.json.
 * Import from here; never re-declare locally in components.
 */

export interface RoadmapStep {
  id: string;
  wave: string;
  title: string;
  status: string;
  tier: string;
  depends_on: string[];
  last_touched?: string;
  plain?: string;
  tools?: string[];
}

export interface Wave {
  id: string;
  name: string;
  plain: string;
}

export interface WaveEvent {
  ts: string;
  wave: number;
  wave_letter?: string;
  event_type: string;
  status: string;
  message: string;
}

export interface LoopExecutionState {
  current_wave: string;
  current_status: string;
  intent_check_result: 'pass' | 'corrected' | 'blocked';
  alignment_steps_taken: string[];
  iteration_count: number;
  pattern_tally: {
    applied_this_run: number;
    discovered_this_run: number;
    promoted_this_run: number;
  };
}

export interface Debt {
  id: string;
  title: string;
  severity: string;
  plain: string;
}

export interface BookInFlight {
  slug: string;
  title: string;
  phase: string;
  phase_status: string;
  cost_to_date_usd: number;
  kind: string;
}

export interface BookShipped {
  slug: string;
  title: string;
  shipped: string;
  episodes: number;
  cost_total_usd: number;
}

export interface RecentCommit {
  sha: string;
  subject: string;
  date: string;
}
