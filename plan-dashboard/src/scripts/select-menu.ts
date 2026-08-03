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
 * THE LIST ALWAYS OPENS DOWNWARD (Asif, 2026-08-03). It used to flip upward when
 * the control sat low in the viewport, and on the Book Composer's chapter picker
 * that was the worse half of the trade: an upward list is bounded by the sticky
 * nav, so an eight-chapter book opened into a window that showed six rows with
 * the last two out of reach behind the top of the screen. Downward the list is
 * bounded only by the viewport, and `open()` scrolls the control up first when
 * the room below is short — so the promise costs nothing. See `place()`.
 *
 * SCOPE: flat, always-enabled options only. `<option disabled>` renders as an
 * ordinary selectable row and `<optgroup>` is ignored — neither occurs in the
 * pickers this serves. Add support before pointing it at a grouped select.
 *
 * Styles: styles/select-menu.css. Keyboard contract follows the ARIA combobox
 * pattern: Enter/Space/Arrow to open, Up/Down/Home/End to move, type-ahead to
 * jump, Enter to choose, Escape to dismiss, Tab to leave.
 */

/** The shortest the list may be capped to. Below this it stops being a list. */
const MIN_SIDE_SPACE = 140;
/** Breathing room left between the list and the viewport edge. */
const VIEWPORT_MARGIN = 12;
/** How long a type-ahead buffer survives between keystrokes. */
const TYPEAHEAD_MS = 700;
/** Fallback for the CSS ceiling when it cannot be read — 22rem at a 16px root,
 *  matching select-menu.css. The live value is READ from the stylesheet rather
 *  than assumed: the Book Composer has a reader text-size control that changes
 *  the root font-size, so 22rem there is ~422px, and a hard-coded 352 let the
 *  list run 65px past the bottom of the viewport it had just been fitted to. */
const CEILING_FALLBACK_PX = 352;

export interface SelectMenu {
  /** Re-read the native select — call after its options or value change. */
  sync: () => void;
  destroy: () => void;
}

/**
 * Enhance one `<select>`. Returns null if the element is missing or already
 * enhanced, so callers can invoke it unconditionally.
 */
export function enhanceSelect(
  select: HTMLSelectElement | null,
): SelectMenu | null {
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

  /** Space below the control, and the height the list wants — both in px.
   *  Reading them together keeps `place()` and `makeRoomBelow()` measuring the
   *  same thing; a list capped by one number and scrolled for another is how the
   *  rows at the far end become unreachable. */
  function metrics(): { below: number; wanted: number; viewportH: number } {
    // Some embedding contexts report an innerHeight of 0. Trusting it would cap
    // the list at nothing, so fall back to the documentElement's height.
    const viewportH =
      window.innerHeight || document.documentElement.clientHeight || 0;
    const below =
      viewportH - button.getBoundingClientRect().bottom - VIEWPORT_MARGIN;
    // Measure the natural height with the cap lifted. Compare against the height
    // the list can actually REACH, not its raw content height: with forty
    // chapters `natural` is far past the ceiling. The ceiling comes from the
    // stylesheet, resolved in px at the CURRENT root font-size — see
    // CEILING_FALLBACK_PX for why assuming it is wrong.
    list.style.removeProperty("--sm-max-h");
    const declared = parseFloat(getComputedStyle(list).maxHeight);
    const ceiling = Number.isFinite(declared) ? declared : CEILING_FALLBACK_PX;
    return { below, wanted: Math.min(list.scrollHeight, ceiling), viewportH };
  }

  /**
   * Cap the list to the room below the control. Placement is always downward.
   *
   * The height is capped to that room, never past it, so the list scrolls
   * internally instead of running off the screen — a book with forty chapters
   * behaves the same as one with four. `MIN_SIDE_SPACE` is the floor: below it
   * the list would be too short to be a list at all, and `makeRoomBelow()` has
   * already scrolled to avoid that wherever the page allows.
   */
  function place(): void {
    root.dataset.placement = "down";
    const { below, wanted, viewportH } = metrics();
    if (!viewportH) return;
    const room = Math.max(MIN_SIDE_SPACE, below);
    // Always write the cap, never only when it bites. Leaving it unset falls
    // back to the CSS ceiling, which is what put the list past the bottom edge
    // whenever the two disagreed about how tall 22rem is.
    list.style.setProperty("--sm-max-h", `${Math.min(wanted, room)}px`);
  }

  /**
   * Scroll the page so a downward list fits, before it is placed.
   *
   * This is what makes "always downward" free rather than a trade. The control
   * near the bottom of a long page had the room; the viewport was just looking
   * at the wrong part of it. Scrolls by the deficit only — never past what the
   * document has left, and never at all when the page cannot scroll.
   */
  function makeRoomBelow(): void {
    const { below, wanted, viewportH } = metrics();
    if (!viewportH || wanted <= below) return;
    const doc = document.documentElement;
    const remaining = doc.scrollHeight - window.scrollY - viewportH;
    const by = Math.min(wanted - below, Math.max(0, remaining));
    // Leave the control clear of the sticky nav it would otherwise slide under.
    const headroom =
      button.getBoundingClientRect().top - navBottom() - VIEWPORT_MARGIN;
    const shift = Math.min(by, Math.max(0, headroom));
    if (shift > 0) window.scrollBy({ top: shift, behavior: "instant" });
  }

  function setActive(i: number): void {
    if (!options.length) return;
    const next = Math.max(0, Math.min(options.length - 1, i));
    options.forEach((o, n) =>
      o.setAttribute("data-active", String(n === next)),
    );
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
    // Room first, then placement: makeRoomBelow moves the control, so placing
    // before it would cap the list against a measurement already stale.
    makeRoomBelow();
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
        const order = [...el.options].map(
          (_, i) => (from + i) % el.options.length,
        );
        const hit = order.find((i) =>
          (el.options[i].textContent ?? "")
            .trim()
            .toLowerCase()
            .startsWith(want),
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

  // A mouse selection must not move focus off the button. The rows are not
  // focusable, so mousedown's default action walks up to the nearest focusable
  // ancestor — on this site the skip-link target <main tabindex="-1"> — and
  // that focus move fires focusout on the root, which closes the list BEFORE
  // the click event can reach the row: the click then lands on whatever was
  // painted behind the vanished list and no option is ever committed.
  // Preventing the default keeps focus on the button for the whole gesture.
  // Guarded to option rows: a mousedown on the list's own scrollbar (the <ul>
  // is the scroll container) must keep its default, or dragging the thumb goes
  // dead on browsers that dispatch scrollbar mousedowns to content (Firefox,
  // WebKit with always-visible scroll bars) — and a scrollbar press moves no
  // focus anyway, so the close-on-focusout bug cannot re-enter through it.
  list.addEventListener("mousedown", (e) => {
    if ((e.target as HTMLElement).closest(".sm-option")) e.preventDefault();
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
  const onReflow = (e?: Event): void => {
    // The list is its OWN scroll container, and this listener is on the capture
    // phase so it sees that scroll too. Re-placing on it lifts the height cap to
    // re-measure and puts it straight back — mid-gesture, every frame — which is
    // how scrolling an eight-chapter list toward its last rows fought back and
    // never arrived. A scroll INSIDE the list moves no control; ignore it.
    if (e && e.target instanceof Node && list.contains(e.target)) return;
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
