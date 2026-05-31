import { startTransition, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { BookMarked, BrainCircuit, Compass, FileSearch, Layers3, Sparkles } from 'lucide-react';
import CorpusExplorer from '../corpus-mock/CorpusExplorer';
import EditorialCards from '../reader/poc/EditorialCards';
import type { CardDef } from '../../lib/reader/editorial';
import type { MockAtom, Tradition } from '../../data/corpus-mock-sample';
import type { ChapterDef, WorkspaceChapter } from '../../lib/reader/book-workspace';

type Mode = 'review' | 'policy' | 'knowledge' | 'augment';

interface RecommendationItem {
  title: string;
  reason: string;
}

interface RecommendationSummary {
  accept: RecommendationItem[];
  reject: RecommendationItem[];
}

interface Props {
  slug: string;
  bookTitle: string;
  chapters: WorkspaceChapter[];
  chapterDefs: ChapterDef[];
  cardDefs: CardDef[];
  recommendationSummary: RecommendationSummary;
}

const MODES: { id: Mode; label: string; blurb: string; icon: typeof Compass }[] = [
  { id: 'review', label: 'Pipeline review', blurb: 'Inspect chapter flow, stage deltas, and review coverage.', icon: FileSearch },
  { id: 'policy', label: 'Editorial policy', blurb: 'Tune canonical decisions and chapter overrides without leaving the shell.', icon: BookMarked },
  { id: 'knowledge', label: 'Knowledge lens', blurb: 'Search concepts, compare evidence, and build an augmentation tray.', icon: BrainCircuit },
  { id: 'augment', label: 'Enrichment plan', blurb: 'Turn selected atoms into a concrete augmentation brief for the active chapter.', icon: Sparkles },
];

const BOOK_TRADITION: Tradition = 'fatimid-ismaili';

export default function OperatorWorkbench({
  slug,
  bookTitle,
  chapters,
  chapterDefs,
  cardDefs,
  recommendationSummary,
}: Props) {
  const [mode, setMode] = useState<Mode>('review');
  const [chapterId, setChapterId] = useState(chapters[0]?.slug ?? '');
  const [stageId, setStageId] = useState(lastAvailableStageId(chapters[0]) ?? '');
  const [selectedAtoms, setSelectedAtoms] = useState<MockAtom[]>([]);
  const deferredAtoms = useDeferredValue(selectedAtoms);

  const activeChapter = useMemo(
    () => chapters.find((chapter) => chapter.slug === chapterId) ?? chapters[0],
    [chapterId, chapters],
  );

  useEffect(() => {
    if (!activeChapter) return;
    setStageId(lastAvailableStageId(activeChapter) ?? activeChapter.stages[0]?.id ?? '');
    window.dispatchEvent(new CustomEvent('studio:chapter-change', { detail: { chapter: activeChapter.slug } }));
  }, [activeChapter]);

  const activeStage = useMemo(
    () => activeChapter?.stages.find((stage) => stage.id === stageId) ?? activeChapter?.stages.find((stage) => stage.available),
    [activeChapter, stageId],
  );

  const activeMetric = useMemo(
    () => activeChapter?.metrics.find((metric) => metric.id === activeStage?.id),
    [activeChapter, activeStage],
  );

  const stageStats = useMemo(() => buildStageStats(chapters), [chapters]);
  const chapterSummary = useMemo(() => buildChapterSummary(activeChapter), [activeChapter]);
  const proseContext = useMemo(
    () => ({
      book: bookTitle,
      chapter: activeChapter?.title ?? 'Chapter review',
      paragraph: stageExcerpt(activeStage?.html ?? ''),
    }),
    [activeChapter, activeStage, bookTitle],
  );
  const enrichmentPlan = useMemo(
    () => buildEnrichmentPlan(activeChapter, deferredAtoms),
    [activeChapter, deferredAtoms],
  );

  if (!activeChapter || !activeStage) {
    return <p className="wb-empty">No chapter workspace is available yet.</p>;
  }

  return (
    <div className="wb-shell">
      <aside className="wb-rail">
        <div className="wb-rail-head">
          <span className="wb-eyebrow">Operator workbench</span>
          <h1 className="wb-title">{bookTitle}</h1>
          <p className="wb-subtitle">
            One shell for review, editorial policy, intelligence lookup, and augmentation planning.
          </p>
        </div>

        <div className="wb-metric-grid">
          <MetricCard label="Chapters in scope" value={String(stageStats.chapterCount)} tone="neutral" />
          <MetricCard label="Approved checkpoints" value={`${stageStats.approvedStageCount}/${stageStats.availableStageCount}`} tone="good" />
          <MetricCard label="Average enrichment lift" value={stageStats.avgEnrichmentLift} tone="accent" />
        </div>

        <nav className="wb-mode-list" aria-label="Workbench modes">
          {MODES.map(({ id, label, blurb, icon: Icon }) => (
            <button
              key={id}
              className={`wb-mode-btn ${mode === id ? 'is-active' : ''}`}
              onClick={() => startTransition(() => setMode(id))}
            >
              <span className="wb-mode-icon"><Icon size={17} /></span>
              <span>
                <strong>{label}</strong>
                <span>{blurb}</span>
              </span>
            </button>
          ))}
        </nav>

        <section className="wb-chapter-list" aria-label="Book chapters">
          <div className="wb-panel-head">
            <h2>Chapter focus</h2>
            <span>{stageStats.reviewedChapterCount} reviewed</span>
          </div>
          {chapterDefs.map((chapter) => {
            const details = chapters.find((candidate) => candidate.slug === chapter.id);
            const status = chapterStatus(details);
            return (
              <button
                key={chapter.id}
                className={`wb-chapter-btn ${chapterId === chapter.id ? 'is-active' : ''}`}
                onClick={() => startTransition(() => setChapterId(chapter.id))}
              >
                <span className="wb-chapter-copy">
                  <strong>{chapter.title}</strong>
                  <span>{status.detail}</span>
                </span>
                <span className={`wb-status-pill tone-${status.tone}`}>{status.label}</span>
              </button>
            );
          })}
        </section>
      </aside>

      <main className="wb-main">
        <header className="wb-main-head">
          <div>
            <span className="wb-eyebrow">{modeLabel(mode)}</span>
            <h2>{activeChapter.title}</h2>
            <p>
              {chapterSummary.availableStages} stages available. {chapterSummary.approvedStages} approved checkpoints.
              {activeMetric?.deltaPct != null ? ` Current stage shift: ${formatDelta(activeMetric.deltaPct)} vs ${activeMetric.comparedTo}.` : ''}
            </p>
          </div>

          <div className="wb-quick-actions">
            <a href="/studio">Open full studio</a>
            <a href="/intake">Start new content</a>
            <a href="/corpus">Inspect corpus</a>
          </div>
        </header>

        {mode === 'review' && (
          <section className="wb-flow">
            <div className="wb-stage-strip" role="tablist" aria-label="Pipeline stages">
              {activeChapter.stages.map((stage) => {
                const metric = activeChapter.metrics.find((candidate) => candidate.id === stage.id);
                return (
                  <button
                    key={stage.id}
                    className={`wb-stage-btn ${stage.id === activeStage.id ? 'is-active' : ''}`}
                    disabled={!stage.available}
                    onClick={() => startTransition(() => setStageId(stage.id))}
                  >
                    <strong>{stage.label}</strong>
                    <span>{stage.available ? stage.slice : 'Not produced yet'}</span>
                    <em>{metric?.deltaPct == null ? 'baseline' : formatDelta(metric.deltaPct)}</em>
                  </button>
                );
              })}
            </div>

            <div className="wb-review-grid">
              <article className="wb-surface wb-stage-view">
                <div className="wb-panel-head">
                  <h3>{activeStage.label}</h3>
                  <span>{activeMetric?.words ?? 0} words</span>
                </div>
                <div className="wb-stage-copy" dangerouslySetInnerHTML={{ __html: activeStage.html }} />
              </article>

              <aside className="wb-surface wb-stage-meta">
                <div className="wb-panel-head">
                  <h3>Stage impact</h3>
                  <span>{activeMetric?.sentences ?? 0} sentences</span>
                </div>
                <dl className="wb-kv">
                  <div>
                    <dt>Compared to</dt>
                    <dd>{activeMetric?.comparedTo ?? 'starting point'}</dd>
                  </div>
                  <div>
                    <dt>Word delta</dt>
                    <dd>{activeMetric?.deltaPct == null ? 'Baseline' : formatDelta(activeMetric.deltaPct)}</dd>
                  </div>
                  <div>
                    <dt>Review status</dt>
                    <dd>{chapterSummary.approvedStages > 0 ? `${chapterSummary.approvedStages} stage approvals recorded` : 'No approvals yet'}</dd>
                  </div>
                </dl>

                <div className="wb-note-card">
                  <h4>What to inspect</h4>
                  <p>{reviewPrompt(activeStage.id)}</p>
                </div>

                <div className="wb-note-card">
                  <h4>Augmentation readiness</h4>
                  <p>
                    {deferredAtoms.length > 0
                      ? `${deferredAtoms.length} atoms are waiting in the shared augmentation tray for this chapter.`
                      : 'No atoms selected yet. Use the knowledge lens to build a doctrine packet before enriching this chapter.'}
                  </p>
                </div>
              </aside>
            </div>
          </section>
        )}

        {mode === 'policy' && (
          <section className="wb-policy-shell">
            <div className="wb-policy-intro wb-surface">
              <div className="wb-panel-head">
                <h3>Canonical decisions</h3>
                <span>Book scope plus chapter overrides</span>
              </div>
              <p>
                This keeps the valuable part of the recommendations: a persistent operating shell with local context.
                It rejects the rewrite advice by reusing the existing editorial contract and save model instead of inventing a new one.
              </p>
            </div>
            <EditorialCards slug={slug} chapters={chapterDefs} cardDefs={cardDefs} />
          </section>
        )}

        {mode === 'knowledge' && (
          <section className="wb-knowledge-shell">
            <CorpusExplorer
              selectedAtoms={selectedAtoms}
              onSelectedAtomsChange={setSelectedAtoms}
              prose={proseContext}
              bookTradition={BOOK_TRADITION}
            />
          </section>
        )}

        {mode === 'augment' && (
          <section className="wb-augment-grid">
            <article className="wb-surface">
              <div className="wb-panel-head">
                <h3>Selected atom tray</h3>
                <span>{deferredAtoms.length} selected</span>
              </div>
              {deferredAtoms.length === 0 ? (
                <p className="wb-empty">
                  Nothing is in the tray yet. Open the knowledge lens, search a concept, and add the atoms you want to carry into this chapter.
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
            </article>

            <aside className="wb-surface">
              <div className="wb-panel-head">
                <h3>Enrichment brief</h3>
                <span>Ready for the next authoring pass</span>
              </div>
              <div className="wb-brief-block">
                <h4>Frame</h4>
                <p>{enrichmentPlan.frame}</p>
              </div>
              <div className="wb-brief-block">
                <h4>Use these anchors</h4>
                <ul className="wb-list">
                  {enrichmentPlan.anchors.map((anchor) => <li key={anchor}>{anchor}</li>)}
                </ul>
              </div>
              <div className="wb-brief-block">
                <h4>Draft insertion</h4>
                <p>{enrichmentPlan.draft}</p>
              </div>
              <div className="wb-brief-block">
                <h4>Guardrails</h4>
                <ul className="wb-list">
                  {enrichmentPlan.guardrails.map((guardrail) => <li key={guardrail}>{guardrail}</li>)}
                </ul>
              </div>
            </aside>
          </section>
        )}
      </main>

      <aside className="wb-inspector">
        <section className="wb-surface">
          <div className="wb-panel-head">
            <h2>Triage synthesis</h2>
            <span>Accepted vs rejected</span>
          </div>
          <div className="wb-decision-stack">
            <DecisionCard title="Kept" items={recommendationSummary.accept} tone="accept" />
            <DecisionCard title="Rejected" items={recommendationSummary.reject} tone="reject" />
          </div>
        </section>

        <section className="wb-surface">
          <div className="wb-panel-head">
            <h2>Live context</h2>
            <span>Current focus</span>
          </div>
          <dl className="wb-kv">
            <div>
              <dt>Chapter</dt>
              <dd>{activeChapter.title}</dd>
            </div>
            <div>
              <dt>Stage</dt>
              <dd>{activeStage.label}</dd>
            </div>
            <div>
              <dt>Knowledge tray</dt>
              <dd>{deferredAtoms.length} atoms selected</dd>
            </div>
            <div>
              <dt>Current mode</dt>
              <dd>{modeLabel(mode)}</dd>
            </div>
          </dl>
        </section>

        <section className="wb-surface">
          <div className="wb-panel-head">
            <h2>Cross-mode promise</h2>
            <span>Why this shell matters</span>
          </div>
          <p>
            The same chapter stays in focus while you inspect the pipeline, tune policy, search the knowledge base,
            and draft enrichment. That is the useful common thread across the triage inputs, and it is what this page now enforces.
          </p>
        </section>
      </aside>
    </div>
  );
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone: 'neutral' | 'good' | 'accent' }) {
  return (
    <div className={`wb-metric tone-${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function DecisionCard({
  title,
  items,
  tone,
}: {
  title: string;
  items: RecommendationItem[];
  tone: 'accept' | 'reject';
}) {
  return (
    <div className={`wb-decision-card tone-${tone}`}>
      <h3>{title}</h3>
      <ul className="wb-list">
        {items.map((item) => (
          <li key={item.title}>
            <strong>{item.title}:</strong> {item.reason}
          </li>
        ))}
      </ul>
    </div>
  );
}

function lastAvailableStageId(chapter?: WorkspaceChapter) {
  return chapter?.stages.filter((stage) => stage.available).at(-1)?.id;
}

function buildStageStats(chapters: WorkspaceChapter[]) {
  const availableStageCount = chapters.reduce(
    (count, chapter) => count + chapter.stages.filter((stage) => stage.available).length,
    0,
  );
  const approvedStageCount = chapters.reduce(
    (count, chapter) => count + Object.values(chapter.reviewed).filter((review) => review?.approved).length,
    0,
  );
  const enrichmentDeltas = chapters
    .flatMap((chapter) => chapter.metrics)
    .filter((metric) => metric.id === 'augmented' && typeof metric.deltaPct === 'number')
    .map((metric) => metric.deltaPct as number);
  const avgEnrichment = enrichmentDeltas.length
    ? `${Math.round(enrichmentDeltas.reduce((sum, value) => sum + value, 0) / enrichmentDeltas.length)}%`
    : 'n/a';

  return {
    chapterCount: chapters.length,
    availableStageCount,
    approvedStageCount,
    reviewedChapterCount: chapters.filter((chapter) => Object.values(chapter.reviewed).some((review) => review?.approved)).length,
    avgEnrichmentLift: avgEnrichment,
  };
}

function buildChapterSummary(chapter?: WorkspaceChapter) {
  return {
    availableStages: chapter?.stages.filter((stage) => stage.available).length ?? 0,
    approvedStages: Object.values(chapter?.reviewed ?? {}).filter((review) => review?.approved).length,
  };
}

function chapterStatus(chapter?: WorkspaceChapter) {
  const availableStages = chapter?.stages.filter((stage) => stage.available).length ?? 0;
  const approvedStages = Object.values(chapter?.reviewed ?? {}).filter((review) => review?.approved).length;

  if (approvedStages > 0) {
    return {
      label: `${approvedStages} approved`,
      detail: `${availableStages} stages available`,
      tone: 'good',
    } as const;
  }

  return {
    label: availableStages > 0 ? 'Needs review' : 'Not ready',
    detail: availableStages > 0 ? `${availableStages} stages ready to inspect` : 'No generated stages yet',
    tone: availableStages > 0 ? 'accent' : 'muted',
  } as const;
}

function reviewPrompt(stageId: string) {
  if (stageId === 'source') return 'Check source fidelity and confirm the raw chapter boundaries are clean before downstream changes hide the errors.';
  if (stageId === 'core') return 'Look for repeated material and structural noise that survived extraction. This is where weak segmentation tends to surface.';
  if (stageId === 'denoised') return 'Make sure cleanup removed junk without flattening voice or deleting meaningful terms.';
  if (stageId === 'normalized') return 'Review register, clarity, and consistency. This stage should improve readability without changing the argument.';
  if (stageId === 'augmented') return 'Verify that enrichment deepens the chapter and does not smuggle in material that changes the original teaching.';
  return 'Use this layer to confirm the final narrative additions still sound like deliberate editorial support rather than a separate document.';
}

function stageExcerpt(html: string) {
  const text = html
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return text ? text.slice(0, 320) : 'Select a stage to preview the current chapter and plan enrichment from real workspace text.';
}

function buildEnrichmentPlan(chapter: WorkspaceChapter | undefined, atoms: MockAtom[]) {
  if (!chapter || atoms.length === 0) {
    return {
      frame: 'Build the augmentation tray first. A good enrichment pass starts with concept selection, not with writing into an empty context.',
      anchors: ['Pick one concept from the knowledge lens.', 'Add at least one scripture anchor and one teaching anchor.', 'Return here to generate a concrete insertion brief.'],
      draft: 'No draft yet.',
      guardrails: ['Keep the added material subordinate to the chapter’s original claim.', 'Do not add atoms that cross the tradition firewall.', 'Prefer concise bridges over explanatory detours.'],
    };
  }

  const leadAtoms = atoms.slice(0, 3);
  const scriptureAnchors = atoms.filter((atom) => atom.type === 'quran' || atom.type === 'hadith');
  const doctrineAnchors = atoms.filter((atom) => atom.type === 'doctrine' || atom.type === 'term' || atom.type === 'etymology');

  return {
    frame: `Enrich ${chapter.title} by anchoring the live prose in ${leadAtoms.map((atom) => atom.gloss.toLowerCase()).join(', ')} without letting the augmentation overpower the chapter’s own argument.`,
    anchors: atoms.slice(0, 5).map((atom) => `${atom.gloss} (${atom.source_ref})`),
    draft: `After the chapter’s main claim is stated, add a short bridge that connects it to ${leadAtoms[0]?.gloss.toLowerCase()}. Support the bridge with ${scriptureAnchors[0]?.source_ref ?? 'one primary text reference'} and then land the point with ${doctrineAnchors[0]?.gloss.toLowerCase() ?? 'one interpretive teaching'} so the enrichment feels grounded rather than decorative.`,
    guardrails: [
      scriptureAnchors.length > 0 ? 'Lead with the strongest scripture or hadith anchor before paraphrasing doctrine.' : 'Add at least one scripture or hadith anchor before approving this enrichment.',
      doctrineAnchors.length > 0 ? 'Use doctrinal atoms to interpret, not to replace, the chapter’s own language.' : 'Bring in one teaching or term atom so the enrichment is explanatory instead of merely referential.',
      'Keep the insertion short enough that the original chapter still feels primary.',
    ],
  };
}

function modeLabel(mode: Mode) {
  return MODES.find((candidate) => candidate.id === mode)?.label ?? 'Workbench';
}

function formatDelta(deltaPct: number) {
  return `${deltaPct > 0 ? '+' : ''}${deltaPct}%`;
}