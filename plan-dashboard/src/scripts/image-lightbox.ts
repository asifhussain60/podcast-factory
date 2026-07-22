/**
 * image-lightbox.ts — a themed, self-sizing modal for reading a visual asset.
 *
 * The Book Composer's candidate palette shows each artifact as a thumbnail with
 * a hover-to-enlarge card, and the card is a fixed ~22rem box — a dense slide
 * (a table, a ledger, small print) is physically unreadable in it, and hover
 * does not exist on touch or keyboard at all. This opens the asset over the
 * whole page instead: the image sizes ITSELF (its natural aspect, capped to the
 * viewport), the caption sits under it, and it closes on Escape, backdrop
 * click, or the X.
 *
 * Same modal contract as confirm-dialog.ts: vanilla, promise-based, focus
 * restored to the opener on close, no inline styles — classes in
 * book-composer.css (`.cx-lightbox-*`) on the --c-* theme tokens.
 */

export interface LightboxOptions {
  /** Servable image URL (raster or SVG — vectors stay sharp at any size). */
  src: string;
  /** Caption shown under the image; also the dialog's accessible name. */
  caption?: string;
}

export function imageLightbox(opts: LightboxOptions): Promise<void> {
  return new Promise((resolve) => {
    const prevFocus = document.activeElement as HTMLElement | null;

    const scrim = document.createElement("div");
    scrim.className = "cx-confirm-scrim cx-lightbox-scrim";

    const box = document.createElement("figure");
    box.className = "cx-lightbox-box";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", opts.caption || "Image preview");

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "cx-lightbox-close";
    closeBtn.setAttribute("aria-label", "Close preview");
    closeBtn.textContent = "×";

    const img = document.createElement("img");
    img.className = "cx-lightbox-img";
    img.src = opts.src;
    // Decorative for AT: the dialog's aria-label and the visible figcaption
    // already carry the caption — alt text would announce it a third time.
    img.alt = "";

    box.append(closeBtn, img);
    if (opts.caption) {
      const cap = document.createElement("figcaption");
      cap.className = "cx-lightbox-cap";
      cap.textContent = opts.caption;
      box.append(cap);
    }
    scrim.append(box);
    document.body.append(scrim);

    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      document.removeEventListener("keydown", onKey, true);
      scrim.remove();
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
      resolve();
    };

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      } else if (e.key === "Tab") {
        e.preventDefault();
        closeBtn.focus(); // trap on the sole control
      }
    };
    document.addEventListener("keydown", onKey, true);
    scrim.addEventListener("mousedown", (e) => {
      // Backdrop AND the figure's own padding close it; only the image and the
      // caption are "content". A reader done with the slide clicks anywhere.
      const t = e.target as HTMLElement;
      if (t === scrim || t === box) close();
    });
    closeBtn.addEventListener("click", close);
    closeBtn.focus();
  });
}
