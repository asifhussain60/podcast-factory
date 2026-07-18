/**
 * SmartForm — Screen 2 of the new-content intake (Phase 6, Q9 + Q12).
 *
 * "Minimal typing": every production setting is a DROPDOWN pre-seeded from the
 * pipeline's own vocabularies (GET /api/intake/form-options — defaults from the
 * content-type registry + blueprint enums, plus any user additions). Each dropdown
 * has an inline "+ add" affordance that PERSISTS a new option to form-options.yml
 * so it survives reloads. When a classifier proposal is supplied, the matching
 * value is pre-selected and its rationale shown beside the field (Q9).
 *
 * bucket is intentionally NOT user-editable — it is DERIVED from content_profile
 * (the whole point of the Phase-2 routing fix), shown read-only so it can't drift.
 *
 * Dependency-free, class-driven, external CSS only — matches NewContentForm.
 */
import { useEffect, useState } from "react";
import { apiFetch, ApiFetchError } from "../../lib/api-fetch";
import VoicePicker from "./VoicePicker";

type Options = Record<string, string[]>;
type Proposal = Record<string, { value: string; rationale?: string }>;

interface Props {
  /** Optional classifier proposal: pre-selects matching values + shows rationale. */
  proposed?: Proposal;
  /** Notified whenever the resolved settings change. */
  onChange?: (values: Record<string, string>) => void;
}

// The fields SmartForm renders as editable dropdowns, in form order, with the
// plain-language label the operator sees. bucket is derived (not listed here).
const FIELD_LABELS: { key: string; label: string }[] = [
  { key: "content_profile", label: "Content profile" },
  { key: "audience_profile", label: "Audience" },
  { key: "host_dynamic", label: "Conversation style" },
  { key: "length_tier", label: "Episode length" },
  { key: "video_style", label: "Video style" },
  { key: "episode_planning_mode", label: "Episode planning" },
  { key: "source_language", label: "Source language" },
];

// Pipeline tokens the operator should read as words. The option VALUE sent to
// the pipeline is always the raw token — only the visible label is humanized.
// Unknown / operator-added tokens fall back to snake_case → sentence case, so
// new options never need an entry here to render readably.
const LABEL_OVERRIDES: Record<string, string> = {
  default_deep_dive: "Default (deep dive)",
};

function humanizeOption(field: string, value: string): string {
  if (LABEL_OVERRIDES[value]) return LABEL_OVERRIDES[value];
  if (field === "source_language") {
    // Render language codes as names: "ar" → "Arabic (ar)".
    try {
      const name = new Intl.DisplayNames(["en"], { type: "language" }).of(
        value,
      );
      if (name && name.toLowerCase() !== value.toLowerCase())
        return `${name} (${value})`;
    } catch {
      /* not a language code — fall through to the generic form */
    }
  }
  const words = value.replace(/[_-]/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// content_profile → bucket, mirrors _rules.bucket_for_profile (display only).
const PROFILE_TO_BUCKET: Record<string, string> = {
  islamic_scholarly: "Islamic",
  technical: "Technical",
  fiction: "Fiction",
  consumer_explainer: "Guides",
  general_nonfiction: "Guides",
};

export default function SmartForm({ proposed, onChange }: Props) {
  const [options, setOptions] = useState<Options | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState<string | null>(null);
  const [addText, setAddText] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Load the option-sets once; pre-select from the proposal (or first option).
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await apiFetch<{ options: Options }>(
          "/api/intake/form-options",
        );
        if (!alive) return;
        const opts: Options = data.options;
        setOptions(opts);
        const initial: Record<string, string> = {};
        for (const { key } of FIELD_LABELS) {
          const proposedVal = proposed?.[key]?.value;
          initial[key] =
            proposedVal && opts[key]?.includes(proposedVal)
              ? proposedVal
              : (opts[key]?.[0] ?? "");
        }
        setValues(initial);
      } catch (e) {
        if (alive)
          setError(
            e instanceof ApiFetchError && e.status !== 0
              ? e.message
              : `Network error: ${String(e)}`,
          );
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Propagate the merged settings to the parent in a commit-phase effect — never
  // inline in a setter/updater (calling the parent's setState during render is
  // the "update a component while rendering another" violation).
  useEffect(() => {
    onChange?.(values);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values]);

  function setValue(key: string, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  // Merge the voice/engine picker's flat keys into the same settings object.
  function mergeVoice(patch: Record<string, string>) {
    setValues((prev) => ({ ...prev, ...patch }));
  }

  async function addOption(field: string) {
    const value = addText.trim();
    if (!value) {
      setAdding(null);
      return;
    }
    try {
      const data = await apiFetch<{ options: Options }>(
        "/api/intake/form-options",
        {
          method: "POST",
          body: { action: "add", field, value },
        },
      );
      setOptions(data.options);
      setValue(field, value); // select the value the operator just added
    } catch (e) {
      setError(
        e instanceof ApiFetchError && e.status !== 0
          ? e.message
          : `Network error: ${String(e)}`,
      );
    } finally {
      setAdding(null);
      setAddText("");
    }
  }

  if (loading)
    return (
      <div className="intake-card">
        <p className="intake-hint" role="status">
          Loading options…
        </p>
      </div>
    );
  if (!options)
    return (
      <div className="intake-card">
        <p className="intake-error" role="alert">
          {error || "No options"}
        </p>
      </div>
    );

  const bucket = PROFILE_TO_BUCKET[values.content_profile] ?? "Islamic";

  return (
    <>
      <div className="intake-card">
        <h2 className="intake-card-title">Production settings</h2>
        <p className="intake-hint">
          Pre-filled from the source. Everything is a dropdown — pick, or add
          your own with the "+ add" button. The folder bucket follows the
          content profile automatically.
        </p>

        {FIELD_LABELS.map(({ key, label }) => (
          <div className="intake-field" key={key}>
            <label className="intake-label" htmlFor={`sf-${key}`}>
              {label}
            </label>
            <div className="intake-smartrow">
              <select
                id={`sf-${key}`}
                className="intake-select"
                value={values[key] ?? ""}
                onChange={(e) => setValue(key, e.target.value)}
              >
                {(options[key] ?? []).map((opt) => (
                  <option key={opt} value={opt}>
                    {humanizeOption(key, opt)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="intake-smalladd"
                onClick={() => {
                  setAdding(adding === key ? null : key);
                  setAddText("");
                }}
                aria-label={`Add a new ${label} option`}
              >
                + add
              </button>
            </div>
            {adding === key && (
              <div className="intake-addrow">
                <input
                  className="intake-input"
                  type="text"
                  value={addText}
                  placeholder={`New ${label.toLowerCase()}…`}
                  onChange={(e) => setAddText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addOption(key);
                    }
                  }}
                  aria-label={`New ${label} value`}
                />
                <button
                  type="button"
                  className="intake-btn intake-btn--primary"
                  onClick={() => addOption(key)}
                >
                  Add
                </button>
              </div>
            )}
            {proposed?.[key]?.rationale && (
              <p className="intake-rationale">
                Suggested: {proposed[key].rationale}
              </p>
            )}
          </div>
        ))}

        <div
          className="intake-field"
          role="group"
          aria-labelledby="sf-bucket-label"
        >
          <span className="intake-label" id="sf-bucket-label">
            Folder bucket <span>(derived from profile)</span>
          </span>
          <p className="intake-derived">{bucket}</p>
        </div>

        {error && (
          <p className="intake-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <VoicePicker onChange={mergeVoice} />
    </>
  );
}
