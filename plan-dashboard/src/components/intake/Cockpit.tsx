/**
 * Cockpit — Screen 4 of the new-content intake (Phase 6, Q10).
 *
 * Polls /api/intake/status for the running volume/book: phase, cost-vs-cap, and
 * per-chapter progress. When the run halts at a human-review gate (0f/0ci/06a/
 * finalize) or the between-volumes pause, it renders an APPROVAL CARD whose button
 * POSTs to /api/intake/resume (resume / --advance). The UI is read-only while the
 * volume runs (single-writer rule) — it only reads state + sends approvals.
 */
import { useEffect, useRef, useState } from 'react';

interface Status {
  found: boolean;
  slug: string;
  phase?: string;
  phase_status?: string;
  publication_status?: string;
  work_slug?: string | null;
  last_error?: string | null;
  at_human_gate?: boolean;
  gate?: { name: string; label: string } | null;
  cost?: {
    book_spend_usd: number;
    per_chapter_cap_usd: number;
    book_cap_usd: number;
    book_cap_active: boolean;
    over_book_cap: boolean;
  };
  chapters?: { completed: number; failed: number; total: number };
}

interface Props {
  slug: string;
  pollMs?: number;
}

export default function Cockpit({ slug, pollMs = 5000 }: Props) {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState('');
  const [approving, setApproving] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  async function poll() {
    try {
      const r = await fetch(`/api/intake/status?slug=${encodeURIComponent(slug)}`);
      const json = await r.json();
      if (r.ok && json.ok) setStatus(json.data.status);
    } catch { /* transient — keep polling */ }
  }

  useEffect(() => {
    poll();
    timer.current = setInterval(poll, pollMs);
    return () => { if (timer.current) clearInterval(timer.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  async function approve(action: 'resume' | 'advance') {
    setApproving(true);
    setError('');
    try {
      const r = await fetch('/api/intake/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, action, work_slug: status?.work_slug ?? undefined }),
      });
      const json = await r.json();
      if (!r.ok || !json.ok) { setError(json.error ?? 'Approval failed'); return; }
      setTimeout(poll, 1500); // give the relaunch a moment, then refresh
    } catch (e) {
      setError(`Network error: ${String(e)}`);
    } finally {
      setApproving(false);
    }
  }

  if (!status) {
    return <div className="intake-card"><p className="intake-hint" role="status">Connecting to the run…</p></div>;
  }
  if (!status.found) {
    return <div className="intake-card"><p className="intake-error" role="alert">Run not found for {slug}.</p></div>;
  }

  const c = status.cost;
  const ch = status.chapters;
  const progressPct = ch && ch.total > 0 ? Math.round((ch.completed / ch.total) * 100) : 0;

  return (
    <div className="intake-card">
      <h2 className="intake-card-title">Run cockpit — {status.slug}</h2>

      <dl className="intake-estimate">
        <div className="intake-estimate-row">
          <dt>Phase</dt>
          <dd>{status.phase ?? '—'} · {status.phase_status ?? '—'}</dd>
        </div>
        <div className="intake-estimate-row">
          <dt>Publication</dt>
          <dd>{status.publication_status ?? 'draft'}</dd>
        </div>
        {c && (
          <div className="intake-estimate-row">
            <dt>Spend</dt>
            <dd className={c.over_book_cap ? 'intake-validation-error' : undefined}>
              ${c.book_spend_usd.toFixed(2)}
              {c.book_cap_active ? ` / $${c.book_cap_usd.toFixed(2)} cap` : ''}
            </dd>
          </div>
        )}
      </dl>

      {ch && ch.total > 0 && (
        <div className="intake-progress">
          <progress
            className="intake-progress-bar"
            value={ch.completed}
            max={ch.total}
            aria-label={`Chapters ${ch.completed} of ${ch.total} complete (${progressPct}%)`}
          />
          <p className="intake-hint">
            {ch.completed} / {ch.total} chapters{ch.failed > 0 ? ` · ${ch.failed} failed` : ''}
          </p>
        </div>
      )}

      {status.last_error && !status.at_human_gate && (
        <p className="intake-validation-warn" role="status">Last note: {status.last_error}</p>
      )}

      {status.at_human_gate && status.gate && (
        <div className="intake-gatecard">
          <p className="intake-gate-title">Waiting for you</p>
          <p className="intake-gate-label">{status.gate.label}</p>
          <div className="intake-actions">
            <button
              className="intake-btn intake-btn--primary"
              type="button"
              disabled={approving}
              onClick={() => approve('resume')}
            >
              {approving ? 'Resuming…' : 'Approve & continue'}
            </button>
          </div>
        </div>
      )}

      {error && <p className="intake-error" role="alert">{error}</p>}
    </div>
  );
}
