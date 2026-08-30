/**
 * BriefReview — step 5. Every answer read back, grouped by the step it came
 * from, each line jumping back to where it was answered.
 *
 * The list is derived from the same FIELDS array the inputs are, so a question
 * added to the wizard appears here without a second edit — there is deliberately
 * no separate summary definition to fall out of step.
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

  return (
    <div className="bf-review">
      <div className="bf-review-headline">
        <p className="intake-hint bf-note">
          This is what will be written down. Anything wrong, click it and you go
          back to where you answered it.
        </p>
      </div>

      <section className="bf-review-group">
        <h3 className="bf-review-group-title">Where it will live</h3>
        <dl className="bf-review-list">
          <div className="bf-review-row">
            <dt>Shelf</dt>
            <dd>{bucket}</dd>
          </div>
          <div className="bf-review-row">
            <dt>Branch</dt>
            <dd>
              <code>
                {bucket}/{values.slug ?? ""}
              </code>
            </dd>
          </div>
          <div className="bf-review-row">
            <dt>Source files</dt>
            <dd>
              {stagedNames.length
                ? stagedNames.join(", ")
                : "none supplied yet"}
            </dd>
          </div>
        </dl>
      </section>

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
          <section className="bf-review-group" key={step.id}>
            <h3 className="bf-review-group-title">
              {step.title}
              <button
                type="button"
                className="bf-review-edit"
                onClick={() => onJump(step.id)}
              >
                Change
              </button>
            </h3>
            <dl className="bf-review-list">
              {rows.map((f) => (
                <div className="bf-review-row" key={f.key}>
                  <dt>{f.label}</dt>
                  <dd>{display(f)}</dd>
                </div>
              ))}
            </dl>
          </section>
        );
      })}
    </div>
  );
}
