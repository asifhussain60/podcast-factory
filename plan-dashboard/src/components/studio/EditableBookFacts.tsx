/**
 * EditableBookFacts.tsx — the "About this book" fact list, editable in place.
 *
 * Safe display fields (title, short_name, author, original_title, category) become
 * inputs in Edit mode with client-side validation; Save persists each changed field
 * via POST /api/studio/book-meta (a line-level meta.yml patch — preserves the rest of
 * the file). SLUG is structural identity (folder + git branch + many refs) and is
 * read-only here; renaming is a separate guarded flow. File-link fields render as links.
 *
 * Mirrors ContentLevelSelector's fetch/status pattern. No inline styles —
 * classes live in studio-pipeline.css / library.css.
 */
import { useState } from 'react';

export interface FactProp {
  key: string;
  label: string;
  value: string;
  editable: boolean;
  control?: 'text' | 'select';
  options?: string[];
  required?: boolean;
  maxLen?: number;
  structural?: boolean;
  link?: { kind: 'file' | 'dir' | 'missing'; name: string; href: string | null; icon: string };
}

interface Props {
  slug: string;
  facts: FactProp[];
}

type Status = 'idle' | 'saving' | 'saved' | 'error';

function validate(f: FactProp, v: string): string | null {
  const name = f.label;
  if (f.required && !v.trim()) return `${name} cannot be empty`;
  if (f.maxLen && v.length > f.maxLen) return `${name} is too long (max ${f.maxLen})`;
  if (/[\r\n]/.test(v)) return `${name} must be a single line`;
  return null;
}

export default function EditableBookFacts({ slug, facts }: Props) {
  const editableKeys = facts.filter((f) => f.editable).map((f) => f.key);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>(
    () => Object.fromEntries(facts.filter((f) => f.editable).map((f) => [f.key, f.value])),
  );
  const [saved, setSaved] = useState<Record<string, string>>(
    () => Object.fromEntries(facts.filter((f) => f.editable).map((f) => [f.key, f.value])),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<Status>('idle');

  function set(key: string, v: string) {
    setDraft((d) => ({ ...d, [key]: v }));
    const f = facts.find((x) => x.key === key)!;
    const err = validate(f, v);
    setErrors((e) => ({ ...e, [key]: err ?? '' }));
  }

  function cancel() {
    setDraft({ ...saved });
    setErrors({});
    setStatus('idle');
    setEditing(false);
  }

  async function save() {
    // Validate all editable fields up front.
    const errs: Record<string, string> = {};
    for (const key of editableKeys) {
      const f = facts.find((x) => x.key === key)!;
      const err = validate(f, draft[key] ?? '');
      if (err) errs[key] = err;
    }
    setErrors(errs);
    if (Object.values(errs).some(Boolean)) { setStatus('error'); return; }

    const changed = editableKeys.filter((k) => (draft[k] ?? '') !== (saved[k] ?? ''));
    if (changed.length === 0) { setEditing(false); setStatus('idle'); return; }

    setStatus('saving');
    try {
      for (const field of changed) {
        const res = await fetch('/api/studio/book-meta', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ slug, field, value: draft[field] ?? '' }),
        });
        if (!res.ok) {
          const msg = await res.json().catch(() => ({}));
          setErrors((e) => ({ ...e, [field]: msg?.error ?? 'Save failed' }));
          setStatus('error');
          return;
        }
      }
      setSaved({ ...saved, ...Object.fromEntries(changed.map((k) => [k, draft[k] ?? ''])) });
      setStatus('saved');
      setEditing(false);
    } catch {
      setStatus('error');
    }
  }

  return (
    <div className="lib-facts-editor">
      <div className="lib-facts-editbar">
        {!editing ? (
          <button type="button" className="lib-edit-btn" onClick={() => { setEditing(true); setStatus('idle'); }}>
            <i className="fa-solid fa-pen" aria-hidden="true"></i> Edit details
          </button>
        ) : (
          <>
            <button type="button" className="lib-edit-btn lib-edit-btn-primary" onClick={save} disabled={status === 'saving'}>
              <i className="fa-solid fa-check" aria-hidden="true"></i> {status === 'saving' ? 'Saving…' : 'Save'}
            </button>
            <button type="button" className="lib-edit-btn lib-edit-btn-ghost" onClick={cancel} disabled={status === 'saving'}>Cancel</button>
          </>
        )}
        <span className="lib-facts-status" data-state={status} aria-live="polite">
          {status === 'saved' && 'Saved'}
          {status === 'error' && 'Fix the highlighted fields'}
        </span>
      </div>

      <dl className="lib-facts">
        {facts.map((f) => (
          <div className="lib-fact" key={f.key}>
            <dt>{f.label}{f.structural && <span className="lib-fact-tag" title="Identity — rename is a separate guarded flow">identity</span>}</dt>
            <dd>
              {editing && f.editable ? (
                <div className="lib-fact-edit">
                  {f.control === 'select' ? (
                    <select className="lib-fact-input" value={draft[f.key] ?? ''} onChange={(e) => set(f.key, e.target.value)}>
                      {(f.options ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input
                      className={`lib-fact-input${errors[f.key] ? ' is-invalid' : ''}`}
                      type="text"
                      value={draft[f.key] ?? ''}
                      maxLength={f.maxLen}
                      aria-invalid={errors[f.key] ? true : undefined}
                      onChange={(e) => set(f.key, e.target.value)}
                    />
                  )}
                  {errors[f.key] && <span className="lib-fact-error">{errors[f.key]}</span>}
                </div>
              ) : f.link ? (
                f.link.href ? (
                  <a className="lib-fact-file" href={f.link.href} target="_blank" rel="noreferrer">
                    <i className={f.link.icon} aria-hidden="true"></i> {f.link.name}
                  </a>
                ) : (
                  <span className={`lib-fact-file is-static${f.link.kind === 'missing' ? ' is-missing' : ''}`}>
                    <i className={f.link.icon} aria-hidden="true"></i> {f.link.name}
                    <span className="lib-fact-file-hint">{f.link.kind === 'dir' ? 'folder' : 'missing'}</span>
                  </span>
                )
              ) : (
                (editing && f.editable ? draft[f.key] : saved[f.key] ?? f.value) || <span className="lib-fact-empty">—</span>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
