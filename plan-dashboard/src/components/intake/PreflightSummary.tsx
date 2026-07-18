/**
 * PreflightSummary — Screen 3 of the new-content intake (Phase 6, Q10).
 *
 * Shows the pre-flight estimate (projected cost/time + the caps in effect) before
 * the launch. The chapter count isn't known until Phase 0d runs, so the operator
 * gives a best-guess count and the estimate (capped per-chapter) updates live.
 * The "Launch" button is the Tier-2 spend gate — it POSTs to /api/intake/launch,
 * which commits the staged files and spawns the pipeline DETACHED. Disabled until
 * the upload roles validate and settings are chosen.
 */
import { useEffect, useState } from "react";

interface Estimate {
  chapter_count: number;
  mean_per_chapter_cost_usd: number;
  projected_cost_usd: number;
  projected_human: string;
  caps: {
    per_chapter_cost_cap_usd: number;
    book_cap_usd: number;
    book_cap_active: boolean;
  };
}

interface Props {
  slug: string | null;
  title: string | null;
  stagingToken: string | null;
  settings: Record<string, string>;
  uploadValid: boolean;
  /** Called with the launched slug once the pipeline is spawned. */
  onLaunched?: (slug: string) => void;
}

export default function PreflightSummary({
  slug,
  title,
  stagingToken,
  settings,
  uploadValid,
  onLaunched,
}: Props) {
  const [chapters, setChapters] = useState(10);
  const [est, setEst] = useState<Estimate | null>(null);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        // Caps are NOT sent — the server applies its authoritative defaults so the
        // figures the operator approves against are the real ones (content integrity).
        const params = new URLSearchParams({ chapters: String(chapters) });
        const r = await fetch(`/api/intake/preflight?${params}`);
        const json = await r.json();
        if (alive && r.ok && json.ok) setEst(json.data.estimate);
      } catch {
        /* estimate is best-effort */
      }
    })();
    return () => {
      alive = false;
    };
  }, [chapters]);

  const ready = !!slug && !!title && !!stagingToken && uploadValid;

  async function launch() {
    if (!ready) return;
    setLaunching(true);
    setError("");
    try {
      const r = await fetch("/api/intake/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          settings,
          staging_token: stagingToken,
          slug,
        }),
      });
      const json = await r.json();
      if (!r.ok || !json.ok) {
        setError(json.error ?? `Launch failed (${r.status})`);
        return;
      }
      onLaunched?.(json.data.slug);
    } catch (e) {
      setError(`Network error: ${String(e)}`);
    } finally {
      setLaunching(false);
    }
  }

  return (
    <div className="intake-card">
      <h2 className="intake-card-title">Pre-flight</h2>
      <p className="intake-hint">
        A rough estimate before you commit. Actual chapter count is set during
        planning; adjust the guess to see the range. Spend is capped per
        chapter, so it can't run away.
      </p>

      <div className="intake-field">
        <label className="intake-label" htmlFor="pf-chapters">
          Estimated chapters
        </label>
        <input
          id="pf-chapters"
          className="intake-input"
          type="number"
          min={1}
          max={200}
          value={chapters}
          onChange={(e) =>
            setChapters(Math.max(1, Number(e.target.value) || 1))
          }
        />
      </div>

      {est && (
        <dl className="intake-estimate">
          <div className="intake-estimate-row">
            <dt>Projected cost</dt>
            <dd>${est.projected_cost_usd.toFixed(2)}</dd>
          </div>
          <div className="intake-estimate-row">
            <dt>Projected time</dt>
            <dd>{est.projected_human}</dd>
          </div>
          <div className="intake-estimate-row">
            <dt>Per-chapter cap</dt>
            <dd>${est.caps.per_chapter_cost_cap_usd.toFixed(2)}</dd>
          </div>
          <div className="intake-estimate-row">
            <dt>Per-book ceiling</dt>
            <dd>
              {est.caps.book_cap_active
                ? `$${est.caps.book_cap_usd.toFixed(2)}`
                : "off"}
            </dd>
          </div>
        </dl>
      )}

      {!ready && (
        <p className="intake-hint">
          Create the folder, stage a valid set of source files (one primary),
          and choose settings to enable launch.
        </p>
      )}
      {error && (
        <p className="intake-error" role="alert">
          {error}
        </p>
      )}

      <div className="intake-actions">
        <button
          className="intake-btn intake-btn--primary"
          type="button"
          disabled={!ready || launching}
          onClick={launch}
        >
          {launching ? "Launching…" : "Launch pipeline"}
        </button>
      </div>
      <p className="intake-hint">
        Launch spawns the pipeline in the background — it keeps running if you
        close this tab.
      </p>
    </div>
  );
}
