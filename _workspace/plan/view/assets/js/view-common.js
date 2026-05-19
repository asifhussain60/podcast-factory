/* =========================================================================
   view-common.js — shared interactivity for podcast workspace views.
   Plain, vanilla, file:// safe. No dependencies. No build step.
   Behaviors:
     - Tab groups (data-tabs)
     - Anchor copy buttons (auto-injected for h2/h3 with id)
     - "Expand all" / "Collapse all" controls for <details> groups
     - Year stamp (data-year)
     - Smooth-scroll friendly anchor highlight on hash
   ========================================================================= */
(function () {
  'use strict';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  /* ------------------------------------------------------------------ Tabs */
  function initTabs() {
    $$('[data-tabs]').forEach(function (group) {
      var btns   = $$('[role="tab"]', group);
      var panels = $$('[role="tabpanel"]', group);
      if (!btns.length || !panels.length) return;

      function activate(idx) {
        btns.forEach(function (b, i) {
          var active = i === idx;
          b.setAttribute('aria-selected', active ? 'true' : 'false');
          b.tabIndex = active ? 0 : -1;
        });
        panels.forEach(function (p, i) {
          p.classList.toggle('is-active', i === idx);
          p.hidden = i !== idx;
        });
      }

      btns.forEach(function (b, i) {
        b.addEventListener('click', function () { activate(i); });
        b.addEventListener('keydown', function (e) {
          if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
            e.preventDefault();
            var dir = e.key === 'ArrowRight' ? 1 : -1;
            var next = (i + dir + btns.length) % btns.length;
            btns[next].focus();
            activate(next);
          } else if (e.key === 'Home') {
            e.preventDefault(); btns[0].focus(); activate(0);
          } else if (e.key === 'End') {
            e.preventDefault();
            btns[btns.length - 1].focus(); activate(btns.length - 1);
          }
        });
      });

      // Honor hash → tab id mapping if requested
      var initial = 0;
      if (window.location.hash) {
        var target = window.location.hash.slice(1);
        var i = btns.findIndex(function (b) { return b.getAttribute('aria-controls') === target; });
        if (i >= 0) initial = i;
      }
      activate(initial);
    });
  }

  /* ----------------------------------------------------- Heading anchors */
  function initHeadingAnchors() {
    $$('main h2[id], main h3[id]').forEach(function (h) {
      if (h.querySelector('.anchor')) return;
      var a = document.createElement('a');
      a.href = '#' + h.id;
      a.className = 'anchor';
      a.setAttribute('aria-label', 'Permalink to ' + (h.textContent || '').trim());
      a.textContent = '#';
      a.style.cssText = 'margin-left:8px;opacity:0;color:var(--text-muted);text-decoration:none;font-weight:400;font-size:0.85em;transition:opacity .15s;';
      h.appendChild(a);
      h.addEventListener('mouseenter', function () { a.style.opacity = '1'; });
      h.addEventListener('mouseleave', function () { a.style.opacity = '0'; });
      h.addEventListener('focusin',  function () { a.style.opacity = '1'; });
    });
  }

  /* ------------------------------------------ Expand / collapse details */
  function initDetailsControls() {
    $$('[data-details-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var scopeSel = btn.getAttribute('data-details-scope') || 'body';
        var action   = btn.getAttribute('data-details-toggle'); // "open" | "close"
        var scope    = $(scopeSel) || document.body;
        $$('details', scope).forEach(function (d) { d.open = (action === 'open'); });
      });
    });
  }

  /* ------------------------------------------------------- Year stamp */
  function initYear() {
    $$('[data-year]').forEach(function (el) {
      el.textContent = String(new Date().getFullYear());
    });
  }

  /* ------------------------------------------------------ Hash highlight */
  function highlightHash() {
    if (!window.location.hash) return;
    var el = document.getElementById(window.location.hash.slice(1));
    if (!el) return;
    el.style.transition = 'background-color 0.4s';
    var orig = el.style.backgroundColor;
    el.style.backgroundColor = 'var(--accent-soft)';
    setTimeout(function () { el.style.backgroundColor = orig; }, 1500);
  }

  /* ------------------------------------------------------------ Boot */
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    initTabs();
    initHeadingAnchors();
    initDetailsControls();
    initYear();
    highlightHash();
    window.addEventListener('hashchange', highlightHash);
  });
})();
