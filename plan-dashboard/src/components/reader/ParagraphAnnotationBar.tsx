/**
 * ParagraphAnnotationBar
 *
 * A single floating React component that attaches to the chapter reader.
 * On mount it scans .prose-body and stamps data-para-idx on every p/h2/h3.
 * Event delegation on .prose-body detects hover; @floating-ui/react positions
 * the toolbar to the left of the hovered paragraph.
 *
 * Horizontal row  — tag chips (pick/classify)
 * Vertical column — action buttons (research, improve, cross-ref, note, flag)
 *
 * Phase 1: action buttons call Gemini + copy formatted prompt to clipboard.
 * Phase 2 (future): direct pipeline wiring + SSE push.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  useFloating,
  offset,
  flip,
  shift,
  autoUpdate,
  type Placement,
} from '@floating-ui/react';
import * as Tooltip from '@radix-ui/react-tooltip';
import * as Dialog from '@radix-ui/react-dialog';
import {
  Eye, Globe, Scale, Trash2, Lightbulb,
  Search, PenLine, GitBranch, MessageSquarePlus, Flag,
  X, Copy, Check, Loader2,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Tag {
  id: number;
  tag_label: string;
  tag_color: string;
  tag_icon: string;
  is_default: number;
}

interface Annotation {
  id: number;
  para_idx: number;
  tag_id: number;
  tag_label: string;
  tag_color: string;
  tag_icon: string;
}

interface ActionDef {
  key: string;
  label: string;
  Icon: React.ComponentType<{ size?: number; className?: string; color?: string; strokeWidth?: number }>;
  color: string;
  bg: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string; color?: string }>> = {
  Eye, Globe, Scale, Trash2, Lightbulb,
  Search, PenLine, GitBranch, MessageSquarePlus, Flag,
};

const ACTIONS: ActionDef[] = [
  { key: 'research',  label: 'Research with Gemini',         Icon: Search,             color: '#ffffff', bg: '#4f46e5' },
  { key: 'improve',   label: 'Suggest improvements',         Icon: PenLine,            color: '#ffffff', bg: '#059669' },
  { key: 'crossref',  label: 'Find cross-references',        Icon: GitBranch,          color: '#ffffff', bg: '#0891b2' },
  { key: 'note',      label: 'Expand with scholarly detail', Icon: MessageSquarePlus,  color: '#ffffff', bg: '#475569' },
  { key: 'flag',      label: 'Flag for human review',        Icon: Flag,               color: '#ffffff', bg: '#ea580c' },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  book: string;
  chapterSlug: string;
  bookTitle?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ParagraphAnnotationBar({ book, chapterSlug, bookTitle }: Props) {
  const [tags, setTags] = useState<Tag[]>([]);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [hoveredPara, setHoveredPara] = useState<HTMLElement | null>(null);
  const [hoveredParaIdx, setHoveredParaIdx] = useState<number | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeAction, setActiveAction] = useState<ActionDef | null>(null);
  const [instruction, setInstruction] = useState('');
  const [researching, setResearching] = useState(false);
  const [resultPrompt, setResultPrompt] = useState('');
  const [resultSources, setResultSources] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);

  // New-tag dialog state
  const [tagDialogOpen, setTagDialogOpen] = useState(false);
  const [newTagLabel, setNewTagLabel] = useState('');
  const [newTagColor, setNewTagColor] = useState('#6b7280');
  const [newTagIcon, setNewTagIcon] = useState('Tag');

  // ---------------------------------------------------------------------------
  // Floating toolbar positioning
  // ---------------------------------------------------------------------------

  const { refs, floatingStyles } = useFloating({
    placement: 'left-start' as Placement,
    middleware: [offset(10), flip({ fallbackPlacements: ['right-start'] }), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
    elements: { reference: hoveredPara },
  });

  // ---------------------------------------------------------------------------
  // Bootstrap: fetch tags + annotations, stamp data-para-idx on DOM
  // ---------------------------------------------------------------------------

  useEffect(() => {
    fetch('/api/annotations/tags')
      .then((r) => r.json())
      .then((data: Tag[]) => setTags(data))
      .catch(console.error);

    fetch(`/api/annotations?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapterSlug)}`)
      .then((r) => r.json())
      .then((data: Annotation[]) => setAnnotations(data))
      .catch(console.error);
  }, [book, chapterSlug]);

  // Stamp data-para-idx after mount and mark already-annotated paragraphs
  useEffect(() => {
    const proseBody = document.querySelector('.prose-body');
    if (!proseBody) return;
    const paras = proseBody.querySelectorAll<HTMLElement>('p, h2, h3, blockquote');
    paras.forEach((el, i) => {
      el.setAttribute('data-para-idx', String(i));
    });
  }, []);

  // Apply visual marks to annotated paragraphs whenever annotations change
  useEffect(() => {
    const proseBody = document.querySelector('.prose-body');
    if (!proseBody) return;
    // Clear all marks first
    proseBody.querySelectorAll<HTMLElement>('[data-para-idx]').forEach((el) => {
      el.style.borderLeft = '';
      el.style.paddingLeft = '';
      el.style.marginLeft = '';
    });
    // Apply color of the first tag (or show multi-color gradient for multiple)
    const byPara = new Map<number, Annotation[]>();
    for (const a of annotations) {
      if (!byPara.has(a.para_idx)) byPara.set(a.para_idx, []);
      byPara.get(a.para_idx)!.push(a);
    }
    byPara.forEach((annots, idx) => {
      const el = proseBody.querySelector<HTMLElement>(`[data-para-idx="${idx}"]`);
      if (!el) return;
      el.style.borderLeft = `3px solid ${annots[0].tag_color}`;
      el.style.paddingLeft = '0.6em';
      el.style.marginLeft = '-0.75em';
      el.style.transition = 'border-left-color 0.2s';
    });
  }, [annotations]);

  // ---------------------------------------------------------------------------
  // Event delegation on .prose-body
  // ---------------------------------------------------------------------------

  const handleMouseEnter = useCallback((e: MouseEvent) => {
    const target = (e.target as HTMLElement).closest<HTMLElement>('[data-para-idx]');
    if (!target) return;
    if (hideTimer.current) clearTimeout(hideTimer.current);
    const idx = Number(target.getAttribute('data-para-idx'));
    setHoveredPara(target);
    setHoveredParaIdx(idx);
    refs.setReference(target);
  }, [refs]);

  const handleMouseLeave = useCallback(() => {
    hideTimer.current = setTimeout(() => {
      setHoveredPara(null);
      setHoveredParaIdx(null);
    }, 350);
  }, []);

  useEffect(() => {
    const proseBody = document.querySelector('.prose-body');
    if (!proseBody) return;
    proseBody.addEventListener('mouseover', handleMouseEnter as EventListener);
    proseBody.addEventListener('mouseout', handleMouseLeave as EventListener);
    return () => {
      proseBody.removeEventListener('mouseover', handleMouseEnter as EventListener);
      proseBody.removeEventListener('mouseout', handleMouseLeave as EventListener);
    };
  }, [handleMouseEnter, handleMouseLeave]);

  // ---------------------------------------------------------------------------
  // Tag toggle
  // ---------------------------------------------------------------------------

  const toggleTag = async (tagId: number) => {
    if (hoveredParaIdx === null) return;
    const res = await fetch('/api/annotations', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ book, chapter: chapterSlug, paraIdx: hoveredParaIdx, tagId }),
    });
    const { added } = await res.json();
    if (added) {
      const tag = tags.find((t) => t.id === tagId)!;
      setAnnotations((prev) => [
        ...prev,
        { id: Date.now(), para_idx: hoveredParaIdx, tag_id: tagId,
          tag_label: tag.tag_label, tag_color: tag.tag_color, tag_icon: tag.tag_icon },
      ]);
    } else {
      setAnnotations((prev) =>
        prev.filter((a) => !(a.para_idx === hoveredParaIdx && a.tag_id === tagId))
      );
    }
  };

  // ---------------------------------------------------------------------------
  // Action: open dialog
  // ---------------------------------------------------------------------------

  const openAction = (action: ActionDef) => {
    setActiveAction(action);
    setInstruction('');
    setResultPrompt('');
    setResultSources([]);
    setCopied(false);
    setDialogOpen(true);
  };

  const runResearch = async () => {
    if (!activeAction || hoveredParaIdx === null) return;
    const paraEl = document.querySelector<HTMLElement>(`[data-para-idx="${hoveredParaIdx}"]`);
    const paragraphText = paraEl?.textContent ?? '';
    setResearching(true);
    try {
      const res = await fetch('/api/ai/research', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          paragraphText,
          instruction: instruction || activeAction.label,
          bookTitle: bookTitle ?? book,
          actionType: activeAction.key,
        }),
      });
      const data = await res.json();
      setResultPrompt(data.prompt ?? '');
      setResultSources(data.sources ?? []);
    } catch (e) {
      setResultPrompt(`Error: ${e}`);
    } finally {
      setResearching(false);
    }
  };

  const copyPrompt = async () => {
    await navigator.clipboard.writeText(resultPrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ---------------------------------------------------------------------------
  // New tag creation
  // ---------------------------------------------------------------------------

  const saveNewTag = async () => {
    if (!newTagLabel.trim()) return;
    const res = await fetch('/api/annotations/tags', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ label: newTagLabel.trim(), color: newTagColor, icon: newTagIcon }),
    });
    const tag: Tag = await res.json();
    setTags((prev) => [...prev, tag]);
    setNewTagLabel('');
    setNewTagColor('#6b7280');
    setNewTagIcon('Tag');
    setTagDialogOpen(false);
  };

  // ---------------------------------------------------------------------------
  // Helper: is a tag active on the currently hovered paragraph?
  // ---------------------------------------------------------------------------

  const isActive = (tagId: number) =>
    hoveredParaIdx !== null &&
    annotations.some((a) => a.para_idx === hoveredParaIdx && a.tag_id === tagId);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Tooltip.Provider delayDuration={400} skipDelayDuration={100}>
      {/* ── Floating toolbar ── */}
      {hoveredPara && (
        <div
          ref={refs.setFloating}
          style={{ ...floatingStyles, zIndex: 9999 }}
          className="anno-bar"
          onMouseEnter={() => { if (hideTimer.current) clearTimeout(hideTimer.current); }}
          onMouseLeave={handleMouseLeave}
        >
          {/* Horizontal tag row */}
          <div className="anno-tags">
            {tags.map((tag) => {
              const Icon = ICON_MAP[tag.tag_icon] ?? Eye;
              const active = isActive(tag.id);
              return (
                <Tooltip.Root key={tag.id}>
                  <Tooltip.Trigger asChild>
                    <button
                      className="anno-btn"
                      style={{
                        background: active ? tag.tag_color : 'transparent',
                        border: `1.5px solid ${tag.tag_color}`,
                        color: active ? '#fff' : tag.tag_color,
                      }}
                      onClick={() => toggleTag(tag.id)}
                      aria-label={tag.tag_label}
                      aria-pressed={active}
                    >
                      <Icon size={13} />
                    </button>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content className="anno-tooltip" sideOffset={5}>
                      {tag.tag_label}
                      <Tooltip.Arrow className="anno-tooltip-arrow" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              );
            })}

            {/* Add new tag */}
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button
                  className="anno-btn anno-btn-add"
                  onClick={() => setTagDialogOpen(true)}
                  aria-label="Add tag"
                >
                  <span style={{ fontSize: 14, lineHeight: 1 }}>+</span>
                </button>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content className="anno-tooltip" sideOffset={5}>
                  Add new tag
                  <Tooltip.Arrow className="anno-tooltip-arrow" />
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          </div>

          {/* Divider */}
          <div className="anno-divider" />

          {/* Vertical action column */}
          <div className="anno-actions">
            {ACTIONS.map((action) => (
              <Tooltip.Root key={action.key}>
                <Tooltip.Trigger asChild>
                  <button
                    className="anno-btn anno-action-btn"
                    style={{ background: action.bg, color: action.color }}
                    onClick={() => openAction(action)}
                    aria-label={action.label}
                  >
                    <action.Icon size={13} />
                  </button>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content className="anno-tooltip" side="right" sideOffset={5}>
                    {action.label}
                    <Tooltip.Arrow className="anno-tooltip-arrow" />
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            ))}
          </div>
        </div>
      )}

      {/* ── Instruction / Research dialog ── */}
      <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="anno-overlay" />
          <Dialog.Content className="anno-dialog">
            <div className="anno-dialog-head">
              <div className="anno-dialog-title-row">
                {activeAction && (() => {
                  const DialogIcon = activeAction.Icon;
                  return (
                    <span className="anno-dialog-icon" style={{ background: activeAction.bg }}>
                      <DialogIcon size={15} color="#fff" />
                    </span>
                  );
                })()}
                <Dialog.Title className="anno-dialog-title">
                  {activeAction?.label ?? 'Action'}
                </Dialog.Title>
              </div>
              <Dialog.Close className="anno-dialog-close" aria-label="Close">
                <X size={16} />
              </Dialog.Close>
            </div>

            <div className="anno-dialog-body">
              <label className="anno-dialog-label">
                Instruction <span className="anno-dialog-hint">(optional — defaults to action type)</span>
              </label>
              <textarea
                className="anno-dialog-textarea"
                rows={3}
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder={`e.g. "Find modern neuroscience research that supports or challenges this claim"`}
                autoFocus
              />

              {!resultPrompt && (
                <button
                  className="anno-dialog-run"
                  onClick={runResearch}
                  disabled={researching}
                >
                  {researching
                    ? <><Loader2 size={14} className="anno-spin" /> Researching…</>
                    : <>Run with Gemini + Search</>}
                </button>
              )}

              {resultPrompt && (
                <div className="anno-result">
                  <div className="anno-result-head">
                    <span className="anno-result-label">VS Code prompt — ready to paste</span>
                    <button className="anno-copy-btn" onClick={copyPrompt}>
                      {copied ? <><Check size={13} /> Copied</> : <><Copy size={13} /> Copy</>}
                    </button>
                  </div>
                  <pre className="anno-result-pre">{resultPrompt}</pre>

                  {resultSources.length > 0 && (
                    <div className="anno-sources">
                      <span className="anno-sources-label">Sources</span>
                      {resultSources.slice(0, 4).map((s, i) => (
                        <a key={i} href={s} target="_blank" rel="noopener noreferrer" className="anno-source-link">
                          {new URL(s).hostname}
                        </a>
                      ))}
                    </div>
                  )}

                  <button
                    className="anno-dialog-run anno-dialog-run-again"
                    onClick={() => { setResultPrompt(''); setResultSources([]); }}
                  >
                    Run again
                  </button>
                </div>
              )}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* ── New tag dialog ── */}
      <Dialog.Root open={tagDialogOpen} onOpenChange={setTagDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="anno-overlay" />
          <Dialog.Content className="anno-dialog anno-dialog-sm">
            <div className="anno-dialog-head">
              <Dialog.Title className="anno-dialog-title">New tag</Dialog.Title>
              <Dialog.Close className="anno-dialog-close"><X size={16} /></Dialog.Close>
            </div>
            <div className="anno-dialog-body">
              <label className="anno-dialog-label">Label</label>
              <input
                className="anno-dialog-input"
                value={newTagLabel}
                onChange={(e) => setNewTagLabel(e.target.value)}
                placeholder="e.g. metaphysical"
                autoFocus
              />
              <label className="anno-dialog-label">Colour</label>
              <div className="anno-color-row">
                <input
                  type="color"
                  className="anno-color-swatch"
                  value={newTagColor}
                  onChange={(e) => setNewTagColor(e.target.value)}
                />
                <span className="anno-color-hex">{newTagColor}</span>
              </div>
              <button className="anno-dialog-run" onClick={saveNewTag} disabled={!newTagLabel.trim()}>
                Save tag
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </Tooltip.Provider>
  );
}
