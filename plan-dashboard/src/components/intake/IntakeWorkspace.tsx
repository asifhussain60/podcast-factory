import { useState } from 'react';
import NewContentForm from './NewContentForm';
import EditorialDefaults from './EditorialDefaults';
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

  return (
    <div className="intake-shell">
      <NewContentForm onCreated={setCreated} onCleared={() => setCreated(null)} />
      <EditorialDefaults slug={created?.slug ?? null} cardDefs={cardDefs} />
    </div>
  );
}