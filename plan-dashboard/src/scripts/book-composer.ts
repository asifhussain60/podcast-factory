/**
 * book-composer.ts — client logic for the Book Composer view (Book Pipeline v2).
 *
 * Reads the server-rendered JSON data island, lets the human curate visual
 * placements WYSIWYG (place from the palette, drag between chapters to move the
 * anchor, set align / flow / width / caption / page_fit, delete), then persists
 * to book/visual-layout.json via the API and triggers a PDF render. All styling
 * is class-based + the --cx-w custom property (set at runtime here, never as an
 * inline HTML attribute), so the view stays lint/Cortex-clean.
 */
import { mountChapterEditor, type ChapterEditor } from './book-md-editor';

type Align = 'left' | 'center' | 'right';
type Flow = 'wrap' | 'standalone';
type PageFit = 'avoid' | 'before' | 'isolate-plate';

interface Visual {
  id: string; type: string; caption: string; file: string; src: string;
  suggested_anchor: string; chapter: string; cleaned: boolean; embedded_title: string;
}
interface Citation { ar: string; tr: string; }
interface Chapter { anchor: string; key: string; title: string; paras: number; citations: Citation[]; }
interface Placement {
  visual_id: string; anchor: string; anchor_para: number | null; align: Align; flow: Flow;
  width_pct: number; caption: string; page_fit: PageFit;
}
interface ComposerData {
  slug: string; chapters: Chapter[]; visuals: Visual[]; placements: Placement[];
}

const WRAP_MAX = 50;

function anchorKey(s: string): string {
  return String(s).replace(/<[^>]+>/g, '').replace(/^#{1,6}\s+/, '')
    .replace(/^\d+\.\s*/, '').trim().toLowerCase();
}

function boot(): void {
  const rootMaybe = document.querySelector<HTMLElement>('.composer[data-slug]');
  const dataEl = document.getElementById('composer-data');
  if (!rootMaybe || !dataEl?.textContent) return;
  const root: HTMLElement = rootMaybe; // narrowed once; nested closures keep non-null
  const data = JSON.parse(dataEl.textContent) as ComposerData;
  const slug = data.slug;
  const visualsById = new Map(data.visuals.map((v) => [v.id, v]));
  const chapterByKey = new Map(data.chapters.map((c) => [c.key, c]));

  // Cache each chapter's pristine prose body so every re-render re-inserts the
  // placed figures inline (at the exact paragraph the PDF would use) without
  // accumulating them across renders.
  const bodyByKey = new Map<string, { el: HTMLElement; html: string }>();
  root.querySelectorAll<HTMLElement>('.cx-chapter').forEach((ch) => {
    const body = ch.querySelector<HTMLElement>('.cx-body');
    if (body) bodyByKey.set(ch.dataset.key ?? '', { el: body, html: body.innerHTML });
  });

  let placements: Placement[] = data.placements.map(normalize);
  let selected: string | null = null;
  let dirty = false;

  const paletteEl = root.querySelector<HTMLElement>('#cx-palette-list')!;
  const controlsEl = root.querySelector<HTMLElement>('#cx-controls')!;
  const saveBtn = root.querySelector<HTMLButtonElement>('#cx-save')!;
  const genBtn = root.querySelector<HTMLButtonElement>('#cx-generate')!;
  const statusEl = root.querySelector<HTMLElement>('#cx-status')!;
  const chapterSelect = root.querySelector<HTMLSelectElement>('#cx-chapter-select');
  const scopeEl = root.querySelector<HTMLElement>('#cx-artifacts-scope');
  let selectedChapter = data.chapters[0]?.key ?? '';

  // ── inspector tabs (Artifacts · Citations · Refinement · Output) ──────────
  const TABS = ['artifacts', 'citations', 'refine', 'output'] as const;
  type TabName = typeof TABS[number];
  const tabBtn = (n: TabName) => root.querySelector<HTMLButtonElement>(`#cx-tab-${n}`);
  const tabPanel = (n: TabName) => root.querySelector<HTMLElement>(`#cx-panel-${n}`);
  function activateTab(name: TabName, focus = false): void {
    for (const n of TABS) {
      const on = n === name;
      const btn = tabBtn(n);
      btn?.classList.toggle('is-active', on);
      btn?.setAttribute('aria-selected', String(on));
      btn?.setAttribute('tabindex', on ? '0' : '-1'); // roving tabindex (ARIA tablist)
      const panel = tabPanel(n);
      if (panel) panel.hidden = !on;
    }
    if (focus) tabBtn(name)?.focus();
  }
  TABS.forEach((n, i) => {
    const btn = tabBtn(n);
    btn?.addEventListener('click', () => activateTab(n));
    // Arrow / Home / End cycling per the ARIA tablist keyboard pattern.
    btn?.addEventListener('keydown', (e) => {
      let next = -1;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (i + 1) % TABS.length;
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (i - 1 + TABS.length) % TABS.length;
      else if (e.key === 'Home') next = 0;
      else if (e.key === 'End') next = TABS.length - 1;
      if (next >= 0) { e.preventDefault(); activateTab(TABS[next], true); }
    });
  });
  activateTab('artifacts'); // initialize roving tabindex on the default tab

  // ── chapter scoping — one chapter visible at a time; tabs follow it ────────
  function showSelectedChapter(): void {
    root.querySelectorAll<HTMLElement>('.cx-chapter').forEach((ch) => {
      ch.hidden = (ch.dataset.key ?? '') !== selectedChapter;
    });
  }
  if (chapterSelect) {
    chapterSelect.value = selectedChapter;
    chapterSelect.addEventListener('change', () => {
      selectedChapter = chapterSelect.value;
      selected = null; // a figure selection doesn't carry across chapters
      showSelectedChapter();
      renderCitations();
      render();
    });
  }

  // ── Read / Edit mode — Edit swaps the chapter body for the TipTap editor ──
  const modeRead = root.querySelector<HTMLButtonElement>('#cx-mode-read');
  const modeEdit = root.querySelector<HTMLButtonElement>('#cx-mode-edit');
  let activeEditor: ChapterEditor | null = null;

  function currentChapterEl(): HTMLElement | null {
    return Array.from(root.querySelectorAll<HTMLElement>('.cx-chapter'))
      .find((c) => (c.dataset.key ?? '') === selectedChapter) ?? null;
  }

  function toolbarBtn(label: string, title: string, run: (ed: ChapterEditor) => void): HTMLButtonElement {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'cx-edit-tool';
    b.textContent = label;
    b.title = title;
    b.setAttribute('aria-label', title); // glyph text is decorative; announce the action
    b.addEventListener('mousedown', (e) => e.preventDefault()); // keep editor selection
    b.addEventListener('click', () => { if (activeEditor) run(activeEditor); });
    return b;
  }

  function exitEdit(): void {
    activeEditor?.destroy();
    activeEditor = null;
    root.querySelector('.cx-edit-shell')?.remove();
    const bodyEl = currentChapterEl()?.querySelector<HTMLElement>('.cx-body');
    if (bodyEl) bodyEl.hidden = false;
    if (chapterSelect) chapterSelect.disabled = false;
  }

  function enterEdit(): void {
    const ch = currentChapterEl();
    const bodyEl = ch?.querySelector<HTMLElement>('.cx-body');
    if (!ch || !bodyEl) return;
    const pristine = bodyByKey.get(selectedChapter)?.html ?? bodyEl.innerHTML;
    bodyEl.hidden = true;

    const shell = document.createElement('div');
    shell.className = 'cx-edit-shell';
    const toolbar = document.createElement('div');
    toolbar.className = 'cx-edit-toolbar';
    toolbar.setAttribute('role', 'toolbar');
    toolbar.setAttribute('aria-label', 'Formatting');
    toolbar.append(
      toolbarBtn('B', 'Bold', (ed) => ed.editor.chain().focus().toggleBold().run()),
      toolbarBtn('i', 'Italic', (ed) => ed.editor.chain().focus().toggleItalic().run()),
      toolbarBtn('H', 'Heading', (ed) => ed.editor.chain().focus().toggleHeading({ level: 3 }).run()),
      toolbarBtn('❝', 'Quote', (ed) => ed.editor.chain().focus().toggleBlockquote().run()),
      toolbarBtn('•', 'Bulleted list', (ed) => ed.editor.chain().focus().toggleBulletList().run()),
    );
    const host = document.createElement('div');
    host.className = 'cx-edit-host';
    const actions = document.createElement('div');
    actions.className = 'cx-edit-actions';
    const saveEditBtn = document.createElement('button');
    saveEditBtn.type = 'button';
    saveEditBtn.className = 'cx-action';
    saveEditBtn.textContent = 'Save prose';
    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'cx-action is-secondary';
    cancelBtn.textContent = 'Cancel';
    const editStatus = document.createElement('p');
    editStatus.className = 'cx-status';
    editStatus.setAttribute('role', 'status');
    editStatus.setAttribute('aria-live', 'polite');
    actions.append(saveEditBtn, cancelBtn);
    shell.append(toolbar, host, actions, editStatus);
    bodyEl.insertAdjacentElement('afterend', shell);

    activeEditor = mountChapterEditor(host, pristine);
    if (chapterSelect) chapterSelect.disabled = true;

    cancelBtn.addEventListener('click', () => setMode('read'));
    saveEditBtn.addEventListener('click', async () => {
      if (!activeEditor) return;
      saveEditBtn.disabled = true;
      editStatus.textContent = 'Saving…';
      editStatus.classList.remove('is-error');
      try {
        const res = await fetch('/api/studio/book-md', {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ slug, chapterKey: selectedChapter, markdown: activeEditor.toMarkdown() }),
        });
        const json = await res.json();
        if (!json.ok) throw new Error(json.error || 'save failed');
        // Reload so the preview + visual anchors reflect the authoritative re-render.
        window.location.reload();
      } catch (err) {
        editStatus.textContent = `Save failed: ${(err as Error).message}`;
        editStatus.classList.add('is-error');
        saveEditBtn.disabled = false;
      }
    });
  }

  function setMode(mode: 'read' | 'edit'): void {
    const edit = mode === 'edit';
    modeRead?.classList.toggle('is-active', !edit);
    modeRead?.setAttribute('aria-pressed', String(!edit));
    modeEdit?.classList.toggle('is-active', edit);
    modeEdit?.setAttribute('aria-pressed', String(edit));
    root.classList.toggle('is-editing', edit);
    if (edit) enterEdit(); else exitEdit();
  }
  modeRead?.addEventListener('click', () => setMode('read'));
  modeEdit?.addEventListener('click', () => setMode('edit'));

  // ── Citations tab: predefined style (persisted) + this chapter's citations ──
  const citeForm = root.querySelector<HTMLFormElement>('.cx-cite-form');
  const citeSave = root.querySelector<HTMLElement>('#cx-cite-save');
  const citeListEl = root.querySelector<HTMLElement>('#cx-citations-list');

  function setCiteStatus(msg: string, state: '' | 'saved' | 'error'): void {
    if (!citeSave) return;
    citeSave.textContent = msg;
    citeSave.classList.toggle('is-saved', state === 'saved');
    citeSave.classList.toggle('is-error', state === 'error');
  }
  async function loadSavedFamily(): Promise<void> {
    try {
      const res = await fetch(`/api/studio/citation-style?slug=${encodeURIComponent(slug)}`);
      const json = await res.json();
      if (!json.ok) return;
      const match = citeForm?.querySelector<HTMLInputElement>(
        `input[name="citation-style"][value="${json.data.family}"]`);
      if (match) match.checked = true;
    } catch { /* keep the pre-checked default if the fetch fails */ }
  }
  citeForm?.addEventListener('change', async (ev) => {
    const t = ev.target as HTMLInputElement;
    if (t?.name !== 'citation-style' || !t.checked) return;
    setCiteStatus('Saving…', '');
    try {
      const res = await fetch('/api/studio/citation-style', {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, family: t.value }),
      });
      const json = await res.json();
      setCiteStatus(json.ok ? `Saved — the book prints in the ${t.value} style.`
        : `Couldn't save: ${json.error}`, json.ok ? 'saved' : 'error');
    } catch (e) {
      setCiteStatus(`Couldn't save: ${(e as Error).message}`, 'error');
    }
  });

  function renderCitations(): void {
    if (!citeListEl) return;
    citeListEl.textContent = '';
    const items = chapterByKey.get(selectedChapter)?.citations ?? [];
    if (!items.length) {
      const p = document.createElement('p');
      p.className = 'cx-empty';
      p.textContent = 'No Quran or hadith citations detected in this chapter.';
      citeListEl.appendChild(p);
      return;
    }
    for (const c of items) {
      const bq = document.createElement('blockquote');
      bq.className = 'bs-verse cx-cite-item';
      const ar = document.createElement('p');
      ar.className = 'bs-ar';
      ar.setAttribute('dir', 'rtl');
      ar.setAttribute('lang', 'ar');
      ar.textContent = c.ar;
      bq.appendChild(ar);
      if (c.tr) {
        const tr = document.createElement('p');
        tr.className = 'bs-tr';
        tr.textContent = c.tr;
        bq.appendChild(tr);
      }
      citeListEl.appendChild(bq);
    }
  }
  void loadSavedFamily();

  function normalize(p: Placement): Placement {
    const align = (['left', 'center', 'right'] as Align[]).includes(p.align) ? p.align : 'center';
    let flow: Flow = p.flow === 'wrap' ? 'wrap' : 'standalone';
    let width = Math.max(1, Math.min(100, Number(p.width_pct) || 60));
    if (align === 'center') flow = 'standalone';
    if (flow === 'wrap' && width > WRAP_MAX) flow = 'standalone';
    const page_fit = (['avoid', 'before', 'isolate-plate'] as PageFit[]).includes(p.page_fit) ? p.page_fit : 'avoid';
    let anchor_para: number | null = p.anchor_para == null ? null : Math.max(0, Math.floor(Number(p.anchor_para)));
    if (anchor_para != null && !Number.isFinite(anchor_para)) anchor_para = null;
    return { visual_id: p.visual_id, anchor: p.anchor, anchor_para, align, flow, width_pct: width, caption: p.caption ?? '', page_fit };
  }

  function markDirty(): void { dirty = true; saveBtn.disabled = false; setStatus(''); }

  function setStatus(msg: string, isError = false): void {
    statusEl.textContent = msg;
    statusEl.classList.toggle('is-error', isError);
  }

  function place(visualId: string, anchor: string, anchorPara: number | null = null): void {
    if (placements.some((p) => p.visual_id === visualId)) return;
    const v = visualsById.get(visualId);
    placements.push(normalize({
      visual_id: visualId, anchor, anchor_para: anchorPara, align: 'center', flow: 'standalone',
      width_pct: 60, caption: v?.caption ?? '', page_fit: 'avoid',
    } as Placement));
    selected = visualId;
    markDirty();
    render();
  }

  function remove(visualId: string): void {
    placements = placements.filter((p) => p.visual_id !== visualId);
    if (selected === visualId) selected = null;
    markDirty();
    render();
  }

  function update(visualId: string, patch: Partial<Placement>): void {
    const i = placements.findIndex((p) => p.visual_id === visualId);
    if (i < 0) return;
    placements[i] = normalize({ ...placements[i], ...patch });
    markDirty();
    render();
  }

  // ── render ──────────────────────────────────────────────────────────────
  function render(): void {
    // Reset every chapter to its pristine prose, then insert each placed figure
    // inline at the exact paragraph the renderer (applyLayout) would use.
    for (const { el, html } of bodyByKey.values()) el.innerHTML = html;
    const placedIds = new Set(placements.map((p) => p.visual_id));

    const firstKey = bodyByKey.keys().next().value ?? '';
    const byChapter = new Map<string, { idx: number; el: HTMLElement }[]>();
    for (const p of placements) {
      const v = visualsById.get(p.visual_id);
      if (!v) continue;
      const key = anchorKey(p.anchor);
      const target = bodyByKey.has(key) ? key : firstKey;
      if (!bodyByKey.has(target)) continue;
      const idx = p.anchor_para == null ? 1 : p.anchor_para; // null -> after intro (mirror)
      if (!byChapter.has(target)) byChapter.set(target, []);
      byChapter.get(target)!.push({ idx, el: figureEl(p, v) });
    }
    for (const [key, figs] of byChapter) insertFiguresInline(bodyByKey.get(key)!.el, figs);

    // palette = unplaced candidates for the selected chapter (+ book-level ones,
    // which have no resolved chapter and must stay reachable from any chapter)
    paletteEl.textContent = '';
    const unplaced = data.visuals.filter((v) =>
      !placedIds.has(v.id) && (v.chapter === selectedChapter || !v.chapter));
    if (!unplaced.length) {
      const p = document.createElement('p');
      p.className = 'cx-empty';
      p.textContent = !data.visuals.length
        ? 'No visual candidates for this book yet.'
        : 'No unplaced candidates for this chapter.';
      paletteEl.appendChild(p);
    } else {
      unplaced.forEach((v) => paletteEl.appendChild(paletteItemEl(v)));
    }
    if (scopeEl) {
      const ch = chapterByKey.get(selectedChapter);
      scopeEl.textContent = ch ? `Candidates for “${ch.title}”.` : '';
    }
    renderControls();
  }

  // Insert figures into a chapter body at their paragraph index, mirroring the
  // renderer's applyLayout: idx<=0 => chapter top; idx=N => after the Nth top-level
  // <p>; idx beyond the paragraph count => flushed at the chapter's end. Figures
  // sharing an index keep their placement order.
  function insertFiguresInline(bodyEl: HTMLElement, figs: { idx: number; el: HTMLElement }[]): void {
    const paras = Array.from(bodyEl.querySelectorAll<HTMLElement>(':scope > p'));
    const groups = new Map<number, HTMLElement[]>();
    for (const f of figs) {
      if (!groups.has(f.idx)) groups.set(f.idx, []);
      groups.get(f.idx)!.push(f.el);
    }
    for (const [idx, els] of groups) {
      if (idx <= 0) {
        const ref = bodyEl.firstChild;
        for (const el of els) bodyEl.insertBefore(el, ref);
      } else if (idx > paras.length) {
        for (const el of els) bodyEl.appendChild(el);
      } else {
        let ref: Element = paras[idx - 1];
        for (const el of els) { ref.insertAdjacentElement('afterend', el); ref = el; }
      }
    }
  }

  // Number of paragraphs whose vertical midpoint is above `clientY` — the
  // anchor_para "after paragraph N" (0 => chapter top). Mirrors applyLayout's
  // top-level <p> counting so a drop lands where the PDF will place the figure.
  function paraIndexAt(bodyEl: HTMLElement, clientY: number): { idx: number; paras: HTMLElement[] } {
    const paras = Array.from(bodyEl.querySelectorAll<HTMLElement>(':scope > p'));
    let idx = 0;
    for (const para of paras) {
      const r = para.getBoundingClientRect();
      if (clientY > r.top + r.height / 2) idx += 1; else break;
    }
    return { idx, paras };
  }

  // Drag the corner handle to resize a placed figure (width_pct). Delta-based so
  // it feels natural at any alignment; the growing edge is the handle's corner
  // (bottom-right normally, bottom-left when right-aligned). Live-updates the CSS
  // width during the drag and commits the snapped value on release.
  function startResize(e: PointerEvent, fig: HTMLElement, p: Placement): void {
    e.preventDefault();
    e.stopPropagation();
    const container = fig.parentElement; // the .cx-body containing block
    const refWidth = container ? container.clientWidth : fig.getBoundingClientRect().width;
    const startX = e.clientX;
    const startW = fig.getBoundingClientRect().width;
    const dir = p.align === 'right' ? -1 : 1;
    const max = p.flow === 'wrap' ? WRAP_MAX : 100;
    fig.draggable = false; // suspend the move-drag while resizing
    fig.classList.add('is-resizing');
    let pct = p.width_pct;
    const onMove = (ev: PointerEvent): void => {
      const w = startW + (ev.clientX - startX) * dir;
      pct = Math.max(10, Math.min(max, Math.round((w / refWidth) * 20) * 5));
      fig.style.setProperty('--cx-w', `${pct}%`);
    };
    const onUp = (): void => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      fig.classList.remove('is-resizing');
      fig.draggable = true;
      if (pct !== p.width_pct) update(p.visual_id, { width_pct: pct });
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }

  function figureEl(p: Placement, v: Visual): HTMLElement {
    const fig = document.createElement('figure');
    fig.className = `cx-fig flow-${p.flow} align-${p.align} page-fit-${p.page_fit}`;
    fig.style.setProperty('--cx-w', `${p.width_pct}%`);
    fig.tabIndex = 0;
    fig.setAttribute('role', 'group');
    fig.setAttribute('aria-label', `Figure: ${p.caption || v.id}`);
    fig.draggable = true;
    if (p.visual_id === selected) fig.classList.add('is-selected');

    const badge = document.createElement('span');
    badge.className = 'cx-fig-badge';
    badge.textContent = v.type;
    fig.appendChild(badge);

    const img = document.createElement('img');
    img.src = v.src;
    img.alt = p.caption || v.id;
    fig.appendChild(img);

    const dupTitle = p.caption && v.embedded_title
      && p.caption.trim().toLowerCase() === v.embedded_title.trim().toLowerCase();
    if (p.caption && !dupTitle) {
      const cap = document.createElement('figcaption');
      cap.textContent = p.caption;
      fig.appendChild(cap);
    }

    const selectAndRefine = (): void => { selected = p.visual_id; activateTab('refine'); render(); };
    fig.addEventListener('click', selectAndRefine);
    fig.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectAndRefine(); }
    });
    fig.addEventListener('dragstart', (e) => {
      e.dataTransfer?.setData('text/plain', p.visual_id);
    });

    const handle = document.createElement('span');
    handle.className = 'cx-fig-handle';
    handle.setAttribute('aria-hidden', 'true');
    handle.title = 'Drag to resize';
    handle.addEventListener('pointerdown', (e) => startResize(e, fig, p));
    handle.addEventListener('click', (e) => e.stopPropagation()); // don't select on a resize click
    fig.appendChild(handle);
    return fig;
  }

  function paletteItemEl(v: Visual): HTMLElement {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'cx-palette-item';
    item.draggable = true;
    item.setAttribute('aria-label', `Place ${v.caption || v.id}`);
    const img = document.createElement('img');
    img.src = v.src; img.alt = '';
    const meta = document.createElement('span');
    meta.className = 'cx-palette-meta';
    const cap = document.createElement('p');
    cap.className = 'cx-palette-cap';
    cap.textContent = v.caption || v.id;
    const type = document.createElement('p');
    type.className = 'cx-palette-type';
    type.textContent = v.cleaned ? v.type : `${v.type} · uncleaned`;
    meta.append(cap, type);
    item.append(img, meta);
    const target = v.suggested_anchor && chapterByKey.get(anchorKey(v.suggested_anchor))
      ? v.suggested_anchor
      : (data.chapters[0]?.anchor ?? '');
    item.addEventListener('click', () => place(v.id, target));
    item.addEventListener('dragstart', (e) => e.dataTransfer?.setData('text/plain', v.id));
    return item;
  }

  // ── controls panel ────────────────────────────────────────────────────────
  function renderControls(): void {
    controlsEl.textContent = '';
    const p = selected ? placements.find((x) => x.visual_id === selected) : undefined;
    if (!p) {
      const hint = document.createElement('p');
      hint.className = 'cx-hint';
      hint.textContent = 'Select a placed figure in the book to refine its alignment, width, position, and caption.';
      controlsEl.appendChild(hint);
      return;
    }

    controlsEl.appendChild(alignField(p));
    controlsEl.appendChild(flowField(p));
    controlsEl.appendChild(widthField(p));
    controlsEl.appendChild(anchorField(p));
    controlsEl.appendChild(positionField(p));
    controlsEl.appendChild(captionField(p));
    controlsEl.appendChild(pageFitField(p));

    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'cx-delete';
    del.textContent = 'Remove from book';
    del.addEventListener('click', () => remove(p.visual_id));
    controlsEl.appendChild(del);
  }

  function field(label: string, control: HTMLElement): HTMLElement {
    const wrap = document.createElement('div');
    wrap.className = 'cx-field';
    const l = document.createElement('label');
    l.textContent = label;
    wrap.append(l, control);
    return wrap;
  }

  function alignField(p: Placement): HTMLElement {
    const row = document.createElement('div');
    row.className = 'cx-btn-row';
    (['left', 'center', 'right'] as Align[]).forEach((a) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cx-toggle';
      b.textContent = a;
      b.setAttribute('aria-pressed', String(p.align === a));
      b.addEventListener('click', () => update(p.visual_id, { align: a }));
      row.appendChild(b);
    });
    return field('Alignment', row);
  }

  function flowField(p: Placement): HTMLElement {
    const row = document.createElement('div');
    row.className = 'cx-btn-row';
    (['standalone', 'wrap'] as Flow[]).forEach((f) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cx-toggle';
      b.textContent = f === 'wrap' ? 'wrap text' : 'standalone';
      b.setAttribute('aria-pressed', String(p.flow === f));
      b.disabled = f === 'wrap' && p.align === 'center';
      // Choosing wrap clamps width into the contract (<=50%) so the user's intent
      // is honored rather than silently reverted to standalone.
      b.addEventListener('click', () => update(
        p.visual_id,
        f === 'wrap' ? { flow: f, width_pct: Math.min(p.width_pct, WRAP_MAX) } : { flow: f },
      ));
      row.appendChild(b);
    });
    return field('Flow', row);
  }

  function widthField(p: Placement): HTMLElement {
    const input = document.createElement('input');
    input.type = 'range';
    input.min = '10';
    input.max = String(p.flow === 'wrap' ? WRAP_MAX : 100);
    input.step = '5';
    input.value = String(p.width_pct);
    input.setAttribute('aria-label', 'Width percent');
    input.addEventListener('input', () => update(p.visual_id, { width_pct: Number(input.value) }));
    return field(`Width — ${p.width_pct}%`, input);
  }

  function anchorField(p: Placement): HTMLElement {
    const sel = document.createElement('select');
    sel.setAttribute('aria-label', 'Anchor chapter');
    data.chapters.forEach((c) => {
      const o = document.createElement('option');
      o.value = c.anchor;
      o.textContent = c.title;
      o.selected = anchorKey(c.anchor) === anchorKey(p.anchor);
      sel.appendChild(o);
    });
    // Moving to a different chapter resets the paragraph position to the default.
    sel.addEventListener('change', () => update(p.visual_id, { anchor: sel.value, anchor_para: null }));
    return field('Anchor chapter', sel);
  }

  function positionField(p: Placement): HTMLElement {
    const paras = chapterByKey.get(anchorKey(p.anchor))?.paras ?? 0;
    const sel = document.createElement('select');
    const opt = (value: string, label: string, selected: boolean) => {
      const o = document.createElement('option');
      o.value = value; o.textContent = label; o.selected = selected;
      sel.appendChild(o);
    };
    sel.setAttribute('aria-label', 'Position in chapter');
    opt('', 'After intro (default)', p.anchor_para == null);
    opt('0', 'Chapter top', p.anchor_para === 0);
    for (let i = 1; i <= paras; i += 1) opt(String(i), `After paragraph ${i}`, p.anchor_para === i);
    sel.addEventListener('change', () =>
      update(p.visual_id, { anchor_para: sel.value === '' ? null : Number(sel.value) }));
    return field('Position in chapter', sel);
  }

  function captionField(p: Placement): HTMLElement {
    const input = document.createElement('input');
    input.type = 'text';
    input.value = p.caption;
    input.placeholder = 'Caption (optional)';
    input.setAttribute('aria-label', 'Caption');
    input.addEventListener('change', () => update(p.visual_id, { caption: input.value }));
    return field('Caption', input);
  }

  function pageFitField(p: Placement): HTMLElement {
    const sel = document.createElement('select');
    sel.setAttribute('aria-label', 'Page fit');
    (['avoid', 'before', 'isolate-plate'] as PageFit[]).forEach((f) => {
      const o = document.createElement('option');
      o.value = f;
      o.textContent = f === 'avoid' ? 'keep together' : f === 'before' ? 'start on new page' : 'own page';
      o.selected = p.page_fit === f;
      sel.appendChild(o);
    });
    sel.addEventListener('change', () => update(p.visual_id, { page_fit: sel.value as PageFit }));
    return field('Page fit', sel);
  }

  // ── drag targets: drop a visual onto a specific paragraph, not just a chapter ─
  let dropMarker: HTMLElement | null = null;
  function clearDropMarker(): void {
    dropMarker?.classList.remove('cx-drop-before', 'cx-drop-after');
    dropMarker = null;
  }
  function showDropMarker(bodyEl: HTMLElement, clientY: number): void {
    const { idx, paras } = paraIndexAt(bodyEl, clientY);
    clearDropMarker();
    if (idx <= 0) {
      const first = bodyEl.firstElementChild as HTMLElement | null;
      if (first) { first.classList.add('cx-drop-before'); dropMarker = first; }
    } else if (idx <= paras.length) {
      paras[idx - 1].classList.add('cx-drop-after'); dropMarker = paras[idx - 1];
    }
  }
  root.querySelectorAll<HTMLElement>('.cx-chapter').forEach((ch) => {
    const body = ch.querySelector<HTMLElement>('.cx-body');
    ch.addEventListener('dragover', (e) => {
      e.preventDefault();
      ch.classList.add('cx-dragover');
      if (body) showDropMarker(body, e.clientY);
    });
    ch.addEventListener('dragleave', () => { ch.classList.remove('cx-dragover'); clearDropMarker(); });
    ch.addEventListener('drop', (e) => {
      e.preventDefault();
      ch.classList.remove('cx-dragover');
      clearDropMarker();
      const id = e.dataTransfer?.getData('text/plain');
      const anchor = ch.dataset.anchor ?? '';
      if (!id || !anchor) return;
      const anchor_para = body ? paraIndexAt(body, e.clientY).idx : null;
      if (placements.some((p) => p.visual_id === id)) update(id, { anchor, anchor_para });
      else place(id, anchor, anchor_para);
    });
  });

  // ── persistence ───────────────────────────────────────────────────────────
  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    setStatus('Saving…');
    try {
      const res = await fetch('/api/studio/visual-layout', {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, placements }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || 'save failed');
      dirty = false;
      setStatus(`Saved ${json.data.count} placement(s).`);
    } catch (err) {
      setStatus(`Save failed: ${(err as Error).message}`, true);
      saveBtn.disabled = false;
    }
  });

  genBtn.addEventListener('click', async () => {
    if (dirty) { setStatus('Save the layout before generating.', true); return; }
    genBtn.disabled = true;
    setStatus('Rendering PDF… this can take a minute.');
    try {
      const res = await fetch('/api/studio/generate-book-pdf', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || 'render failed');
      setStatus(`PDF ready (${json.data.kb} KB).`);
    } catch (err) {
      setStatus(`Generate failed: ${(err as Error).message}`, true);
    } finally {
      genBtn.disabled = false;
    }
  });

  saveBtn.disabled = true;
  showSelectedChapter();
  renderCitations();
  render();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
