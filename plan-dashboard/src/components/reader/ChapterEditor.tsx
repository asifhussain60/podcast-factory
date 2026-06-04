/**
 * ChapterEditor — ambient inline review-editor.
 *
 * No edit-mode toggle. Every block in .prose-body is always click-to-
 * edit: hover surfaces a subtle ring, click promotes the block to a
 * carved-border editor, click outside (blur) commits + visually marks
 * changes in the user-chosen edit-highlight color.
 *
 * Per-block hover chips (↺ revert / ✕ delete / ✦ rewrite) appear on
 * changed blocks so no panel trip is needed for common operations.
 *
 * Annotations: select + ⌘⇧A drops a margin note. Quoted selection
 * preserved. Uses the shared PopupCard modal.
 *
 * AI rewrite: selecting >12 chars surfaces a floating sparkle button
 * with mode picker. Click → Gemini Flash returns 3 cards in a
 * PopupCard.
 *
 * AI instruction: a separate ChapterInstructionPanel (right rail)
 * dispatches `chapter-editor:apply-edits` events that this island
 * consumes to apply block-level edits with a flash animation.
 *
 * Copy-patch: floating bottom-left panel summarises changes + emits
 * a base-sha-stamped markdown patch to the clipboard.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { STORAGE_KEYS } from '../../lib/reader/storage-keys';

interface Props {
  book: string;
  chapterSlug: string;
  chapterTitle: string;
  sourceText: string;
}

interface BlockSnapshot {
  id: string;
  tag: string;
  original: string;
  current: string;
  deleted: boolean;
  source: 'user' | 'ai';
}

interface Annotation {
  id: string;
  blockId: string;
  selection: string;
  note: string;
}

interface RewriteState {
  rect: DOMRect;
  selection: string;
  blockId: string;
  range: Range;
  loading: boolean;
  options: string[];
  error?: string;
}

interface PersistedEditorState {
  blocks: Array<{ id: string; current: string; deleted: boolean; source: 'user' | 'ai' }>;
  annotations: Annotation[];
}

const editorStateKey = (book: string, chapterSlug: string) => STORAGE_KEYS.chapterEditor(book, chapterSlug);

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function tokenizeWords(text: string): string[] {
  return text.trim().split(/\s+/).filter(Boolean);
}

function wordDiff(original: string, current: string): { op: 'same' | 'add' | 'del'; text: string }[] {
  const a = tokenizeWords(original);
  const b = tokenizeWords(current);
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0));

  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      if (a[i] === b[j]) dp[i][j] = dp[i + 1][j + 1] + 1;
      else dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const ops: { op: 'same' | 'add' | 'del'; text: string }[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      ops.push({ op: 'same', text: a[i] });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      ops.push({ op: 'del', text: a[i] });
      i += 1;
    } else {
      ops.push({ op: 'add', text: b[j] });
      j += 1;
    }
  }
  while (i < n) {
    ops.push({ op: 'del', text: a[i] });
    i += 1;
  }
  while (j < m) {
    ops.push({ op: 'add', text: b[j] });
    j += 1;
  }

  return ops;
}

function renderDiffHtml(original: string, current: string): string {
  const ops = wordDiff(original, current);
  return ops
    .map((x) => {
      const txt = escapeHtml(x.text);
      if (x.op === 'same') return `<span>${txt}</span>`;
      if (x.op === 'add') return `<mark class="edit-diff-add">${txt}</mark>`;
      return `<del class="edit-diff-del">${txt}</del>`;
    })
    .join(' ');
}

function paintBlockDiff(block: HTMLElement, snap: BlockSnapshot): void {
  if (snap.deleted) {
    block.classList.add('edit-block-deleted', 'edit-block-changed', 'edit-block-saved');
    block.textContent = snap.current || snap.original;
    return;
  }
  if (snap.current !== snap.original) {
    block.classList.add('edit-block-changed', 'edit-block-saved');
    block.innerHTML = renderDiffHtml(snap.original, snap.current);
  } else {
    block.classList.remove('edit-block-changed', 'edit-block-deleted', 'edit-block-saved');
    block.textContent = snap.current;
  }
}

async function sha1Hex(s: string): Promise<string> {
  const buf = new TextEncoder().encode(s);
  const hash = await crypto.subtle.digest('SHA-1', buf);
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function plainText(el: HTMLElement): string {
  return (el.innerText || '').replace(/\s+/g, ' ').trim();
}

function assignBlockIds(): HTMLElement[] {
  const article = document.querySelector('.prose-body');
  if (!article) return [];
  const blocks = Array.from(article.querySelectorAll('p, h1, h2, h3, h4, li, blockquote')) as HTMLElement[];
  const counters: Record<string, number> = {};
  let currentHeading = 'top';
  blocks.forEach((el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'h1' || tag === 'h2' || tag === 'h3' || tag === 'h4') {
      const slug = el.id || el.textContent?.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40) || tag;
      el.dataset.editorId = `${tag}:${slug}`;
      currentHeading = slug;
      return;
    }
    counters[tag] = (counters[tag] ?? 0) + 1;
    el.dataset.editorId = `${tag}:${currentHeading}#${counters[tag]}`;
  });
  return blocks;
}

function collectBlocksForAI(): { id: string; tag: string; text: string }[] {
  const blocks = Array.from(document.querySelectorAll<HTMLElement>('.prose-body [data-editor-id]'));
  return blocks.map((b) => ({ id: b.dataset.editorId!, tag: b.tagName.toLowerCase(), text: plainText(b) }));
}

export default function ChapterEditor({ book, chapterSlug, chapterTitle, sourceText }: Props) {
  const storageKey = editorStateKey(book, chapterSlug);
  const [snapshots, setSnapshots] = useState<Map<string, BlockSnapshot>>(new Map());
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [baseSha, setBaseSha] = useState('');
  const [copied, setCopied] = useState(false);
  const [annotateBlockId, setAnnotateBlockId] = useState<string | null>(null);
  const [annotateText, setAnnotateText] = useState('');
  const [annotateSelection, setAnnotateSelection] = useState('');
  const [rewrite, setRewrite] = useState<RewriteState | null>(null);
  const [rewriteMode, setRewriteMode] = useState<'clarify' | 'tighten' | 'simplify' | 'formal'>('clarify');
  const hintShownRef = useRef(false);
  const snapshotsRef = useRef<Map<string, BlockSnapshot>>(new Map());

  useEffect(() => {
    snapshotsRef.current = snapshots;
  }, [snapshots]);

  // base sha
  useEffect(() => { sha1Hex(sourceText).then((h) => setBaseSha(h.slice(0, 12))); }, [sourceText]);

  // assign ids + take snapshots
  useEffect(() => {
    const blocks = assignBlockIds();
    const map = new Map<string, BlockSnapshot>();
    blocks.forEach((b) => {
      const id = b.dataset.editorId!;
      const t = plainText(b);
      map.set(id, { id, tag: b.tagName.toLowerCase(), original: t, current: t, deleted: false, source: 'user' });
    });
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const persisted = JSON.parse(raw) as PersistedEditorState;
        persisted.blocks?.forEach((p) => {
          const existing = map.get(p.id);
          if (!existing) return;
          const merged: BlockSnapshot = { ...existing, current: p.current, deleted: p.deleted, source: p.source };
          map.set(p.id, merged);
          const block = document.querySelector<HTMLElement>(`[data-editor-id="${cssEscape(p.id)}"]`);
          if (block) paintBlockDiff(block, merged);
        });
        if (Array.isArray(persisted.annotations)) setAnnotations(persisted.annotations);
      }
    } catch {
      // no-op
    }
    setSnapshots(map);
  }, [storageKey]);

  useEffect(() => {
    const persist: PersistedEditorState = {
      blocks: Array.from(snapshots.values())
        .filter((s) => s.deleted || s.current !== s.original)
        .map((s) => ({ id: s.id, current: s.current, deleted: s.deleted, source: s.source })),
      annotations,
    };

    try {
      localStorage.setItem(storageKey, JSON.stringify(persist));
    } catch {
      // no-op
    }
  }, [snapshots, annotations, storageKey]);

  // Ambient click-to-edit: install once on the article.
  useEffect(() => {
    const article = document.querySelector('.prose-body') as HTMLElement | null;
    if (!article) return;

    const onClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const block = target.closest('[data-editor-id]') as HTMLElement | null;
      if (!block || block.getAttribute('contenteditable') === 'true') return;
      // Don't intercept clicks on glossary spans (term popover handles those)
      if (target.closest('.ar-overlay')) return;
      // Don't intercept clicks on hover-chips
      if (target.closest('.edit-block-actions') || target.closest('.edit-block-chip')) return;
      const id = block.dataset.editorId!;
      const snap = snapshotsRef.current.get(id);
      if (snap) {
        block.textContent = snap.current;
        block.classList.remove('edit-block-deleted', 'edit-block-saved');
      }
      block.setAttribute('contenteditable', 'true');
      block.setAttribute('spellcheck', 'true');
      // Place caret where user clicked, if possible
      const sel = window.getSelection();
      if (sel && sel.rangeCount > 0) {
        // browser already set caret at click point
      } else {
        block.focus();
      }
    };

    const onBlur = (e: FocusEvent) => {
      const block = e.target as HTMLElement;
      if (!block.matches?.('[data-editor-id][contenteditable="true"]')) return;
      const id = block.dataset.editorId!;
      block.removeAttribute('contenteditable');
      block.removeAttribute('spellcheck');
      setSnapshots((prev) => {
        const next = new Map(prev);
        const snap = next.get(id);
        if (!snap) return prev;
        const txt = plainText(block);
        const merged = { ...snap, current: txt, deleted: false };
        paintBlockDiff(block, merged);
        next.set(id, merged);
        return next;
      });
    };

    const onInput = (e: Event) => {
      const block = (e.target as HTMLElement).closest('[data-editor-id][contenteditable="true"]') as HTMLElement | null;
      if (!block) return;
      const id = block.dataset.editorId!;
      const txt = plainText(block);
      setSnapshots((prev) => {
        const next = new Map(prev);
        const snap = next.get(id);
        if (!snap) return prev;
        next.set(id, { ...snap, current: txt });
        return next;
      });
    };

    article.addEventListener('click', onClick);
    article.addEventListener('blur', onBlur, true);  // capture for blur (doesn't bubble)
    article.addEventListener('input', onInput);
    return () => {
      article.removeEventListener('click', onClick);
      article.removeEventListener('blur', onBlur, true);
      article.removeEventListener('input', onInput);
    };
  }, []);

  // First-visit hint
  useEffect(() => {
    if (hintShownRef.current) return;
    if (sessionStorage.getItem('podcast-reader:edit-hint-seen')) return;
    hintShownRef.current = true;
    setTimeout(() => {
      sessionStorage.setItem('podcast-reader:edit-hint-seen', '1');
    }, 5000);
  }, []);

  // Selection-driven rewrite sparkle
  useEffect(() => {
    const onSelChange = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) { setRewrite((r) => r && !r.options.length ? null : r); return; }
      const text = sel.toString().trim();
      if (text.length < 12) return;
      const anchorEl = sel.anchorNode?.parentElement?.closest('[data-editor-id]') as HTMLElement | null;
      if (!anchorEl) return;
      const range = sel.getRangeAt(0).cloneRange();
      const rect = range.getBoundingClientRect();
      setRewrite({ rect, selection: text, blockId: anchorEl.dataset.editorId!, range, loading: false, options: [] });
    };
    document.addEventListener('selectionchange', onSelChange);
    return () => document.removeEventListener('selectionchange', onSelChange);
  }, []);

  // ⌘⇧A annotation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'A' || e.key === 'a')) {
        e.preventDefault();
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed) return;
        const block = sel.anchorNode?.parentElement?.closest('[data-editor-id]') as HTMLElement | null;
        if (!block) return;
        setAnnotateBlockId(block.dataset.editorId!);
        setAnnotateSelection(sel.toString().slice(0, 200));
        setAnnotateText('');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Listen for AI-instruction edits dispatched by the instruction panel
  useEffect(() => {
    const onApply = (e: Event) => {
      const detail = (e as CustomEvent).detail as { edits: { block_id: string; action: string; new_text?: string }[] };
      if (!detail?.edits) return;
      applyEdits(detail.edits, 'ai');
    };
    window.addEventListener('chapter-editor:apply-edits', onApply);
    return () => window.removeEventListener('chapter-editor:apply-edits', onApply);
  }, []);

  useEffect(() => {
    const onFinalize = () => {
      setSnapshots((prev) => {
        const next = new Map<string, BlockSnapshot>();
        prev.forEach((snap, id) => {
          const normalized: BlockSnapshot = {
            ...snap,
            original: snap.current,
            current: snap.current,
            deleted: false,
            source: 'user',
          };
          next.set(id, normalized);

          const block = document.querySelector<HTMLElement>(`[data-editor-id="${cssEscape(id)}"]`);
          if (block) {
            block.classList.remove('edit-block-changed', 'edit-block-deleted', 'edit-block-ai-flash');
            block.textContent = normalized.current;
          }
        });
        return next;
      });

      setAnnotations([]);
      try {
        localStorage.removeItem(storageKey);
      } catch {
        // no-op
      }
    };

    window.addEventListener('chapter-editor:finalize', onFinalize);
    return () => window.removeEventListener('chapter-editor:finalize', onFinalize);
  }, [storageKey]);

  const applyEdits = (edits: { block_id: string; action: string; new_text?: string }[], source: 'user' | 'ai') => {
    setSnapshots((prev) => {
      const next = new Map(prev);
      edits.forEach((ed) => {
        const block = document.querySelector<HTMLElement>(`[data-editor-id="${cssEscape(ed.block_id)}"]`);
        if (!block) return;
        const snap = next.get(ed.block_id);
        if (!snap) return;

        if (ed.action === 'replace' && typeof ed.new_text === 'string') {
          block.textContent = ed.new_text;
          const merged: BlockSnapshot = { ...snap, current: plainText(block), deleted: false, source };
          paintBlockDiff(block, merged);
          if (source === 'ai') {
            block.classList.add('edit-block-ai-flash');
            setTimeout(() => block.classList.remove('edit-block-ai-flash'), 700);
          }
          next.set(ed.block_id, merged);
        } else if (ed.action === 'delete') {
          block.classList.add('edit-block-deleted', 'edit-block-changed');
          if (source === 'ai') {
            block.classList.add('edit-block-ai-flash');
            setTimeout(() => block.classList.remove('edit-block-ai-flash'), 700);
          }
          next.set(ed.block_id, { ...snap, deleted: true, source });
        } else if (ed.action === 'insert_after' && typeof ed.new_text === 'string') {
          // Build a new block element matching the referenced block's tag.
          const newEl = document.createElement(snap.tag === 'h2' || snap.tag === 'h3' ? 'p' : snap.tag);
          newEl.textContent = ed.new_text;
          const counter = Date.now().toString(36).slice(-4);
          const newId = `${snap.tag}:${ed.block_id.split('#')[0].split(':')[1] ?? 'ins'}#new-${counter}`;
          newEl.dataset.editorId = newId;
          if (source === 'ai') {
            newEl.classList.add('edit-block-ai-flash');
            setTimeout(() => newEl.classList.remove('edit-block-ai-flash'), 700);
          }
          block.insertAdjacentElement('afterend', newEl);
          const inserted: BlockSnapshot = { id: newId, tag: snap.tag, original: '', current: ed.new_text, deleted: false, source };
          paintBlockDiff(newEl, inserted);
          next.set(newId, inserted);
        }
      });
      return next;
    });
  };

  const askRewrite = async () => {
    if (!rewrite) return;
    setRewrite({ ...rewrite, loading: true });
    try {
      const block = document.querySelector(`[data-editor-id="${cssEscape(rewrite.blockId)}"]`) as HTMLElement | null;
      const context = block ? plainText(block) : '';
      const res = await fetch('/api/ai/rewrite', {
        method: 'POST', headers: { 'content-type': 'application/json' },
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
    } catch { /* ignore */ }
    const block = document.querySelector(`[data-editor-id="${cssEscape(rewrite.blockId)}"]`) as HTMLElement | null;
    if (block) {
      const id = block.dataset.editorId!;
      const txt = plainText(block);
      setSnapshots((prev) => {
        const next = new Map(prev);
        const snap = next.get(id);
        if (!snap) return prev;
        const merged: BlockSnapshot = { ...snap, current: txt, deleted: false, source: 'ai' };
        paintBlockDiff(block, merged);
        block.classList.add('edit-block-ai-flash');
        setTimeout(() => block.classList.remove('edit-block-ai-flash'), 700);
        next.set(id, merged);
        return next;
      });
    }
    setRewrite(null);
    window.getSelection()?.removeAllRanges();
  };

  const revert = (id: string) => {
    const snap = snapshots.get(id);
    if (!snap) return;
    const block = document.querySelector<HTMLElement>(`[data-editor-id="${cssEscape(id)}"]`);
    if (block) {
      if (snap.original === '') {
        // inserted block — remove from DOM
        block.remove();
      } else {
        block.textContent = snap.original;
        block.classList.remove('edit-block-changed', 'edit-block-deleted');
      }
    }
    setSnapshots((prev) => {
      const n = new Map(prev);
      if (snap.original === '') n.delete(id);
      else n.set(id, { ...snap, current: snap.original, deleted: false });
      return n;
    });
  };

  const toggleDelete = (id: string) => {
    const snap = snapshots.get(id);
    if (!snap) return;
    const willDelete = !snap.deleted;
    const block = document.querySelector<HTMLElement>(`[data-editor-id="${cssEscape(id)}"]`);
    if (block) {
      block.classList.toggle('edit-block-deleted', willDelete);
      block.classList.add('edit-block-changed');
    }
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
    setAnnotateBlockId(null); setAnnotateText(''); setAnnotateSelection('');
  };

  // Render hover-chips for every changed block (one floating element
  // appended into each, via a portal effect).
  useEffect(() => {
    const blocks = Array.from(document.querySelectorAll<HTMLElement>('.prose-body [data-editor-id]'));
    blocks.forEach((b) => {
      const id = b.dataset.editorId!;
      const snap = snapshots.get(id);
      const changed = snap && (snap.deleted || snap.current !== snap.original);
      let actions = b.querySelector(':scope > .edit-block-actions') as HTMLElement | null;
      if (changed) {
        if (!actions) {
          actions = document.createElement('span');
          actions.className = 'edit-block-actions';
          actions.contentEditable = 'false';
          actions.innerHTML = `
            <span class="edit-block-chip" data-action="revert" title="Revert to original">↺ Revert</span>
            <span class="edit-block-chip" data-action="delete" title="${snap?.deleted ? 'Restore' : 'Mark deleted'}">${snap?.deleted ? '+ Restore' : '✕ Delete'}</span>
          `;
          actions.addEventListener('click', (ev) => {
            const t = (ev.target as HTMLElement).closest('[data-action]') as HTMLElement | null;
            if (!t) return;
            ev.stopPropagation();
            const action = t.dataset.action;
            if (action === 'revert') revert(id);
            else if (action === 'delete') toggleDelete(id);
          });
          b.appendChild(actions);
        }
      } else if (actions) {
        actions.remove();
      }
    });
  });

  const changes = useMemo(() =>
    Array.from(snapshots.values()).filter((s) => s.deleted || s.current !== s.original),
    [snapshots]);

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
        lines.push(`## edit#${n} — block "${c.id}" (${c.tag}) — DELETE${c.source === 'ai' ? ' (AI)' : ''}`);
        lines.push('- ' + c.original.replace(/\n/g, ' '));
      } else if (c.original === '') {
        lines.push(`## edit#${n} — block "${c.id}" (${c.tag}) — INSERT${c.source === 'ai' ? ' (AI)' : ''}`);
        lines.push('+ ' + c.current.replace(/\n/g, ' '));
      } else {
        lines.push(`## edit#${n} — block "${c.id}" (${c.tag})${c.source === 'ai' ? ' (AI)' : ''}`);
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
    try {
      await navigator.clipboard.writeText(buildPatch());
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* ignore */ }
  };

  // Expose blocks-for-AI to the docked instruction panel
  useEffect(() => {
    (window as any).__chapterEditor = {
      collectBlocks: collectBlocksForAI,
      bookContext: book,
      chapterTitle,
    };
    return () => { delete (window as any).__chapterEditor; };
  }, [book, chapterTitle]);

  return (
    <>
      {/* Floating sparkle on selection */}
      {rewrite && rewrite.options.length === 0 && !rewrite.loading && !rewrite.error && (
        <button
          onClick={askRewrite}
          className="fixed z-50 inline-flex items-center gap-1 rounded-full border border-amber-400 bg-white/90 px-2.5 py-1 text-[11px] font-medium text-amber-800 shadow-lg backdrop-blur hover:bg-amber-50"
          style={{ top: rewrite.rect.top + window.scrollY - 38, left: rewrite.rect.left + window.scrollX }}
          title="Suggest rewrites (Gemini)"
          onMouseDown={(e) => e.preventDefault()}
        >
          <span>✦</span> Rewrite
          <select
            value={rewriteMode}
            onChange={(e) => { e.stopPropagation(); setRewriteMode(e.target.value as any); }}
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            className="ml-1 rounded border border-amber-300 bg-white px-1 py-0 text-[10px]"
          >
            <option value="clarify">clarify</option>
            <option value="tighten">tighten</option>
            <option value="simplify">simplify</option>
            <option value="formal">formal</option>
          </select>
        </button>
      )}

      {/* Rewrite results card */}
      {rewrite && (rewrite.loading || rewrite.options.length > 0 || rewrite.error) && (
        <div
          className="popup-card fixed z-50 w-[460px]"
          style={{ top: rewrite.rect.bottom + window.scrollY + 8, left: Math.min(rewrite.rect.left + window.scrollX, window.scrollX + window.innerWidth - 480) }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="popup-card-header">
            <span>Rewrite · {rewriteMode}</span>
            <button className="popup-card-close" onClick={() => setRewrite(null)} aria-label="Close">✕</button>
          </div>
          <div className="popup-card-body">
            {rewrite.loading && <div className="text-[12px] text-stone-500">Asking Gemini Flash…</div>}
            {rewrite.error && <div className="text-[12px] text-rose-600">Failed: {rewrite.error}</div>}
            <div className="space-y-2">
              {rewrite.options.map((opt, i) => (
                <div key={i} className="rounded-lg border border-stone-200 bg-white/60 p-2 text-[13px] leading-snug">
                  <div className="text-stone-800">{opt}</div>
                  <button onClick={() => acceptRewrite(opt)} className="mt-1.5 rounded-md bg-amber-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white hover:bg-amber-700">
                    Accept
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Annotation modal */}
      {annotateBlockId && (
        <div className="popup-modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) setAnnotateBlockId(null); }}>
          <div className="popup-card w-[480px] max-w-full">
            <div className="popup-card-header">
              <span>Margin note</span>
              <button className="popup-card-close" onClick={() => setAnnotateBlockId(null)} aria-label="Close">✕</button>
            </div>
            <div className="popup-card-body">
              {annotateSelection && (
                <div className="mb-2 rounded-md border-l-2 border-amber-400 bg-amber-50/70 px-2 py-1 text-[12px] italic text-stone-700">
                  "{annotateSelection}"
                </div>
              )}
              <textarea
                value={annotateText}
                onChange={(e) => setAnnotateText(e.target.value)}
                autoFocus rows={3}
                placeholder="e.g. is 'Sayyidina' the right transliteration here?"
                className="w-full rounded-md border border-stone-300 bg-white px-2 py-1.5 text-[13px] focus:border-amber-400 focus:outline-none"
              />
              <div className="mt-2 flex justify-end gap-2">
                <button onClick={() => setAnnotateBlockId(null)} className="rounded px-3 py-1 text-[12px] text-stone-500 hover:text-stone-900">Cancel</button>
                <button onClick={saveAnnotation} className="rounded-md bg-emerald-600 px-3 py-1 text-[12px] font-semibold text-white hover:bg-emerald-700">Save note</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Changes panel — floats bottom-left when there are any */}
      {(changes.length > 0 || annotations.length > 0) && (
        <div className="popup-card fixed bottom-6 left-6 z-30 w-[340px]">
          <button
            onClick={() => setPanelOpen((v) => !v)}
            className="popup-card-header w-full edit-changes-toggle"
          >
            <span>Changes <span className="ml-1 rounded bg-emerald-100 px-1.5 py-0 text-[10px] text-emerald-800">{changes.length}</span>{annotations.length > 0 && <span className="ml-1 rounded bg-amber-100 px-1.5 py-0 text-[10px] text-amber-800">{annotations.length} notes</span>}</span>
            <span>{panelOpen ? '−' : '+'}</span>
          </button>
          {panelOpen && (
            <div className="popup-card-body max-h-[40vh] overflow-y-auto text-[12px]">
              {changes.map((c) => (
                <div key={c.id} className="mb-2 border-l-2 pl-2 edit-change-row">
                  <div className="font-ui text-[9px] uppercase tracking-wider text-stone-500">{c.tag} · {c.id}{c.source === 'ai' ? ' · AI' : ''}</div>
                  {c.deleted ? (
                    <div className="text-stone-500 line-through">{c.original.slice(0, 100)}…</div>
                  ) : c.original === '' ? (
                    <div className="text-emerald-700">+ {c.current.slice(0, 100)}</div>
                  ) : (
                    <>
                      <div className="text-rose-700 line-through opacity-60">{c.original.slice(0, 70)}…</div>
                      <div className="text-emerald-700">{c.current.slice(0, 70)}…</div>
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
                  <div className="text-stone-700">{a.note}</div>
                  <button onClick={() => setAnnotations((all) => all.filter((x) => x.id !== a.id))} className="text-[10px] text-stone-500 hover:text-rose-700">remove</button>
                </div>
              ))}
            </div>
          )}
          <div className="border-t border-stone-200/60 p-3">
            <button
              onClick={copyPatch}
              className="w-full rounded-md bg-emerald-600 px-3 py-2 text-[12px] font-semibold text-white shadow-sm hover:bg-emerald-700"
            >
              {copied ? '✓ Copied — paste back to Claude' : `Copy patch (${changes.length} edit${changes.length === 1 ? '' : 's'}${annotations.length ? `, ${annotations.length} notes` : ''})`}
            </button>
            <div className="mt-1 text-center font-ui text-[10px] text-stone-400">base-sha: {baseSha}</div>
          </div>
        </div>
      )}
    </>
  );
}

function cssEscape(s: string): string {
  return s.replace(/(["\\#:.\[\]])/g, '\\$1');
}
