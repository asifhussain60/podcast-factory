/**
 * BriefWizard — the Intake commissioning form.
 *
 * Five steps, each asking about one thing, over the shared FieldDef array in
 * lib/brief/fields.ts. Option lists come from two endpoints and are merged here:
 * /api/brief/vocabularies (the source-property and product-route knobs) and the
 * existing /api/intake/form-options (the seven it already owns). Neither list is
 * written in this file — a value the pipeline rejects can never be offered.
 *
 * Nothing is written to disk until Generate. The draft is mirrored to
 * sessionStorage so a refresh mid-wizard does not lose the answers, and an
 * abandoned draft leaves nothing behind.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, ApiFetchError } from "../../lib/api-fetch";
import UploadStaging from "../intake/UploadStaging";
import VoicePicker from "../intake/VoicePicker";
import BriefStep from "./BriefStep";
import BriefReview from "./BriefReview";
import BriefProgress from "./BriefProgress";
import BriefDialog from "./BriefDialog";
import PromptPanel from "./PromptPanel";
import type { Option } from "./BriefField";
import { humanizeToken } from "../../lib/brief/humanize";
import {
  FIELDS,
  STEPS,
  invalidOn,
  missingOn,
  slugify,
  type FieldDef,
  type StepId,
} from "../../lib/brief/fields";

const DRAFT_KEY = "pf-intake-brief-draft";

interface VocabPayload {
  vocabularies: Record<string, Option[]>;
  defaults: Record<string, string>;
  profileNarrativeFrame: Record<string, string>;
  profileBucket: Record<string, string>;
  familyProfiles: Record<string, Record<string, string>>;
  profileCategory: Record<string, string>;
  profileAudioEngine: Record<string, string>;
  profileVoiceCast: Record<string, Record<string, string>>;
}

interface GenerateResult {
  slug: string;
  bucket: string;
  briefDir: string;
  prompt: string;
  files: string[];
  replaced: boolean;
}

function readDraft(): Record<string, string> | null {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : null;
  } catch {
    return null;
  }
}

export default function BriefWizard() {
  const [step, setStep] = useState<StepId>(1);
  // The furthest step reached. Steps 2-5 arrive pre-answered from the content
  // profile's defaults and carry no REQUIRED field, so "has no blockers" alone
  // would call them complete before they had been seen — a blank form reported
  // four of five done. Completion means answered AND walked through.
  const [furthest, setFurthest] = useState<StepId>(1);
  const [values, setValues] = useState<Record<string, string>>({});
  const [vocab, setVocab] = useState<VocabPayload | null>(null);
  const [options, setOptions] = useState<Record<string, string[]>>({});
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [stagingToken, setStagingToken] = useState<string | null>(null);
  const [stagedNames, setStagedNames] = useState<string[]>([]);
  const [slugTouched, setSlugTouched] = useState(false);
  const [explain, setExplain] = useState<{
    field: FieldDef;
    options: Option[];
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GenerateResult | null>(null);

  // Load both option sources, then seed defaults over any restored draft.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [v, o] = await Promise.all([
          apiFetch<VocabPayload>("/api/brief/vocabularies"),
          apiFetch<{ options: Record<string, string[]> }>(
            "/api/intake/form-options",
          ),
        ]);
        if (!alive) return;
        setVocab(v);
        setOptions(o.options);
        const seeded: Record<string, string> = { ...v.defaults };
        for (const f of FIELDS) {
          if (f.kind === "switch")
            seeded[f.key] = f.defaultOn ? "true" : "false";
          else if (seeded[f.key] === undefined) {
            if (f.options) seeded[f.key] = o.options[f.options]?.[0] ?? "";
            else if (f.vocab && f.required)
              seeded[f.key] = v.vocabularies[f.vocab]?.[0]?.value ?? "";
          }
        }
        // Resolve the profile from the MERGED values, after the draft is laid
        // over the defaults -- never from the defaults alone. A draft saved
        // before the family question existed carries a content_profile and a
        // category but no content_family, so resolving first and merging second
        // let the stale pair win: the form showed "Islamic" while the shelf,
        // the profile and the legacy tag all still said Technical / Articles.
        // The family and medium on screen are the authority, always.
        const draft = readDraft();
        const merged: Record<string, string> = { ...seeded, ...(draft ?? {}) };
        const profile =
          v.familyProfiles[merged.content_family ?? ""]?.[
            merged.source_medium ?? ""
          ];
        if (profile) {
          merged.content_profile = profile;
          merged.narrative_frame =
            v.profileNarrativeFrame[profile] ?? merged.narrative_frame;
          merged.category = v.profileCategory[profile] ?? merged.category;
        }
        setValues(merged);
        if (draft?.slug) setSlugTouched(true);
      } catch (e) {
        if (alive)
          setLoadError(
            e instanceof ApiFetchError && e.status !== 0
              ? e.message
              : `Could not load the form options: ${String(e)}`,
          );
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Mirror the draft so a refresh mid-wizard does not lose the answers.
  useEffect(() => {
    if (loading) return;
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(values));
    } catch {
      /* private mode / quota — the wizard still works, it just won't restore */
    }
  }, [values, loading]);

  const goTo = useCallback((id: StepId) => {
    setStep(id);
    setFurthest((f) => (id > f ? id : f));
  }, []);

  const setValue = useCallback(
    (key: string, value: string) => {
      setValues((prev) => {
        const next = { ...prev, [key]: value };
        if (key === "slug") setSlugTouched(true);
        // The folder name follows the title until you edit it yourself.
        if (key === "title" && !slugTouched) next.slug = slugify(value);
        // The narrative frame follows the profile's own default, same rule.
        // The pipeline profile is never chosen directly. It falls out of the
        // kind of content plus where it came from, which is what lets "Islamic
        // scholarly" and "Islamic session" stop being a choice anyone has to
        // understand: both are Islamic, and the medium tells them apart.
        if (key === "content_family" || key === "source_medium") {
          const profile =
            vocab?.familyProfiles[next.content_family ?? ""]?.[
              next.source_medium ?? ""
            ];
          if (profile) {
            next.content_profile = profile;
            // Everything the profile decides follows it in the same step, so
            // the derived shelf, frame and legacy tag can never lag a change.
            const frame = vocab?.profileNarrativeFrame[profile];
            if (frame) next.narrative_frame = frame;
            const category = vocab?.profileCategory[profile];
            if (category) next.category = category;
          }
        }
        return next;
      });
    },
    [slugTouched, vocab],
  );

  const mergeVoice = useCallback((patch: Record<string, string>) => {
    setValues((prev) => ({ ...prev, ...patch }));
  }, []);

  const optionsFor = useCallback(
    (f: FieldDef): Option[] => {
      if (f.vocab) return vocab?.vocabularies[f.vocab] ?? [];
      if (f.options)
        return (options[f.options] ?? []).map((v) => ({
          value: v,
          label: humanizeToken(f.key, v),
        }));
      return [];
    },
    [vocab, options],
  );

  const bucket =
    vocab?.profileBucket[values.content_profile ?? ""] ?? "Islamic";

  // Open the native folder chooser and take the folder's NAME as the slug.
  // showDirectoryPicker gives us that name without reading what is inside, so
  // pointing it at a big folder costs nothing; the webkitdirectory input is the
  // fallback, and there the first entry's relative path starts with the folder.
  // Nothing here touches the server -- the browser's own picker IS Finder.
  const pickFolder = useCallback(async () => {
    setError("");
    const apply = (name: string) => {
      const s = slugify(name);
      if (!s) {
        setError(
          `"${name}" has no letters or digits to make a folder name from.`,
        );
        return;
      }
      setSlugTouched(true);
      setValues((prev) => ({ ...prev, slug: s }));
    };

    const picker = (
      window as unknown as {
        showDirectoryPicker?: () => Promise<{ name: string }>;
      }
    ).showDirectoryPicker;

    if (picker) {
      try {
        const handle = await picker();
        apply(handle.name);
      } catch (e) {
        // Cancelling the dialog is not a failure and must not shout about it.
        if ((e as { name?: string })?.name !== "AbortError") {
          setError(`Could not read that folder: ${String(e)}`);
        }
      }
      return;
    }

    const input = document.createElement("input");
    input.type = "file";
    input.setAttribute("webkitdirectory", "");
    input.addEventListener("change", () => {
      const first = input.files?.[0];
      const folder = first?.webkitRelativePath?.split("/")[0];
      if (folder) apply(folder);
    });
    input.click();
  }, []);

  const blockers = useMemo(() => {
    const out: { step: StepId; reasons: string[] }[] = [];
    for (const s of STEPS) {
      const reasons = [
        ...missingOn(s.id, values).map((f) => `${f.label} is needed`),
        ...invalidOn(s.id, values).map(
          (f) => `${f.label} is not in the right form`,
        ),
      ];
      if (reasons.length) out.push({ step: s.id, reasons });
    }
    return out;
  }, [values]);

  const stepBlocked = blockers.find((b) => b.step === step);
  const canGenerate = blockers.length === 0 && !busy;

  // You may reach a step only when every step BEFORE it is answered. Derived
  // from the live blocker list rather than remembering how far you once got:
  // going back and emptying a required field re-locks everything after it,
  // which a high-water mark would not do. The step you are standing on always
  // stays reachable so the gate can never strand you on a page you cannot leave.
  const firstBlockedStep = blockers.length
    ? Math.min(...blockers.map((b) => b.step))
    : Number.POSITIVE_INFINITY;
  const canVisit = (id: StepId) => id <= firstBlockedStep || id === step;

  async function generate() {
    setBusy(true);
    setError("");
    try {
      const data = await apiFetch<GenerateResult>("/api/brief/generate", {
        method: "POST",
        body: { values, stagingToken },
      });
      setResult(data);
      try {
        sessionStorage.removeItem(DRAFT_KEY);
      } catch {
        /* nothing to clean up */
      }
    } catch (e) {
      setError(
        e instanceof ApiFetchError && e.status !== 0
          ? e.message
          : `Could not write the brief: ${String(e)}`,
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading)
    return (
      <div className="intake-card">
        <p className="intake-hint bf-note" role="status">
          Reading the pipeline's own vocabularies…
        </p>
      </div>
    );

  if (loadError)
    return (
      <div className="intake-card">
        <p className="intake-error bf-note" role="alert">
          {loadError}
        </p>
      </div>
    );

  if (result)
    return (
      <section className="bf-card bf-card-done" aria-live="polite">
        <h2 className="bf-step-title">The commission is written down</h2>
        <PromptPanel
          prompt={result.prompt}
          briefDir={result.briefDir}
          files={result.files}
          replaced={result.replaced}
          onSendToLauncher={() => {
            window.location.href = `/studio/new?brief=${encodeURIComponent(result.slug)}`;
          }}
        />
      </section>
    );

  const current = STEPS.find((s) => s.id === step)!;

  return (
    <>
      <BriefProgress
        current={step}
        furthest={furthest}
        blockedSteps={blockers.map((b) => b.step)}
      />
      <div className="bf-wizard">
        <ol className="bf-rail" aria-label="Steps">
          {STEPS.map((s) => {
            const state =
              s.id === step ? "current" : s.id < step ? "done" : "ahead";
            const short = blockers.some((b) => b.step === s.id);
            const locked = !canVisit(s.id);
            return (
              <li
                className={`bf-rail-item is-${state}${locked ? " is-locked" : ""}`}
                key={s.id}
              >
                <button
                  type="button"
                  className="bf-rail-link"
                  aria-current={s.id === step ? "step" : undefined}
                  disabled={locked}
                  title={
                    locked
                      ? "Finish the steps before this one first."
                      : undefined
                  }
                  onClick={() => goTo(s.id)}
                >
                  <span className="bf-rail-num" aria-hidden="true">
                    {s.id}
                  </span>
                  <span className="bf-rail-text">
                    <span className="bf-rail-title">{s.title}</span>
                    <span className="bf-rail-blurb">{s.blurb}</span>
                  </span>
                  {short && s.id !== step && (
                    <span
                      className="bf-rail-flag"
                      aria-label="unanswered questions"
                    >
                      !
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ol>

        <section className="bf-card" aria-labelledby="bf-step-heading">
          <header className="bf-step-head">
            <p className="bf-step-eyebrow">
              Step {step} of {STEPS.length}
            </p>
            <h2 className="bf-step-title" id="bf-step-heading">
              {current.title}
            </h2>
            <p className="bf-step-blurb">{current.blurb}</p>
          </header>

          {step === 5 ? (
            <>
              <BriefReview
                values={values}
                bucket={bucket}
                stagedNames={stagedNames}
                optionsFor={optionsFor}
                onJump={goTo}
              />
              <BriefStep
                step={5}
                values={values}
                optionsFor={optionsFor}
                onChange={setValue}
                onExplain={(field, opts) =>
                  setExplain({ field, options: opts })
                }
                onPickFolder={pickFolder}
              />
            </>
          ) : (
            <BriefStep
              step={step}
              values={values}
              optionsFor={optionsFor}
              onChange={setValue}
              onExplain={(field, opts) => setExplain({ field, options: opts })}
              onPickFolder={pickFolder}
            >
              {step === 1 && values.content_profile && (
                <p className="bf-derived">
                  This goes on the <strong>{bucket}</strong> shelf, and will run
                  on the branch{" "}
                  <code>
                    {bucket}/{values.slug || "…"}
                  </code>
                  .
                </p>
              )}
              {step === 2 && (
                <UploadStaging
                  onChange={({ token, files }) => {
                    setStagingToken(token);
                    setStagedNames(files.map((f) => f.filename));
                  }}
                />
              )}
              {step === 4 && (
                // The picker's own default is ElevenLabs, retired in 2026-08. The
                // engine each profile actually uses comes from the content-type
                // registry instead, so a brief cannot commission a dead engine.
                <VoicePicker
                  key={values.content_profile}
                  defaultEngine={
                    vocab?.profileAudioEngine[values.content_profile ?? ""] ??
                    "notebooklm"
                  }
                  defaultHostA={
                    vocab?.profileVoiceCast[values.content_profile ?? ""]
                      ?.host_a
                  }
                  defaultHostB={
                    vocab?.profileVoiceCast[values.content_profile ?? ""]
                      ?.host_b
                  }
                  onChange={mergeVoice}
                />
              )}
            </BriefStep>
          )}

          {error && (
            <p className="intake-error bf-note" role="alert">
              {error}
            </p>
          )}

          <footer className="bf-nav">
            <button
              type="button"
              className="bf-btn"
              disabled={step === 1}
              onClick={() => goTo((step > 1 ? step - 1 : step) as StepId)}
            >
              Back
            </button>

            {step < 5 ? (
              <button
                type="button"
                className="bf-btn bf-btn-primary"
                disabled={!!stepBlocked}
                onClick={() => goTo((step + 1) as StepId)}
              >
                Next
              </button>
            ) : (
              <button
                type="button"
                className="bf-btn bf-btn-primary"
                disabled={!canGenerate}
                onClick={generate}
              >
                {busy ? "Writing…" : "Generate the brief"}
              </button>
            )}
          </footer>

          {stepBlocked && (
            <p className="intake-hint bf-blocked" role="status">
              Before moving on: {stepBlocked.reasons.join(", ")}.
            </p>
          )}
          {step === 5 && blockers.length > 0 && (
            <ul className="bf-blockers" aria-label="What is still missing">
              {blockers.map((b) => (
                <li key={b.step}>
                  <button
                    type="button"
                    className="bf-blocker-link"
                    onClick={() => goTo(b.step)}
                  >
                    {STEPS.find((s) => s.id === b.step)?.title}
                  </button>
                  {" — "}
                  {b.reasons.join(", ")}
                </li>
              ))}
            </ul>
          )}
        </section>

        <BriefDialog
          open={!!explain}
          title={explain ? explain.field.label : ""}
          onClose={() => setExplain(null)}
        >
          <dl className="bf-explain-list">
            {(explain?.options ?? []).map((o) => (
              <div className="bf-explain-row" key={o.value}>
                <dt>{o.label}</dt>
                <dd>{o.description || "—"}</dd>
              </div>
            ))}
          </dl>
        </BriefDialog>
      </div>
    </>
  );
}
