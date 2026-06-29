/**
 * HaltReview.tsx — the decision control for a pipeline halt.
 *
 * Renders the halt's artifacts as in-site reader links (read) plus a decision
 * form (approve & continue / request changes + notes). Saving POSTs to
 * /api/studio/halt-decision, which writes _system/halt-reviews.json — the file
 * the orchestrator reads to know whether the halt was approved.
 *
 * Mounted client:load so it server-renders (the read view survives a hydration
 * hiccup) and then becomes interactive. No inline styles — classes live in
 * studio-pipeline.css.
 */
import { useState } from 'react';

export interface HaltArtifactLink {
  label: string;
  href: string;
  exists: boolean;
}
export interface SavedDecision {
  decision: 'approved' | 'changes';
  notes?: string;
  ts?: string;
}

interface Props {
  slug: string;
  haltId: string;
  artifacts: HaltArtifactLink[];
  saved: SavedDecision | null;
}

type Status = 'idle' | 'saving' | 'saved' | 'error';

export default function HaltReview({ slug, haltId, artifacts, saved }: Props) {
  const [decision, setDecision] = useState<'approved' | 'changes'>(saved?.decision ?? 'approved');
  const [notes, setNotes] = useState(saved?.notes ?? '');
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');
  const [savedAt, setSavedAt] = useState(saved?.ts ?? '');

  const present = artifacts.filter((a) => a.exists);
  const missing = artifacts.filter((a) => !a.exists);
  const needsNote = decision === 'changes' && !notes.trim();

  async function save() {
    if (needsNote) {
      setError('Add a note describing the changes you want.');
      setStatus('error');
      return;
    }
    setStatus('saving');
    setError('');
    try {
      const res = await fetch('/api/studio/halt-decision', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, haltId, decision, notes }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok && j?.ok) {
        setStatus('saved');
        setSavedAt(j.data?.saved?.ts ?? new Date().toISOString());
        return;
      }
      setError(j?.error ?? 'Save failed.');
      setStatus('error');
    } catch {
      setError('Save failed — check the server.');
      setStatus('error');
    }
  }

  return (
    <div className="halt-review">
      <div className="halt-review-artifacts">
        <span className="halt-review-artifacts-label">Read before deciding</span>
        <ul className="halt-review-artifact-list">
          {present.map((a) => (
            <li key={a.href}>
              <a className="halt-review-artifact" href={a.href}>
                <i className="fa-regular fa-file-lines" aria-hidden="true"></i> {a.label}
              </a>
            </li>
          ))}
          {missing.map((a) => (
            <li key={a.label}>
              <span className="halt-review-artifact is-missing">
                <i className="fa-regular fa-file" aria-hidden="true"></i> {a.label}
                <span className="halt-review-artifact-hint">not produced yet</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <fieldset className="halt-review-decision">
        <legend>Your decision</legend>
        <label className={`halt-review-opt${decision === 'approved' ? ' is-on' : ''}`}>
          <input
            type="radio"
            name="halt-decision"
            checked={decision === 'approved'}
            onChange={() => { setDecision('approved'); setStatus('idle'); }}
          />
          <span><strong>Approve &amp; continue</strong> — the pipeline may proceed past this gate.</span>
        </label>
        <label className={`halt-review-opt${decision === 'changes' ? ' is-on' : ''}`}>
          <input
            type="radio"
            name="halt-decision"
            checked={decision === 'changes'}
            onChange={() => { setDecision('changes'); setStatus('idle'); }}
          />
          <span><strong>Request changes</strong> — note what needs correcting before continuing.</span>
        </label>
        <textarea
          className="halt-review-notes"
          placeholder={decision === 'changes' ? 'What should change before this gate is cleared?' : 'Optional notes for the record'}
          value={notes}
          maxLength={8000}
          onChange={(e) => { setNotes(e.target.value); setStatus('idle'); }}
        />
      </fieldset>

      <div className="halt-review-actions">
        <button
          type="button"
          className="lib-edit-btn lib-edit-btn-primary"
          onClick={save}
          disabled={status === 'saving' || needsNote}
        >
          <i className="fa-solid fa-check" aria-hidden="true"></i>{' '}
          {status === 'saving' ? 'Saving…' : 'Save decision'}
        </button>
        <span className="lib-facts-status" data-state={status} aria-live="polite">
          {status === 'saved' && 'Saved'}
          {status === 'error' && error}
        </span>
        {savedAt && status !== 'error' && (
          <span className="halt-review-saved-at">Last saved {new Date(savedAt).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
}
