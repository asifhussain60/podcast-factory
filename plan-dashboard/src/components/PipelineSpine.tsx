import { useState, useMemo, useEffect, useRef } from 'react';
import AgentCard from './AgentCard';

interface Phase {
  id: string;
  name: string;
  kind: string;
  agent: string | null;
  plain: string;
  duration_minutes: number;
  modules: string[];
}

interface Module {
  id: string;
  name: string;
  plain: string;
}

interface Agent {
  id: string;
  name: string;
  role: string;
  icon: string;
  tone: string;
  plain: string;
  what_it_knows: string;
  boundary_in: string;
  boundary_out: string;
  does_not: string;
  cost_profile: string;
  failure_mode: string;
}

interface Props {
  phases: Phase[];
  modules: Module[];
  agents: Agent[];
}

const KIND_META: Record<string, { label: string; icon: string }> = {
  agentic:    { label: 'Agent',      icon: 'robot' },
  hybrid:     { label: 'Hybrid',     icon: 'shuffle' },
  mechanical: { label: 'Mechanical', icon: 'gear' },
};

// ── Service chip definitions ────────────────────────────────────────────────

type VendorKey = 'anthropic' | 'azure' | 'google' | 'internal';

interface SvcChip {
  id: string;
  vendor: VendorKey;
  icon: string;          // font-awesome solid name
  label: string;         // short e.g. "Document Intelligence"
  sublabel: string;      // e.g. "Azure AI" or agent friendly name
  resource?: string;     // exact Azure resource / model / product name
  detail: string;        // tooltip body
  cost?: string;
}

const VENDOR_META: Record<VendorKey, { color: string; wordmark: string }> = {
  anthropic: { color: 'var(--c-vendor-anthropic)', wordmark: 'Anthropic' },
  azure:     { color: 'var(--c-vendor-azure)',     wordmark: 'Azure AI' },
  google:    { color: 'var(--c-vendor-google)',    wordmark: 'Google' },
  internal:  { color: 'var(--c-ink-dim)',           wordmark: 'Internal' },
};

const AZURE_MODULE_CHIPS: Record<string, Omit<SvcChip, 'id'>> = {
  'azure-document-intelligence': {
    vendor: 'azure', icon: 'file-lines',
    label: 'Document Intelligence',
    sublabel: 'Azure AI',
    resource: 'journal-docintel',
    detail: 'Reads every page of the source PDF using Azure AI Document Intelligence — recognizes Arabic script, headings, tables, and footnotes with full layout awareness.',
    cost: 'Charged per page analyzed',
  },
  'azure-translator': {
    vendor: 'azure', icon: 'language',
    label: 'Translator',
    sublabel: 'Azure AI',
    resource: 'journal-translator',
    detail: 'Translates recognized Arabic text to an English working copy using Azure AI Translator. The original Arabic is preserved alongside it for reference.',
    cost: 'Charged per million characters',
  },
};

const PHASE_EXTRA_CHIPS: Record<string, Omit<SvcChip, 'id'>[]> = {
  P10: [{
    vendor: 'google', icon: 'headphones',
    label: 'NotebookLM',
    sublabel: 'Google',
    resource: 'Audio Overview',
    detail: 'The finished episode bundle is uploaded to Google NotebookLM. Its Audio Overview feature generates the two-host podcast conversation from the source material.',
    cost: 'Per-episode generation',
  }],
};

function buildChips(p: Phase, agent: Agent | null): SvcChip[] {
  const chips: SvcChip[] = [];

  // Azure chips from module IDs
  p.modules.forEach((mid, i) => {
    const def = AZURE_MODULE_CHIPS[mid];
    if (def) chips.push({ id: `${p.id}-az-${i}`, ...def });
  });

  // Anthropic chip for all agent-driven phases
  if ((p.kind === 'agentic' || p.kind === 'hybrid') && agent) {
    chips.push({
      id: `${p.id}-claude`,
      vendor: 'anthropic', icon: 'robot',
      label: 'Claude',
      sublabel: agent.name,
      resource: 'claude-3-5-sonnet',
      detail: `${agent.role}. ${agent.plain}`,
      cost: agent.cost_profile,
    });
  }

  // Per-phase extras (NotebookLM at P10)
  (PHASE_EXTRA_CHIPS[p.id] ?? []).forEach((def, i) =>
    chips.push({ id: `${p.id}-extra-${i}`, ...def })
  );

  return chips;
}

// ── Vendor tag (compact, non-interactive, eyebrow row) ────────────────────

const VENDOR_ICONS: Record<VendorKey, string> = {
  anthropic: 'robot',
  azure:     'cloud',
  google:    'google',
  internal:  'code',
};

function vendorTagsForChips(chips: SvcChip[]): Array<{ vendor: VendorKey; wordmark: string }> {
  const seen = new Set<VendorKey>();
  const out: Array<{ vendor: VendorKey; wordmark: string }> = [];
  for (const c of chips) {
    if (!seen.has(c.vendor)) {
      seen.add(c.vendor);
      out.push({ vendor: c.vendor, wordmark: VENDOR_META[c.vendor].wordmark });
    }
  }
  return out;
}

// ── ServiceChip component ───────────────────────────────────────────────────

function ServiceChip({ chip, open, onToggle }: {
  chip: SvcChip;
  open: boolean;
  onToggle: () => void;
}) {
  const meta = VENDOR_META[chip.vendor];
  return (
    <div className={`svc-chip vendor-${chip.vendor} ${open ? 'is-open' : ''}`}>
      <button
        type="button"
        className="svc-chip-pill"
        aria-expanded={open}
        onClick={onToggle}
        title={`${chip.label} — click for details`}
      >
        <span className="svc-chip-dot" style={{ background: meta.color }} aria-hidden="true" />
        <span className="svc-chip-label">{chip.label}</span>
        <i className={`fa-solid fa-chevron-${open ? 'up' : 'down'} svc-chip-caret`} aria-hidden="true" />
      </button>
      {open && (
        <div className="svc-chip-popover" role="tooltip">
          <div className="svc-chip-pop-head">
            <i className={`fa-solid fa-${chip.icon}`} aria-hidden="true" style={{ color: meta.color }} />
            <div>
              <strong className="svc-chip-pop-title">{chip.label}</strong>
              <span className="svc-chip-pop-wordmark">{meta.wordmark}</span>
            </div>
          </div>
          {chip.sublabel && (
            <div className="svc-chip-pop-row">
              <span className="svc-chip-pop-key">Role</span>
              <span className="svc-chip-pop-val">{chip.sublabel}</span>
            </div>
          )}
          {chip.resource && (
            <div className="svc-chip-pop-row">
              <span className="svc-chip-pop-key">{chip.vendor === 'azure' ? 'Resource' : chip.vendor === 'anthropic' ? 'Model' : 'Product'}</span>
              <code className="svc-chip-pop-code">{chip.resource}</code>
            </div>
          )}
          <p className="svc-chip-pop-detail">{chip.detail}</p>
          {chip.cost && (
            <div className="svc-chip-pop-cost">
              <i className="fa-solid fa-coins" aria-hidden="true" />
              {chip.cost}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const sectionId = (id: string) => `station-${id}`;

export default function PipelineSpine({ phases, modules, agents }: Props) {
  const [active, setActive] = useState<string>(phases[0]?.id ?? '');
  const [openChip, setOpenChip] = useState<string | null>(null);
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});
  const railItemRefs = useRef<Record<string, HTMLLIElement | null>>({});

  const moduleMap = useMemo(() => {
    const m = new Map<string, Module>();
    modules.forEach((mod) => m.set(mod.id, mod));
    return m;
  }, [modules]);

  const agentMap = useMemo(() => {
    const m = new Map<string, Agent>();
    agents.forEach((a) => m.set(a.id, a));
    return m;
  }, [agents]);

  // Scrollspy — pick the topmost section whose top has crossed 30% of viewport.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onScroll = () => {
      const ids = phases.map((p) => p.id);
      const trigger = window.innerHeight * 0.30;
      let current = ids[0];
      for (const id of ids) {
        const el = sectionRefs.current[id];
        if (!el) continue;
        const top = el.getBoundingClientRect().top;
        if (top - trigger <= 0) current = id; else break;
      }
      setActive(current);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [phases]);

  // Close chip popover when clicking outside
  useEffect(() => {
    if (!openChip) return;
    const handler = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      if (!t.closest('.svc-chip')) setOpenChip(null);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [openChip]);

  // Auto-scroll the active rail item into view within the sticky panel
  useEffect(() => {
    const el = railItemRefs.current[active];
    if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [active]);

  const jumpTo = (id: string) => {
    const el = sectionRefs.current[id];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="pipeline-shell">
      {/* ── LEFT: sticky mini-rail ─────────────────────────────── */}
      <nav className="pipeline-rail" aria-label="Pipeline stations">
        <div className="pipeline-rail-sticky">
          <span className="eyebrow rail-eyebrow">The pipeline</span>
          <ol className="rail-list">
            {phases.map((p, i) => {
              const meta = KIND_META[p.kind] ?? KIND_META.mechanical;
              const isActive = p.id === active;
              return (
                <li key={p.id} ref={(el) => { railItemRefs.current[p.id] = el; }} className={`rail-item kind-${p.kind} ${isActive ? 'is-active' : ''}`}>
                  <button type="button" onClick={() => jumpTo(p.id)} className="rail-link">
                    <span className="rail-dot" aria-hidden="true">
                      <i className={`fa-solid fa-${meta.icon}`}></i>
                    </span>
                    <span className="rail-text">
                      <span className="rail-meta">Step {i + 1} · {p.duration_minutes} min</span>
                      <span className="rail-name">{p.name}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          <div className="rail-foot">
            <span className="rail-foot-line">Scroll the right column to walk through the pipeline. The active step lights up here.</span>
          </div>
        </div>
      </nav>

      {/* ── RIGHT: vertical stack of full station sections ──────── */}
      <main className="pipeline-stations">
        {phases.map((p, i) => {
          const meta = KIND_META[p.kind] ?? KIND_META.mechanical;
          const agent = p.agent ? agentMap.get(p.agent) : null;
          const phaseModules = p.modules.map((m) => moduleMap.get(m)).filter(Boolean) as Module[];
          const isActive = p.id === active;
          const chips = buildChips(p, agent ?? null);

          return (
            <section
              key={p.id}
              id={sectionId(p.id)}
              ref={(el) => { sectionRefs.current[p.id] = el; }}
              className={`station-section kind-tone-${p.kind} ${isActive ? 'is-active' : ''}`}
            >
              <header className="station-section-head">
                <div className="station-section-numwrap">
                  <span className="station-section-number">{i + 1}</span>
                </div>
                <div className="station-section-headtext">
                  <div className="row station-section-eyebrow-row">
                    <span className="eyebrow">Station {p.id} · {p.duration_minutes} min</span>
                    <div className="vendor-tags">
                      {vendorTagsForChips(chips).map(({ vendor, wordmark }) => (
                        <span key={vendor} className={`vendor-tag vendor-tag-${vendor}`}>
                          <span className="vendor-tag-dot" style={{ background: VENDOR_META[vendor].color }} aria-hidden="true" />
                          <i className={`fa-brands fa-${vendor === 'anthropic' ? 'aws' : vendor === 'azure' ? 'microsoft' : 'google'} vendor-tag-icon`} aria-hidden="true" />
                          {wordmark}
                        </span>
                      ))}
                      {chips.length === 0 && (
                        <span className="vendor-tag vendor-tag-internal">
                          <span className="vendor-tag-dot" style={{ background: 'var(--c-ink-muted)' }} aria-hidden="true" />
                          Python script
                        </span>
                      )}
                    </div>
                  </div>
                  <h2 className="station-section-title">{p.name}</h2>
                  {chips.length > 0 && (
                    <div className="svc-chips-row">
                      {chips.map((chip) => (
                        <ServiceChip
                          key={chip.id}
                          chip={chip}
                          open={openChip === chip.id}
                          onToggle={() => setOpenChip(openChip === chip.id ? null : chip.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </header>

              <p className="station-section-lede">{p.plain}</p>

              {phaseModules.length > 0 && (
                <div className="station-section-modules">
                  <span className="eyebrow section-sub-eyebrow">Azure services used</span>
                  <div className="section-module-grid">
                    {phaseModules.map((m) => {
                      const azChip = AZURE_MODULE_CHIPS[m.id];
                      return (
                        <div key={m.id} className="section-module">
                          <div className="section-module-head">
                            <i className="fa-solid fa-puzzle-piece" aria-hidden="true"></i>
                            <strong>{m.name}</strong>
                            {azChip?.resource && (
                              <code style={{ fontSize: 'var(--fs-2xs)', opacity: 0.65, fontFamily: "ui-monospace,'SF Mono',monospace", marginLeft: '4px' }}>
                                azure.{azChip.resource}
                              </code>
                            )}
                          </div>
                          <p className="small muted">{m.plain}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {agent && (
                <div className="station-section-agent">
                  <span className="eyebrow section-sub-eyebrow">
                    {p.kind === 'hybrid' ? 'Claude + Azure runs this step' : 'Claude runs this step'}
                  </span>
                  <AgentCard agent={agent} />
                </div>
              )}

              {!agent && p.kind === 'mechanical' && (
                <div className="focus-empty">
                  <i className="fa-solid fa-gear focus-empty-icon" aria-hidden="true"></i>
                  <div>
                    <strong>Python runs this step.</strong>
                    <p className="small muted">A deterministic script does this work the same way for every book. Nothing to reason about, nothing to drift.</p>
                  </div>
                </div>
              )}
            </section>
          );
        })}
      </main>
    </div>
  );
}
