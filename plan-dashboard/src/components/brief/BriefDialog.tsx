/**
 * BriefDialog — a native <dialog>, opened and closed from React state.
 *
 * <dialog> is used rather than a hand-built overlay because it brings the focus
 * trap, the Esc handler and the top layer with it. showModal() throws if called
 * on an already-open dialog, so both calls are guarded by the element's own
 * `open` property.
 */
import { useEffect, useId, useRef } from "react";

interface Props {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  /** Extra controls beside Close. */
  actions?: React.ReactNode;
}

export default function BriefDialog({
  open,
  title,
  onClose,
  children,
  actions,
}: Props) {
  const ref = useRef<HTMLDialogElement | null>(null);
  // A modal with no accessible name announces as just "dialog"; the heading it
  // already renders is that name.
  const titleId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="bf-dialog"
      aria-labelledby={titleId}
      onClose={onClose}
    >
      <div className="bf-dialog-head">
        <h2 className="bf-dialog-title" id={titleId}>
          {title}
        </h2>
        <button type="button" className="bf-dialog-x" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="bf-dialog-body">{children}</div>
      {actions && <div className="bf-dialog-actions">{actions}</div>}
    </dialog>
  );
}
