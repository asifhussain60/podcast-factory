/**
 * ChapterSources — drop or paste screenshots of a contents page, and load back
 * the chapter list Claude Code works out from them.
 *
 * PASTE IS THE POINT. A screenshot goes to the clipboard, and making someone
 * save it to disk before they can hand it over is the exact friction this
 * removes. The paste listener is on the window rather than on the drop zone: a
 * pasted image has no focused field to land in, and requiring a click first is
 * the same friction wearing a different hat. It is armed only while this step
 * is on screen, so it cannot swallow a paste meant for the notes box.
 *
 * IT CALLS NO MODEL. The images are saved beside the commission and Claude Code
 * reads them there, with the transcript open beside them — because the contents
 * page and the recordings disagree, and only the second says which chapters are
 * actually taught. Handing the pictures to a model here would answer the
 * cheaper question and present it as the answer to the real one.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiFetchError } from "../../lib/api-fetch";

interface Finding {
  title: string;
  covered?: boolean;
}

interface State {
  images: string[];
  found: { chapters: Finding[]; note?: string } | null;
  dir: string;
}

interface Props {
  /** The commission's folder name. Nothing can be saved before there is one. */
  slug: string;
  /** Hands back the chapter list to write into the "The chapters" box. */
  onChapters: (titles: string[]) => void;
}

export default function ChapterSources({ slug, onChapters }: Props) {
  const [state, setState] = useState<State | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const load = useCallback(async () => {
    if (!slug) return;
    try {
      const d = await apiFetch<State>("/api/brief/chapter-sources", {
        query: { slug },
      });
      setState(d);
    } catch {
      /* nothing saved yet is the normal case, not an error worth showing */
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const upload = useCallback(
    async (files: File[]) => {
      const images = files.filter((f) => f.type.startsWith("image/"));
      if (!images.length || !slug) return;
      setBusy(true);
      setError("");
      try {
        const form = new FormData();
        form.append("slug", slug);
        for (const f of images) form.append("images", f);
        // Raw fetch, not apiFetch: multipart body, and apiFetch is JSON-only.
        const r = await fetch("/api/brief/chapter-sources", {
          method: "POST",
          body: form,
        });
        const json = await r.json();
        if (!r.ok || !json.ok) {
          setError(json.error ?? `Could not save (${r.status})`);
          return;
        }
        const data = json.data as State & {
          rejected?: { filename: string; reason: string }[];
        };
        setState((prev) => ({
          images: data.images,
          found: prev?.found ?? null,
          dir: data.dir,
        }));
        if (data.rejected?.length) {
          setError(
            `Skipped: ${data.rejected
              .map((x) => `${x.filename} (${x.reason})`)
              .join(", ")}`,
          );
        }
      } catch (e) {
        setError(`Network error: ${String(e)}`);
      } finally {
        setBusy(false);
      }
    },
    [slug],
  );

  // Window-level, and only while this step is mounted — see the note above.
  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      const files = Array.from(e.clipboardData?.files ?? []);
      if (!files.some((f) => f.type.startsWith("image/"))) return;
      e.preventDefault();
      upload(files);
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [upload]);

  async function remove(name: string) {
    try {
      const d = await apiFetch<{ images: string[] }>(
        "/api/brief/chapter-sources",
        { method: "DELETE", query: { slug, name } },
      );
      setState((s) => (s ? { ...s, images: d.images } : s));
    } catch (e) {
      if (!(e instanceof ApiFetchError) || e.status === 0) throw e;
      setError(e.message || "Could not remove that image");
    }
  }

  const prompt =
    `In ${state?.dir ?? ""} there are screenshots of this book's contents ` +
    `page. Read them, read the transcript staged for "${slug}", and work out ` +
    `the chapters: every chapter the screenshots list, in order, each marked ` +
    `whether the transcript actually reaches it. Write the result to ` +
    `chapters.json in that same folder as ` +
    `{"chapters":[{"title":"…","covered":true}],"note":"…"} and tell me what ` +
    `you found. Do not rename a chapter the contents page already names.`;

  async function copyPrompt() {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not reach the clipboard — select the text and copy it.");
    }
  }

  if (!slug) return null;

  const images = state?.images ?? [];
  const found = state?.found ?? null;
  const covered = found?.chapters.filter((c) => c.covered !== false) ?? [];
  const uncovered = found?.chapters.filter((c) => c.covered === false) ?? [];

  return (
    <section className="bf-shots" aria-labelledby="bf-shots-title">
      <h3 className="bf-shots-title" id="bf-shots-title">
        Or hand over the contents page
        <span className="bf-shots-note">
          Drop or paste screenshots — Claude Code reads them with the transcript
          and works the chapters out.
        </span>
      </h3>

      <div
        className={`intake-drop${dragging ? " intake-drop--active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(Array.from(e.dataTransfer?.files ?? []));
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
      >
        <p className="intake-drop-primary">
          {busy ? "Saving…" : "Drop screenshots here, or press ⌘V"}
        </p>
        <p className="intake-drop-secondary">
          or click to choose · several pages is normal
        </p>
        <input
          ref={inputRef}
          className="intake-drop-input"
          type="file"
          multiple
          accept="image/*"
          onChange={(e) => {
            if (e.target.files) upload(Array.from(e.target.files));
            e.target.value = "";
          }}
        />
      </div>

      {error && <p className="intake-error">{error}</p>}

      {images.length > 0 && (
        <>
          <ul className="bf-shots-list">
            {images.map((name) => (
              <li key={name} className="bf-shot">
                <img
                  className="bf-shot-img"
                  src={`/api/brief/chapter-source?slug=${encodeURIComponent(slug)}&name=${encodeURIComponent(name)}`}
                  alt={`Contents page ${name}`}
                  loading="lazy"
                />
                <button
                  type="button"
                  className="bf-shot-remove"
                  onClick={() => remove(name)}
                >
                  Remove <span className="bf-shot-name">{name}</span>
                </button>
              </li>
            ))}
          </ul>

          <div className="bf-shots-handoff">
            <p className="intake-hint">
              {images.length} {images.length === 1 ? "page" : "pages"} saved
              with this commission. Paste this into Claude Code, then come back
              and press Load.
            </p>
            <div className="bf-shots-actions">
              <button
                type="button"
                className="intake-btn intake-btn--ghost"
                onClick={copyPrompt}
              >
                {copied ? "Copied" : "Copy the prompt for Claude Code"}
              </button>
              <button
                type="button"
                className="intake-btn intake-btn--ghost"
                onClick={load}
              >
                Check for a result
              </button>
            </div>
          </div>
        </>
      )}

      {found && (
        <div className="bf-shots-found" role="status">
          <p className="intake-hint">
            Claude Code worked out <strong>{found.chapters.length}</strong>{" "}
            {found.chapters.length === 1 ? "chapter" : "chapters"}
            {uncovered.length > 0 && (
              <>
                {" "}
                — <strong>{covered.length}</strong> reached by the recordings,{" "}
                {uncovered.length} not:{" "}
                <span className="bf-shots-uncovered">
                  {uncovered.map((c) => c.title).join(", ")}
                </span>
              </>
            )}
            .
          </p>
          {found.note && <p className="intake-hint">{found.note}</p>}
          {/* Asif, 2026-08-31: enabled only once screenshots are here. A result
              file outlives the images it was read from — delete the pages and
              chapters.json remains — so the button was offering to load a list
              from evidence that is no longer on screen, which reads as the form
              having invented it. */}
          <button
            type="button"
            className="intake-btn intake-btn--primary"
            disabled={images.length === 0}
            onClick={() => onChapters(covered.map((c) => c.title))}
          >
            Load {covered.length}{" "}
            {covered.length === 1 ? "chapter" : "chapters"} into the box above
          </button>
          {images.length === 0 && (
            <p className="intake-hint">
              This was worked out from screenshots that are no longer here. Drop
              the contents page again to load it.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
