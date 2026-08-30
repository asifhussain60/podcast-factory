import { useEffect, useState } from "react";
import NewContentForm from "./NewContentForm";
import EditorialDefaults from "./EditorialDefaults";
import UploadStaging from "./UploadStaging";
import SmartForm from "./SmartForm";
import PreflightSummary from "./PreflightSummary";
import Cockpit from "./Cockpit";
import type { CardDef } from "../../lib/reader/editorial";
import { apiFetch } from "../../lib/api-fetch";

interface CreateResult {
  slug: string;
  category: string;
  title: string;
  path: string;
}

interface Props {
  cardDefs: CardDef[];
}

export default function IntakeWorkspace({ cardDefs }: Props) {
  const [created, setCreated] = useState<CreateResult | null>(null);
  // /studio/new?brief=<slug> arrives from the Intake wizard once its commission
  // has been reviewed. Loaded before the form mounts so the inputs start filled
  // rather than filling in under the cursor; without the parameter this whole
  // block is inert and the page behaves exactly as it always has.
  const [brief, setBrief] = useState<Record<string, string> | null>(null);
  // Read at mount rather than in the effect: the URL is already known when the
  // component first renders, so deriving these from it is initial state, not a
  // state update. Setting them inside the effect instead would render once with
  // the wrong answer and immediately re-render with the right one.
  const [briefSlug] = useState<string | null>(() =>
    new URLSearchParams(window.location.search).get("brief"),
  );
  const [briefState, setBriefState] = useState<
    "none" | "loading" | "ready" | "failed"
  >(briefSlug ? "loading" : "none");

  const [stagingToken, setStagingToken] = useState<string | null>(null);
  const [uploadValid, setUploadValid] = useState(false);
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [launchedSlug, setLaunchedSlug] = useState<string | null>(null);

  useEffect(() => {
    if (!briefSlug) return;
    let alive = true;
    apiFetch<{ values: Record<string, string> }>(
      `/api/brief/${encodeURIComponent(briefSlug)}`,
    )
      .then((data) => {
        if (!alive) return;
        setBrief(data.values ?? {});
        setBriefState("ready");
      })
      .catch(() => alive && setBriefState("failed"));
    return () => {
      alive = false;
    };
  }, [briefSlug]);

  // Once the pipeline is launched, the run is read-only — show only the cockpit.
  if (launchedSlug) {
    return (
      <div className="intake-shell intake-shell--single">
        <Cockpit slug={launchedSlug} />
      </div>
    );
  }

  // Hold the form back until the brief has resolved, so it never mounts with
  // empty defaults and then swaps them out from under a half-typed answer.
  if (briefState === "loading") {
    return (
      <div className="intake-shell intake-shell--single">
        <div className="intake-card">
          <p className="intake-hint" role="status">
            Loading the commission for {briefSlug}…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="intake-shell">
      <div className="intake-column">
        {briefState === "ready" && (
          <p className="intake-hint" role="status">
            Pre-filled from the commission for <strong>{briefSlug}</strong>.
            Change anything before launching.
          </p>
        )}
        {briefState === "failed" && (
          <p className="intake-error" role="alert">
            No commission found for {briefSlug} — the form below is blank.
          </p>
        )}
        <NewContentForm
          initial={
            brief
              ? {
                  slug: brief.slug,
                  category: brief.category,
                  title: brief.title,
                }
              : undefined
          }
          onCreated={setCreated}
          onCleared={() => setCreated(null)}
        />
        <UploadStaging
          onChange={({ token, valid }) => {
            setStagingToken(token);
            setUploadValid(valid);
          }}
        />
        <EditorialDefaults slug={created?.slug ?? null} cardDefs={cardDefs} />
      </div>
      <div className="intake-column">
        <SmartForm initial={brief ?? undefined} onChange={setSettings} />
        <PreflightSummary
          slug={created?.slug ?? null}
          title={created?.title ?? null}
          stagingToken={stagingToken}
          settings={settings}
          uploadValid={uploadValid}
          onLaunched={setLaunchedSlug}
        />
      </div>
    </div>
  );
}
