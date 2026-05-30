import { useCallback, useEffect, useMemo, useRef, useState, type ComponentType } from 'react';
import { STORAGE_KEYS } from '../../lib/reader/storage-keys';
import {
  Eye,
  Globe,
  Scale,
  Trash2,
  Lightbulb,
  Search,
  PenLine,
  GitBranch,
  MessageSquarePlus,
  Flag,
  Copy,
  Check,
  Save,
  Trash,
  Loader2,
} from 'lucide-react';

type Scope = 'paragraph' | 'book' | 'global';

type QueueItem = {
  id: string;
  kind: 'action' | 'marker';
  scope: Scope;
  paraIdx: number | null;
  paragraphPreview: string;
  actionType: string;
  instruction: string;
  tags: string[];
  createdAt: string;
};

type Tag = {
  id: number;
  tag_label: string;
  tag_color: string;
  tag_icon: string;
};

type Annotation = {
  id: number;
  para_idx: number;
  tag_id: number;
  tag_label: string;
  tag_color: string;
  tag_icon: string;
};

type ActionDef = {
  key: string;
  label: string;
  Icon: ComponentType<{ size?: number; className?: string }>;
};

const ICON_MAP: Record<string, ComponentType<{ size?: number; className?: string }>> = {
  Eye,
  Globe,
  Scale,
  Trash2,
  Lightbulb,
};

const ICON_GLYPH: Record<string, string> = {
  Eye: '◉',
  Globe: '◎',
  Scale: '⚖',
  Trash2: '✕',
  Lightbulb: '✦',
};

const ACTIONS: ActionDef[] = [
  { key: 'research', label: 'Research', Icon: Search },
  { key: 'improve', label: 'Improve', Icon: PenLine },
  { key: 'crossref', label: 'Cross-reference', Icon: GitBranch },
  { key: 'note', label: 'Expand', Icon: MessageSquarePlus },
  { key: 'flag', label: 'Flag', Icon: Flag },
];

interface Props {
  book: string;
  chapterSlug: string;
  bookTitle?: string;
}

const queueKey = (book: string, chapter: string) => STORAGE_KEYS.annotationQueue(book, chapter);

function textPreview(text: string, max = 180): string {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max)}...`;
}

function buildQueueText(items: QueueItem[], book: string, chapter: string): string {
  const lines: string[] = [];
  lines.push(`# queued annotation instructions for ${book} / ${chapter}`);
  lines.push('');
  if (items.length === 0) {
    lines.push('- no queued items yet');
    return lines.join('\n');
  }

  items.forEach((item, i) => {
    lines.push(`${i + 1}. [${item.scope}] ${item.actionType}`);
    if (item.paraIdx !== null) lines.push(`   paragraph: ${item.paraIdx}`);
    if (item.tags.length > 0) lines.push(`   tags: ${item.tags.join(', ')}`);
    if (item.paragraphPreview) lines.push(`   text: ${item.paragraphPreview}`);
    lines.push(`   instruction: ${item.instruction}`);
  });

  lines.push('');
  lines.push('Execute in order. Keep factual integrity and report changes item-by-item.');
  return lines.join('\n');
}

export default function AnnotationWorkbench({ book, chapterSlug, bookTitle }: Props) {
  const [tags, setTags] = useState<Tag[]>([]);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [notesByPara, setNotesByPara] = useState<Record<number, string>>({});
  const [activeParaIdx, setActiveParaIdx] = useState<number | null>(null);
  const [activeParagraphText, setActiveParagraphText] = useState('');
  const [scope, setScope] = useState<Scope>('paragraph');
  const [selectedAction, setSelectedAction] = useState<string>('research');
  const [instruction, setInstruction] = useState('');
  const [noteDraft, setNoteDraft] = useState('');
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [resultPrompt, setResultPrompt] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [queueCopied, setQueueCopied] = useState(false);
  const [savedLabel, setSavedLabel] = useState('');

  const lastNoteRef = useRef('');
  const lastParaRef = useRef<number | null>(null);
  const workbenchRef = useRef<HTMLElement | null>(null);

  const saveCurrentNote = useCallback(async () => {
    if (lastParaRef.current === null) return;
    const idx = lastParaRef.current;
    const text = lastNoteRef.current;

    await fetch('/api/annotations', {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ book, chapter: chapterSlug, paraIdx: idx, note: text }),
    });

    setNotesByPara((prev) => {
      const next = { ...prev };
      if (text.trim()) next[idx] = text;
      else delete next[idx];
      return next;
    });

    setSavedLabel(`saved paragraph ${idx}`);
    setTimeout(() => setSavedLabel(''), 1400);
  }, [book, chapterSlug]);

  const loadSnapshot = useCallback(async () => {
    const [tagsRes, snapshotRes] = await Promise.all([
      fetch('/api/annotations/tags'),
      fetch(`/api/annotations?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapterSlug)}`),
    ]);

    const nextTags = (await tagsRes.json()) as Tag[];
    const snapshot = await snapshotRes.json();
    const nextAnnotations = Array.isArray(snapshot) ? (snapshot as Annotation[]) : ((snapshot.annotations ?? []) as Annotation[]);
    const nextNotesRaw = (snapshot.notes ?? []) as Array<{ para_idx: number; note: string }>;

    const nextNotes: Record<number, string> = {};
    nextNotesRaw.forEach((n) => { nextNotes[n.para_idx] = n.note; });

    setTags(nextTags);
    setAnnotations(nextAnnotations);
    setNotesByPara(nextNotes);
  }, [book, chapterSlug]);

  useEffect(() => {
    loadSnapshot().catch(console.error);
  }, [loadSnapshot]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(queueKey(book, chapterSlug));
      if (!raw) return;
      const parsed = JSON.parse(raw) as QueueItem[];
      if (Array.isArray(parsed)) setQueue(parsed);
    } catch {
      // no-op
    }
  }, [book, chapterSlug]);

  useEffect(() => {
    try {
      localStorage.setItem(queueKey(book, chapterSlug), JSON.stringify(queue));
    } catch {
      // no-op
    }
  }, [queue, book, chapterSlug]);

  useEffect(() => {
    const prose = document.querySelector('.prose-body');
    if (!prose) return;
    const paras = prose.querySelectorAll<HTMLElement>('p, h2, h3, blockquote');
    paras.forEach((el, i) => el.setAttribute('data-para-idx', String(i)));

    const onOver = (e: Event) => {
      const target = (e.target as HTMLElement).closest<HTMLElement>('[data-para-idx]');
      if (!target) return;
      const idx = Number(target.getAttribute('data-para-idx'));
      if (Number.isNaN(idx)) return;
      setActiveParaIdx(idx);
      setActiveParagraphText(textPreview(target.textContent ?? '', 260));
    };

    const onClick = (e: Event) => {
      const target = (e.target as HTMLElement).closest<HTMLElement>('[data-para-idx]');
      if (!target) return;
      const idx = Number(target.getAttribute('data-para-idx'));
      if (Number.isNaN(idx)) return;
      setActiveParaIdx(idx);
      setActiveParagraphText(textPreview(target.textContent ?? '', 260));
      workbenchRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      const actionInput = workbenchRef.current?.querySelector<HTMLTextAreaElement>('.anno-instruction-input');
      actionInput?.focus();
    };

    prose.addEventListener('mouseover', onOver);
    prose.addEventListener('click', onClick);
    return () => {
      prose.removeEventListener('mouseover', onOver);
      prose.removeEventListener('click', onClick);
    };
  }, []);

  useEffect(() => {
    const prose = document.querySelector('.prose-body');
    if (!prose) return;

    prose.querySelectorAll<HTMLElement>('[data-para-idx]').forEach((el) => {
      el.classList.remove('anno-workbench-active');
      el.classList.remove('anno-workbench-saved');
      el.style.borderLeft = '';
      el.style.paddingLeft = '';
      el.style.marginLeft = '';
    });

    const grouped = new Map<number, Annotation[]>();
    annotations.forEach((a) => {
      if (!grouped.has(a.para_idx)) grouped.set(a.para_idx, []);
      grouped.get(a.para_idx)!.push(a);
    });

    grouped.forEach((items, idx) => {
      const el = prose.querySelector<HTMLElement>(`[data-para-idx="${idx}"]`);
      if (!el) return;
      el.classList.add('anno-has-tags');
      el.classList.add('anno-workbench-saved');
      el.style.borderLeft = `3px solid ${items[0].tag_color}`;
      el.style.paddingLeft = '0.6em';
      el.style.marginLeft = '-0.75em';

      let badgeHost = el.querySelector<HTMLElement>(':scope > .anno-corner-badges');
      if (!badgeHost) {
        badgeHost = document.createElement('span');
        badgeHost.className = 'anno-corner-badges';
        el.appendChild(badgeHost);
      }

      badgeHost.innerHTML = items
        .slice(0, 4)
        .map((a) => {
          const glyph = ICON_GLYPH[a.tag_icon] ?? '•';
          return `<span class="anno-corner-badge" style="--anno-badge-color:${a.tag_color}" title="${a.tag_label}">${glyph}</span>`;
        })
        .join('');
    });

    Object.keys(notesByPara).forEach((key) => {
      const idx = Number(key);
      if (Number.isNaN(idx)) return;
      const el = prose.querySelector<HTMLElement>(`[data-para-idx="${idx}"]`);
      if (el) el.classList.add('anno-workbench-saved');
    });

    prose.querySelectorAll<HTMLElement>('.anno-corner-badges').forEach((host) => {
      const parent = host.parentElement as HTMLElement | null;
      if (!parent) return;
      const idx = Number(parent.getAttribute('data-para-idx'));
      if (!grouped.has(idx)) {
        host.remove();
        parent.classList.remove('anno-has-tags');
      }
    });

    if (activeParaIdx !== null) {
      const el = prose.querySelector<HTMLElement>(`[data-para-idx="${activeParaIdx}"]`);
      if (el) el.classList.add('anno-workbench-active');
    }
  }, [annotations, activeParaIdx, notesByPara]);

  useEffect(() => {
    if (lastParaRef.current !== null && lastParaRef.current !== activeParaIdx) {
      saveCurrentNote().catch(console.error);
    }

    if (activeParaIdx !== null) {
      const next = notesByPara[activeParaIdx] ?? '';
      setNoteDraft(next);
      lastNoteRef.current = next;
      lastParaRef.current = activeParaIdx;
    }
  }, [activeParaIdx, notesByPara, saveCurrentNote]);

  useEffect(() => {
    const onBeforeUnload = () => {
      if (lastParaRef.current === null) return;
      void fetch('/api/annotations', {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          book,
          chapter: chapterSlug,
          paraIdx: lastParaRef.current,
          note: lastNoteRef.current,
        }),
        keepalive: true,
      });
    };

    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [book, chapterSlug]);

  const activeTags = useMemo(() => {
    if (activeParaIdx === null) return [] as Tag[];
    const activeIds = annotations
      .filter((a) => a.para_idx === activeParaIdx)
      .map((a) => a.tag_id);
    return tags.filter((t) => activeIds.includes(t.id));
  }, [annotations, tags, activeParaIdx]);

  const toggleTag = async (tag: Tag) => {
    if (activeParaIdx === null) return;

    const res = await fetch('/api/annotations', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        book,
        chapter: chapterSlug,
        paraIdx: activeParaIdx,
        tagId: tag.id,
      }),
    });
    const data = await res.json();

    if (data.added) {
      setAnnotations((prev) => [
        ...prev,
        {
          id: Date.now(),
          para_idx: activeParaIdx,
          tag_id: tag.id,
          tag_label: tag.tag_label,
          tag_color: tag.tag_color,
          tag_icon: tag.tag_icon,
        },
      ]);
    } else {
      setAnnotations((prev) => prev.filter((a) => !(a.para_idx === activeParaIdx && a.tag_id === tag.id)));
    }

    setQueue((prev) => [
      {
        id: `m-${Date.now()}`,
        kind: 'marker' as const,
        scope: 'paragraph' as const,
        paraIdx: activeParaIdx,
        paragraphPreview: activeParagraphText,
        actionType: data.added ? 'marker-added' : 'marker-removed',
        instruction: `${tag.tag_label} ${data.added ? 'added' : 'removed'}`,
        tags: [tag.tag_label],
        createdAt: new Date().toISOString(),
      },
      ...prev,
    ].slice(0, 60));
  };

  const runAction = async () => {
    if (scope === 'paragraph' && activeParaIdx === null) return;
    const effectiveInstruction = instruction.trim() || `Apply ${selectedAction} to this ${scope} context`;

    setBusy(true);
    setResultPrompt('');
    setSources([]);
    try {
      const res = await fetch('/api/ai/research', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          paragraphText: scope === 'paragraph' ? activeParagraphText : `${scope}-scope instruction`,
          instruction: effectiveInstruction,
          bookTitle: bookTitle ?? book,
          actionType: selectedAction,
        }),
      });
      const data = await res.json();
      setResultPrompt(data.prompt ?? 'No prompt returned.');
      setSources(Array.isArray(data.sources) ? data.sources : []);
    } catch (e) {
      setResultPrompt(String(e));
    } finally {
      setBusy(false);
    }
  };

  const addResultToQueue = () => {
    if (!resultPrompt.trim()) return;
    const item: QueueItem = {
      id: `a-${Date.now()}`,
      kind: 'action',
      scope,
      paraIdx: scope === 'paragraph' ? activeParaIdx : null,
      paragraphPreview: scope === 'paragraph' ? activeParagraphText : '',
      actionType: selectedAction,
      instruction: resultPrompt.trim(),
      tags: activeTags.map((t) => t.tag_label),
      createdAt: new Date().toISOString(),
    };
    setQueue((prev) => [item, ...prev].slice(0, 60));
  };

  const copyLatest = async () => {
    if (!resultPrompt.trim()) return;
    await navigator.clipboard.writeText(resultPrompt.trim());
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const copyQueueSet = async () => {
    const text = buildQueueText(queue, book, chapterSlug);
    await navigator.clipboard.writeText(text);
    setQueueCopied(true);
    setTimeout(() => setQueueCopied(false), 1500);
  };

  const syncQueueForAi = async () => {
    const res = await fetch('/api/annotations/export', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ book, chapter: chapterSlug, bookTitle, queue }),
    });
    const data = await res.json();
    if (!res.ok) {
      setSavedLabel(data.error ?? 'Could not sync queue');
      return;
    }
    await navigator.clipboard.writeText(data.combinedText);
    setSavedLabel(`synced ${data.itemCount} items → ${data.relativePath}`);
    setTimeout(() => setSavedLabel(''), 2200);
  };

  const finalizeAndFlush = async () => {
    const ok = window.confirm('Finalize this chapter and reset markers, notes, queue, and visual indicators?');
    if (!ok) return;

    await saveCurrentNote();

    const res = await fetch(
      `/api/annotations?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapterSlug)}`,
      { method: 'DELETE' }
    );
    if (!res.ok) {
      setSavedLabel('Could not finalize reset');
      setTimeout(() => setSavedLabel(''), 2200);
      return;
    }

    setAnnotations([]);
    setNotesByPara({});
    setQueue([]);
    setResultPrompt('');
    setSources([]);
    setInstruction('');
    setNoteDraft('');
    lastParaRef.current = null;
    lastNoteRef.current = '';

    try {
      localStorage.removeItem(queueKey(book, chapterSlug));
    } catch {
      // no-op
    }

    window.dispatchEvent(new CustomEvent('chapter-editor:finalize'));

    setSavedLabel('Chapter finalized and reset');
    setTimeout(() => setSavedLabel(''), 2200);
  };

  return (
    <section className="rail-panel anno-workbench" ref={workbenchRef}>
      <div className="rail-panel-head">
        <span className="rail-panel-icon" aria-hidden>✦</span>
        <span className="rail-panel-label">Annotation workspace</span>
      </div>

      <div className="anno-workbench-scope">
        {(['paragraph', 'book', 'global'] as Scope[]).map((s) => (
          <button
            key={s}
            className={`anno-scope-btn ${scope === s ? 'is-active' : ''}`}
            onClick={() => setScope(s)}
            type="button"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="anno-target">
        <div className="anno-target-label">Active target</div>
        {scope === 'paragraph' ? (
          <>
            <div className="anno-target-meta">{activeParaIdx !== null ? `Paragraph ${activeParaIdx}` : 'Hover a paragraph to start'}</div>
            <div className="anno-target-text">{activeParaIdx !== null ? activeParagraphText : 'Move your cursor over the chapter text. Edits save when you move to another paragraph.'}</div>
          </>
        ) : (
          <>
            <div className="anno-target-meta">{scope === 'book' ? 'Book-level instruction' : 'Global instruction'}</div>
            <div className="anno-target-text">No paragraph required for this scope.</div>
          </>
        )}
      </div>

      <div className="anno-tag-grid">
        {tags.map((tag) => {
          const Icon = ICON_MAP[tag.tag_icon] ?? Eye;
          const active = activeTags.some((t) => t.id === tag.id);
          return (
            <button
              key={tag.id}
              className={`anno-chip ${active ? 'is-active' : ''}`}
              style={{ borderColor: tag.tag_color, color: active ? '#fff' : tag.tag_color, background: active ? tag.tag_color : 'transparent' }}
              onClick={() => toggleTag(tag)}
              disabled={activeParaIdx === null}
              type="button"
              title={tag.tag_label}
            >
              <Icon size={12} />
              <span>{tag.tag_label}</span>
            </button>
          );
        })}
      </div>

      <label className="anno-field-label">Paragraph note (autosaves on paragraph exit)</label>
      <textarea
        className="rail-textarea"
        rows={3}
        value={noteDraft}
        onChange={(e) => {
          setNoteDraft(e.target.value);
          lastNoteRef.current = e.target.value;
        }}
        disabled={scope !== 'paragraph' || activeParaIdx === null}
        placeholder={scope === 'paragraph' ? 'Write your note here. It will save when you move away from this paragraph.' : 'Paragraph notes are available in paragraph scope.'}
      />

      <label className="anno-field-label">Action</label>
      <div className="anno-action-row">
        {ACTIONS.map((a) => {
          const Icon = a.Icon;
          return (
            <button
              key={a.key}
              className={`anno-action-pill ${selectedAction === a.key ? 'is-active' : ''}`}
              onClick={() => setSelectedAction(a.key)}
              type="button"
            >
              <Icon size={12} />
              <span>{a.label}</span>
            </button>
          );
        })}
      </div>

      <label className="anno-field-label">Instruction</label>
      <textarea
        className="rail-textarea anno-instruction-input"
        rows={3}
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        placeholder="Describe what you want the AI assistant to do with this target."
      />

      <div className="rail-row">
        <span className="rail-hint">{savedLabel || 'Markers and notes persist automatically.'}</span>
        <button
          className="rail-btn rail-btn-primary"
          onClick={runAction}
          disabled={busy || (scope === 'paragraph' && activeParaIdx === null)}
          type="button"
        >
          {busy ? <><Loader2 size={13} className="anno-spin" /> Running…</> : 'Generate instruction'}
        </button>
      </div>

      {resultPrompt && (
        <div className="anno-result-card">
          <div className="anno-result-head-row">
            <span className="anno-result-title">Generated instruction</span>
            <div className="anno-copy-row">
              <button className="anno-mini-btn" onClick={copyLatest} type="button">
                {copied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
              </button>
              <button className="anno-mini-btn" onClick={copyQueueSet} type="button">
                {queueCopied ? <><Check size={12} /> Queue copied</> : <><Copy size={12} /> Copy queue</>}
              </button>
            </div>
          </div>
          <pre className="anno-result-pre">{resultPrompt}</pre>
          <div className="anno-result-actions">
            <button className="anno-mini-btn" onClick={addResultToQueue} type="button">
              <Save size={12} /> Add to queue
            </button>
            <button className="anno-mini-btn" onClick={syncQueueForAi} type="button">
              <Save size={12} /> Sync JSON + copy set
            </button>
          </div>
          {sources.length > 0 && (
            <div className="anno-source-list">
              {sources.slice(0, 4).map((s) => (
                <a key={s} href={s} target="_blank" rel="noreferrer" className="anno-source-link-inline">
                  {new URL(s).hostname}
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="anno-queue">
        <div className="anno-queue-head">
          <span>Instruction queue ({queue.length})</span>
          <div className="anno-copy-row">
            <button
              className="anno-mini-btn"
              onClick={() => setQueue([])}
              disabled={queue.length === 0}
              type="button"
            >
              <Trash size={12} /> Clear
            </button>
            <button className="anno-mini-btn anno-mini-btn-danger" onClick={finalizeAndFlush} type="button">
              Finalize
            </button>
          </div>
        </div>
        <div className="anno-queue-list">
          {queue.length === 0 && <div className="anno-queue-empty">No queued items yet.</div>}
          {queue.map((q) => (
            <div key={q.id} className="anno-queue-item">
              <div className="anno-queue-item-top">
                <span>{q.scope}</span>
                <span>{q.actionType}</span>
                <button
                  className="anno-mini-btn"
                  onClick={() => setQueue((prev) => prev.filter((x) => x.id !== q.id))}
                  type="button"
                >
                  remove
                </button>
              </div>
              <div className="anno-queue-text">{q.instruction}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
