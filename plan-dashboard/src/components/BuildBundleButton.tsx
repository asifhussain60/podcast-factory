/**
 * BuildBundleButton — generates the NotebookLM pronunciation-probe bundle and
 * displays both output files (source + framing) in side-by-side preview panels
 * with one-click copy buttons.
 *
 * No inline styles — class-driven via pronunciation.css (.bundle-*).
 */
import { useState } from "react";

type Format = "deep-dive" | "debate";
type BundleLength = "long" | "short";
type Status = "idle" | "loading" | "ready" | "error";

interface Props {
  slug: string;
}

interface BundleData {
  source: string;
  framing: string;
}

export default function BuildBundleButton({ slug }: Props) {
  const [format, setFormat] = useState<Format>("deep-dive");
  const [length, setLength] = useState<BundleLength>("long");
  const [status, setStatus] = useState<Status>("idle");
  const [bundle, setBundle] = useState<BundleData | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<"source" | "framing" | null>(null);

  async function generate() {
    setStatus("loading");
    setError("");
    setBundle(null);
    try {
      const res = await fetch("/api/pronunciation/build-bundle", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ slug, format, length }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || "build failed");
      setBundle(json.data);
      setStatus("ready");
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  }

  async function copy(text: string, which: "source" | "framing") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(which);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      /* clipboard blocked — do nothing */
    }
  }

  return (
    <div className="bundle-wrap">
      <div className="bundle-controls">
        <div className="bundle-seg" role="group" aria-label="NotebookLM format">
          <button
            className={`bundle-segbtn${format === "deep-dive" ? " is-on" : ""}`}
            onClick={() => setFormat("deep-dive")}
          >
            Deep dive
          </button>
          <button
            className={`bundle-segbtn${format === "debate" ? " is-on" : ""}`}
            onClick={() => setFormat("debate")}
          >
            Debate
          </button>
        </div>

        <div className="bundle-seg" role="group" aria-label="NotebookLM length">
          <button
            className={`bundle-segbtn${length === "long" ? " is-on" : ""}`}
            onClick={() => setLength("long")}
          >
            Long
          </button>
          <button
            className={`bundle-segbtn${length === "short" ? " is-on" : ""}`}
            onClick={() => setLength("short")}
          >
            Short
          </button>
        </div>

        <button
          className="bundle-gen-btn"
          onClick={generate}
          disabled={status === "loading"}
          aria-live="polite"
        >
          {status === "loading" ? (
            <>
              <span className="bundle-spinner" aria-hidden="true" />
              Generating…
            </>
          ) : (
            "Generate source + framing"
          )}
        </button>
      </div>

      {status === "error" && (
        <p className="bundle-error" role="alert">
          {error}
        </p>
      )}

      {status === "ready" && bundle && (
        <div className="bundle-output">
          <p className="bundle-nlm-note">
            In NotebookLM → Audio Overview → Customize → format:{" "}
            <strong>{format === "deep-dive" ? "Deep dive" : "Debate"}</strong> ·
            length: <strong>{length === "long" ? "Long" : "Short"}</strong>
          </p>

          <div className="bundle-panels">
            <div className="bundle-panel">
              <div className="bundle-panel-head">
                <span className="bundle-panel-label">
                  Source — upload to NotebookLM
                </span>
                <button
                  className={`bundle-copy${copied === "source" ? " is-copied" : ""}`}
                  onClick={() => copy(bundle.source, "source")}
                >
                  {copied === "source" ? "✓ Copied" : "Copy"}
                </button>
              </div>
              <pre className="bundle-pre">{bundle.source}</pre>
            </div>

            <div className="bundle-panel">
              <div className="bundle-panel-head">
                <span className="bundle-panel-label">
                  Framing — paste into Customize
                </span>
                <button
                  className={`bundle-copy${copied === "framing" ? " is-copied" : ""}`}
                  onClick={() => copy(bundle.framing, "framing")}
                >
                  {copied === "framing" ? "✓ Copied" : "Copy"}
                </button>
              </div>
              <pre className="bundle-pre">{bundle.framing}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
