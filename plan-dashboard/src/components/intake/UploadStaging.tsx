/**
 * UploadStaging — Screen 1 of the new-content intake (Phase 6, Q6 + Q7).
 *
 * Drag-and-drop (or click-to-pick) upload of mixed-type files into a per-session
 * staging area. Each staged file gets a ROLE; exactly one primary_source is
 * required and audio-as-primary is warned. Nothing touches the canonical _source/
 * until the final confirm — this screen only stages.
 *
 * Dependency-free + class-driven (no inline styles), matching NewContentForm. All
 * vocabulary/validation comes from the server (intake_staging.py) — the single
 * source of truth — so the UI can't drift from what the pipeline accepts.
 */
import { useCallback, useRef, useState } from "react";
import { apiFetch, ApiFetchError } from "../../lib/api-fetch";

interface StagedFile {
  id: string;
  filename: string;
  role: string;
  ext: string;
}

interface Validation {
  ok: boolean;
  errors: string[];
  warnings: string[];
}

interface Props {
  /** Notified whenever the staged set changes, so the parent can gate "Next". */
  onChange?: (state: {
    token: string | null;
    files: StagedFile[];
    valid: boolean;
  }) => void;
}

// Mirrors intake_staging.ROLES, in the same order. Labels say what the file IS
// to a reader, not the pipeline's key.
const ROLE_OPTIONS = [
  { value: "primary_source", label: "Primary source" },
  { value: "source_recording", label: "Source recording" },
  { value: "pronunciation_reference", label: "Pronunciation reference" },
  {
    value: "timestamped_transcript",
    label: "Timestamped transcript (timings for the recording)",
  },
  { value: "supplementary_text", label: "Supplementary text" },
];

const ACCEPT = ".pdf,.mp3,.m4a,.wav,.txt,.md,.docx,.json,.srt,.vtt";

export default function UploadStaging({ onChange }: Props) {
  const [token, setToken] = useState<string | null>(null);
  const [files, setFiles] = useState<StagedFile[]>([]);
  const [validation, setValidation] = useState<Validation | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  const emit = useCallback(
    (t: string | null, f: StagedFile[], v: Validation | null) => {
      onChange?.({ token: t, files: f, valid: !!v?.ok && f.length > 0 });
    },
    [onChange],
  );

  async function upload(fileList: FileList | File[]) {
    const arr = Array.from(fileList);
    if (arr.length === 0) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      if (token) form.append("token", token);
      for (const f of arr) form.append("files", f);
      // Raw fetch (not apiFetch): multipart FormData body — apiFetch is JSON-only.
      const r = await fetch("/api/intake/upload", {
        method: "POST",
        body: form,
      });
      const json = await r.json();
      if (!r.ok || !json.ok) {
        setError(json.error ?? `Upload failed (${r.status})`);
        return;
      }
      const data = json.data as {
        token: string;
        staged: StagedFile[];
        rejected: { filename: string; reason: string }[];
        validation: Validation;
      };
      const nextToken = data.token;
      const nextFiles = [...files, ...data.staged];
      setToken(nextToken);
      setFiles(nextFiles);
      setValidation(data.validation);
      if (data.rejected?.length) {
        setError(
          `Skipped: ${data.rejected.map((x) => `${x.filename} (${x.reason})`).join(", ")}`,
        );
      }
      emit(nextToken, nextFiles, data.validation);
    } catch (e) {
      setError(`Network error: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(fileId: string, role: string) {
    if (!token) return;
    let data: { validation: Validation };
    try {
      data = await apiFetch<{ validation: Validation }>("/api/intake/staging", {
        method: "POST",
        body: { token, action: "set-role", file_id: fileId, role },
      });
    } catch (e) {
      // Transport failures previously escaped this handler; only surface
      // server-reported errors, as the old !r.ok / !json.ok branch did.
      if (!(e instanceof ApiFetchError) || e.status === 0) throw e;
      setError(e.message || "Could not change role");
      return;
    }
    const next = files.map((f) => (f.id === fileId ? { ...f, role } : f));
    setFiles(next);
    setValidation(data.validation);
    emit(token, next, data.validation);
  }

  async function removeFile(fileId: string) {
    if (!token) return;
    let data: { validation: Validation };
    try {
      data = await apiFetch<{ validation: Validation }>("/api/intake/staging", {
        method: "POST",
        body: { token, action: "remove", file_id: fileId },
      });
    } catch (e) {
      if (!(e instanceof ApiFetchError) || e.status === 0) throw e;
      setError(e.message || "Could not remove file");
      return;
    }
    const next = files.filter((f) => f.id !== fileId);
    setFiles(next);
    setValidation(data.validation);
    emit(token, next, data.validation);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer?.files?.length) upload(e.dataTransfer.files);
  }

  return (
    <div className="intake-card intake-card--grow">
      <h2 className="intake-card-title">Source files</h2>
      <p className="intake-hint">
        Drop your source material — a PDF, an audio recording, a transcript, a
        pronunciation glossary. Assign each a role. Files stage here; nothing is
        committed until you confirm.
      </p>

      <div
        className={`intake-drop${dragging ? " intake-drop--active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
      >
        <p className="intake-drop-primary">
          {busy ? "Uploading…" : "Drop files here"}
        </p>
        <p className="intake-drop-secondary">
          or click to choose · PDF · audio · text
        </p>
        <input
          ref={inputRef}
          className="intake-drop-input"
          type="file"
          multiple
          accept={ACCEPT}
          onChange={(e) => {
            if (e.target.files) upload(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {error && <p className="intake-error">{error}</p>}

      {files.length > 0 && (
        <ul className="intake-filelist">
          {files.map((f) => (
            <li key={f.id} className="intake-filerow">
              <span className="intake-file-name" title={f.filename}>
                {f.filename}
              </span>
              <select
                className="intake-select intake-file-role"
                value={f.role}
                onChange={(e) => changeRole(f.id, e.target.value)}
                aria-label={`Role for ${f.filename}`}
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
              <button
                className="intake-file-remove"
                type="button"
                onClick={() => removeFile(f.id)}
                aria-label={`Remove ${f.filename}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {validation && files.length > 0 && (
        <div className="intake-validation">
          {validation.errors.map((msg) => (
            <p key={msg} className="intake-validation-error">
              {msg}
            </p>
          ))}
          {validation.warnings.map((msg) => (
            <p key={msg} className="intake-validation-warn">
              {msg}
            </p>
          ))}
          {validation.ok && validation.warnings.length === 0 && (
            <p className="intake-validation-ok">
              Roles look good — exactly one primary source.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
