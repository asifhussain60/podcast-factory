/**
 * NewContentForm — Step 1 of the /intake page (WC8 Slice 6b).
 *
 * Collects: slug, category, title, sourceHint. POSTs to /api/intake/create.
 * On success, notifies the parent via onCreated so the editorial panel can load.
 *
 * Validation: slug checked client-side before submit; server repeats validation.
 * Dependency-free: no Zod, no React Hook Form — the form is simple enough to
 * hand-roll and keeping dependencies minimal is the standing preference.
 */
import { useState } from 'react';

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const CATEGORIES = [
  { value: 'books',      label: 'Book' },
  { value: 'articles',   label: 'Article' },
  { value: 'documents',  label: 'Document' },
  { value: 'lectures',   label: 'Lecture' },
  { value: 'interviews', label: 'Interview' },
  { value: 'letters',    label: 'Letter' },
  { value: 'asbaaq',     label: 'Sabaq (lesson)' },
];

interface CreateResult {
  slug: string;
  category: string;
  title: string;
  path: string;
}

interface Props {
  onCreated?: (result: CreateResult) => void;
  onCleared?: () => void;
}

export default function NewContentForm({ onCreated, onCleared }: Props) {
  const [slug, setSlug]           = useState('');
  const [category, setCategory]   = useState('books');
  const [title, setTitle]         = useState('');
  const [sourceHint, setSourceHint] = useState('');
  const [slugError, setSlugError] = useState('');
  const [serverError, setServerError] = useState('');
  const [created, setCreated]     = useState<CreateResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validateSlug(v: string): string {
    if (!v) return 'Slug is required';
    if (!SLUG_RE.test(v)) return 'Lowercase letters, digits, and hyphens only (e.g. my-book-title)';
    return '';
  }

  function handleSlugChange(v: string) {
    // Auto-convert spaces and underscores to hyphens, strip other invalid chars.
    const clean = v.toLowerCase().replace(/[\s_]+/g, '-').replace(/[^a-z0-9-]/g, '');
    setSlug(clean);
    setSlugError(validateSlug(clean));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validateSlug(slug);
    if (err) { setSlugError(err); return; }
    if (!title.trim()) return;

    setSubmitting(true);
    setServerError('');
    try {
      const r = await fetch('/api/intake/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, category, title: title.trim(), sourceHint: sourceHint.trim() }),
      });
      const json = await r.json();
      if (!r.ok || !json.ok) {
        setServerError(json.error ?? `Server error ${r.status}`);
        return;
      }
      const result: CreateResult = json.data;
      setCreated(result);
      onCreated?.(result);
    } catch (e) {
      setServerError(`Network error: ${String(e)}`);
    } finally {
      setSubmitting(false);
    }
  }

  function handleReset() {
    setCreated(null);
    setSlug(''); setCategory('books'); setTitle(''); setSourceHint('');
    setSlugError(''); setServerError('');
    onCleared?.();
  }

  if (created) {
    return (
      <div className="intake-card">
        <div className="intake-success">
          <p className="intake-success-title">"{created.title}" scaffolded</p>
          <p className="intake-success-path">{created.path}</p>
          <p className="intake-success-next">
            Set canonical editorial decisions in the panel on the right, then ask Claude Code
            to run intake for this content.
          </p>
        </div>
        <div className="intake-actions">
          <button className="intake-btn intake-btn--ghost" onClick={handleReset}>
            Add another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="intake-card">
      <h2 className="intake-card-title">New content</h2>
      <form onSubmit={handleSubmit} noValidate>

        <div className="intake-field">
          <label className="intake-label" htmlFor="intake-title">
            Title <span>(required)</span>
          </label>
          <input
            id="intake-title"
            className="intake-input"
            type="text"
            placeholder="e.g. Kitab al-Riyad"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div className="intake-field">
          <label className="intake-label" htmlFor="intake-slug">
            Slug <span>(required — auto-filled from title)</span>
          </label>
          <input
            id="intake-slug"
            className={`intake-input${slugError ? ' error' : ''}`}
            type="text"
            placeholder="e.g. kitab-al-riyad"
            value={slug || (title ? title.toLowerCase().replace(/[\s_]+/g, '-').replace(/[^a-z0-9-]/g, '') : '')}
            onChange={(e) => handleSlugChange(e.target.value)}
            required
          />
          {slugError && <p className="intake-error">{slugError}</p>}
          <p className="intake-hint">Lowercase, hyphens, no spaces. Used as the folder name and branch slug.</p>
        </div>

        <div className="intake-field">
          <label className="intake-label" htmlFor="intake-category">
            Category <span>(required)</span>
          </label>
          <select
            id="intake-category"
            className="intake-select"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div className="intake-field">
          <label className="intake-label" htmlFor="intake-source">
            Source hint <span>(optional)</span>
          </label>
          <textarea
            id="intake-source"
            className="intake-textarea"
            placeholder="e.g. PDF at content/drafts/books/…, YouTube URL, local audio files"
            value={sourceHint}
            onChange={(e) => setSourceHint(e.target.value)}
            rows={2}
          />
          <p className="intake-hint">Where the source material lives — helps Claude find it on resume.</p>
        </div>

        {serverError && <p className="intake-error">{serverError}</p>}

        <div className="intake-actions">
          <button
            className="intake-btn intake-btn--primary"
            type="submit"
            disabled={submitting || !!slugError || !title.trim()}
          >
            {submitting ? 'Creating…' : 'Create workshop folder'}
          </button>
        </div>
      </form>
    </div>
  );
}
