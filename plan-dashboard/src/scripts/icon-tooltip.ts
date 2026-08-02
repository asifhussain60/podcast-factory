/**
 * icon-tooltip.ts — hover/focus tooltips for icon-only controls.
 *
 * Why this exists: the Composer's inspector tabs are four icons on one row, and
 * the first attempt at showing what they mean revealed each tab's hidden label
 * IN PLACE (`position: static` on hover). Revealing text inside a `flex: 1 1 0`
 * tab widens that tab, so the strip re-flows under the pointer and the label
 * collides with its neighbours. A tooltip must not participate in layout at all.
 *
 * Two constraints shaped the implementation:
 *   1. `.cx-surface` is `overflow: hidden` (its frame clips; the content inside
 *      scrolls), so a tooltip rendered as a descendant of the tab strip is cut
 *      off at the surface edge. This one is appended to <body> and positioned
 *      with `position: fixed`, which puts it outside every clipping ancestor.
 *   2. Position must be computed, but the site DoD forbids inline styling. So
 *      the JS writes two CUSTOM PROPERTIES (--tip-x / --tip-y) and the actual
 *      declarations live in book-composer.css — the same division of labour
 *      panel-text-size.ts uses for --panel-fs.
 *
 * Accessibility: the trigger's label span stays in the DOM and remains the
 * button's accessible NAME. The tooltip shows that same string, so it is marked
 * `aria-hidden` — wiring it up with aria-describedby as well would make a screen
 * reader announce "Artifacts, Artifacts". The visual affordance is for sighted
 * pointer/keyboard users; the name was never missing for anyone else.
 *
 * Timing: a delay going IN so sweeping the pointer across four adjacent icons
 * does not flash four tooltips, and NO delay going out. Escape dismisses,
 * per the WAI-ARIA tooltip pattern.
 */

/** Milliseconds of hover/focus before a tooltip appears. None on the way out. */
const DELAY_IN = 400;
/** Gap between the trigger's bottom edge and the tooltip. */
const OFFSET_Y = 6;
/** Minimum distance from the viewport edge when the tooltip is clamped. */
const EDGE_PAD = 8;

/** A control's name, and the part you cannot read off its glyph. */
export interface TooltipContent {
  title: string;
  /** What it produces and what it expects selected first. One or two sentences. */
  detail: string;
}

export interface IconTooltipOptions {
  /** Selector for the trigger elements to look up inside `scope`. */
  trigger: string;
  /** Selector, WITHIN a trigger, for the element holding its label text. Used
   *  when `content` has nothing for this trigger. */
  label?: string;
  /**
   * Rich text by trigger key. Wins over `label` where both could answer.
   *
   * The tab strip this module was built for only ever needed to reveal a name
   * the icon was standing in for. A formatting toolbar needs more than that: the
   * useful thing about a verse button is not that it is called "Qur'anic
   * quotation" but that you select the Arabic BEFORE clicking it.
   */
  content?: Readonly<Record<string, TooltipContent>>;
  /** How a trigger keys into `content`. Default: its `data-rte-id`. */
  keyOf?: (el: HTMLElement) => string;
  /**
   * Hover/focus delay in ms. Default 400.
   *
   * A bar of twelve adjacent icons wants this SHORTER than a strip of four: you
   * sweep across a toolbar to find something, and a delay long enough to prevent
   * flicker on four tabs is long enough to feel broken on twelve.
   */
  delayIn?: number;
  /**
   * Remove each trigger's `title` attribute on mount. Default false.
   *
   * The browser's native tooltip is the thing this module replaces, and it is
   * not suppressible any other way. Leave it and both appear — ours promptly,
   * the OS's a second later, on top, saying less. Safe because `aria-label`
   * carries the accessible name on these controls; `title` was only ever the
   * sighted-pointer affordance.
   */
  dropNativeTitle?: boolean;
}

/**
 * Give every `opts.trigger` inside `scope` a hover/focus tooltip — the rich text
 * `opts.content` holds for it, or failing that the text of its `opts.label`
 * child. Returns a dispose function that removes the listeners and the shared
 * tooltip node.
 */
export function mountIconTooltips(
  scope: HTMLElement,
  opts: IconTooltipOptions,
): () => void {
  const triggers = Array.from(
    scope.querySelectorAll<HTMLElement>(opts.trigger),
  );
  if (!triggers.length) return () => {};

  const keyOf = opts.keyOf ?? ((el: HTMLElement) => el.dataset.rteId ?? "");
  const delayIn = opts.delayIn ?? DELAY_IN;
  // Kept so dispose can put back exactly what it took, rather than assuming the
  // attribute was absent.
  const nativeTitles = new Map<HTMLElement, string>();
  if (opts.dropNativeTitle) {
    for (const t of triggers) {
      if (!t.hasAttribute("title")) continue;
      nativeTitles.set(t, t.getAttribute("title") ?? "");
      t.removeAttribute("title");
    }
  }

  // ONE tooltip node for the whole strip, reused. Four nodes would be four
  // things to keep in sync and four ways to leave one on screen.
  const tip = document.createElement("div");
  tip.className = "cx-tip";
  tip.setAttribute("aria-hidden", "true"); // visual duplicate of the name — see header
  tip.hidden = true;
  document.body.appendChild(tip);

  let timer = 0;

  function hide(): void {
    window.clearTimeout(timer);
    timer = 0;
    tip.hidden = true;
  }

  function show(trigger: HTMLElement): void {
    const rich = opts.content?.[keyOf(trigger)];
    const plain = opts.label
      ? (trigger.querySelector(opts.label)?.textContent?.trim() ?? "")
      : "";
    if (!rich && !plain) return;

    // Rebuilt rather than mutated: a stale detail line left over from the
    // previous trigger under a new title is the one failure mode worth spending
    // two element creations to make impossible.
    tip.replaceChildren();
    // `.is-rich` carries the wider, wrapping, sentence-case treatment; without
    // it the tip keeps the original single-line uppercase chip look the tab
    // strip is built around.
    tip.classList.toggle("is-rich", Boolean(rich));
    if (rich) {
      const t = document.createElement("strong");
      t.className = "cx-tip-title";
      t.textContent = rich.title;
      const d = document.createElement("span");
      d.className = "cx-tip-detail";
      d.textContent = rich.detail;
      tip.append(t, d);
    } else {
      tip.textContent = plain;
    }
    tip.hidden = false; // unhide first: a hidden element measures as 0 wide

    const r = trigger.getBoundingClientRect();
    const half = tip.offsetWidth / 2;
    // Centre on the icon, then clamp so an edge tab's tooltip stays on screen.
    const centre = Math.min(
      Math.max(r.left + r.width / 2, EDGE_PAD + half),
      window.innerWidth - EDGE_PAD - half,
    );
    tip.style.setProperty("--tip-x", `${Math.round(centre)}px`);
    tip.style.setProperty("--tip-y", `${Math.round(r.bottom + OFFSET_Y)}px`);
  }

  function schedule(trigger: HTMLElement): void {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => show(trigger), delayIn);
  }

  const cleanups: (() => void)[] = [];
  for (const trigger of triggers) {
    const onEnter = () => schedule(trigger);
    // Keyboard focus only. A pointer press focuses the button too, and a
    // tooltip that reappears on the tab you just clicked reads as a stuck one.
    const onFocus = () => {
      if (trigger.matches(":focus-visible")) schedule(trigger);
    };
    trigger.addEventListener("mouseenter", onEnter);
    trigger.addEventListener("mouseleave", hide);
    trigger.addEventListener("focus", onFocus);
    trigger.addEventListener("blur", hide);
    trigger.addEventListener("click", hide);
    cleanups.push(() => {
      trigger.removeEventListener("mouseenter", onEnter);
      trigger.removeEventListener("mouseleave", hide);
      trigger.removeEventListener("focus", onFocus);
      trigger.removeEventListener("blur", hide);
      trigger.removeEventListener("click", hide);
    });
  }

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") hide();
  };
  // A fixed tooltip does not travel with its trigger, so anything that moves the
  // trigger dismisses it rather than leaving it pointing at empty space. Capture
  // phase because the drawer's surfaces scroll internally and those events do
  // not bubble to window.
  document.addEventListener("keydown", onKey);
  window.addEventListener("scroll", hide, { capture: true, passive: true });
  window.addEventListener("resize", hide, { passive: true });

  return () => {
    hide();
    for (const [el, title] of nativeTitles) el.setAttribute("title", title);
    cleanups.forEach((fn) => fn());
    document.removeEventListener("keydown", onKey);
    window.removeEventListener("scroll", hide, { capture: true });
    window.removeEventListener("resize", hide);
    tip.remove();
  };
}
