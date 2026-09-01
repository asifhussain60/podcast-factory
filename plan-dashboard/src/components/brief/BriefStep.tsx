/**
 * BriefStep — the fields of one wizard step, from the shared FieldDef array.
 *
 * EVERY field is on screen. Until 2026-08-31 the rarely-touched ones sat behind
 * a collapsed <details> accordion, which meant the commission could be
 * generated without their ever having been read: a setting you did not know was
 * there is not a setting you decided. Asif asked for them expanded, and the
 * accordion is gone rather than merely defaulted open — a panel that can be
 * closed is a panel that will be.
 *
 * `advanced` survives on the FieldDef as an ORDERING hint only. The questions
 * most commissions answer come first, the rest follow under a quiet subheading,
 * and both are visible without a click.
 */
import BriefField, { type Option } from "./BriefField";
import {
  fieldsForStep,
  isVisible,
  type FieldDef,
  type StepId,
} from "../../lib/brief/fields";

interface Props {
  step: StepId;
  values: Record<string, string>;
  optionsFor: (f: FieldDef) => Option[];
  onChange: (key: string, value: string) => void;
  onExplain: (field: FieldDef, options: Option[]) => void;
  onPickFolder: (field: FieldDef) => void;
  /** Fields that are read-only because a piece of existing content is loaded. */
  lockedFields?: ReadonlySet<string>;
  /** Rendered between the common fields and the rest (uploader, voices). */
  children?: React.ReactNode;
}

export default function BriefStep({
  step,
  values,
  optionsFor,
  onChange,
  onExplain,
  onPickFolder,
  lockedFields,
  children,
}: Props) {
  const all = fieldsForStep(step).filter((f) => isVisible(f, values));
  const common = all.filter((f) => !f.advanced);
  const rest = all.filter((f) => f.advanced);

  const render = (f: FieldDef) => (
    <BriefField
      key={f.key}
      field={f}
      value={values[f.key] ?? ""}
      options={optionsFor(f)}
      onChange={onChange}
      onExplain={onExplain}
      onPickFolder={onPickFolder}
      locked={lockedFields?.has(f.key)}
    />
  );

  return (
    <div className="bf-step-fields">
      <div className="bf-grid">{common.map(render)}</div>
      {children}
      {rest.length > 0 && (
        <section className="bf-more" aria-labelledby={`bf-more-${step}`}>
          <h3 className="bf-more-title" id={`bf-more-${step}`}>
            Also on this step
            <span className="bf-more-note">
              Sensible defaults are already chosen — change them only if you
              need to.
            </span>
          </h3>
          <div className="bf-grid">{rest.map(render)}</div>
        </section>
      )}
    </div>
  );
}
