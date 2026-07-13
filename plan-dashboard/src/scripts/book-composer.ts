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
type Align = 'left' | 'center' | 'right';
type Flow = 'wrap' | 'standalone';
type PageFit = 'avoid' | 'before' | 'isolate-plate';

interface Visual {
  id: string; type: string; caption: string; file: string; src: string;
  suggested_anchor: string; cleaned: boolean; embedded_title: string;
}
interface Chapter { anchor: string; key: string; title: string; paras: number; }
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
  let placements: Placement[] = data.placements.map(normalize);
  let selected: string | null = null;
  let dirty = false;

  const paletteEl = root.querySelector<HTMLElement>('#cx-palette-list')!;
  const controlsEl = root.querySelector<HTMLElement>('#cx-controls')!;
  const saveBtn = root.querySelector<HTMLButtonElement>('#cx-save')!;
  const genBtn = root.querySelector<HTMLButtonElement>('#cx-generate')!;
  const statusEl = root.querySelector<HTMLElement>('#cx-status')!;

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

  function place(visualId: string, anchor: string): void {
    if (placements.some((p) => p.visual_id === visualId)) return;
    const v = visualsById.get(visualId);
    placements.push(normalize({
      visual_id: visualId, anchor, anchor_para: null, align: 'center', flow: 'standalone',
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
    root.querySelectorAll<HTMLElement>('.cx-figures').forEach((z) => { z.textContent = ''; });
    const placedIds = new Set(placements.map((p) => p.visual_id));

    for (const p of placements) {
      const v = visualsById.get(p.visual_id);
      if (!v) continue;
      const key = anchorKey(p.anchor);
      const zone = root.querySelector<HTMLElement>(`.cx-figures[data-key="${cssEsc(key)}"]`)
        || root.querySelector<HTMLElement>('.cx-figures');
      if (!zone) continue;
      zone.appendChild(figureEl(p, v));
    }

    // palette = unplaced visuals
    paletteEl.textContent = '';
    const unplaced = data.visuals.filter((v) => !placedIds.has(v.id));
    if (!unplaced.length) {
      const p = document.createElement('p');
      p.className = 'cx-empty';
      p.textContent = placedIds.size ? 'All candidates placed.' : 'No visual candidates for this book yet.';
      paletteEl.appendChild(p);
    } else {
      unplaced.forEach((v) => paletteEl.appendChild(paletteItemEl(v)));
    }
    renderControls();
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

    fig.addEventListener('click', () => { selected = p.visual_id; render(); });
    fig.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selected = p.visual_id; render(); }
    });
    fig.addEventListener('dragstart', (e) => {
      e.dataTransfer?.setData('text/plain', p.visual_id);
    });
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
    if (!selected) {
      controlsEl.hidden = true;
      return;
    }
    const p = placements.find((x) => x.visual_id === selected);
    if (!p) { controlsEl.hidden = true; return; }
    controlsEl.hidden = false;

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

  // ── drag targets: chapters accept a moved/placed visual ───────────────────
  root.querySelectorAll<HTMLElement>('.cx-chapter').forEach((ch) => {
    ch.addEventListener('dragover', (e) => { e.preventDefault(); ch.classList.add('cx-dragover'); });
    ch.addEventListener('dragleave', () => ch.classList.remove('cx-dragover'));
    ch.addEventListener('drop', (e) => {
      e.preventDefault();
      ch.classList.remove('cx-dragover');
      const id = e.dataTransfer?.getData('text/plain');
      const anchor = ch.dataset.anchor ?? '';
      if (!id || !anchor) return;
      if (placements.some((p) => p.visual_id === id)) update(id, { anchor });
      else place(id, anchor);
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
  render();
}

function cssEsc(s: string): string {
  return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/["\\]/g, '\\$&');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
