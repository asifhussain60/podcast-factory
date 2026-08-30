import { useEffect, useMemo, useRef, useState } from "react";

/**
 * ContentPicker — commission something new, or load a piece that already exists.
 *
 * The one primary control on the Intake landing. Existing content is grouped by
 * shelf so a list of twenty-six is scannable, and each entry says whether it is
 * published, because that is what tells you how much care an edit needs.
 *
 * REBUILT 2026-08-30 as a filter-as-you-type combobox, from Asif's screenshot: a
 * native <select> lists every one of twenty-six items whether or not they match
 * anything he's looking for, and a native dropdown cannot be given a search box —
 * that control simply has no such feature. Not the <input list> datalist combo
 * BriefField already uses elsewhere: a datalist inserts the OPTION VALUE into the
 * input on pick, and the value here is a slug — selecting "Al-Anwaar al-Lateefah"
 * would leave the box reading "al-anwaar-al-lateefah-vol-02". This keeps its own
 * committed slug in state and only ever shows the human title.
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

const NEW_LABEL = "Commission something new";

export default function ContentPicker({ items, value, busy, onChange }: Props) {
  const selected = items.find((i) => i.slug === value) ?? null;

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // The box shows the committed selection until you start typing over it. Typing
  // is the only thing that opens the list — arriving already filtered to "Al-A"
  // because the field happens to hold last time's title would hide everything
  // else the moment you focus in, which defeats the point of a filter.
  const displayValue = open ? query : (selected?.title ?? (value ? value : ""));

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pool = q
      ? items.filter((i) => i.title.toLowerCase().includes(q))
      : items;
    const byBucket = new Map<string, Item[]>();
    for (const i of pool) {
      const list = byBucket.get(i.bucket) ?? [];
      list.push(i);
      byBucket.set(i.bucket, list);
    }
    return [...byBucket.entries()];
  }, [items, query]);

  const flatMatches = useMemo(
    () => filtered.flatMap(([, list]) => list),
    [filtered],
  );
  // "Commission something new" is a real row, filtered by the same query, so
  // typing "new" finds it exactly the way typing a title finds a book.
  const showNewRow = NEW_LABEL.toLowerCase().includes(
    query.trim().toLowerCase(),
  );
  const rowCount = flatMatches.length + (showNewRow ? 1 : 0);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, open]);

  useEffect(() => {
    if (!open) return;
    function onDocPointerDown(e: PointerEvent) {
      if (!rootRef.current?.contains(e.target as Node)) close();
    }
    document.addEventListener("pointerdown", onDocPointerDown);
    return () => document.removeEventListener("pointerdown", onDocPointerDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function openList() {
    setQuery("");
    setOpen(true);
  }

  function close() {
    setOpen(false);
    setQuery("");
  }

  function pick(slug: string) {
    onChange(slug);
    close();
    inputRef.current?.blur();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "Enter") {
        e.preventDefault();
        openList();
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      inputRef.current?.blur();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, rowCount - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (rowCount === 0) return;
      if (showNewRow && activeIndex === 0) pick("");
      else pick(flatMatches[activeIndex - (showNewRow ? 1 : 0)].slug);
    }
  }

  let rowIndex = -1;

  return (
    <div className="bf-picker" ref={rootRef}>
      <label className="intake-label bf-picker-label" htmlFor="bf-picker">
        What are you working on
      </label>
      <div className="bf-combo">
        <input
          ref={inputRef}
          id="bf-picker"
          type="text"
          className="intake-input bf-picker-input"
          role="combobox"
          aria-expanded={open}
          aria-controls="bf-picker-list"
          aria-autocomplete="list"
          autoComplete="off"
          placeholder={NEW_LABEL}
          value={displayValue}
          disabled={busy}
          onFocus={openList}
          onChange={(e) => {
            if (!open) setOpen(true);
            setQuery(e.target.value);
          }}
          onKeyDown={onKeyDown}
        />
        {open && (
          <ul id="bf-picker-list" role="listbox" className="bf-combo-list">
            {rowCount === 0 && (
              <li className="bf-combo-empty">No match for "{query}"</li>
            )}
            {showNewRow &&
              (() => {
                rowIndex += 1;
                const idx = rowIndex;
                return (
                  <li
                    key="__new__"
                    role="option"
                    aria-selected={value === ""}
                    className={
                      "bf-combo-option bf-combo-option--new" +
                      (idx === activeIndex ? " is-active" : "")
                    }
                    onPointerDown={(e) => e.preventDefault()}
                    onClick={() => pick("")}
                  >
                    {NEW_LABEL}
                  </li>
                );
              })()}
            {filtered.map(([bucket, list]) => (
              <li key={bucket} className="bf-combo-group" role="presentation">
                <span className="bf-combo-group-label">{bucket}</span>
                <ul role="presentation">
                  {list.map((i) => {
                    rowIndex += 1;
                    const idx = rowIndex;
                    return (
                      <li
                        key={i.slug}
                        role="option"
                        aria-selected={i.slug === value}
                        className={
                          "bf-combo-option" +
                          (idx === activeIndex ? " is-active" : "")
                        }
                        onPointerDown={(e) => e.preventDefault()}
                        onClick={() => pick(i.slug)}
                      >
                        {i.title}
                        {i.status === "published" && (
                          <span className="bf-combo-published">published</span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="intake-hint bf-note">
        {value
          ? "Editing an existing piece. Changes are saved back to its own files; the Library picks them up at the next publish."
          : "Answer the five steps and you get a written commission and a hand-off prompt. Nothing is created until you press Generate."}
      </p>
    </div>
  );
}
