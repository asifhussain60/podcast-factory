/**
 * ChapterEditor — review-mode editor over the rendered chapter.
 *
 * One toggle (pencil icon in header or `e` key) turns every block in
 * .prose-body into a contenteditable region. On mount we snapshot the
 * original plain text of each block keyed by a stable id derived from
 * tag + position. As edits happen we diff current-vs-original; the
 * right-rail panel lists every change with one-click revert.
 *
 * "Copy patch" emits a parseable markdown patch including base-sha so
 * Claude can apply it cleanly to the source .txt and refuse if the
 * source has drifted since the snapshot.
 *
 * Annotations: select text + ⌘⇧A drops a margin note that travels in
 * the patch as `## note#N` without changing the prose.
 *
 * AI-assist: with edit mode ON, selecting text reveals a sparkle
 * button. Click → Gemini Flash returns 3 rewrite options as cards;
 * accept replaces the selection, reject discards.
 */

import { useEffect, useMemo, useRef, useState } from 'react';

interface Props {
  book: string;
  chapterSlug: string;
  chapterTitle: string;
  /** Raw source .txt content. Used for base-sha and for the patch header. */
  sourceText: string;
}

interface BlockSnapshot {
  id: string;
  tag: string;       // p, h2, h3, li, blockquote
  original: string;
  current: string;
  deleted: boolean;
}

interface Annotation {
  id: string;
  blockId: string;
  selection: string;
  note: string;
}

interface RewriteSuggestion {
  rect: DOMRect;
  selection: string;
  blockId: string;
  range: Range;
  loading: boolean;
  options: string[];
  error?: string;
}

async function sha1Hex(s: string): Promise<string> {
  const buf = new TextEncoder().encode(s);
  const hash = await crypto.subtle.digest('SHA-1', buf);
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function assignBlockIds(): HTMLElement[] {
  const article = document.querySelector('.prose-body');
  if (!article) return [];
  const blocks = Array.from(article.querySelectorAll('p, h1, h2, h3, h4, li, blockquote')) as HTMLElement[];
  const counters: Record<string, number> = {};
  const headingStack: string[] = [];
  blocks.forEach((el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'h1' || tag === 'h2' || tag === 'h3' || tag === 'h4') {
      const slug = el.id || el.textContent?.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40) || tag;
      el.dataset.editorId = `${tag}:${slug}`;
      headingStack.length = 0;
      headingStack.push(slug);
      return;
    }
    counters[tag] = (counters[tag] ?? 0) + 1;
    const ctx = headingStack[0] ?? 'top';
    el.dataset.editorId = `${tag}:${ctx}#${counters[tag]}`;
  });
  return blocks;
}

function plainText(el: HTMLElement): string {
  return (el.innerText || '').replace(/\s+/g, ' ').trim();
}

export default function ChapterEditor({ book, chapterSlug, chapterTitle, sourceText }: Props) {
  const [editing, setEditing] = useState(false);
  const [snapshots, setSnapshots] = useState<Map<string, BlockSnapshot>>(new Map());
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [panelOpen, setPanelOpen] = useState(true);
  const [baseSha, setBaseSha] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [annotateBlockId, setAnnotateBlockId] = useState<string | null>(null);
  const [annotateText, setAnnotateText] = useState('');
  const [annotateSelection, setAnnotateSelection] = useState('');
  const [rewrite, setRewrite] = useState<RewriteSuggestion | null>(null);
  const [rewriteMode, setRewriteMode] = useState<'clarify' | 'tighten' | 'simplify' | 'formal'>('clarify');
  const observerRef = useRef<MutationObserver | null>(null);

  // Compute base sha once.
  useEffect(() => {
    sha1Hex(sourceText).then((h) => setBaseSha(h.slice(0, 12)));
  }, [sourceText]);

  // Init snapshots + assign ids on mount.
  useEffect(() => {
    const blocks = assignBlockIds();
    const map = new Map<string, BlockSnapshot>();
    blocks.forEach((b) => {
      const id = b.dataset.editorId!;
      const txt = plainText(b);
      map.set(id, { id, tag: b.tagName.toLowerCase(), original: txt, current: txt, deleted: false });
    });
    setSnapshots(map);
  }, []);

  // Toggle contenteditable + ring class on blocks when editing flips.
  useEffect(() => {
    const blocks = Array.from(document.querySelectorAll<HTMLElement>('.prose-body [data-editor-id]'));
    blocks.forEach((b) => {
      if (editing) {
        b.setAttribute('contenteditable', 'true');
        b.classList.add('editor-block');
        b.setAttribute('spellcheck', 'true');
      } else {
        b.removeAttribute('contenteditable');
        b.classList.remove('editor-block', 'editor-block-changed', 'editor-block-deleted');
        b.removeAttribute('spellcheck');
      }
    });
    document.documentElement.classList.toggle('chapter-editor-on', editing);
    return () => {
      blocks.forEach((b) => b.removeAttribute('contenteditable'));
    };
  }, [editing]);

  // Live diff via input events + MutationObserver. We listen at the
  // article level once so adding/removing blocks doesn't lose state.
  useEffect(() => {
    if (!editing) return;
    const article = document.querySelector('.prose-body');
    if (!article) return;

    const onInput = (e: Event) => {
      const target = (e.target as HTMLElement).closest('[data-editor-id]') as HTMLElement | null;
      if (!target) return;
      const id = target.dataset.editorId!;
      const text = plainText(target);
      setSnapshots((prev) => {
        const next = new Map(prev);
        const snap = next.get(id);
        if (!snap) return prev;
        const changed = text !== snap.original;
        target.classList.toggle('editor-block-changed', changed);
        next.set(id, { ...snap, current: text });
        return next;
      });
    };
    article.addEventListener('input', onInput);
    return () => article.removeEventListener('input', onInput);
  }, [editing]);

  // Keyboard: e toggles, ⌘⇧A annotates selection.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      const inEditable = tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable;
      if (!inEditable && e.key === 'e' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        setEditing((v) => !v);
      }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'A' || e.key === 'a')) {
        e.preventDefault();
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed) return;
        const block = (sel.anchorNode?.parentElement?.closest('[data-editor-id]')) as HTMLElement | null;
        if (!block) return;
        setAnnotateBlockId(block.dataset.editorId!);
        setAnnotateSelection(sel.toString().slice(0, 200));
        setAnnotateText('');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Show floating sparkle on selection (edit mode only).
  useEffect(() => {
    if (!editing) return;
    const onSelChange = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) { setRewrite(null); return; }
      const text = sel.toString().trim();
      if (text.length < 12) return;
      const anchorEl = sel.anchorNode?.parentElement?.closest('[data-editor-id]') as HTMLElement | null;
      if (!anchorEl) return;
      const range = sel.getRangeAt(0).cloneRange();
      const rect = range.getBoundingClientRect();
      setRewrite({
        rect,
        selection: text,
        blockId: anchorEl.dataset.editorId!,
        range,
        loading: false,
        options: [],
      });
    };
    document.addEventListener('selectionchange', onSelChange);
    return () => document.removeEventListener('selectionchange', onSelChange);
  }, [editing]);

  const askRewrite = async () => {
    if (!rewrite) return;
    setRewrite({ ...rewrite, loading: true, options: [] });
    try {
      const block = document.querySelector(`[data-editor-id="${rewrite.blockId}"]`) as HTMLElement | null;
      const context = block ? plainText(block) : '';
      const res = await fetch('/api/ai/rewrite', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: rewrite.selection, mode: rewriteMode, context }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? `AI ${res.status}`);
      setRewrite((r) => r ? { ...r, loading: false, options: data.options ?? [] } : r);
    } catch (e) {
      setRewrite((r) => r ? { ...r, loading: false, error: (e as Error).message } : r);
    }
  };

  const acceptRewrite = (opt: string) => {
    if (!rewrite) return;
    try {
      rewrite.range.deleteContents();
      rewrite.range.insertNode(document.createTextNode(opt));
    } catch { /* range invalidated */ }
    // Trigger input event manually so snapshots update.
    const block = document.querySelector(`[data-editor-id="${rewrite.blockId}"]`) as HTMLElement | null;
    if (block) block.dispatchEvent(new InputEvent('input', { bubbles: true }));
    setRewrite(null);
    window.getSelection()?.removeAllRanges();
  };

  const revert = (id: string) => {
    const snap = snapshots.get(id);
    if (!snap) return;
    const block = document.querySelector<HTMLElement>(`[data-editor-id="${id}"]`);
    if (block) {
      block.textContent = snap.original;
      block.classList.remove('editor-block-changed', 'editor-block-deleted');
    }
    setSnapshots((prev) => {
      const n = new Map(prev);
      n.set(id, { ...snap, current: snap.original, deleted: false });
      return n;
    });
  };

  const toggleDelete = (id: string) => {
    const snap = snapshots.get(id);
    if (!snap) return;
    const willDelete = !snap.deleted;
    const block = document.querySelector<HTMLElement>(`[data-editor-id="${id}"]`);
    if (block) block.classList.toggle('editor-block-deleted', willDelete);
    setSnapshots((prev) => {
      const n = new Map(prev);
      n.set(id, { ...snap, deleted: willDelete });
      return n;
    });
  };

  const saveAnnotation = () => {
    if (!annotateBlockId || !annotateText.trim()) return;
    setAnnotations((a) => [...a, {
      id: `note-${Date.now()}`,
      blockId: annotateBlockId,
      selection: annotateSelection,
      note: annotateText.trim(),
    }]);
    setAnnotateBlockId(null);
    setAnnotateText('');
    setAnnotateSelection('');
  };

  const changes = useMemo(() => {
    return Array.from(snapshots.values()).filter((s) => s.deleted || s.current !== s.original);
  }, [snapshots]);

  const buildPatch = (): string => {
    const lines: string[] = [];
    lines.push(`# CHAPTER EDIT — ${book} / ${chapterSlug}`);
    lines.push(`# title: ${chapterTitle}`);
    lines.push(`# base-sha: ${baseSha}`);
    lines.push(`# edits: ${changes.length} · annotations: ${annotations.length}`);
    lines.push('');
    let n = 0;
    for (const c of changes) {
      n += 1;
      if (c.deleted) {
        lines.push(`## edit#${n} — block "${c.id}" (${c.tag}) — DELETE`);
        lines.push('- ' + c.original.replace(/\n/g, ' '));
      } else {
        lines.push(`## edit#${n} — block "${c.id}" (${c.tag})`);
        lines.push('- ' + c.original.replace(/\n/g, ' '));
        lines.push('+ ' + c.current.replace(/\n/g, ' '));
      }
      lines.push('');
    }
    let m = 0;
    for (const a of annotations) {
      m += 1;
      lines.push(`## note#${m} — block "${a.blockId}"`);
      if (a.selection) lines.push(`> selection: "${a.selection}"`);
      lines.push('  ' + a.note);
      lines.push('');
    }
    return lines.join('\n');
  };

  const copyPatch = async () => {
    const patch = buildPatch();
    try {
      await navigator.clipboard.writeText(patch);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* ignore */ }
  };

  return (
    <>
      {/* Header toggle — fixed top-right under the existing legend pill */}
      <button
        type="button"
        onClick={() => setEditing((v) => !v)}
        className={
          'fixed top-3 right-[78px] z-40 inline-flex items-center gap-1.5 rounded-full border-2 px-3 py-1.5 text-[12px] font-medium shadow-sm transition ' +
          (editing
            ? 'border-emerald-500 bg-emerald-50 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-100'
            : 'border-stone-300 bg-white text-stone-700 hover:border-emerald-400 hover:text-emerald-700 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-200')
        }
        title="Toggle edit mode (e)"
        aria-pressed={editing}
      >
        <span aria-hidden>✎</span>
        <span>{editing ? 'Editing' : 'Edit'}</span>
        {editing && changes.length > 0 && (
          <span className="rounded-full bg-emerald-600 px-1.5 py-0 text-[9px] font-bold uppercase tracking-wider text-white">
            {changes.length}{annotations.length ? `+${annotations.length}` : ''}
          </span>
        )}
      </button>

      {/* Floating sparkle near selection (edit mode only) */}
      {editing && rewrite && rewrite.options.length === 0 && !rewrite.loading && (
        <button
          onClick={askRewrite}
          className="fixed z-50 inline-flex items-center gap-1 rounded-full border border-amber-400 bg-white px-2 py-1 text-[11px] font-medium text-amber-800 shadow-lg hover:bg-amber-50 dark:bg-stone-800 dark:text-amber-200"
          style={{ top: rewrite.rect.top + window.scrollY - 36, left: rewrite.rect.left + window.scrollX }}
          title="Suggest rewrites (Gemini)"
        >
          <span>✦</span> Rewrite
          <select
            value={rewriteMode}
            onChange={(e) => { e.stopPropagation(); setRewriteMode(e.target.value as any); }}
            onClick={(e) => e.stopPropagation()}
            className="ml-1 rounded border border-amber-300 bg-white px-1 py-0 text-[10px]"
          >
            <option value="clarify">clarify</option>
            <option value="tighten">tighten</option>
            <option value="simplify">simplify</option>
            <option value="formal">formal</option>
          </select>
        </button>
      )}

      {/* Rewrite options card */}
      {editing && rewrite && (rewrite.loading || rewrite.options.length > 0 || rewrite.error) && (
        <div
          className="fixed z-50 w-[440px] rounded-lg border border-stone-200 bg-white p-3 shadow-2xl dark:border-stone-700 dark:bg-stone-800"
          style={{ top: rewrite.rect.bottom + window.scrollY + 8, left: Math.min(rewrite.rect.left + window.scrollX, window.scrollX + window.innerWidth - 460) }}
        >
          <div className="mb-2 flex items-center justify-between">
            <div className="font-ui text-[10px] font-semibold uppercase tracking-wider text-stone-500">Rewrite · {rewriteMode}</div>
            <button onClick={() => setRewrite(null)} className="text-stone-400 hover:text-stone-900 dark:hover:text-stone-100">✕</button>
          </div>
          {rewrite.loading && <div className="text-[12px] text-stone-500">Asking Gemini Flash…</div>}
          {rewrite.error && <div className="text-[12px] text-rose-600">Failed: {rewrite.error}</div>}
          <div className="space-y-2">
            {rewrite.options.map((opt, i) => (
              <div key={i} className="rounded border border-stone-200 bg-stone-50/60 p-2 text-[13px] leading-snug dark:border-stone-700 dark:bg-stone-900/40">
                <div className="text-stone-800 dark:text-stone-100">{opt}</div>
                <button onClick={() => acceptRewrite(opt)} className="mt-1.5 rounded bg-amber-600 px-2 py-0.5 text-[10px] font-semibold text-white hover:bg-amber-700">
                  Accept
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Annotation composer */}
      {annotateBlockId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/30" onClick={(e) => { if (e.target === e.currentTarget) setAnnotateBlockId(null); }}>
          <div className="w-[460px] rounded-lg border border-stone-200 bg-white p-4 shadow-2xl dark:border-stone-700 dark:bg-stone-800">
            <div className="mb-2 font-ui text-[10px] font-semibold uppercase tracking-wider text-stone-500">Annotation</div>
            {annotateSelection && (
              <div className="mb-2 rounded border-l-2 border-amber-400 bg-amber-50 px-2 py-1 text-[12px] italic text-stone-700 dark:bg-amber-900/20 dark:text-stone-200">
                "{annotateSelection}"
              </div>
            )}
            <textarea
              value={annotateText}
              onChange={(e) => setAnnotateText(e.target.value)}
              autoFocus
              rows={3}
              placeholder="e.g. is 'Sayyidina' the right transliteration here?"
              className="w-full rounded border border-stone-300 bg-white px-2 py-1 text-[13px] focus:border-amber-400 focus:outline-none dark:border-stone-600 dark:bg-stone-900"
            />
            <div className="mt-2 flex justify-end gap-2">
              <button onClick={() => setAnnotateBlockId(null)} className="rounded px-3 py-1 text-[12px] text-stone-500 hover:text-stone-900">Cancel</button>
              <button onClick={saveAnnotation} className="rounded bg-emerald-600 px-3 py-1 text-[12px] font-semibold text-white hover:bg-emerald-700">Save note</button>
            </div>
          </div>
        </div>
      )}

      {/* Changes panel — bottom-left floating, only in edit mode */}
      {editing && (
        <div className="fixed bottom-6 left-6 z-30 w-[340px] rounded-xl border border-stone-200 bg-white shadow-2xl dark:border-stone-700 dark:bg-stone-800">
          <button
            onClick={() => setPanelOpen((v) => !v)}
            className="flex w-full items-center justify-between rounded-t-xl border-b border-stone-200 px-3 py-2 font-ui text-[11px] font-semibold uppercase tracking-wider text-stone-600 dark:border-stone-700 dark:text-stone-300"
          >
            <span>Changes <span className="ml-1 rounded bg-emerald-100 px-1.5 py-0 text-[10px] text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200">{changes.length}</span>{annotations.length > 0 && <span className="ml-1 rounded bg-amber-100 px-1.5 py-0 text-[10px] text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{annotations.length} notes</span>}</span>
            <span>{panelOpen ? '−' : '+'}</span>
          </button>
          {panelOpen && (
            <div className="max-h-[40vh] overflow-y-auto p-3 text-[12px]">
              {changes.length === 0 && annotations.length === 0 && (
                <div className="text-stone-400">
                  Click any paragraph and edit. Select text + <kbd className="rounded border px-1">⌘⇧A</kbd> to drop a note. Select text in edit mode for a Gemini rewrite.
                </div>
              )}
              {changes.map((c) => (
                <div key={c.id} className="mb-2 border-l-2 border-emerald-400 pl-2">
                  <div className="font-ui text-[9px] uppercase tracking-wider text-stone-500">{c.tag} · {c.id}</div>
                  {c.deleted ? (
                    <div className="text-stone-500 line-through">{c.original.slice(0, 100)}{c.original.length > 100 ? '…' : ''}</div>
                  ) : (
                    <>
                      <div className="text-rose-700 dark:text-rose-300">− {c.original.slice(0, 70)}{c.original.length > 70 ? '…' : ''}</div>
                      <div className="text-emerald-700 dark:text-emerald-300">+ {c.current.slice(0, 70)}{c.current.length > 70 ? '…' : ''}</div>
                    </>
                  )}
                  <div className="mt-0.5 flex gap-2 text-[10px]">
                    <button onClick={() => revert(c.id)} className="text-stone-500 hover:text-stone-900">revert</button>
                    <button onClick={() => toggleDelete(c.id)} className="text-stone-500 hover:text-rose-700">{c.deleted ? 'undelete' : 'delete'}</button>
                  </div>
                </div>
              ))}
              {annotations.map((a) => (
                <div key={a.id} className="mb-2 border-l-2 border-amber-400 pl-2">
                  <div className="font-ui text-[9px] uppercase tracking-wider text-stone-500">note · {a.blockId}</div>
                  {a.selection && <div className="italic text-stone-500">"{a.selection.slice(0, 60)}…"</div>}
                  <div className="text-stone-700 dark:text-stone-200">{a.note}</div>
                  <button onClick={() => setAnnotations((all) => all.filter((x) => x.id !== a.id))} className="text-[10px] text-stone-500 hover:text-rose-700">remove</button>
                </div>
              ))}
            </div>
          )}
          {(changes.length > 0 || annotations.length > 0) && (
            <div className="border-t border-stone-200 p-3 dark:border-stone-700">
              <button
                onClick={copyPatch}
                className="w-full rounded bg-emerald-600 px-3 py-2 text-[12px] font-semibold text-white hover:bg-emerald-700"
              >
                {copied ? '✓ Copied — paste back to Claude' : `Copy patch (${changes.length} edit${changes.length === 1 ? '' : 's'}${annotations.length ? `, ${annotations.length} notes` : ''})`}
              </button>
              <div className="mt-1 font-ui text-[10px] text-stone-400">base-sha: {baseSha}</div>
            </div>
          )}
        </div>
      )}

      <style>{`
        html.chapter-editor-on .prose-body [data-editor-id] {
          outline: 1px dashed transparent;
          outline-offset: 4px;
          border-radius: 3px;
          transition: outline-color 120ms, background-color 120ms;
        }
        html.chapter-editor-on .prose-body [data-editor-id]:hover {
          outline-color: rgba(180, 140, 50, 0.35);
          cursor: text;
        }
        html.chapter-editor-on .prose-body [data-editor-id]:focus {
          outline: 2px solid #b58a2a;
          outline-offset: 4px;
          background: rgba(180, 140, 50, 0.04);
        }
        .editor-block-changed {
          background: linear-gradient(to right, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.02));
          border-left: 2px solid #10b981;
          padding-left: 0.6em;
          margin-left: -0.6em;
        }
        .editor-block-deleted {
          opacity: 0.45;
          text-decoration: line-through;
          text-decoration-color: rgba(225, 29, 72, 0.6);
        }
      `}</style>
    </>
  );
}
