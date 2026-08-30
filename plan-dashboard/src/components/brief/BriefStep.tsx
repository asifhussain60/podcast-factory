/**
 * BriefStep — the fields of one wizard step, from the shared FieldDef array.
 *
 * Surface fields render directly; the rarely-touched ones live behind a native
 * <details> accordion so the common case is four or five questions per screen
 * rather than forty on one page. The accordion is pure HTML — the same no-JS
 * pattern StudioSubnav.astro already uses here.
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
  onReveal: (field: FieldDef) => void;
  /** Rendered between the surface fields and the accordion (uploader, voices). */
  children?: React.ReactNode;
}

export default function BriefStep({
  step,
  values,
  optionsFor,
  onChange,
  onExplain,
  onReveal,
  children,
}: Props) {
  const all = fieldsForStep(step).filter((f) => isVisible(f, values));
  const surface = all.filter((f) => !f.advanced);
  const advanced = all.filter((f) => f.advanced);

  const render = (f: FieldDef) => (
    <BriefField
      key={f.key}
      field={f}
      value={values[f.key] ?? ""}
      options={optionsFor(f)}
      onChange={onChange}
      onExplain={onExplain}
      onReveal={onReveal}
    />
  );

  return (
    <div className="bf-step-fields">
      <div className="bf-grid">{surface.map(render)}</div>
      {children}
      {advanced.length > 0 && (
        <details className="bf-advanced">
          <summary className="bf-advanced-summary">
            Advanced
            <span className="bf-advanced-count">
              {advanced.length} more{" "}
              {advanced.length === 1 ? "setting" : "settings"}
            </span>
          </summary>
          <div className="bf-grid bf-advanced-grid">{advanced.map(render)}</div>
        </details>
      )}
    </div>
  );
}
