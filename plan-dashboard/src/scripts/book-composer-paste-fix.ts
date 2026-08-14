/**
 * book-composer-paste-fix.ts — the "Paste & fix chapter" tool for the Book
 * Composer's Refinement tab (Sessions-lane books only).
 *
 * Split out of book-composer.ts (DR-005 size ratchet). The paste NEVER
 * touches the live editor. It lands in a dedicated box; the server checks it
 * (image restoration, paragraph repair, Scholar continuity, house-style
 * formatting, the fidelity gate — the exact same compose_articulate.py the
 * CLI skill uses) and hands back a fixed body for review; only on explicit
 * Apply does that fixed body reach book.md, through the same writer every
 * other Compose save uses. A raw, broken paste is never in a position for
 * autosave to persist before it has been fixed.
 *
 * `deps` is the host's live editor/chapter state, threaded in as getters so
 * this module never holds a stale snapshot of what book-composer.ts owns.
 */
import { apiFetch } from "../lib/api-fetch";
import type { ChapterEditor } from "./book-md-editor";

interface PasteFixCheckResult {
  heading: string;
  base_words: number;
  new_words: number;
  ratio: number;
  findings: string[];
  images_restored: { path: string; anchor: string; placement: string }[];
  paragraph_changes: { kind: string }[];
  format_changes: { kind: string }[];
  quote_kind_declarations?: { first_line: string; kind: string }[];
  continuity_changes: {
    kind: string;
    status: string;
    grounded?: number;
    morphology?: boolean;
    reason?: string;
    findings?: string[];
  }[];
  readability_review?: {
    status: "not-run" | "checked" | "skipped";
    budget?: number;
    proposed?: number;
    gated_out?: { quote?: string; reasons?: string[] }[];
    reason?: string;
    questions: {
      defect?: string;
      question?: string;
      quote?: string;
    }[];
    companion_notes?: {
      id?: string;
      kind?: string;
      body?: string;
      anchor?: string;
      quote?: string;
      etymology?: string[];
      review?: "proposed" | "kept";
      source?: {
        provider?: string;
        ref?: string;
        locator?: string;
        label?: string;
      };
    }[];
    answered?: number;
    unanswered?: number;
    unsourced?: { quote?: string; question?: string }[];
  };
  body: string;
  clean: boolean;
}

export interface PasteFixDeps {
  getActiveEditor: () => ChapterEditor | null;
  getSelectedChapter: () => string;
  getChapterTitle: (chapterKey: string) => string;
  setAiStatus: (message: string, isError?: boolean) => void;
  reloadPreservingChapter: () => void;
  slug: string;
}

export function createPasteFixController(deps: PasteFixDeps): {
  open: () => void;
} {
  const {
    getActiveEditor,
    getSelectedChapter,
    getChapterTitle,
    setAiStatus,
    reloadPreservingChapter,
    slug,
  } = deps;

  let pasteFixOpen = false;

  function renderPasteFixReview(
    container: HTMLElement,
    result: PasteFixCheckResult,
  ): void {
    container.textContent = "";
    const summary = document.createElement("ul");
    summary.className = "cx-paste-fix-summary";
    const words = document.createElement("li");
    words.textContent = `${result.base_words} → ${result.new_words} words (${result.ratio}×)`;
    summary.appendChild(words);
    if (result.images_restored.length > 0) {
      const li = document.createElement("li");
      const n = result.images_restored.length;
      li.textContent = `${n} image${n === 1 ? "" : "s"} restored`;
      summary.appendChild(li);
    }
    if (result.format_changes.length > 0) {
      const li = document.createElement("li");
      const n = result.format_changes.length;
      li.textContent = `${n} formatting fix${n === 1 ? "" : "es"} applied`;
      summary.appendChild(li);
    }
    const paragraphChanges = result.paragraph_changes ?? [];
    const continuityChanges = result.continuity_changes ?? [];
    const readabilityReview = result.readability_review ?? {
      status: "not-run",
      questions: [],
    };

    if (paragraphChanges.length > 0) {
      const li = document.createElement("li");
      const n = paragraphChanges.length;
      li.textContent = `${n} paragraph repair${n === 1 ? "" : "s"} applied`;
      summary.appendChild(li);
    }
    if (continuityChanges.length > 0) {
      const kept = continuityChanges.filter((c) => c.status === "kept").length;
      const reverted = continuityChanges.filter(
        (c) => c.status === "reverted",
      ).length;
      const skipped = continuityChanges.filter(
        (c) => c.status === "skipped",
      ).length;
      const li = document.createElement("li");
      li.textContent = kept
        ? "Scholar continuity repair applied"
        : reverted
          ? "Scholar continuity repair was reverted by gates"
          : `Scholar continuity repair skipped${skipped > 1 ? ` (${skipped})` : ""}`;
      summary.appendChild(li);
    }
    if (readabilityReview.status === "checked") {
      const li = document.createElement("li");
      const n = readabilityReview.questions?.length ?? 0;
      const drafts = readabilityReview.companion_notes?.length ?? 0;
      li.textContent = drafts
        ? `Student Reader prepared ${drafts} Companion draft${drafts === 1 ? "" : "s"}`
        : n
          ? `Student Reader found ${n} gap${n === 1 ? "" : "s"}, but prepared no Companion draft${n === 1 ? "" : "s"}`
          : "Student Reader readability check passed";
      summary.appendChild(li);
    } else if (readabilityReview.status === "skipped") {
      const li = document.createElement("li");
      li.textContent = "Student Reader readability check skipped";
      summary.appendChild(li);
    }
    container.appendChild(summary);

    if (result.findings.length > 0) {
      const warn = document.createElement("div");
      warn.className = "cx-paste-fix-findings";
      const head = document.createElement("p");
      head.textContent = "The fidelity gates flagged this rewrite:";
      warn.appendChild(head);
      const ul = document.createElement("ul");
      for (const f of result.findings) {
        const li = document.createElement("li");
        li.textContent = f;
        ul.appendChild(li);
      }
      warn.appendChild(ul);
      container.appendChild(warn);
    } else {
      const clean = document.createElement("p");
      clean.className = "cx-paste-fix-clean";
      clean.innerHTML =
        '<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Clean — every deterministic gate passed.';
      container.appendChild(clean);
    }
  }

  function openPasteFixModal(): void {
    if (!getActiveEditor() || pasteFixOpen) return;
    pasteFixOpen = true;
    const title = getChapterTitle(getSelectedChapter());

    const scrim = document.createElement("div");
    scrim.className = "cx-confirm-scrim cx-paste-fix-scrim";
    const box = document.createElement("div");
    box.className = "cx-confirm-box cx-paste-fix-box";
    scrim.appendChild(box);

    const heading = document.createElement("h2");
    heading.className = "cx-confirm-title";
    heading.textContent = `Paste & fix “${title}”`;
    box.appendChild(heading);

    const hint = document.createElement("p");
    hint.className = "cx-confirm-body";
    hint.textContent =
      "Paste the edited chapter below. Dropped images, split paragraphs, headings, Scholar continuity gaps, and Student Reader readability are checked before anything is saved.";
    box.appendChild(hint);

    const textarea = document.createElement("textarea");
    textarea.className = "cx-paste-fix-textarea";
    textarea.placeholder = "Paste the edited chapter text here…";
    box.appendChild(textarea);

    const workingEl = document.createElement("div");
    workingEl.className = "cx-paste-fix-working";
    workingEl.hidden = true;
    workingEl.setAttribute("role", "status");
    workingEl.setAttribute("aria-live", "polite");
    const workingHead = document.createElement("div");
    workingHead.className = "cx-paste-fix-working-head";
    const spinner = document.createElement("span");
    spinner.className = "cx-paste-fix-spinner";
    spinner.setAttribute("aria-hidden", "true");
    const workingLabel = document.createElement("strong");
    workingLabel.className = "cx-paste-fix-working-label";
    workingHead.append(spinner, workingLabel);
    const workingBar = document.createElement("div");
    workingBar.className = "cx-paste-fix-progress";
    workingBar.setAttribute("aria-hidden", "true");
    workingEl.append(workingHead, workingBar);
    box.appendChild(workingEl);

    const reviewEl = document.createElement("div");
    reviewEl.className = "cx-paste-fix-review";
    reviewEl.hidden = true;
    box.appendChild(reviewEl);

    const statusEl = document.createElement("p");
    statusEl.className = "cx-status";
    statusEl.setAttribute("role", "status");
    statusEl.setAttribute("aria-live", "polite");
    box.appendChild(statusEl);

    const actions = document.createElement("div");
    actions.className = "cx-confirm-actions";
    box.appendChild(actions);

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "cx-confirm-btn";
    cancelBtn.textContent = "Cancel";

    const backBtn = document.createElement("button");
    backBtn.type = "button";
    backBtn.className = "cx-confirm-btn";
    backBtn.textContent = "Back";
    backBtn.hidden = true;

    const fixBtn = document.createElement("button");
    fixBtn.type = "button";
    fixBtn.className = "cx-confirm-btn cx-confirm-btn--primary";
    fixBtn.textContent = "Fix";

    actions.append(cancelBtn, backBtn, fixBtn);
    box.appendChild(actions);

    let fixedBody = "";
    let quoteKindDeclarations: { first_line: string; kind: string }[] = [];
    let companionNotes: NonNullable<
      PasteFixCheckResult["readability_review"]
    >["companion_notes"] = [];
    let working = false;
    let workingStepTimer: number | null = null;

    function clearWorkingSteps(): void {
      if (workingStepTimer !== null) {
        window.clearInterval(workingStepTimer);
        workingStepTimer = null;
      }
    }

    function close(): void {
      if (working) return;
      clearWorkingSteps();
      document.removeEventListener("keydown", onKey);
      scrim.remove();
      pasteFixOpen = false;
    }
    function onKey(e: KeyboardEvent): void {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", onKey);
    cancelBtn.addEventListener("click", close);
    scrim.addEventListener("click", (e) => {
      if (e.target === scrim) close();
    });

    function setWorking(message: string | null): void {
      working = Boolean(message);
      if (!message) clearWorkingSteps();
      workingEl.hidden = !message;
      if (message) workingLabel.textContent = message;
      box.classList.toggle("is-working", working);
      textarea.disabled = working;
      cancelBtn.disabled = working;
      backBtn.disabled = working;
      fixBtn.disabled = working;
      scrim.setAttribute("aria-busy", working ? "true" : "false");
    }

    function startWorkingSteps(steps: string[]): void {
      clearWorkingSteps();
      const labels = steps.filter(Boolean);
      setWorking(labels[0] ?? "Working");
      let index = 0;
      workingStepTimer = window.setInterval(() => {
        if (!working || labels.length <= 1) return;
        index = Math.min(index + 1, labels.length - 1);
        workingLabel.textContent = labels[index];
      }, 3600);
    }

    function showPasteStep(): void {
      clearWorkingSteps();
      textarea.hidden = false;
      textarea.disabled = false;
      reviewEl.hidden = true;
      workingEl.hidden = true;
      backBtn.hidden = true;
      fixBtn.textContent = "Fix";
      fixBtn.disabled = false;
      cancelBtn.disabled = false;
      statusEl.textContent = "";
      textarea.focus();
    }
    backBtn.addEventListener("click", showPasteStep);

    fixBtn.addEventListener("click", async () => {
      const applying =
        fixBtn.textContent === "Apply" || fixBtn.textContent === "Apply anyway";
      if (applying) {
        startWorkingSteps([
          "Saving the fixed chapter",
          "Filing Companion drafts",
          "Refreshing Arabic audit labels",
          "Reloading the chapter",
        ]);
        statusEl.textContent = "";
        try {
          const saved = await apiFetch<{ companionNotes?: number }>(
            "/api/studio/paste-fix",
            {
              method: "PUT",
              body: {
                slug,
                chapterKey: getSelectedChapter(),
                markdown: fixedBody,
                quoteKindDeclarations,
                companionNotes,
              },
            },
          );
          clearWorkingSteps();
          workingLabel.textContent = "Saved. Reloading the chapter";
          const filed = saved.companionNotes ?? 0;
          setAiStatus(
            filed
              ? `Paste & Fix applied. ${filed} Companion draft${filed === 1 ? "" : "s"} filed. Reloading the chapter…`
              : "Paste & Fix applied. Reloading the chapter…",
          );
          document.removeEventListener("keydown", onKey);
          scrim.remove();
          pasteFixOpen = false;
          reloadPreservingChapter();
        } catch (e) {
          setWorking(null);
          statusEl.textContent = `Save failed: ${(e as Error).message}`;
        }
        return;
      }

      const pasted = textarea.value;
      if (!pasted.trim()) {
        statusEl.textContent = "Paste the chapter text first.";
        return;
      }
      startWorkingSteps([
        "Checking the pasted chapter",
        "Restoring dropped images",
        "Repairing pasted paragraph breaks",
        "Normalizing headings and citations",
        "Running Scholar continuity",
        "Reading as a first-time student",
        "Preparing Companion drafts",
        "Running fidelity gates",
      ]);
      statusEl.textContent = "";
      try {
        const result = await apiFetch<PasteFixCheckResult>(
          "/api/studio/paste-fix",
          {
            method: "POST",
            body: { slug, chapterTitle: title, pastedMarkdown: pasted },
          },
        );
        fixedBody = result.body;
        quoteKindDeclarations = result.quote_kind_declarations ?? [];
        companionNotes = result.readability_review?.companion_notes ?? [];
        renderPasteFixReview(reviewEl, result);
        setWorking(null);
        textarea.hidden = true;
        reviewEl.hidden = false;
        backBtn.hidden = false;
        backBtn.disabled = false;
        fixBtn.textContent = result.findings.length ? "Apply anyway" : "Apply";
        fixBtn.disabled = false;
        statusEl.textContent = "";
      } catch (e) {
        setWorking(null);
        statusEl.textContent = `Check failed: ${(e as Error).message}`;
        fixBtn.disabled = false;
      }
    });

    document.body.appendChild(scrim);
    textarea.focus();
  }

  return { open: openPasteFixModal };
}
