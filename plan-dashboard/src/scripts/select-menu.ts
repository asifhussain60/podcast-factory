/**
 * select-menu.ts — replace a native <select>'s drop-down with one we can style.
 *
 * A native <select> paints its open list through the operating system. No
 * stylesheet reaches inside it, so on this site the closed control matched the
 * editorial design while the list dropping out of it was a grey OS panel in a
 * different typeface — the mismatch that prompted this component.
 *
 * THE NATIVE ELEMENT STAYS. It is hidden visually but remains in the DOM as the
 * single source of truth: `.value`, `.disabled`, `change` events and form
 * association all behave exactly as before. Callers already reading the select
 * (the Book Composer has ten such usages) need no change at all, and if this
 * script never runs the page degrades to a working native picker.
 *
 * Placement is decided per-open from the space actually available above and
 * below the control, and the list's height is capped to that space, so a long
 * chapter list neither sprawls off-screen nor opens into a direction it does not
 * fit. See `place()`.
 *
 * SCOPE: flat, always-enabled options only. `<option disabled>` renders as an
 * ordinary selectable row and `<optgroup>` is ignored — neither occurs in the
 * pickers this serves. Add support before pointing it at a grouped select.
 *
 * Styles: styles/select-menu.css. Keyboard contract follows the ARIA combobox
 * pattern: Enter/Space/Arrow to open, Up/Down/Home/End to move, type-ahead to
 * jump, Enter to choose, Escape to dismiss, Tab to leave.
 */

/** Space a list needs before it is worth opening on a side at all. */
const MIN_SIDE_SPACE = 140;
/** Breathing room left between the list and the viewport edge. */
const VIEWPORT_MARGIN = 12;
/** How long a type-ahead buffer survives between keystrokes. */
const TYPEAHEAD_MS = 700;
/** The list's tallest permitted height, mirroring the 22rem ceiling in
 *  select-menu.css. Kept here too so `place()` can decide which side to open on
 *  by the height the list will ACTUALLY reach rather than its raw content
 *  height. Change both together. */
const CEILING_PX = 352;

export interface SelectMenu {
  /** Re-read the native select — call after its options or value change. */
  sync: () => void;
  destroy: () => void;
}

/**
 * Enhance one `<select>`. Returns null if the element is missing or already
 * enhanced, so callers can invoke it unconditionally.
 */
export function enhanceSelect(select: HTMLSelectElement | null): SelectMenu | null {
  if (!select || select.dataset.smEnhanced === "true") return null;
  // Bind once so the closures below keep the non-null narrowing.
  const el: HTMLSelectElement = select;
  el.dataset.smEnhanced = "true";

  const root = document.createElement("div");
  root.className = "sm-root";
  root.dataset.placement = "down";

  const button = document.createElement("button");
  button.type = "button";
  button.className = "sm-button";
  button.setAttribute("role", "combobox");
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-haspopup", "listbox");

  const label = document.createElement("span");
  label.className = "sm-label";
  const caret = document.createElement("span");
  caret.className = "sm-caret";
  caret.setAttribute("aria-hidden", "true");
  button.append(label, caret);

  const list = document.createElement("ul");
  list.className = "sm-list";
  list.setAttribute("role", "listbox");
  list.hidden = true;
  const listId = `sm-list-${el.id || Math.random().toString(36).slice(2, 8)}`;
  list.id = listId;
  button.setAttribute("aria-controls", listId);

  // Carry the native label across so the new control is still named.
  const labelled = el.id
    ? document.querySelector<HTMLLabelElement>(
        `label[for="${typeof CSS !== "undefined" && CSS.escape ? CSS.escape(el.id) : el.id}"]`,
      )
    : null;
  const onLabelClick = (e: MouseEvent): void => {
    // The label still points `for` at the native select, which is now clipped
    // and aria-hidden — clicking it would drop focus onto a 1x1 invisible
    // element and the next Tab would resume from somewhere unseeable.
    e.preventDefault();
    button.focus();
  };
  if (labelled) {
    if (!labelled.id) labelled.id = `${listId}-label`;
    button.setAttribute("aria-labelledby", `${labelled.id} ${listId}-value`);
    label.id = `${listId}-value`;
    list.setAttribute("aria-labelledby", labelled.id);
    labelled.addEventListener("click", onLabelClick);
  }

  el.classList.add("sm-native");
  el.tabIndex = -1;
  el.setAttribute("aria-hidden", "true");
  el.parentNode?.insertBefore(root, select);
  root.append(button, list, select);

  let options: HTMLLIElement[] = [];
  let activeIndex = -1;
  let typeahead = "";
  let typeaheadAt = 0;

  const isOpen = (): boolean => !list.hidden;

  /** Rebuild the rendered list from the native element. */
  function sync(): void {
    list.textContent = "";
    options = Array.from(el.options).map((opt, i) => {
      const li = document.createElement("li");
      li.className = "sm-option";
      li.setAttribute("role", "option");
      li.id = `${listId}-opt-${i}`;
      li.dataset.value = opt.value;
      li.setAttribute("aria-selected", String(opt.selected));

      const tick = document.createElement("span");
      tick.className = "sm-tick";
      tick.setAttribute("aria-hidden", "true");
      tick.textContent = "✓";

      // An option may carry its own number (`data-ordinal`). Render it in its
      // own element so it can sit in a fixed-width column and read as a marker
      // rather than as part of the title. The <option> text still contains it,
      // so the native fallback shows the number too.
      li.append(tick);
      const ordinal = opt.dataset.ordinal ?? "";
      const text = document.createElement("span");
      text.className = "sm-option-label";
      const bare = (opt.textContent ?? "").trim();
      if (ordinal) {
        const num = document.createElement("span");
        num.className = "sm-ordinal";
        num.textContent = ordinal;
        li.append(num);
        text.textContent = bare.replace(new RegExp(`^${ordinal}\\.\\s*`), "");
      } else {
        text.textContent = bare;
      }

      // Lower-cased once here so type-ahead compares label to label.
      li.dataset.label = (opt.textContent ?? "").trim().toLowerCase();
      li.append(text);
      list.append(li);
      return li;
    });
    label.textContent = el.selectedOptions[0]?.textContent ?? "";
    button.disabled = el.disabled;
    // Rebuilding the rows drops data-active, but aria-activedescendant still
    // names one — an active option with no visible highlight. Re-apply it.
    if (!list.hidden && activeIndex >= 0) setActive(activeIndex);
  }

  /** Bottom edge of the sticky site nav, which paints UNDER this list's
   *  z-index — so it is the real top of the space this component may use. */
  function navBottom(): number {
    const nav = document.querySelector(".topnav");
    return nav ? Math.max(nav.getBoundingClientRect().bottom, 0) : 0;
  }

  /**
   * Decide which side to open on, and how tall the list may be.
   *
   * Preference is downward, because that is what a reader expects. It flips up
   * when the control sits low enough that a downward list would be clipped AND
   * there is more room above. Either way the height is capped to the space on
   * the chosen side, so the list scrolls internally instead of running off the
   * screen — a book with forty chapters behaves the same as one with four.
   */
  function place(): void {
    const rect = button.getBoundingClientRect();
    // Some embedding contexts report an innerHeight of 0. Trusting it would put
    // the list in the wrong place and cap it at nothing, so fall back to the
    // documentElement's height and, failing that, leave the CSS ceiling alone.
    const viewportH =
      window.innerHeight || document.documentElement.clientHeight || 0;
    if (!viewportH) {
      root.dataset.placement = "down";
      return;
    }
    const below = viewportH - rect.bottom - VIEWPORT_MARGIN;
    // The site nav is sticky at the top and paints under this list's z-index, so
    // the space "above" ends at the nav's bottom edge, not the viewport's.
    const above = rect.top - navBottom() - VIEWPORT_MARGIN;

    // Measure the natural height with the cap lifted, then hand the measured
    // ceiling to CSS as a custom property. The `max-height` DECLARATION stays in
    // select-menu.css — only the number, which cannot be known until layout,
    // comes from here.
    list.style.removeProperty("--sm-max-h");
    const natural = list.scrollHeight;

    // Compare against the height the list can actually reach, not its raw
    // content height: with forty chapters `natural` is far past the ceiling, so
    // comparing it raw flipped the menu upward on almost every viewport even
    // when there was ample room below for a scrolled list.
    const wanted = Math.min(natural, CEILING_PX);
    const fitsBelow = wanted <= below;
    const openUp = !fitsBelow && above > below && above >= MIN_SIDE_SPACE;

    root.dataset.placement = openUp ? "up" : "down";
    const room = Math.max(MIN_SIDE_SPACE, openUp ? above : below);
    if (wanted > room) list.style.setProperty("--sm-max-h", `${room}px`);
  }

  function setActive(i: number): void {
    if (!options.length) return;
    const next = Math.max(0, Math.min(options.length - 1, i));
    options.forEach((o, n) => o.setAttribute("data-active", String(n === next)));
    activeIndex = next;
    const active = options[next];
    button.setAttribute("aria-activedescendant", active.id);
    // Scroll the LIST, never the page: scrollIntoView walks every scrollable
    // ancestor, and any window scroll re-enters place() through the scroll
    // listener, changing placement in the middle of a keystroke.
    const top = active.offsetTop;
    const bottom = top + active.offsetHeight;
    if (top < list.scrollTop) list.scrollTop = top;
    else if (bottom > list.scrollTop + list.clientHeight)
      list.scrollTop = bottom - list.clientHeight;
  }

  function open(): void {
    if (isOpen() || el.disabled) return;
    sync();
    list.hidden = false;
    button.setAttribute("aria-expanded", "true");
    place();
    setActive(Math.max(0, el.selectedIndex));
  }

  function close(focusButton = true): void {
    if (!isOpen()) return;
    list.hidden = true;
    button.setAttribute("aria-expanded", "false");
    button.removeAttribute("aria-activedescendant");
    activeIndex = -1;
    if (focusButton) button.focus();
  }

  /** Commit an index THROUGH the native element, so listeners fire as before.
   *  Used by the open list and by the closed-state Home/End/type-ahead moves. */
  function commit(i: number): void {
    if (i < 0 || i >= el.options.length) return;
    const changed = el.selectedIndex !== i;
    el.selectedIndex = i; // exact, and index-parallel to the rendered list
    close();
    sync();
    if (changed) {
      // A native select fires input BEFORE change; match it so listeners on
      // either event behave the same as they did before this component.
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function onTypeahead(key: string): void {
    const now = Date.now();
    typeahead = now - typeaheadAt > TYPEAHEAD_MS ? key : typeahead + key;
    typeaheadAt = now;
    const from = activeIndex + (typeahead.length === 1 ? 1 : 0);
    const hunt = [...options.slice(from), ...options.slice(0, from)];
    // Match the LABEL, not the row: every row carries a tick glyph for
    // alignment, so `o.textContent` reads "\u2713A Stranger in the City" and no
    // type-ahead would ever match its first letter.
    const hit = hunt.find((o) =>
      (o.dataset.label ?? "").startsWith(typeahead.toLowerCase()),
    );
    if (hit) setActive(options.indexOf(hit));
  }

  button.addEventListener("click", () => (isOpen() ? close() : open()));

  button.addEventListener("keydown", (e) => {
    if (!isOpen()) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
        e.preventDefault();
        open();
        return;
      }
      // Closed-state moves, which a native select performs without opening.
      const last = el.options.length - 1;
      if (e.key === "Home" || e.key === "End") {
        e.preventDefault();
        commit(e.key === "Home" ? 0 : last);
      } else if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        const want = e.key.toLowerCase();
        const from = el.selectedIndex + 1;
        const order = [...el.options].map((_, i) => (from + i) % el.options.length);
        const hit = order.find((i) =>
          (el.options[i].textContent ?? "").trim().toLowerCase().startsWith(want),
        );
        if (hit !== undefined) commit(hit);
      }
      return;
    }
    if (e.altKey && e.key === "ArrowUp") {
      e.preventDefault();
      close();
      return;
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActive(activeIndex + 1);
        break;
      case "ArrowUp":
        e.preventDefault();
        setActive(activeIndex - 1);
        break;
      case "Home":
        e.preventDefault();
        setActive(0);
        break;
      case "End":
        e.preventDefault();
        setActive(options.length - 1);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        commit(activeIndex);
        break;
      case "Escape":
        e.preventDefault();
        close();
        break;
      case "Tab":
        close(false);
        break;
      default:
        if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {
          e.preventDefault();
          onTypeahead(e.key);
        }
    }
  });

  // Pointer and keyboard share one highlight, so they cannot disagree.
  list.addEventListener("mousemove", (e) => {
    const li = (e.target as HTMLElement).closest<HTMLLIElement>(".sm-option");
    if (li) setActive(options.indexOf(li));
  });
  list.addEventListener("click", (e) => {
    const li = (e.target as HTMLElement).closest<HTMLLIElement>(".sm-option");
    if (li) commit(options.indexOf(li));
  });

  root.addEventListener("focusout", (e) => {
    // Any route out of the component closes it — otherwise the list can be left
    // open, aria-expanded true, with focus somewhere else entirely.
    const to = (e as FocusEvent).relatedTarget as Node | null;
    if (to && !root.contains(to)) close(false);
  });

  const onDocPointer = (e: PointerEvent): void => {
    if (!root.contains(e.target as Node)) close(false);
  };
  let reflowPending = false;
  const onReflow = (): void => {
    // place() writes then reads, so running it per scroll event thrashes layout
    // on a page with a long chapter body. One call per frame is enough.
    if (!isOpen() || reflowPending) return;
    reflowPending = true;
    requestAnimationFrame(() => {
      reflowPending = false;
      if (!isOpen()) return;
      // The list is anchored to the control. Once a scroll has carried that
      // control out of the band a reader can actually see — behind the sticky
      // nav, or past the bottom edge — re-placing it is not enough: the list
      // followed it up, painted straight over the nav, and ran off the top of
      // the screen with its first rows unreachable. A native select's popup
      // does not survive the page scrolling out from under it either. Dismiss,
      // with close(false) so focus is not dragged to an off-screen control.
      const rect = button.getBoundingClientRect();
      const viewportH =
        window.innerHeight || document.documentElement.clientHeight || 0;
      if (viewportH && (rect.bottom <= navBottom() || rect.top >= viewportH)) {
        close(false);
        return;
      }
      place();
    });
  };
  document.addEventListener("pointerdown", onDocPointer);
  window.addEventListener("resize", onReflow);
  // Capture phase: a scroll in any ancestor moves the control, not just window.
  window.addEventListener("scroll", onReflow, true);

  sync();

  return {
    sync,
    destroy: () => {
      // Close first: if focus is inside the list when root.remove() runs it
      // falls to <body> and the user loses their place.
      const hadFocus = root.contains(document.activeElement);
      close(false);
      document.removeEventListener("pointerdown", onDocPointer);
      window.removeEventListener("resize", onReflow);
      window.removeEventListener("scroll", onReflow, true);
      labelled?.removeEventListener("click", onLabelClick);
      el.classList.remove("sm-native");
      el.removeAttribute("aria-hidden");
      // removeAttribute, not tabIndex=0 — the latter stamps an explicit
      // tabindex the element never had.
      el.removeAttribute("tabindex");
      delete el.dataset.smEnhanced;
      root.parentNode?.insertBefore(select, root);
      root.remove();
    },
  };
}
