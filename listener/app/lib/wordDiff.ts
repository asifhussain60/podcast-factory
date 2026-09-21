/**
 * A word-level diff, for showing a moderator (and the admin deciding) exactly what a
 * correction would change. Pure and dependency-free so it runs on the server and in the
 * browser alike.
 *
 * Returns segments in reading order. Whitespace is kept as its own tokens, so joining the
 * `same` and `del` segments reproduces the original and joining `same` and `ins` reproduces
 * the proposal — which is what makes it safe to render straight from.
 */
export interface DiffPart {
  kind: "same" | "del" | "ins";
  text: string;
}

export function wordDiff(before: string, after: string): DiffPart[] {
  const a = before.split(/(\s+)/).filter(Boolean);
  const b = after.split(/(\s+)/).filter(Boolean);
  const n = a.length;
  const m = b.length;

  // Longest-common-subsequence table, filled from the end so the walk below goes forward.
  const table: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0),
  );
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      table[i]![j] =
        a[i] === b[j]
          ? table[i + 1]![j + 1]! + 1
          : Math.max(table[i + 1]![j]!, table[i]![j + 1]!);

  const parts: DiffPart[] = [];
  const push = (kind: DiffPart["kind"], text: string) => {
    const last = parts[parts.length - 1];
    if (last?.kind === kind) last.text += text;
    else parts.push({ kind, text });
  };

  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      push("same", a[i]!);
      i++;
      j++;
    } else if (table[i + 1]![j]! >= table[i]![j + 1]!) push("del", a[i++]!);
    else push("ins", b[j++]!);
  }
  while (i < n) push("del", a[i++]!);
  while (j < m) push("ins", b[j++]!);
  return parts;
}
