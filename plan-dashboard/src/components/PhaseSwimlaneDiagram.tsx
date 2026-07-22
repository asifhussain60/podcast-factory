/**
 * PhaseSwimlaneDiagram — L3 Pipeline Phase Sequence (semantic table).
 *
 * Was a 470-line hand-built SVG grid; now a real <table>. The data is tabular
 * (phase / station / service / model / cost tier / notes across ~16 rows), so a
 * table is the correct form — accessible to screen readers, searchable,
 * copy-pasteable, and density-uncapped. Pure presentational: no hooks, no
 * handlers, so it renders at BUILD TIME (no client: directive in the page).
 *
 * Colour-coding is delivered entirely through CSS classes keyed to the existing
 * --c-* design tokens (see architecture.css) — zero inline styling, theme
 * unchanged. Colour is decorative only; every cell also carries its text label,
 * so meaning never depends on colour alone.
 */

interface SwimPhase {
  id: string;
  label: string;
  service: string;
  vendor: "anthropic" | "azure" | "google" | "local" | "human";
  model: string;
  cost: "low" | "mid" | "high" | "zero" | "gate";
  note?: string;
  isGate?: boolean;
  isFuture?: boolean;
}

const PHASES: SwimPhase[] = [
  {
    id: "P0",
    label: "Read the source",
    service: "Azure Document Intelligence + Translator",
    vendor: "azure",
    model: "—",
    cost: "low",
    note: "Branches: pdf → DocIntel / audio → Turboscribe + Translator",
  },
  {
    id: "P1",
    label: "Strip the noise",
    service: "Anthropic (routed: Haiku → Sonnet → Gemini)",
    vendor: "anthropic",
    model: "Haiku / Sonnet / Gemini",
    cost: "low",
    note: "Model selected per passage complexity; tradition-specific idioms → Gemini",
    isFuture: true,
  },
  {
    id: "P2",
    label: "Polish the text",
    service: "Anthropic Claude",
    vendor: "anthropic",
    model: "Sonnet",
    cost: "low",
  },
  {
    id: "P3",
    label: "Learn the names",
    service: "Local + Anthropic (pre-gate analysis)",
    vendor: "local",
    model: "Haiku (analysis)",
    cost: "low",
    note: "Phonetics sidecar + pre-gate structural warnings",
  },
  {
    id: "GATE 1",
    label: "Source Review Gate",
    service: "Podcast Reader (Astro site)",
    vendor: "human",
    model: "—",
    cost: "gate",
    note: "Human reviews chapters, noise log, vocabulary gaps. Approves before expensive phases run.",
    isGate: true,
    isFuture: true,
  },
  {
    id: "P4",
    label: "Plan the episodes",
    service: "Anthropic Claude Opus",
    vendor: "anthropic",
    model: "Opus",
    cost: "high",
    note: "Content-first slicing: ~30-min learning arc per episode",
  },
  {
    id: "P5",
    label: "Enrich with context",
    service: "Anthropic Claude Sonnet",
    vendor: "anthropic",
    model: "Sonnet",
    cost: "mid",
    note: "Tradition firewall active — atoms matched to book’s tradition",
    isFuture: true,
  },
  {
    id: "P6",
    label: "Bring in knowledge",
    service: "Anthropic + Local knowledge base",
    vendor: "anthropic",
    model: "Sonnet",
    cost: "mid",
    note: "Tradition-tagged atoms (Quran / Hadith / doctrine); missing citations flagged",
    isFuture: true,
  },
  {
    id: "P7",
    label: "Cut the pieces",
    service: "Local (mechanical)",
    vendor: "local",
    model: "—",
    cost: "zero",
  },
  {
    id: "P7f",
    label: "Write narrator framing",
    service: "Anthropic Claude Opus",
    vendor: "anthropic",
    model: "Opus",
    cost: "high",
    note: "Host roles consistent across series; never flip mid-book",
  },
  {
    id: "P7g",
    label: "Optimize for teaching",
    service: "Anthropic Claude Sonnet",
    vendor: "anthropic",
    model: "Sonnet",
    cost: "mid",
    note: "Arc validation + NotebookLM hygiene — Sonnet only (Gemini kept independent)",
    isFuture: true,
  },
  {
    id: "P8",
    label: "Design the slides",
    service: "Anthropic Claude Sonnet",
    vendor: "anthropic",
    model: "Sonnet",
    cost: "mid",
  },
  {
    id: "P9",
    label: "Audit and converge",
    service: "Claude Challenger + Gemini second-opinion",
    vendor: "google",
    model: "Gemini (independent)",
    cost: "mid",
    note: "Dual-auditor: Claude + Gemini. Up to 5 passes per chapter.",
    isFuture: true,
  },
  {
    id: "GATE 2",
    label: "Publish Review Gate",
    service: "Podcast Reader (Astro site)",
    vendor: "human",
    model: "—",
    cost: "gate",
    note: "Human sees complete product: episode list, challenger findings, upload checklist.",
    isGate: true,
  },
];

const MODEL_CLASS: Record<string, string> = {
  Opus: "m-opus",
  Sonnet: "m-sonnet",
  Haiku: "m-haiku",
  "Haiku / Sonnet / Gemini": "m-haiku",
  "Haiku (analysis)": "m-haiku",
  "Gemini (independent)": "m-gemini",
};

const COST_LABELS: Record<SwimPhase["cost"], string> = {
  zero: "No LLM",
  low: "Low cost",
  mid: "Mid cost",
  high: "High cost",
  gate: "Human",
};

export default function PhaseSwimlaneDiagram() {
  return (
    <figure className="diagram-container swimlane-figure">
      <div className="table-container">
        <table className="swimlane-table">
          <caption className="sr-only">
            Pipeline phase sequence — every station with its service, AI model
            tier, token-cost tier, notes, and the two human-halt review gates.
          </caption>
          <thead>
            <tr>
              <th scope="col">Phase</th>
              <th scope="col">Station</th>
              <th scope="col">Service</th>
              <th scope="col">Model</th>
              <th scope="col">Cost tier</th>
              <th scope="col">Notes</th>
            </tr>
          </thead>
          <tbody>
            {PHASES.map((p) =>
              p.isGate ? (
                <tr key={p.id} className="swim-gate-row">
                  <th scope="row" className="swim-gate-mark">
                    <span aria-hidden="true">✋</span> Human halt
                  </th>
                  <td colSpan={5}>
                    <span className="swim-gate-name">{p.label}</span>
                    {p.note && <span className="swim-gate-note">{p.note}</span>}
                  </td>
                </tr>
              ) : (
                <tr
                  key={p.id}
                  className={p.isFuture ? "swim-future" : undefined}
                >
                  <th scope="row">
                    <span className={`swim-phase-badge v-${p.vendor}`}>
                      {p.id}
                    </span>
                  </th>
                  <td>
                    <span className="swim-station">{p.label}</span>
                    {p.isFuture && (
                      <span className="swim-future-tag">Future</span>
                    )}
                  </td>
                  <td className="swim-service">{p.service}</td>
                  <td>
                    {p.model !== "—" ? (
                      <span
                        className={`swim-model ${MODEL_CLASS[p.model] ?? "m-sonnet"}`}
                      >
                        {p.model}
                      </span>
                    ) : (
                      <span className="swim-model-none">—</span>
                    )}
                  </td>
                  <td>
                    <span className={`swim-cost cost-${p.cost}`}>
                      {COST_LABELS[p.cost]}
                    </span>
                  </td>
                  <td className="swim-note-cell">{p.note ?? ""}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
      <figcaption>
        Every planned pipeline station with the AI model it uses, the service it
        calls, and its token-cost tier. Stations tagged <strong>Future</strong>{" "}
        are designed and tracked in the roadmap but not yet deployed; the two{" "}
        <strong>Human halt</strong> rows are the hard gates where the pipeline
        waits for approval before continuing.
      </figcaption>
    </figure>
  );
}
