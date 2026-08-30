/**
 * BriefField — one control in the Intake wizard, rendered from its FieldDef.
 *
 * Every control here is built-in HTML: a <select>, an <input list> combobox, a
 * button acting as a switch, a textarea. No control library, matching the
 * dependency-free preference the intake components already keep.
 *
 * Validation is the browser's own — required / pattern / maxlength — surfaced
 * through :user-invalid in the stylesheet so an error appears after you have
 * engaged with a field rather than while you are still typing into it.
 */
import type { FieldDef } from "../../lib/brief/fields";

export interface Option {
  value: string;
  label: string;
  description?: string;
}

interface Props {
  field: FieldDef;
  value: string;
  options: Option[];
  onChange: (key: string, value: string) => void;
  /** Opens the explainer dialog for a field whose options carry descriptions. */
  onExplain?: (field: FieldDef, options: Option[]) => void;
  /** Shows the folder this piece will land in, for a field marked `reveal`. */
  onReveal?: (field: FieldDef) => void;
}

export default function BriefField({
  field,
  value,
  options,
  onChange,
  onExplain,
  onReveal,
}: Props) {
  const id = `bf-${field.key}`;
  const labelId = `${id}-label`;
  const hintId = field.hint || field.patternHint ? `${id}-hint` : undefined;
  const widthClass = `bf-w-${field.width ?? "name"}`;
  const explainable =
    !!onExplain && options.some((o) => (o.description ?? "").trim().length > 0);

  const describedBy = hintId;

  let control: React.ReactNode;

  if (field.kind === "switch") {
    const on = value === "true";
    // aria-labelledby, not the <label for>: a button's accessible name comes
    // from its contents, which here are only "Yes"/"No". Naming it from the
    // label keeps the question in the announcement and leaves aria-checked to
    // carry the state.
    control = (
      <button
        type="button"
        id={id}
        role="switch"
        aria-checked={on}
        aria-labelledby={labelId}
        aria-describedby={describedBy}
        className="bf-switch"
        onClick={() => onChange(field.key, on ? "false" : "true")}
      >
        <span className="bf-switch-track" aria-hidden="true">
          <span className="bf-switch-thumb" />
        </span>
        <span className="bf-switch-text">{on ? "Yes" : "No"}</span>
      </button>
    );
  } else if (field.kind === "select") {
    control = (
      <select
        id={id}
        className={`intake-select ${widthClass}`}
        value={value}
        required={field.required}
        aria-describedby={describedBy}
        onChange={(e) => onChange(field.key, e.target.value)}
      >
        {!field.required && <option value="">—</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    );
  } else if (field.kind === "combo") {
    control = (
      <>
        <input
          id={id}
          list={`${id}-list`}
          className={`intake-input ${widthClass}`}
          value={value}
          required={field.required}
          maxLength={field.maxLength}
          aria-describedby={describedBy}
          onChange={(e) => onChange(field.key, e.target.value)}
        />
        <datalist id={`${id}-list`}>
          {options.map((o) => (
            <option key={o.value} value={o.value} label={o.label} />
          ))}
        </datalist>
      </>
    );
  } else if (field.kind === "textarea") {
    control = (
      <textarea
        id={id}
        className={`intake-textarea ${widthClass}`}
        value={value}
        rows={7}
        maxLength={field.maxLength}
        aria-describedby={describedBy}
        onChange={(e) => onChange(field.key, e.target.value)}
      />
    );
  } else {
    control = (
      <input
        id={id}
        type={field.kind === "number" ? "number" : "text"}
        min={field.kind === "number" ? 1 : undefined}
        className={`intake-input ${widthClass}`}
        value={value}
        required={field.required}
        maxLength={field.maxLength}
        pattern={field.pattern}
        dir={field.rtl ? "rtl" : undefined}
        lang={field.rtl ? "ar" : undefined}
        aria-describedby={describedBy}
        onChange={(e) => onChange(field.key, e.target.value)}
      />
    );
  }

  return (
    <div className="intake-field bf-field">
      <div className="bf-label-row">
        <label className="intake-label bf-label" id={labelId} htmlFor={id}>
          {field.label}
          {/* The control's own `required` attribute is what announces this; the
           * star is the sighted cue for the same fact, so it is hidden rather
           * than aria-labelled (aria-label on a role-less span is ignored). */}
          {field.required && (
            <span className="bf-req" aria-hidden="true">
              *
            </span>
          )}
        </label>
        {explainable && (
          <button
            type="button"
            className="bf-explain"
            onClick={() => onExplain?.(field, options)}
          >
            What do these mean?
          </button>
        )}
        {field.reveal && onReveal && (
          <button
            type="button"
            className="bf-explain"
            onClick={() => onReveal(field)}
          >
            Show in Finder
          </button>
        )}
      </div>
      {control}
      {hintId && (
        <p className="intake-hint bf-hint" id={hintId}>
          {field.hint}
          {field.hint && field.patternHint ? " " : ""}
          {field.patternHint}
        </p>
      )}
    </div>
  );
}
