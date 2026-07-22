/**
 * BookPalette.tsx — command-palette book switcher (replaces the Studio dropdown).
 *
 * A trigger button shows the current book; clicking it (or pressing Cmd/Ctrl-K)
 * opens a cmdk palette to type-and-jump to any book's reader. Scales as books
 * grow — no more scrolling a long dropdown. cmdk is already a dependency
 * (used by CorpusExplorer). Classes in studio-pipeline.css.
 */
import { Command } from "cmdk";
import { useEffect, useState } from "react";

interface Book {
  slug: string;
  title: string;
}

export default function BookPalette({
  books,
  currentSlug,
}: {
  books: Book[];
  currentSlug?: string;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const current = books.find((b) => b.slug === currentSlug);
  const go = (href: string) => {
    window.location.href = href;
  };

  return (
    <>
      <button
        type="button"
        className="studio-bookpick-trigger"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
      >
        <span className="studio-bookpick-eyebrow">Book</span>
        <span className="studio-bookpick-current">
          {current?.title ?? "Pick a book"}
        </span>
        <kbd className="studio-bookpick-kbd">⌘K</kbd>
      </button>

      <Command.Dialog
        open={open}
        onOpenChange={setOpen}
        label="Jump to a book"
        className="book-palette"
      >
        <Command.Input
          placeholder="Search books…"
          className="book-palette-input"
        />
        <Command.List className="book-palette-list">
          <Command.Empty className="book-palette-empty">
            No books found.
          </Command.Empty>
          {books.map((b) => (
            <Command.Item
              key={b.slug}
              value={`${b.title} ${b.slug}`}
              onSelect={() => go(`/studio/${b.slug}`)}
              className="book-palette-item"
            >
              <i className="fa-solid fa-book" aria-hidden="true"></i>
              <span className="book-palette-item-title">{b.title}</span>
              {b.slug === currentSlug && (
                <span className="book-palette-tag">current</span>
              )}
            </Command.Item>
          ))}
          <Command.Item
            value="new content create book"
            onSelect={() => go("/studio/new")}
            className="book-palette-item book-palette-new"
          >
            <i className="fa-solid fa-plus" aria-hidden="true"></i>
            <span className="book-palette-item-title">New content</span>
          </Command.Item>
        </Command.List>
      </Command.Dialog>
    </>
  );
}
