import type { Correction } from "~/lib/corrections";
import { CorrectionCard } from "./CorrectionCard";
import type { useCorrections } from "./useCorrections";

type Api = ReturnType<typeof useCorrections>;

/**
 * One correction with every action wired to the corrections route.
 *
 * Shared by the reader's panel and the book page's Corrections tab, so the two cannot drift: the
 * buttons a card offers come from the `authority` the SERVER computed for this viewer, and the
 * actions it fires are the same intents either way. Wiring them twice was how a second front door
 * would have grown a rule the first one did not have.
 */
export function CorrectionRow({
  correction: c,
  api,
  bookTitle,
  onEdit,
  onUseSuggestion,
  flashing,
}: {
  correction: Correction;
  api: Pick<Api, "busy" | "send" | "history">;
  bookTitle: string;
  onEdit: (c: Correction) => void;
  onUseSuggestion: (c: Correction, text: string) => void;
  flashing?: boolean;
}) {
  const { busy, send, history } = api;
  const decide = (intent: string, note?: string) =>
    void send({
      intent,
      id: c.id,
      expectedUpdatedAt: c.updatedAt,
      ...(note === undefined ? {} : { note }),
    });

  return (
    <CorrectionCard
      correction={c}
      busy={busy}
      bookTitle={bookTitle}
      loadHistory={history}
      flashing={flashing}
      onEdit={onEdit}
      onUseSuggestion={onUseSuggestion}
      onConfirm={() => decide("confirm")}
      onAccept={() => decide("accept")}
      onDismiss={(x, note) =>
        decide(
          x.status === "suggested" ? "dismiss-suggestion" : "dismiss",
          note,
        )
      }
      onRemove={() => void send({ intent: "remove", id: c.id })}
      onComment={(x, body) => void send({ intent: "comment", id: x.id, body })}
      onUncomment={(commentId) =>
        void send({ intent: "uncomment", id: commentId })
      }
    />
  );
}
