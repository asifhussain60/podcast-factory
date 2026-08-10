/**
 * claude-plans.ts — client behavior for /claude-plans (index search) and
 * /claude-plans/[slug] (masked/full toggle). External module, feature-detects
 * each page's markup so one file covers both (Cortex Astro-delivery delta —
 * no logic lives inline in either page).
 */
interface PlanSearchEntry {
  slug: string;
  text: string;
}

function initSearch(): void {
  const input = document.getElementById(
    "cp-search-input",
  ) as HTMLInputElement | null;
  const indexEl = document.getElementById("cp-search-index");
  if (!input || !indexEl) return;

  let entries: PlanSearchEntry[];
  try {
    entries = JSON.parse(indexEl.textContent || "[]");
  } catch {
    return;
  }
  const bySlug = new Map(entries.map((e) => [e.slug, e.text]));
  const countEl = document.getElementById("cp-search-count");

  const apply = () => {
    const q = input.value.trim().toLowerCase();
    const cards = Array.from(
      document.querySelectorAll<HTMLElement>("[data-plan-slug]"),
    );
    let shown = 0;
    for (const card of cards) {
      const slug = card.dataset.planSlug ?? "";
      const text = bySlug.get(slug) ?? "";
      const matches = q.length === 0 || text.includes(q);
      card.hidden = !matches;
      if (matches) shown++;
    }
    if (countEl) {
      countEl.textContent =
        q.length === 0
          ? `${cards.length} plan${cards.length === 1 ? "" : "s"}`
          : `${shown} of ${cards.length} match "${input.value.trim()}"`;
    }
  };

  input.addEventListener("input", apply);
  apply();
}

function initMaskedToggle(): void {
  const toggle = document.getElementById(
    "cp-toggle-full",
  ) as HTMLButtonElement | null;
  const masked = document.getElementById("cp-masked");
  const full = document.getElementById("cp-full");
  if (!toggle || !masked || !full) return;

  toggle.addEventListener("click", () => {
    const showingFull = !full.hidden;
    full.hidden = showingFull;
    masked.hidden = !showingFull;
    toggle.textContent = showingFull
      ? "Show the full technical plan"
      : "Back to the simplified view";
    toggle.setAttribute("aria-pressed", String(!showingFull));
  });
}

initSearch();
initMaskedToggle();
