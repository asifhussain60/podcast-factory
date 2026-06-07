/**
 * site-chrome.ts — WC6f shared view chrome (back-to-top).
 * External module loaded once by Base.astro; no logic lives inline in the
 * layout (Cortex Astro-delivery delta). Honors prefers-reduced-motion.
 */
function initBackToTop(): void {
  const btn = document.getElementById('to-top');
  if (!btn) return;

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SHOW_AFTER = 600; // px scrolled before the control appears

  const onScroll = () => {
    if (window.scrollY > SHOW_AFTER) btn.classList.add('is-visible');
    else btn.classList.remove('is-visible');
  };

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
  });

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

function initJumpNav(): void {
  const nav = document.getElementById('jump-nav') as HTMLElement | null;
  if (!nav) return;

  const sections = Array.from(
    document.querySelectorAll<HTMLElement>('main section[id]')
  ).filter(s => /^s\d/.test(s.id));

  if (sections.length < 2) { nav.hidden = true; return; }

  const label = document.createElement('span');
  label.className = 'jump-nav-label';
  label.textContent = 'On this page';
  nav.appendChild(label);

  sections.forEach(s => {
    const heading = s.querySelector('h2, h3');
    const text = (heading?.textContent ?? s.id)
      .replace(/^\d+\s*/, '').trim();
    const a = document.createElement('a');
    a.className = 'jump-nav-link';
    a.href = `#${s.id}`;
    a.textContent = text;
    nav.appendChild(a);
  });

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  nav.querySelectorAll<HTMLAnchorElement>('.jump-nav-link').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const target = document.getElementById(a.hash.slice(1));
      target?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    });
  });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      const link = nav.querySelector<HTMLAnchorElement>(`a[href="#${entry.target.id}"]`);
      if (!link) return;
      if (entry.isIntersecting) link.classList.add('is-active');
      else link.classList.remove('is-active');
    });
  }, { rootMargin: '-10% 0px -70% 0px', threshold: 0 });

  sections.forEach(s => observer.observe(s));
}

function initNavScroll(): void {
  const strip = document.querySelector<HTMLElement>('.topnav-sections');
  const active = document.querySelector<HTMLElement>('.topnav-section.is-active');
  if (!strip || !active) return;
  // Scroll only the tab strip, not the page (scrollIntoView walks all ancestors).
  const sRect = strip.getBoundingClientRect();
  const aRect = active.getBoundingClientRect();
  const tabCenterInStrip = aRect.left - sRect.left + strip.scrollLeft + aRect.width / 2;
  strip.scrollLeft = tabCenterInStrip - strip.clientWidth / 2;
}

function init(): void {
  initBackToTop();
  initJumpNav();
  initNavScroll();
}

if (document.readyState !== 'loading') init();
else document.addEventListener('DOMContentLoaded', init);
