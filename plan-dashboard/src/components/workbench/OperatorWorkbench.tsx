import { startTransition, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { BookMarked, BrainCircuit, FileSearch, Sparkles } from 'lucide-react';
import CorpusExplorer from '../corpus-mock/CorpusExplorer';
import EditorialCards from '../reader/poc/EditorialCards';
import type { CardDef } from '../../lib/reader/editorial';
import type { MockAtom, Tradition } from '../../lib/db/knowledge';
import type { ChapterDef, WorkspaceChapter } from '../../lib/reader/book-workspace';

type Mode = 'review' | 'policy' | 'knowledge' | 'augment';

interface Props {
  slug: string;
  bookTitle: string;
  chapters: WorkspaceChapter[];
  chapterDefs: ChapterDef[];
  cardDefs: CardDef[];
  /** Pre-select a chapter by slug — used by the Library→Studio deep-link (R-1). */
  initialChapterId?: string;
}

const MODES: { id: Mode; label: string; icon: typeof FileSearch }[] = [
  { id: 'review',    label: 'Pipeline review',   icon: FileSearch  },
  { id: 'policy',    label: 'Editorial policy',   icon: BookMarked  },
  { id: 'knowledge', label: 'Knowledge lens',     icon: BrainCircuit },
  { id: 'augment',   label: 'Enrichment plan',    icon: Sparkles    },
];

const BOOK_TRADITION: Tradition = 'fatimid-ismaili';

export default function OperatorWorkbench({ slug, bookTitle, chapters, chapterDefs, cardDefs, initialChapterId }: Props) {
  const [mode, setMode]           = useState<Mode>('review');
  const defaultChapter = initialChapterId && chapters.some((c) => c.slug === initialChapterId)
    ? initialChapterId
    : chapters[0]?.slug ?? '';
  const [chapterId, setChapterId] = useState(defaultChapter);
  const [stageId, setStageId]     = useState(lastAvailableStageId(chapters[0]) ?? '');
  const [selectedAtoms, setSelectedAtoms] = useState<MockAtom[]>([]);
  const deferredAtoms = useDeferredValue(selectedAtoms);

  const activeChapter = useMemo(
    () => chapters.find((c) => c.slug === chapterId) ?? chapters[0],
    [chapterId, chapters],
  );

  useEffect(() => {
    if (!activeChapter) return;
    setStageId(lastAvailableStageId(activeChapter) ?? activeChapter.stages[0]?.id ?? '');
    window.dispatchEvent(new CustomEvent('studio:chapter-change', { detail: { chapter: activeChapter.slug } }));
  }, [activeChapter]);

  const activeStage = useMemo(
    () => activeChapter?.stages.find((s) => s.id === stageId) ?? activeChapter?.stages.find((s) => s.available),
    [activeChapter, stageId],
  );

  const activeMetric = useMemo(
    () => activeChapter?.metrics.find((m) => m.id === activeStage?.id),
    [activeChapter, activeStage],
  );

  const stageStats    = useMemo(() => buildStageStats(chapters), [chapters]);
  const enrichmentPlan = useMemo(() => buildEnrichmentPlan(activeChapter, deferredAtoms), [activeChapter, deferredAtoms]);

  const proseContext = useMemo(() => ({
    book: bookTitle,
    chapter: activeChapter?.title ?? '',
    paragraph: stageExcerpt(activeStage?.html ?? ''),
  }), [activeChapter, activeStage, bookTitle]);

  if (!activeChapter || !activeStage) {
    return <p className="wb-empty">No chapter workspace available yet.</p>;
  }

  return (
    <div className="wb-shell">
      {/* ── Head ─────────────────────────────────────────── */}
      <header className="wb-head">
        <div>
          <span className="wb-eyebrow">Operator workbench</span>
          <h1>{bookTitle}</h1>
        </div>
        <nav className="wb-quick-actions" aria-label="Quick links">
          <a href="/studio">All books</a>
          <a href={`/library/${slug}`}>Read in Library</a>
          <a href="/corpus">Corpus</a>
        </nav>
      </header>

      {/* ── Metrics ──────────────────────────────────────── */}
      <div className="wb-metric-strip" role="region" aria-label="Book metrics">
        <div className="wb-metric tone-neutral">
          <strong>{stageStats.chapterCount}</strong>
          <span>Chapters</span>
        </div>
        <div className="wb-metric tone-good">
          <strong>{stageStats.approvedStageCount}/{stageStats.availableStageCount}</strong>
          <span>Approved</span>
        </div>
        <div className="wb-metric tone-accent">
          <strong>{stageStats.avgEnrichmentLift}</strong>
          <span>Avg enrichment lift</span>
        </div>
      </div>

      {/* ── Mode tabs ────────────────────────────────────── */}
      <nav className="wb-tabs" role="tablist" aria-label="Workbench modes">
        {MODES.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            role="tab"
            aria-selected={mode === id}
            className={`wb-tab${mode === id ? ' is-active' : ''}`}
            onClick={() => startTransition(() => setMode(id))}
          >
            <Icon size={15} aria-hidden="true" />
            {label}
          </button>
        ))}
      </nav>

      {/* ── Body ─────────────────────────────────────────── */}
      <div className="wb-body">
        {/* Chapter rail */}
        <aside className="wb-chapter-rail" aria-label="Chapter selection">
          <div className="wb-chapter-rail-head">
            <h2>Chapters</h2>
            <span>{stageStats.reviewedChapterCount} reviewed</span>
          </div>
          {chapterDefs.map((ch) => {
            const details = chapters.find((c) => c.slug === ch.id);
            const status  = chapterStatus(details);
            return (
              <button
                key={ch.id}
                className={`wb-chapter-btn${chapterId === ch.id ? ' is-active' : ''}`}
                onClick={() => startTransition(() => setChapterId(ch.id))}
              >
                <span>
                  <strong>{ch.title}</strong>
                  <span className="wb-ch-sub">{status.detail}</span>
                </span>
                <span className={`wb-status-pill tone-${status.tone}`}>{status.label}</span>
              </button>
            );
          })}
        </aside>

        {/* Canvas */}
        <main className="wb-canvas" role="tabpanel" aria-label={MODES.find((m) => m.id === mode)?.label}>

          {/* ── Pipeline review ──────────────────────────── */}
          {mode === 'review' && (
            <>
              <div className="wb-stage-tabs" role="tablist" aria-label="Pipeline stages">
                {activeChapter.stages.map((stage) => (
                  <button
                    key={stage.id}
                    role="tab"
                    aria-selected={stage.id === activeStage.id}
                    className={`wb-stage-tab${stage.id === activeStage.id ? ' is-active' : ''}`}
                    disabled={!stage.available}
                    onClick={() => startTransition(() => setStageId(stage.id))}
                  >
                    <strong>{stage.label}</strong>
                    <span>{stage.available ? stage.slice : 'Not produced yet'}</span>
                  </button>
                ))}
              </div>

              <article className="wb-surface">
                <div className="wb-surface-head">
                  <h3>{activeStage.label}</h3>
                  <span>{activeMetric?.words ?? 0} words · {activeMetric?.sentences ?? 0} sentences</span>
                </div>

                {activeStage.available ? (
                  <div className="wb-stage-copy" dangerouslySetInnerHTML={{ __html: activeStage.html }} />
                ) : (
                  <p className="wb-empty">This stage has not been produced yet.</p>
                )}

                <div className="wb-note">
                  <h4>What to inspect</h4>
                  <p>{reviewPrompt(activeStage.id)}</p>
                </div>

                {activeMetric && (
                  <dl className="wb-kv">
                    <dt>Word delta</dt>
                    <dd>{activeMetric.deltaPct == null ? 'Baseline' : formatDelta(activeMetric.deltaPct)}</dd>
                    <dt>Compared to</dt>
                    <dd>{activeMetric.comparedTo ?? 'starting point'}</dd>
                    <dt>Review status</dt>
                    <dd>
                      {Object.values(activeChapter.reviewed).filter((r) => r?.approved).length > 0
                        ? `${Object.values(activeChapter.reviewed).filter((r) => r?.approved).length} approvals`
                        : 'No approvals yet'}
                    </dd>
                  </dl>
                )}
              </article>
            </>
          )}

          {/* ── Editorial policy ─────────────────────────── */}
          {mode === 'policy' && (
            <div className="wb-surface">
              <div className="wb-surface-head">
                <h3>Canonical decisions</h3>
                <span>Book scope · chapter overrides</span>
              </div>
              <EditorialCards slug={slug} chapters={chapterDefs} cardDefs={cardDefs} />
            </div>
          )}

          {/* ── Knowledge lens ───────────────────────────── */}
          {mode === 'knowledge' && (
            <CorpusExplorer
              selectedAtoms={selectedAtoms}
              onSelectedAtomsChange={setSelectedAtoms}
              prose={proseContext}
              bookTradition={BOOK_TRADITION}
            />
          )}

          {/* ── Enrichment plan ──────────────────────────── */}
          {mode === 'augment' && (
            <div className="wb-augment-pair">
              <div className="wb-surface">
                <div className="wb-surface-head">
                  <h3>Selected atom tray</h3>
                  <span>{deferredAtoms.length} selected</span>
                </div>
                {deferredAtoms.length === 0 ? (
                  <p className="wb-empty">
                    Nothing in the tray yet. Open the Knowledge lens, search a concept, and add atoms you want to carry into this chapter.
                  </p>
                ) : (
                  <div className="wb-chip-list">
                    {deferredAtoms.map((atom) => (
                      <div key={atom.id} className="wb-atom-card">
                        <div className="wb-atom-head">
                          <span className={`cm-badge type-${atom.type}`}>{atom.type}</span>
                          <span className="wb-source-chip">{atom.source_ref}</span>
                        </div>
                        <strong>{atom.gloss}</strong>
                        <p>{atom.text_en}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="wb-surface">
                <div className="wb-surface-head">
                  <h3>Enrichment brief</h3>
                  <span>Ready for the next authoring pass</span>
                </div>
                <div className="wb-brief-block">
                  <h4>Frame</h4>
                  <p>{enrichmentPlan.frame}</p>
                </div>
                <div className="wb-brief-block">
                  <h4>Anchors</h4>
                  <ul className="wb-list">
                    {enrichmentPlan.anchors.map((a) => <li key={a}>{a}</li>)}
                  </ul>
                </div>
                <div className="wb-brief-block">
                  <h4>Draft insertion</h4>
                  <p>{enrichmentPlan.draft}</p>
                </div>
                <div className="wb-brief-block">
                  <h4>Guardrails</h4>
                  <ul className="wb-list">
                    {enrichmentPlan.guardrails.map((g) => <li key={g}>{g}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

/* ── Helpers ──────────────────────────────────────────────── */

function lastAvailableStageId(chapter?: WorkspaceChapter) {
  return chapter?.stages.filter((s) => s.available).at(-1)?.id;
}

function buildStageStats(chapters: WorkspaceChapter[]) {
  const availableStageCount = chapters.reduce(
    (n, c) => n + c.stages.filter((s) => s.available).length, 0,
  );
  const approvedStageCount = chapters.reduce(
    (n, c) => n + Object.values(c.reviewed).filter((r) => r?.approved).length, 0,
  );
  const enrichmentDeltas = chapters
    .flatMap((c) => c.metrics)
    .filter((m) => m.id === 'augmented' && typeof m.deltaPct === 'number')
    .map((m) => m.deltaPct as number);
  return {
    chapterCount: chapters.length,
    availableStageCount,
    approvedStageCount,
    reviewedChapterCount: chapters.filter(
      (c) => Object.values(c.reviewed).some((r) => r?.approved),
    ).length,
    avgEnrichmentLift: enrichmentDeltas.length
      ? `${Math.round(enrichmentDeltas.reduce((s, v) => s + v, 0) / enrichmentDeltas.length)}%`
      : 'n/a',
  };
}

function chapterStatus(chapter?: WorkspaceChapter) {
  const available = chapter?.stages.filter((s) => s.available).length ?? 0;
  const approved  = Object.values(chapter?.reviewed ?? {}).filter((r) => r?.approved).length;
  if (approved > 0) return { label: `${approved} approved`, detail: `${available} stages available`, tone: 'good' } as const;
  return {
    label: available > 0 ? 'Needs review' : 'Not ready',
    detail: available > 0 ? `${available} stages ready` : 'No generated stages yet',
    tone: available > 0 ? 'accent' : 'muted',
  } as const;
}

function reviewPrompt(stageId: string) {
  if (stageId === 'source')     return 'Check source fidelity and confirm chapter boundaries are clean before downstream changes hide errors.';
  if (stageId === 'core')       return 'Look for repeated material and structural noise. This is where weak segmentation surfaces.';
  if (stageId === 'denoised')   return 'Make sure cleanup removed junk without flattening voice or deleting meaningful terms.';
  if (stageId === 'normalized') return 'Review register, clarity, and consistency. Should improve readability without changing the argument.';
  if (stageId === 'augmented')  return 'Verify enrichment deepens the chapter and does not smuggle in material that changes the original teaching.';
  return 'Confirm the final narrative additions feel like deliberate editorial support rather than a separate document.';
}

function stageExcerpt(html: string) {
  const text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  return text ? text.slice(0, 320) : '';
}

function buildEnrichmentPlan(chapter: WorkspaceChapter | undefined, atoms: MockAtom[]) {
  if (!chapter || atoms.length === 0) {
    return {
      frame: 'Build the augmentation tray first. A good enrichment pass starts with concept selection, not with writing into an empty context.',
      anchors: ['Pick one concept from the knowledge lens.', 'Add at least one scripture anchor and one teaching anchor.', 'Return here to generate a concrete insertion brief.'],
      draft: 'No draft yet.',
      guardrails: [
        "Keep added material subordinate to the chapter's original claim.",
        'Do not add atoms that cross the tradition firewall.',
        'Prefer concise bridges over explanatory detours.',
      ],
    };
  }
  const lead      = atoms.slice(0, 3);
  const scripture = atoms.filter((a) => a.type === 'quran' || a.type === 'hadith');
  const doctrine  = atoms.filter((a) => a.type === 'doctrine' || a.type === 'term' || a.type === 'etymology');
  return {
    frame: `Enrich ${chapter.title} by anchoring the live prose in ${lead.map((a) => a.gloss.toLowerCase()).join(', ')} without letting the augmentation overpower the chapter's own argument.`,
    anchors: atoms.slice(0, 5).map((a) => `${a.gloss} (${a.source_ref})`),
    draft: `After the chapter's main claim, add a short bridge connecting it to ${lead[0]?.gloss.toLowerCase()}. Support with ${scripture[0]?.source_ref ?? 'one primary text reference'} and land the point with ${doctrine[0]?.gloss.toLowerCase() ?? 'one interpretive teaching'}.`,
    guardrails: [
      scripture.length > 0 ? 'Lead with the strongest scripture or hadith anchor before paraphrasing doctrine.' : 'Add at least one scripture or hadith anchor before approving this enrichment.',
      doctrine.length > 0 ? "Use doctrinal atoms to interpret, not replace, the chapter's own language." : 'Bring in one teaching or term atom so the enrichment is explanatory, not merely referential.',
      'Keep the insertion short enough that the original chapter still feels primary.',
    ],
  };
}

function formatDelta(deltaPct: number) {
  return `${deltaPct > 0 ? '+' : ''}${deltaPct}%`;
}
