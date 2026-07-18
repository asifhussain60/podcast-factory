/**
 * PreUploadTabs — tabbed pre-upload review component.
 *
 * Tab 1: Pronunciation Review — fill the listen-checklist.
 * Tab 2: Framing Fixes — apply ambiguity findings to episode framings.
 *
 * All CSS classes are defined in styles/pre-upload.css (no inline styles).
 */

import { useState, useCallback } from "react";
import { lookupTranslation } from "../lib/term-translations";

// ─── shared types (mirror lib/pre-upload.ts) ─────────────────────────────

interface ChecklistTerm {
  n: number;
  term: string;
  rendered: string;
  ok: "" | "y" | "n" | "r" | "d";
  fix: string;
}

type AmbiguityPriority = "high" | "medium" | "low";
type AmbiguityStatus = "pending" | "applied" | "skipped";

interface AmbiguityItem {
  id: string;
  priority: AmbiguityPriority;
  type: string;
  description: string;
  episodes: string[];
  section: string;
  framing_hint: string;
  status: AmbiguityStatus;
}

interface Props {
  slug: string;
  title: string;
  terms: ChecklistTerm[];
  ambiguityItems: AmbiguityItem[];
  audioPath: string | null;
}

// ─── Pronunciation tab ────────────────────────────────────────────────────

function ChecklistRow({
  term: initTerm,
  onChange,
}: {
  term: ChecklistTerm;
  onChange: (updated: ChecklistTerm) => void;
}) {
  const [row, setRow] = useState<ChecklistTerm>(initTerm);

  function update(patch: Partial<ChecklistTerm>) {
    const next = { ...row, ...patch };
    setRow(next);
    onChange(next);
  }

  const rowClass =
    row.ok === "y"
      ? "is-ok"
      : row.ok === "n"
        ? "is-fix"
        : row.ok === "r"
          ? "is-replace"
          : row.ok === "d"
            ? "is-delete"
            : "";

  return (
    <tr className={rowClass}>
      <td className="pu-n">{row.n}</td>
      <td>
        <span className="pu-term-name">{row.term}</span>
      </td>
      <td>
        <code className="pu-rendered">{row.rendered}</code>
      </td>
      <td>
        <div className="pu-radio-group">
          <label
            className={`pu-radio-btn${row.ok === "y" ? " is-ok-active" : ""}`}
          >
            <input
              type="radio"
              name={`ok-${row.n}`}
              checked={row.ok === "y"}
              onChange={() => update({ ok: "y", fix: "" })}
            />
            ✓ OK
          </label>
          <label
            className={`pu-radio-btn${row.ok === "n" ? " is-fix-active" : ""}`}
          >
            <input
              type="radio"
              name={`ok-${row.n}`}
              checked={row.ok === "n"}
              onChange={() => update({ ok: "n" })}
            />
            Fix
          </label>
          <label
            className={`pu-radio-btn${row.ok === "r" ? " is-replace-active" : ""}`}
          >
            <input
              type="radio"
              name={`ok-${row.n}`}
              checked={row.ok === "r"}
              onChange={() => {
                const suggestion = lookupTranslation(row.term)?.english ?? "";
                update({ ok: "r", fix: row.fix.trim() || suggestion });
              }}
            />
            Replace
          </label>
          <label
            className={`pu-radio-btn${row.ok === "d" ? " is-delete-active" : ""}`}
          >
            <input
              type="radio"
              name={`ok-${row.n}`}
              checked={row.ok === "d"}
              onChange={() => update({ ok: "d", fix: "" })}
            />
            Delete
          </label>
        </div>
      </td>
      <td>
        <input
          type="text"
          className="pu-fix-input"
          placeholder={
            row.ok === "n"
              ? "substitute for NotebookLM framing…"
              : row.ok === "r"
                ? "English / biblical equivalent in source…"
                : row.ok === "d"
                  ? "generic substitute — or leave blank to drop the sentence"
                  : ""
          }
          value={row.fix}
          disabled={row.ok !== "n" && row.ok !== "r" && row.ok !== "d"}
          onChange={(e) => update({ fix: e.target.value })}
        />
      </td>
    </tr>
  );
}

function PronunciationTab({
  slug,
  terms: initTerms,
  audioPath,
}: {
  slug: string;
  terms: ChecklistTerm[];
  audioPath: string | null;
}) {
  const [terms, setTerms] = useState<ChecklistTerm[]>(initTerms);
  const [saveState, setSaveState] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [saveMsg, setSaveMsg] = useState("");
  const [replaceState, setReplaceState] = useState<
    "idle" | "applying" | "done" | "error"
  >("idle");
  const [replaceMsg, setReplaceMsg] = useState("");
  const [deleteState, setDeleteState] = useState<
    "idle" | "applying" | "done" | "error"
  >("idle");
  const [deleteMsg, setDeleteMsg] = useState("");

  const handleChange = useCallback((updated: ChecklistTerm) => {
    setTerms((prev) => prev.map((t) => (t.n === updated.n ? updated : t)));
  }, []);

  const done = terms.filter(
    (t) =>
      t.ok === "y" ||
      (t.ok === "n" && t.fix.trim()) ||
      (t.ok === "r" && t.fix.trim()) ||
      t.ok === "d",
  ).length;
  const total = terms.length;
  const replaceTerms = terms.filter((t) => t.ok === "r" && t.fix.trim());
  const deleteTerms = terms.filter((t) => t.ok === "d");

  async function handleSave() {
    setSaveState("saving");
    try {
      const res = await fetch("/api/pre-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "save-checklist", slug, terms }),
      });
      const data = await res.json();
      if (data.ok) {
        setSaveState("saved");
        setSaveMsg(`Saved ${data.saved} terms to listen-checklist.md`);
      } else {
        setSaveState("error");
        setSaveMsg(data.error ?? "Save failed");
      }
    } catch (e) {
      setSaveState("error");
      setSaveMsg(String(e));
    }
    setTimeout(() => setSaveState("idle"), 4000);
  }

  async function handleApplyReplacements() {
    setReplaceState("applying");
    try {
      const res = await fetch("/api/pre-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "apply-source-replacements",
          slug,
          replacements: replaceTerms.map((t) => ({
            term: t.term,
            replacement: t.fix,
          })),
        }),
      });
      const data = await res.json();
      if (data.ok) {
        setReplaceState("done");
        setReplaceMsg(
          `${data.total_replacements} replacement${data.total_replacements !== 1 ? "s" : ""} across ${data.files_changed} chapter file${data.files_changed !== 1 ? "s" : ""}`,
        );
      } else {
        setReplaceState("error");
        setReplaceMsg(data.error ?? "Failed");
      }
    } catch (e) {
      setReplaceState("error");
      setReplaceMsg(String(e));
    }
    setTimeout(() => setReplaceState("idle"), 6000);
  }

  async function handleApplyDeletions() {
    setDeleteState("applying");
    try {
      const res = await fetch("/api/pre-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "apply-deletions-to-source",
          slug,
          deletions: deleteTerms.map((t) => ({
            term: t.term,
            substitute: t.fix,
          })),
        }),
      });
      const data = await res.json();
      if (data.ok) {
        setDeleteState("done");
        setDeleteMsg(
          `${data.total_changes} change${data.total_changes !== 1 ? "s" : ""} across ${data.files_changed} file${data.files_changed !== 1 ? "s" : ""}`,
        );
      } else {
        setDeleteState("error");
        setDeleteMsg(data.error ?? "Failed");
      }
    } catch (e) {
      setDeleteState("error");
      setDeleteMsg(String(e));
    }
    setTimeout(() => setDeleteState("idle"), 6000);
  }

  return (
    <section aria-label="Pronunciation Review">
      <div className="pu-section-head">
        <h2 className="pu-section-title">Pronunciation Review</h2>
        <p className="pu-section-note">
          Listen to the EP00 probe, then mark each term: <strong>OK</strong>{" "}
          (correct), <strong>Fix</strong> (substitute in NotebookLM framing
          only), <strong>Replace</strong> (swap with English/biblical equivalent
          in chapter source), or <strong>Delete</strong> (type a generic
          substitute, e.g. "the Fatimid scholar" — or leave blank to drop the
          whole sentence). Do <em>not</em> write hyphen-CAPS respellings.
        </p>
      </div>

      {audioPath && (
        <a
          href={audioPath}
          className="pu-audio-link"
          target="_blank"
          rel="noreferrer"
        >
          <i className="fa-solid fa-headphones" aria-hidden="true"></i>
          Open EP00 probe audio
        </a>
      )}

      <div className="pu-table-wrap">
        <table className="pu-table" aria-label="Pronunciation checklist">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Term</th>
              <th scope="col">Hosts told to say</th>
              <th scope="col">Verdict</th>
              <th scope="col">Fix / Replace</th>
            </tr>
          </thead>
          <tbody>
            {terms.map((t) => (
              <ChecklistRow key={t.n} term={t} onChange={handleChange} />
            ))}
          </tbody>
        </table>
      </div>

      <div className="pu-save-bar">
        <button
          className="pu-btn pu-btn-primary"
          disabled={saveState === "saving"}
          onClick={handleSave}
        >
          {saveState === "saving" ? "Saving…" : "Save corrections"}
        </button>
        {replaceTerms.length > 0 && (
          <button
            className="pu-btn pu-btn-replace"
            disabled={replaceState === "applying"}
            onClick={handleApplyReplacements}
          >
            {replaceState === "applying"
              ? "Applying…"
              : replaceState === "done"
                ? "✓ Applied to source"
                : `Apply ${replaceTerms.length} replacement${replaceTerms.length !== 1 ? "s" : ""} to source`}
          </button>
        )}
        {deleteTerms.length > 0 && (
          <button
            className="pu-btn pu-btn-danger"
            disabled={deleteState === "applying"}
            onClick={handleApplyDeletions}
          >
            {deleteState === "applying"
              ? "Applying…"
              : deleteState === "done"
                ? "✓ Deletions applied"
                : `Apply ${deleteTerms.length} deletion${deleteTerms.length !== 1 ? "s" : ""} to source`}
          </button>
        )}
        <span className="pu-save-status">
          {done}/{total} terms reviewed
        </span>
        {saveState === "saved" && (
          <span className="pu-save-status success">{saveMsg}</span>
        )}
        {saveState === "error" && (
          <span className="pu-save-status error">{saveMsg}</span>
        )}
        {replaceState === "done" && (
          <span className="pu-save-status success">{replaceMsg}</span>
        )}
        {replaceState === "error" && (
          <span className="pu-save-status error">{replaceMsg}</span>
        )}
        {deleteState === "done" && (
          <span className="pu-save-status success">{deleteMsg}</span>
        )}
        {deleteState === "error" && (
          <span className="pu-save-status error">{deleteMsg}</span>
        )}
      </div>
    </section>
  );
}

// ─── Ambiguity tab ────────────────────────────────────────────────────────

const PRIORITY_EMOJI: Record<AmbiguityPriority, string> = {
  high: "🔴",
  medium: "🟡",
  low: "🟢",
};

function AmbiguityCard({
  slug,
  item: initItem,
}: {
  slug: string;
  item: AmbiguityItem;
}) {
  const [item, setItem] = useState<AmbiguityItem>(initItem);
  const [clarText, setClarText] = useState(initItem.framing_hint);
  const [originalHint] = useState(initItem.framing_hint);
  const [saveResState, setSaveResState] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [saveResMsg, setSaveResMsg] = useState("");
  const [applyState, setApplyState] = useState<
    Record<string, "idle" | "applying" | "done" | "error">
  >({});
  const [applyMsg, setApplyMsg] = useState<Record<string, string>>({});

  async function handleSaveResolution() {
    setSaveResState("saving");
    try {
      const res = await fetch("/api/pre-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "save-clarification",
          slug,
          item_id: item.id,
          text: clarText,
        }),
      });
      const data = await res.json();
      if (data.ok) {
        setSaveResState("saved");
        setSaveResMsg("Saved");
      } else {
        setSaveResState("error");
        setSaveResMsg(data.error ?? "Save failed");
      }
    } catch (e) {
      setSaveResState("error");
      setSaveResMsg(String(e));
    }
    setTimeout(() => setSaveResState("idle"), 3500);
  }

  async function handleApply(episodeId: string) {
    setApplyState((s) => ({ ...s, [episodeId]: "applying" }));
    try {
      const res = await fetch("/api/pre-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "apply-fix",
          slug,
          item_id: item.id,
          episode_id: episodeId,
          section: item.section,
          fix_text: clarText,
        }),
      });
      const data = await res.json();
      if (data.ok) {
        setApplyState((s) => ({ ...s, [episodeId]: "done" }));
        setApplyMsg((m) => ({ ...m, [episodeId]: `Applied to ${episodeId}` }));
        setItem((i) => ({ ...i, status: "applied" }));
      } else {
        setApplyState((s) => ({ ...s, [episodeId]: "error" }));
        setApplyMsg((m) => ({ ...m, [episodeId]: data.error ?? "Failed" }));
      }
    } catch (e) {
      setApplyState((s) => ({ ...s, [episodeId]: "error" }));
      setApplyMsg((m) => ({ ...m, [episodeId]: String(e) }));
    }
  }

  async function handleApplyAll() {
    for (const ep of item.episodes) {
      if (applyState[ep] === "done") continue;
      await handleApply(ep);
    }
  }

  async function handleSkip() {
    await fetch("/api/pre-upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "mark-fix-status",
        slug,
        item_id: item.id,
        status: "skipped",
      }),
    });
    setItem((i) => ({ ...i, status: "skipped" }));
  }

  const cardClass = [
    "pu-amb-card",
    `priority-${item.priority}`,
    item.status !== "pending" ? `status-${item.status}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const lastApplyMsg =
    Object.values(applyMsg).filter(Boolean).slice(-1)[0] ?? "";
  const hasError = Object.values(applyState).some((s) => s === "error");
  const hasApplying = Object.values(applyState).some((s) => s === "applying");

  return (
    <div
      className={cardClass}
      aria-label={`Ambiguity item: ${item.description}`}
    >
      <div className="pu-amb-head">
        <span className={`pu-amb-priority ${item.priority}`}>
          {PRIORITY_EMOJI[item.priority]} {item.priority}
        </span>
        <div className="pu-amb-meta">
          <div className="pu-amb-desc">{item.description}</div>
          <div className="pu-amb-target">
            <strong>Target:</strong> {item.episodes.join(", ")} — {item.section}{" "}
            section
          </div>
        </div>
        {item.status !== "pending" && (
          <span className={`pu-amb-status-badge ${item.status}`}>
            {item.status === "applied" ? "✓ Applied" : "Skipped"}
          </span>
        )}
      </div>

      <div className="pu-amb-body">
        {/* ── Resolution zone ──────────────────────────────────── */}
        <div className="pu-amb-resolution">
          <div className="pu-amb-res-header">
            <span className="pu-amb-res-label">Your resolution</span>
            {saveResState === "saved" && (
              <span className="pu-amb-saved-badge">✓ Saved</span>
            )}
            {saveResState === "error" && (
              <span className="pu-amb-saved-badge is-error">{saveResMsg}</span>
            )}
          </div>
          <textarea
            className="pu-amb-textarea"
            value={clarText}
            onChange={(e) => {
              setClarText(e.target.value);
              if (saveResState === "saved") setSaveResState("idle");
            }}
            placeholder="Enter your interpretation or clarification for this gap…"
            aria-label="Your resolution for this ambiguity"
            rows={6}
          />
          <div className="pu-amb-char-count">{clarText.length} characters</div>
        </div>

        {/* ── Actions ──────────────────────────────────────────── */}
        <div className="pu-amb-actions">
          <button
            className="pu-btn pu-btn-sm"
            disabled={saveResState === "saving"}
            onClick={handleSaveResolution}
            aria-label="Save resolution to the ambiguity file"
          >
            {saveResState === "saving" ? "Saving…" : "Save resolution"}
          </button>

          <span className="pu-amb-sep" aria-hidden="true">
            |
          </span>

          <button
            className="pu-btn pu-btn-primary pu-btn-sm"
            disabled={
              hasApplying ||
              item.episodes.every((ep) => applyState[ep] === "done")
            }
            onClick={handleApplyAll}
            aria-label="Apply resolution to all episodes"
          >
            {hasApplying
              ? "Applying…"
              : item.episodes.every((ep) => applyState[ep] === "done")
                ? "✓ Applied to All"
                : "Apply to All"}
          </button>

          <div className="pu-amb-episode-btns">
            {item.episodes.map((ep) => (
              <button
                key={ep}
                className="pu-btn pu-btn-primary pu-btn-sm"
                disabled={hasApplying || applyState[ep] === "done"}
                onClick={() => handleApply(ep)}
                aria-label={`Apply resolution to ${ep}`}
              >
                {applyState[ep] === "applying"
                  ? "…"
                  : applyState[ep] === "done"
                    ? `✓ ${ep}`
                    : `Apply → ${ep}`}
              </button>
            ))}
          </div>

          <span className="pu-amb-sep" aria-hidden="true">
            |
          </span>

          <button
            className="pu-btn pu-btn-sm"
            disabled={item.status === "skipped"}
            onClick={handleSkip}
            aria-label="Skip this item"
          >
            Skip
          </button>

          {lastApplyMsg && (
            <span
              className={`pu-amb-apply-status ${hasError ? "error" : "success"}`}
            >
              {lastApplyMsg}
            </span>
          )}
        </div>

        {/* ── Original suggestion (collapsible) ────────────────── */}
        {originalHint && (
          <details className="pu-amb-hint-details">
            <summary className="pu-amb-hint-summary">
              Original system suggestion
            </summary>
            <div className="pu-amb-hint-text">{originalHint}</div>
          </details>
        )}
      </div>
    </div>
  );
}

function AmbiguityTab({
  slug,
  items,
}: {
  slug: string;
  items: AmbiguityItem[];
}) {
  const applied = items.filter((i) => i.status === "applied").length;
  const total = items.length;

  return (
    <section aria-label="Framing Fixes">
      <div className="pu-section-head">
        <h2 className="pu-section-title">Framing Fixes</h2>
        <p className="pu-section-note">
          Apply these findings to the episode framing files before upload to
          NotebookLM. Edit the text area, then click{" "}
          <strong>Apply → EP##</strong> to insert it into that episode's
          framing.
        </p>
      </div>

      <div className="pu-progress">
        <div
          className={`pu-progress-chip ${applied === total ? "done" : applied > 0 ? "in-progress" : "pending"}`}
        >
          <span className="pu-progress-num">
            {applied}/{total}
          </span>
          items applied
        </div>
      </div>

      {items.length === 0 ? (
        <div className="pu-empty">No ambiguity items found for this book.</div>
      ) : (
        <div className="pu-amb-list">
          {items.map((item) => (
            <AmbiguityCard key={item.id} slug={slug} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

// ─── Root tabbed component ────────────────────────────────────────────────

type Tab = "pronunciation" | "ambiguity";

export default function PreUploadTabs({
  slug,
  title,
  terms,
  ambiguityItems,
  audioPath,
}: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("pronunciation");

  const pronDone = terms.filter(
    (t) =>
      t.ok === "y" ||
      (t.ok === "n" && t.fix.trim()) ||
      (t.ok === "r" && t.fix.trim()) ||
      t.ok === "d",
  ).length;
  const ambApplied = ambiguityItems.filter(
    (i) => i.status === "applied",
  ).length;

  return (
    <div>
      <header className="pu-header">
        <h1 className="pu-title">{title}</h1>
        <p className="pu-lede">
          Pre-upload review — complete both tabs before generating audio in
          NotebookLM.
        </p>
      </header>

      <div className="pu-progress">
        <div
          className={`pu-progress-chip ${pronDone === terms.length && terms.length > 0 ? "done" : pronDone > 0 ? "in-progress" : "pending"}`}
        >
          <span className="pu-progress-num">{pronDone}</span>/
          <span>{terms.length}</span>&nbsp;pronunciation terms
        </div>
        <div
          className={`pu-progress-chip ${ambApplied === ambiguityItems.length && ambiguityItems.length > 0 ? "done" : ambApplied > 0 ? "in-progress" : "pending"}`}
        >
          <span className="pu-progress-num">{ambApplied}</span>/
          <span>{ambiguityItems.length}</span>&nbsp;framing fixes
        </div>
      </div>

      <div
        className="pu-tabs tabbar"
        role="tablist"
        aria-label="Review sections"
      >
        <button
          role="tab"
          aria-selected={activeTab === "pronunciation"}
          className={`tab${activeTab === "pronunciation" ? " is-active" : ""}`}
          onClick={() => setActiveTab("pronunciation")}
        >
          Pronunciation
          {pronDone === terms.length && terms.length > 0 && " ✓"}
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "ambiguity"}
          className={`tab${activeTab === "ambiguity" ? " is-active" : ""}`}
          onClick={() => setActiveTab("ambiguity")}
        >
          Framing Fixes
          {ambApplied === ambiguityItems.length &&
            ambiguityItems.length > 0 &&
            " ✓"}
        </button>
      </div>

      <div role="tabpanel">
        {activeTab === "pronunciation" && (
          <PronunciationTab slug={slug} terms={terms} audioPath={audioPath} />
        )}
        {activeTab === "ambiguity" && (
          <AmbiguityTab slug={slug} items={ambiguityItems} />
        )}
      </div>
    </div>
  );
}
