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
 * localStorage on every keystroke so neither a refresh nor closing the tab
 * loses the answers, and Generate clears it so an abandoned draft leaves
 * nothing behind.
 *
 * localStorage, NOT sessionStorage (2026-08-30): sessionStorage is scoped to the
 * tab and is dropped the moment it closes, so the one case worth protecting
 * against — navigating away mid-commission and coming back — was the one case it
 * did not cover. This form asks ~40 questions; losing them to a stray click is
 * not a refresh problem, it is the whole risk.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch, ApiFetchError } from "../../lib/api-fetch";
import UploadStaging from "../intake/UploadStaging";
import VoicePicker from "../intake/VoicePicker";
import BriefStep from "./BriefStep";
import BriefReview from "./BriefReview";
import BriefProgress from "./BriefProgress";
import ContentPicker from "./ContentPicker";
import ChapterSources from "./ChapterSources";
import BriefDialog from "./BriefDialog";
import PromptPanel from "./PromptPanel";
import SavedPrompt from "./SavedPrompt";
import type { Option } from "./BriefField";
import { humanizeToken } from "../../lib/brief/humanize";
import {
  FIELDS,
  FIELDS_BY_KEY,
  STEPS,
  completenessProblems,
  invalidOn,
  missingOn,
  slugify,
  type FieldDef,
  type StepId,
  WORK_STEP,
  SOURCE_STEP,
  CHAPTERS_STEP,
  PODCAST_STEP,
  REVIEW_STEP,
} from "../../lib/brief/fields";
import { chapterList } from "../../lib/brief/render";

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

interface ContentItem {
  slug: string;
  title: string;
  bucket: string;
  status: string;
  /** When the book was last worked on, ms since the epoch; 0 when never. */
  touched?: number;
}

interface LoadedContent {
  slug: string;
  bucket: string;
  dir: string;
  values: Record<string, string>;
  present: { meta: boolean; series: boolean };
  status: string;
  locked: string[];
}

interface SaveResult {
  slug: string;
  dir: string;
  written: { field: string; file: string; path: string; value: string }[];
  skipped: { field: string; reason: string }[];
  created?: string[];
  /** Hand-off prompt describing the book as it now stands. */
  prompt?: string;
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
    const raw = localStorage.getItem(DRAFT_KEY);
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
  // The ROLES too, not just the names: whether a recorded session has its
  // recording attached is a readiness question, and a filename cannot answer it.
  const [stagedRoles, setStagedRoles] = useState<string[]>([]);
  const [slugTouched, setSlugTouched] = useState(false);
  const [explain, setExplain] = useState<{
    field: FieldDef;
    options: Option[];
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GenerateResult | null>(null);
  // Existing-content mode. `baseline` is what was on disk when it loaded, so a
  // save can send only what actually changed rather than rewriting every key.
  const [items, setItems] = useState<ContentItem[]>([]);
  const [editing, setEditing] = useState<LoadedContent | null>(null);
  const [baseline, setBaseline] = useState<Record<string, string>>({});
  const [loadingBook, setLoadingBook] = useState(false);
  const [saved, setSaved] = useState<SaveResult | null>(null);
  // The seeded defaults, kept so switching between a new commission and an
  // existing piece can rebuild values from a known base rather than from
  // whatever the previous selection left behind.
  const seedRef = useRef<Record<string, string>>({});

  // Load both option sources, then seed defaults over any restored draft.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [v, o, c] = await Promise.all([
          apiFetch<VocabPayload>("/api/brief/vocabularies"),
          apiFetch<{ options: Record<string, string[]> }>(
            "/api/intake/form-options",
          ),
          apiFetch<{ items: ContentItem[] }>("/api/brief/content"),
        ]);
        if (!alive) return;
        setVocab(v);
        setOptions(o.options);
        setItems(c.items);
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
        seedRef.current = { ...seeded };
        // A restored draft is not trusted blindly: if a value is not one its
        // field currently offers, it is dropped back to the default. Otherwise a
        // draft written before a vocabulary changed can seat a value the form
        // has no way to correct, and the form is stuck at the last step.
        const draft = readDraft() ?? {};
        for (const f of FIELDS) {
          const val = draft[f.key];
          if (val === undefined || f.kind === "text" || f.kind === "textarea")
            continue;
          const offered = f.vocab
            ? v.vocabularies[f.vocab]?.map((o) => o.value)
            : f.options
              ? o.options[f.options]
              : undefined;
          if (offered && val !== "" && !offered.includes(val))
            delete draft[f.key];
        }
        const merged: Record<string, string> = { ...seeded, ...draft };
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

  // Mirror the draft so neither a refresh nor leaving the page loses answers.
  // Runs on every `values` change, i.e. every keystroke and every selection —
  // there is no debounce and there should not be: the write is a few hundred
  // bytes, and a debounce is a window in which the answers are not yet saved,
  // which is exactly what this exists to prevent.
  //
  // NOT while an existing piece is loaded. The draft belongs to the NEW
  // commission, and writing an existing book's settings into it meant the next
  // visit seeded the blank form with that book's values -- including ones the
  // form cannot offer, like `video_style: none` -- leaving Generate refusing a
  // value the operator never chose and could not change.
  useEffect(() => {
    if (loading || editing) return;
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(values));
    } catch {
      /* private mode / quota — the wizard still works, it just won't restore */
    }
  }, [values, loading, editing]);

  const goTo = useCallback((id: StepId) => {
    setStep(id);
    setFurthest((f) => (id > f ? id : f));
  }, []);

  // Bring the new step into view and put focus on its heading.
  //
  // Keyed on `step` rather than done inside goTo, because goTo is not the only
  // way the step changes -- selecting an existing piece and clearing the form
  // both call setStep(1) directly, and a scroll that only fired from the Next
  // button would leave those two landing mid-page.
  //
  // Focus moves with the scroll: a wizard step is a new screenful of questions,
  // and leaving focus on the Next button (now offscreen) means a keyboard tab
  // resumes from the bottom of the previous step and a screen reader announces
  // nothing at all. `tabIndex={-1}` on the heading makes it focusable without
  // adding it to the tab order. `preventScroll` lets the smooth scroll below own
  // the movement, instead of focus jumping instantly and the animation chasing it.
  // Scrolls the CARD, not the heading: the card opens with the "Step N of 5"
  // eyebrow, and landing below that loses the one line that says where you are.
  const cardRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const firstStepRender = useRef(true);
  useEffect(() => {
    // Not on mount: the page has just loaded at the top and nothing has moved,
    // so scrolling and stealing focus would be an unprompted jump.
    if (firstStepRender.current) {
      firstStepRender.current = false;
      return;
    }
    headingRef.current?.focus({ preventScroll: true });
    const reduced = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    cardRef.current?.scrollIntoView({
      behavior: reduced ? "auto" : "smooth",
      block: "start",
    });
  }, [step]);

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
            // A recording is PROOFREAD, never re-voiced, and `episode_voice`
            // is the field the pipeline reads to know that — the same field
            // that decides whether the chapters ARE the reading edition or a
            // fresh one is authored from the transcript. It was never gathered
            // here: `purification-of-the-heart` only carries it because it was
            // typed into series-config.yaml by hand after a rewriting pass had
            // already reached two of its chapters. Derived rather than asked,
            // because on a recording there is no second right answer.
            if (next.source_medium === "audio_lecture")
              next.episode_voice = "verbatim";
            else delete next.episode_voice;
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

  // Load an existing piece, or drop back to commissioning a new one. The draft
  // in localStorage belongs to the NEW commission and is deliberately left
  // alone while editing, so switching back does not lose half-typed answers.
  const selectContent = useCallback(async (slug: string) => {
    setError("");
    setSaved(null);
    setStep(1);
    if (!slug) {
      setEditing(null);
      setBaseline({});
      setValues({ ...seedRef.current, ...(readDraft() ?? {}) });
      return;
    }
    setLoadingBook(true);
    try {
      const data = await apiFetch<LoadedContent>(
        `/api/brief/content/${encodeURIComponent(slug)}`,
      );
      setEditing(data);
      // Defaults underneath, so a setting the book never recorded still shows
      // the value the pipeline would use rather than an empty box.
      const shown = { ...seedRef.current, ...data.values };
      setValues(shown);
      // The baseline is WHAT WAS SHOWN, not what was on disk. Comparing against
      // disk alone counted every defaulted-but-absent setting as an edit -- one
      // real change reported as twelve -- and pressing save would have written a
      // dozen default keys into a book that never carried them. Only a field
      // you actually touch after loading is written now.
      setBaseline(shown);
      setFurthest(REVIEW_STEP);
    } catch (e) {
      setError(
        e instanceof ApiFetchError && e.status !== 0
          ? e.message
          : `Could not load ${slug}: ${String(e)}`,
      );
    } finally {
      setLoadingBook(false);
    }
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

  /**
   * Land on the piece you were last working on (Asif, 2026-08-31).
   *
   * Opening the form on a blank new commission meant re-picking the same book
   * every visit, when nine visits in ten are to carry on with the one already
   * in flight. "Last" is the same `touched` the picker sorts by — the newest
   * change among the files a working session actually writes.
   *
   * THREE THINGS IT WILL NOT DO. It never runs twice (the ref), so choosing
   * "Commission something new" is not undone a moment later. It never runs when
   * a draft is in progress, because loading a book replaces what is on screen
   * and a half-answered commission must not be thrown away. And it loads a
   * book, which is a read — nothing is written, and every field stays exactly
   * as editable as if you had picked it yourself.
   */
  const preloaded = useRef(false);
  useEffect(() => {
    if (preloaded.current || loading || items.length === 0) return;
    preloaded.current = true;
    const draft = readDraft();
    // A draft with a title or a folder name is real work in progress. The seed
    // values alone are not — those are just the defaults written back.
    if (draft?.title?.trim() || draft?.slug?.trim()) return;
    const last = [...items].sort(
      (a, b) => (b.touched ?? 0) - (a.touched ?? 0),
    )[0];
    if (last?.touched) selectContent(last.slug);
  }, [items, loading, selectContent]);

  const bucket = editing
    ? editing.bucket
    : (vocab?.profileBucket[values.content_profile ?? ""] ?? "Islamic");

  const lockedFields = useMemo(() => new Set(editing?.locked ?? []), [editing]);

  // Only what actually differs from what was on disk, and never a locked field.
  const changed = useMemo(() => {
    if (!editing) return {} as Record<string, string>;
    const out: Record<string, string> = {};
    for (const f of FIELDS) {
      if (f.formOnly || lockedFields.has(f.key)) continue;
      const now = (values[f.key] ?? "").trim();
      const was = (baseline[f.key] ?? "").trim();
      if (now !== was) out[f.key] = now;
    }
    return out;
  }, [editing, values, baseline, lockedFields]);

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

  /**
   * The pipeline-readiness problems, which gate GENERATING and nothing else.
   *
   * Deliberately separate from `blockers`, which gate NAVIGATION: not having
   * uploaded the recording yet is a perfectly good reason to be refused a
   * brief, and a terrible reason to be unable to reach the questions about
   * chapters. These are the SERVER's own checks, imported rather than
   * restated, so the button is lit exactly when the endpoint would accept.
   */
  const notReady = useMemo(
    () =>
      completenessProblems(values, {
        sourceCount: stagedNames.length,
        roles: stagedRoles,
        // A book that already exists has its sources in its own folder, and
        // nothing is staged when you merely open it — so the upload checks
        // would report a book with a recording sitting on disk as having
        // nothing to work from, and refuse to write its brief.
        existing: !!editing,
      }),
    [values, stagedNames, stagedRoles, editing],
  );

  const stepBlocked = blockers.find((b) => b.step === step);
  const canGenerate = blockers.length === 0 && notReady.length === 0 && !busy;

  // You may reach a step only when every step BEFORE it is answered. Derived
  // from the live blocker list rather than remembering how far you once got:
  // going back and emptying a required field re-locks everything after it,
  // which a high-water mark would not do. The step you are standing on always
  // stays reachable so the gate can never strand you on a page you cannot leave.
  const firstBlockedStep = blockers.length
    ? Math.min(...blockers.map((b) => b.step))
    : Number.POSITIVE_INFINITY;
  const canVisit = (id: StepId) => id <= firstBlockedStep || id === step;

  async function saveChanges() {
    if (!editing) return;
    setBusy(true);
    setError("");
    try {
      const data = await apiFetch<SaveResult>(
        `/api/brief/content/${encodeURIComponent(editing.slug)}`,
        { method: "POST", body: { changes: changed } },
      );
      setSaved(data);
      // What was written is the new baseline, so the change list empties and a
      // second press cannot rewrite the same values.
      setBaseline((prev) => ({ ...prev, ...changed }));
    } catch (e) {
      setError(
        e instanceof ApiFetchError && e.status !== 0
          ? e.message
          : `Could not save: ${String(e)}`,
      );
    } finally {
      setBusy(false);
    }
  }

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
        localStorage.removeItem(DRAFT_KEY);
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

  const chapterCount = chapterList({
    values,
    bucket,
    briefDir: "",
    repoRoot: "",
    sources: [],
    generatedAt: "",
  }).length;
  const current = STEPS.find((s) => s.id === step)!;

  return (
    <>
      <ContentPicker
        items={items}
        value={editing?.slug ?? ""}
        busy={loadingBook || busy}
        onChange={selectContent}
      />
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

        <section
          className="bf-card"
          aria-labelledby="bf-step-heading"
          ref={cardRef}
        >
          <header className="bf-step-head">
            <p className="bf-step-eyebrow">
              Step {step} of {STEPS.length}
            </p>
            <h2
              className="bf-step-title"
              id="bf-step-heading"
              ref={headingRef}
              tabIndex={-1}
            >
              {current.title}
            </h2>
            <p className="bf-step-blurb">{current.blurb}</p>
          </header>

          {step === REVIEW_STEP ? (
            <>
              <BriefReview
                values={values}
                bucket={bucket}
                stagedNames={stagedNames}
                optionsFor={optionsFor}
                onJump={goTo}
              />
              <BriefStep
                step={REVIEW_STEP}
                values={values}
                optionsFor={optionsFor}
                onChange={setValue}
                onExplain={(field, opts) =>
                  setExplain({ field, options: opts })
                }
                onPickFolder={pickFolder}
                lockedFields={lockedFields}
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
              lockedFields={lockedFields}
            >
              {step === WORK_STEP && values.content_profile && (
                <p className="bf-derived">
                  This goes on the <strong>{bucket}</strong> shelf, and will run
                  on the branch{" "}
                  <code>
                    {bucket}/{values.slug || "…"}
                  </code>
                  .
                </p>
              )}
              {step === CHAPTERS_STEP && values.slug && (
                <ChapterSources
                  slug={values.slug}
                  onChapters={(titles) =>
                    setValue("chapter_list", titles.join("\n"))
                  }
                />
              )}
              {step === CHAPTERS_STEP && chapterCount > 0 && (
                // Reading a count off a textarea is exactly the kind of thing a
                // person should not have to do by eye, and the number is what
                // the run is measured against.
                <p className="bf-derived">
                  <strong>{chapterCount}</strong>{" "}
                  {chapterCount === 1 ? "chapter" : "chapters"} listed. The
                  pipeline will use these names exactly, in this order.
                </p>
              )}
              {step === SOURCE_STEP && (
                <UploadStaging
                  onChange={({ token, files }) => {
                    setStagingToken(token);
                    setStagedNames(files.map((f) => f.filename));
                    setStagedRoles(files.map((f) => f.role));
                  }}
                />
              )}
              {step === PODCAST_STEP &&
                values.source_medium === "audio_lecture" && (
                  // A recorded session IS its own audio. No episode is generated
                  // for it and no voice is synthesised, so every question on this
                  // step -- the voice picker included -- has no answer that means
                  // anything. Say so rather than leaving a step that looks broken.
                  <p className="bf-derived">
                    No podcast is made from a recorded session &mdash; the
                    recording is the episode &mdash; so the episode and voice
                    settings do not apply and are not asked. The two questions
                    left describe the material itself. Slide decks are still
                    produced; that choice is on <strong>The edition</strong>.
                  </p>
                )}
              {step === PODCAST_STEP &&
                values.source_medium !== "audio_lecture" && (
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
              disabled={step === WORK_STEP}
              onClick={() => goTo((step > 1 ? step - 1 : step) as StepId)}
            >
              Back
            </button>

            {step < REVIEW_STEP ? (
              <button
                type="button"
                className="bf-btn bf-btn-primary"
                disabled={!!stepBlocked}
                onClick={() => goTo((step + 1) as StepId)}
              >
                Next
              </button>
            ) : (
              <>
                {/* Editing a piece that already exists had NO way to reach the
                    brief at all: its primary action is Save, and Generate was
                    the primary action of the other mode (Asif, 2026-08-31).
                    Added as the SECONDARY action rather than a second primary,
                    so exactly one Generate is ever on screen — in a new
                    commission it IS the primary, here it sits beside Save. */}
                {editing && (
                  <button
                    type="button"
                    className="bf-btn"
                    disabled={!canGenerate}
                    onClick={generate}
                    title="Write the commission and the hand-off prompt for this piece"
                  >
                    {busy ? "Working…" : "Generate the brief"}
                  </button>
                )}
                <button
                  type="button"
                  className="bf-btn bf-btn-primary"
                  disabled={
                    editing
                      ? busy || Object.keys(changed).length === 0
                      : !canGenerate
                  }
                  onClick={editing ? saveChanges : generate}
                >
                  {busy
                    ? "Saving…"
                    : editing
                      ? `Save ${Object.keys(changed).length || "no"} change${
                          Object.keys(changed).length === 1 ? "" : "s"
                        }`
                      : "Generate the brief"}
                </button>
              </>
            )}
          </footer>

          {saved && (
            <div className="bf-saved" role="status">
              <p className="bf-saved-head">
                {saved.written.length
                  ? `Saved ${saved.written.length} change${saved.written.length === 1 ? "" : "s"} to disk.`
                  : "Nothing was written."}
              </p>
              {saved.created?.length ? (
                <p className="bf-saved-note">
                  Created{" "}
                  {saved.created.map((f, i) => (
                    <span key={f}>
                      {i > 0 && ", "}
                      <code>{f}</code>
                    </span>
                  ))}{" "}
                  — this book did not have one, so these settings had nowhere to
                  go until now.
                </p>
              ) : null}
              {saved.written.length > 0 && (
                <ul className="bf-saved-list">
                  {saved.written.map((w) => (
                    <li key={w.field}>
                      <strong>
                        {FIELDS_BY_KEY[w.field]?.label ?? w.field}
                      </strong>
                      {" → "}
                      <code>
                        {w.file === "meta" ? "meta.yml" : "series-config.yaml"}
                      </code>
                    </li>
                  ))}
                </ul>
              )}
              {saved.skipped.length > 0 && (
                <ul className="bf-saved-list bf-saved-skipped">
                  {saved.skipped.map((k) => (
                    <li key={k.field}>
                      <strong>
                        {FIELDS_BY_KEY[k.field]?.label ?? k.field}
                      </strong>
                      {" — not written: "}
                      {k.reason}
                    </li>
                  ))}
                </ul>
              )}
              <p className="intake-hint bf-note">
                The live Library still shows the previous values until this book
                is published again.
              </p>
              {saved.prompt && (
                <SavedPrompt prompt={saved.prompt} slug={saved.slug} />
              )}
            </div>
          )}

          {stepBlocked && (
            <p className="intake-hint bf-blocked" role="status">
              Before moving on: {stepBlocked.reasons.join(", ")}.
            </p>
          )}
          {step === REVIEW_STEP && blockers.length + notReady.length > 0 && (
            <ul className="bf-blockers" aria-label="What is still missing">
              {[
                ...blockers,
                // Readiness problems read the same way as missing answers and
                // are fixed the same way -- by going to a step -- so they are
                // listed together rather than in a second list of their own.
                ...notReady.map((n) => ({ step: n.step, reasons: [n.reason] })),
              ].map((b, i) => (
                <li key={`${b.step}-${i}`}>
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
