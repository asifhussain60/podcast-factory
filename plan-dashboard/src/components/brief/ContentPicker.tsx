/**
 * ContentPicker — commission something new, or load a piece that already exists.
 *
 * The one primary control on the Intake landing. Existing content is grouped by
 * shelf so a list of twenty-six is scannable, and each entry says whether it is
 * published, because that is what tells you how much care an edit needs.
 */
interface Item {
  slug: string;
  title: string;
  bucket: string;
  status: string;
}

interface Props {
  items: Item[];
  /** The slug being edited, or "" for a new commission. */
  value: string;
  busy?: boolean;
  onChange: (slug: string) => void;
}

export default function ContentPicker({ items, value, busy, onChange }: Props) {
  const byBucket = new Map<string, Item[]>();
  for (const i of items) {
    const list = byBucket.get(i.bucket) ?? [];
    list.push(i);
    byBucket.set(i.bucket, list);
  }

  return (
    <div className="bf-picker">
      <label className="intake-label bf-picker-label" htmlFor="bf-picker">
        What are you working on
      </label>
      <select
        id="bf-picker"
        className="intake-select bf-picker-select"
        value={value}
        disabled={busy}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Commission something new</option>
        {[...byBucket.entries()].map(([bucket, list]) => (
          <optgroup key={bucket} label={bucket}>
            {list.map((i) => (
              <option key={i.slug} value={i.slug}>
                {i.title}
                {i.status === "published" ? " · published" : ""}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <p className="intake-hint bf-note">
        {value
          ? "Editing an existing piece. Changes are saved back to its own files; the Library picks them up at the next publish."
          : "Answer the five steps and you get a written commission and a hand-off prompt. Nothing is created until you press Generate."}
      </p>
    </div>
  );
}
