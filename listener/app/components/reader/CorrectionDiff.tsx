import { wordDiff } from "~/lib/wordDiff";

/** What a correction would change, in reading order: struck-through out, highlighted in. */
export function CorrectionDiff({
  before,
  after,
}: {
  before: string;
  after: string;
}) {
  return (
    <>
      {wordDiff(before, after).map((part, i) =>
        part.kind === "del" ? (
          <del key={i}>{part.text}</del>
        ) : part.kind === "ins" ? (
          <ins key={i}>{part.text}</ins>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  );
}
