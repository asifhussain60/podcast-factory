import { useState } from 'react';
import NewContentForm from './NewContentForm';
import EditorialDefaults from './EditorialDefaults';
import UploadStaging from './UploadStaging';
import SmartForm from './SmartForm';
import PreflightSummary from './PreflightSummary';
import Cockpit from './Cockpit';
import type { CardDef } from '../../lib/reader/editorial';

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
  const [stagingToken, setStagingToken] = useState<string | null>(null);
  const [uploadValid, setUploadValid] = useState(false);
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [launchedSlug, setLaunchedSlug] = useState<string | null>(null);

  // Once the pipeline is launched, the run is read-only — show only the cockpit.
  if (launchedSlug) {
    return (
      <div className="intake-shell intake-shell--single">
        <Cockpit slug={launchedSlug} />
      </div>
    );
  }

  return (
    <div className="intake-shell">
      <div className="intake-column">
        <NewContentForm onCreated={setCreated} onCleared={() => setCreated(null)} />
        <UploadStaging
          onChange={({ token, valid }) => { setStagingToken(token); setUploadValid(valid); }}
        />
      </div>
      <div className="intake-column">
        <SmartForm onChange={setSettings} />
        <PreflightSummary
          slug={created?.slug ?? null}
          title={created?.title ?? null}
          stagingToken={stagingToken}
          settings={settings}
          uploadValid={uploadValid}
          onLaunched={setLaunchedSlug}
        />
        <EditorialDefaults slug={created?.slug ?? null} cardDefs={cardDefs} />
      </div>
    </div>
  );
}
