/**
 * BriefReview — step 5. Every answer read back before it is written down.
 *
 * The list is derived from the same FIELDS array the inputs are, so a question
 * added to the wizard appears here without a second edit — there is deliberately
 * no separate summary definition to fall out of step.
 *
 * REDESIGNED 2026-08-30. It was a stack of full-width definition lists, one per
 * step, every row the same weight: forty facts flattened into one grey column
 * with nothing to look at first. Three changes, structure only — the palette is
 * the site's own `--c-*` and is untouched:
 *
 *   1. A MASTHEAD. The commission is a thing with a name, and the page never
 *      said so — the title sat as row four of section one, in the same type as
 *      "Density". It now opens with what is being made and where it lands.
 *   2. CARDS IN A GRID rather than stacked lists. Each step's answers are their
 *      own card, so the eye can go to "The edition" without reading past "The
 *      work", and on a wide screen two sit side by side instead of one column
 *      of full-width rows running past the fold.
 *   3. VALUE OVER LABEL. The label is small and muted, the answer is the line
 *      you read — the reverse of a `dt`/`dd` pair rendered at one size, where
 *      the word "Archetype" competes with the answer beside it.
 *
 * Card structure and the chip treatment are adapted from Sphere's section cards
 * and skill tags (Wrapbootstrap archive, reference only — nothing is imported
 * from it; the CSS lives in styles/intake-brief.css and uses this site's tokens).
 */
import {
  FIELDS,
  STEPS,
  isVisible,
  type FieldDef,
  type StepId,
} from "../../lib/brief/fields";
import type { Option } from "./BriefField";

interface Props {
  values: Record<string, string>;
  bucket: string;
  stagedNames: string[];
  optionsFor: (f: FieldDef) => Option[];
  onJump: (step: StepId) => void;
}

export default function BriefReview({
  values,
  bucket,
  stagedNames,
  optionsFor,
  onJump,
}: Props) {
  function display(f: FieldDef): string {
    const raw = (values[f.key] ?? "").trim();
    if (f.kind === "switch") return raw === "true" ? "Yes" : "No";
    const hit = optionsFor(f).find((o) => o.value === raw);
    return hit?.label ?? raw;
  }

  const title = (values.title ?? "").trim() || "Untitled";
  const author = (values.author ?? "").trim();
  const slug = (values.slug ?? "").trim();

  return (
    <div className="bf-review">
      <header className="bf-rv-masthead">
        <p className="bf-rv-eyebrow">About to be written down</p>
        <h3 className="bf-rv-title">{title}</h3>
        {author && <p className="bf-rv-byline">{author}</p>}
        <dl className="bf-rv-facts">
          <div className="bf-rv-fact">
            <dt>Shelf</dt>
            <dd>{bucket}</dd>
          </div>
          <div className="bf-rv-fact">
            <dt>Branch</dt>
            <dd>
              <code>
                {bucket}/{slug}
              </code>
            </dd>
          </div>
          <div className="bf-rv-fact">
            <dt>Source files</dt>
            <dd>
              {stagedNames.length ? (
                <span className="bf-rv-chips">
                  {stagedNames.map((n) => (
                    <span className="bf-rv-chip" key={n}>
                      {n}
                    </span>
                  ))}
                </span>
              ) : (
                <span className="bf-rv-empty">none supplied yet</span>
              )}
            </dd>
          </div>
        </dl>
      </header>

      <p className="intake-hint bf-rv-note">
        Anything wrong, use the Change link on that card and you go back to
        where you answered it.
      </p>

      <div className="bf-rv-grid">
        {STEPS.filter((s) => s.id !== 5).map((step) => {
          const rows = FIELDS.filter(
            (f) =>
              f.step === step.id &&
              f.kind !== "textarea" &&
              isVisible(f, values) &&
              (values[f.key] ?? "").trim() !== "",
          );
          if (!rows.length) return null;
          return (
            <section className="bf-rv-card" key={step.id}>
              <header className="bf-rv-card-head">
                <h4 className="bf-rv-card-title">{step.title}</h4>
                <button
                  type="button"
                  className="bf-rv-change"
                  onClick={() => onJump(step.id)}
                >
                  Change
                  <span className="bf-rv-sr"> {step.title}</span>
                </button>
              </header>
              <dl className="bf-rv-rows">
                {rows.map((f) => (
                  <div className="bf-rv-row" key={f.key}>
                    <dt>{f.label}</dt>
                    <dd>{display(f)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          );
        })}
      </div>
    </div>
  );
}
