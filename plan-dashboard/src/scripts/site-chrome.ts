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

if (document.readyState !== 'loading') initBackToTop();
else document.addEventListener('DOMContentLoaded', initBackToTop);
