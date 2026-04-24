/* insert-event.js — header Add-event button + insert-mode flow with AI.
 *
 * Insert mode reveals dashed rails in the gaps between events. Clicking a
 * gap opens a two-pane modal: chat/prompt on the left (Sonnet + web_search
 * via /api/suggest-insert) and streamed candidate cards on the right.
 * Clicking a card promotes it to the active pick and pre-fills a compact
 * start/duration/notes form below. Save POSTs /api/insert-event and
 * triggers __refreshItinerary.
 *
 * Self-contained vanilla JS. Same vibe as findAlternate/requestDelete —
 * DOM mutations only, no framework.
 */
(function () {
  'use strict';

  var CHROME_ATTR = 'data-insert-chrome';
  var DAY_START_MIN = 8 * 60;
  var DAY_END_MIN   = 22 * 60;
  var MIN_DURATION_MIN = 15;
  var DEFAULT_DURATION_MIN = 60;
  var BUFFER_AFTER_PREV_MIN = 15;

  var DESTINATION_TAGS = ['DINING', 'CAFE', 'NATURE', 'SHOPPING', 'SPA',
    'ENTERTAINMENT', 'REST', 'ENGAGEMENT_HIGHLIGHT', 'EVENT', 'CELEBRATION'];
  var NON_DEST_TAGS = ['TRAVEL', 'APPOINTMENT', 'FREE'];
  var ALL_TAGS = DESTINATION_TAGS.concat(NON_DEST_TAGS);

  // Starter chips — demoted to the collapsed "Quick starts" row below the
  // prompt box in the redesigned panel. Clicking a chip fills the input so
  // the user can edit before sending (no auto-send).
  var STARTER_CHIPS = [
    { label: 'Halal dinner nearby', text: 'A halal dinner spot within 15 minutes of the prior stop, mid-range.' },
    { label: 'Coffee / tea break', text: 'A specialty coffee or tea spot, cozy, quick 30-min stop.' },
    { label: 'Quick scenic stroll', text: 'A short scenic walk, park, or garden — no more than 45 minutes.' },
    { label: 'Dessert run', text: 'A dessert or ice-cream spot with strong reviews, close by.' },
    { label: 'Date-night drinks', text: 'A romantic bar or lounge for couple\'s drinks, quiet and well-rated.' },
  ];

  // Scope radius chips — controls the hard drive-time cap applied by the
  // server sub-prompt. Smart default is computed from gap window size.
  var SCOPE_CHIPS = [
    { key: 'walking', label: 'Walking',       sub: '≤ 5 min',    capMin: 5 },
    { key: '15min',   label: '≤ 15 min drive', sub: 'Nearby',    capMin: 15 },
    { key: '30min',   label: '≤ 30 min drive', sub: 'Short hop', capMin: 30 },
    { key: 'expand',  label: 'Expand',        sub: 'County-wide', capMin: 60 },
  ];

  // Smart scope default: tight gap → tighter radius. Respects the idea that
  // you can't drive 30 min out-and-back in a 1h gap.
  function defaultScopeForGap(gapMin) {
    if (!Number.isFinite(gapMin) || gapMin <= 0) return '15min';
    if (gapMin <= 60)  return '15min';
    if (gapMin <= 150) return '30min';
    return '30min'; // expand is only set manually; conservative default
  }

  var PROGRESS_STEPS = [
    'Reading your request\u2026',
    'Searching nearby venues\u2026',
    'Cross-checking ratings and hours\u2026',
    'Ranking by fit and drive time\u2026',
    'Almost there \u2014 hang tight\u2026',
  ];

  var state = {
    active: false,
    modalOpen: false,
    inflight: false,
    aiAbortCtrl: null,
    aiStatusTimer: null,
    history: [],            // [{ role: 'user'|'ai', text, candidates?, status?, turnId }]
    currentCandidates: [],
    pickedIdx: null,        // which candidate card is active
    manualMode: false,
    modalCtx: null,
    saving: false,
    // Redesign state (Q1–Q8 locked 2026-04-24)
    scopeRadius: '30min',   // Walking / ≤15min / ≤30min / Expand
    lastIntent: null,       // { mode, vendorName, categoryHint, confidence }
    lastSearchPrompt: null, // remembers the last sent prompt for retry-with-expand
  };

  // ─── Utilities ──────────────────────────────────────────────────────
  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function isDestinationTag(tag) {
    return DESTINATION_TAGS.indexOf(String(tag || '').toUpperCase()) !== -1;
  }

  function parseTimeToMin(raw) {
    if (typeof raw !== 'string') return null;
    var s = raw.replace(/[~≈]/g, '').trim();
    var m = s.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?/);
    if (!m) return null;
    var h = Number(m[1]);
    var min = Number(m[2] || 0);
    var ampm = (m[3] || '').toUpperCase();
    if (ampm === 'PM' && h < 12) h += 12;
    if (ampm === 'AM' && h === 12) h = 0;
    if (!Number.isFinite(h) || !Number.isFinite(min)) return null;
    return h * 60 + min;
  }

  function formatMin(totalMin) {
    if (!Number.isFinite(totalMin)) return '';
    var mins = ((totalMin % 1440) + 1440) % 1440;
    var h = Math.floor(mins / 60);
    var m = mins % 60;
    var ampm = h >= 12 ? 'PM' : 'AM';
    var h12 = h % 12 === 0 ? 12 : h % 12;
    return h12 + ':' + (m < 10 ? '0' + m : m) + ' ' + ampm;
  }

  function formatDuration(min) {
    if (!Number.isFinite(min) || min < 0) return '';
    var h = Math.floor(min / 60);
    var m = min % 60;
    if (h === 0) return m + 'm';
    if (m === 0) return h + 'h';
    return h + 'h ' + m + 'm';
  }

  function eventEndMin(ev) {
    var start = parseTimeToMin(ev && ev.time);
    if (start == null) return null;
    var dur = Number(ev && ev.duration_min);
    if (!Number.isFinite(dur) || dur <= 0) dur = DEFAULT_DURATION_MIN;
    return start + dur;
  }

  // ─── Gap computation ────────────────────────────────────────────────
  function computeGaps(events) {
    var evs = Array.isArray(events) ? events : [];
    if (!evs.length) {
      return [{
        prevEvIdx: -1, nextEvIdx: 0,
        winStart: DAY_START_MIN, winEnd: DAY_END_MIN,
        prevTitle: null, nextTitle: null,
        insertEventIdx: 0, disabled: false,
      }];
    }
    var gaps = [];
    var firstStart = parseTimeToMin(evs[0] && evs[0].time);
    gaps.push({
      prevEvIdx: -1, nextEvIdx: 0,
      winStart: DAY_START_MIN,
      winEnd: firstStart != null ? firstStart : DAY_END_MIN,
      prevTitle: null,
      nextTitle: evs[0] && evs[0].event,
      insertEventIdx: 0,
      disabled: false,
    });
    for (var i = 0; i < evs.length - 1; i += 1) {
      var prev = evs[i];
      var next = evs[i + 1];
      var prevEnd = eventEndMin(prev);
      var nextStart = parseTimeToMin(next && next.time);
      gaps.push({
        prevEvIdx: i, nextEvIdx: i + 1,
        winStart: prevEnd != null ? prevEnd : DAY_START_MIN,
        winEnd: nextStart != null ? nextStart : DAY_END_MIN,
        prevTitle: prev && prev.event,
        nextTitle: next && next.event,
        insertEventIdx: i + 1,
        disabled: false,
      });
    }
    var lastEnd = eventEndMin(evs[evs.length - 1]);
    gaps.push({
      prevEvIdx: evs.length - 1, nextEvIdx: evs.length,
      winStart: lastEnd != null ? lastEnd : DAY_START_MIN,
      winEnd: DAY_END_MIN,
      prevTitle: evs[evs.length - 1] && evs[evs.length - 1].event,
      nextTitle: null,
      insertEventIdx: evs.length,
      disabled: false,
    });
    gaps.forEach(function (g) {
      if (g.winEnd - g.winStart < MIN_DURATION_MIN) g.disabled = true;
    });
    return gaps;
  }

  // ─── Rail DOM ───────────────────────────────────────────────────────
  function clearAllRails() {
    document.querySelectorAll('.insert-gap-rail').forEach(function (el) {
      el.parentNode && el.parentNode.removeChild(el);
    });
    document.querySelectorAll('.event.is-insert-neighbor').forEach(function (el) {
      el.classList.remove('is-insert-neighbor');
    });
  }

  function renderRailsForAllDays() {
    clearAllRails();
    var trip = window.__tripData;
    if (!trip || !Array.isArray(trip.days)) return;
    var timeline = document.querySelector('.timeline');
    if (!timeline) return;

    trip.days.forEach(function (day, dayIdx) {
      var card = timeline.querySelector('.day-card[data-day="' + day.day + '"]');
      if (!card) return;
      var list = card.querySelector('.event-list');
      if (!list) return;

      var gaps = computeGaps(day.events || []);
      var eventNodes = list.querySelectorAll('.event');

      gaps.forEach(function (gap) {
        var rail = buildRail(gap, dayIdx);
        if (gap.nextEvIdx >= eventNodes.length) {
          list.appendChild(rail);
        } else {
          var anchor = eventNodes[gap.nextEvIdx];
          list.insertBefore(rail, anchor);
        }
      });
    });
  }

  function buildRail(gap, dayIdx) {
    var rail = document.createElement('button');
    rail.type = 'button';
    rail.className = 'insert-gap-rail' + (gap.disabled ? ' is-disabled' : '');
    rail.setAttribute(CHROME_ATTR, '');
    rail.setAttribute('data-day-idx', String(dayIdx));
    rail.setAttribute('data-insert-idx', String(gap.insertEventIdx));
    rail.setAttribute('data-win-start', String(gap.winStart));
    rail.setAttribute('data-win-end', String(gap.winEnd));
    rail.setAttribute('aria-label', gap.disabled
      ? 'No time available here'
      : 'Insert event between ' + formatMin(gap.winStart) + ' and ' + formatMin(gap.winEnd));
    if (gap.disabled) {
      rail.disabled = true;
      rail.title = 'No time available here.';
    } else {
      rail.title = 'Insert event \u00b7 ' + formatMin(gap.winStart) + ' \u2192 ' + formatMin(gap.winEnd);
    }

    rail.innerHTML =
      '<span class="insert-gap-rail-line" aria-hidden="true"></span>' +
      '<span class="insert-gap-rail-pill">' +
      '  <i class="fa-solid fa-plus" aria-hidden="true"></i>' +
      '  <span class="insert-gap-rail-label">Insert event</span>' +
      '  <span class="insert-gap-rail-win">' +
      escHtml(formatMin(gap.winStart)) + ' \u2192 ' + escHtml(formatMin(gap.winEnd)) +
      '  </span>' +
      '</span>';

    rail.addEventListener('click', function (e) {
      e.stopPropagation();
      if (gap.disabled) return;
      openInsertModal({
        dayIdx: dayIdx,
        insertEventIdx: gap.insertEventIdx,
        winStart: gap.winStart,
        winEnd: gap.winEnd,
        prevTitle: gap.prevTitle,
        nextTitle: gap.nextTitle,
      });
    });
    rail.addEventListener('mouseenter', function () {
      if (gap.disabled) return;
      highlightNeighbors(rail, dayIdx, gap);
    });
    rail.addEventListener('focus', function () {
      if (gap.disabled) return;
      highlightNeighbors(rail, dayIdx, gap);
    });
    rail.addEventListener('mouseleave', unhighlightNeighbors);
    rail.addEventListener('blur', unhighlightNeighbors);
    return rail;
  }

  function highlightNeighbors(rail, dayIdx, gap) {
    unhighlightNeighbors();
    var list = rail.parentElement;
    if (!list) return;
    var eventNodes = list.querySelectorAll('.event');
    if (gap.prevEvIdx >= 0 && eventNodes[gap.prevEvIdx]) {
      eventNodes[gap.prevEvIdx].classList.add('is-insert-neighbor');
    }
    if (gap.nextEvIdx < eventNodes.length && eventNodes[gap.nextEvIdx]) {
      eventNodes[gap.nextEvIdx].classList.add('is-insert-neighbor');
    }
  }

  function unhighlightNeighbors() {
    document.querySelectorAll('.event.is-insert-neighbor').forEach(function (el) {
      el.classList.remove('is-insert-neighbor');
    });
  }

  // ─── Mode toggle + nav button ───────────────────────────────────────
  function activate() {
    if (state.active) return;
    state.active = true;
    document.body.setAttribute('data-insert-mode', 'on');
    updateNavButton();
    renderRailsForAllDays();
    if (window.notify && typeof window.notify.message === 'function') {
      window.notify.message('Insert mode \u2014 pick a gap to add an event.');
    }
  }

  function deactivate(opts) {
    if (!state.active) return;
    state.active = false;
    document.body.removeAttribute('data-insert-mode');
    updateNavButton();
    clearAllRails();
    if (!(opts && opts.silent) && window.notify && typeof window.notify.message === 'function') {
      window.notify.message('Insert mode off.');
    }
  }

  function toggle() {
    if (state.active) deactivate();
    else activate();
  }

  var navBtn = null;

  function buildNavButton() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'insert-event-nav-btn';
    btn.setAttribute(CHROME_ATTR, '');
    btn.setAttribute('aria-pressed', 'false');
    btn.innerHTML =
      '<i class="fa-solid fa-plus" aria-hidden="true"></i>' +
      '<span class="insert-event-nav-btn-label">Add event</span>';
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      toggle();
    });
    return btn;
  }

  function updateNavButton() {
    if (!navBtn) return;
    navBtn.classList.toggle('is-on', state.active);
    navBtn.setAttribute('aria-pressed', state.active ? 'true' : 'false');
    var label = navBtn.querySelector('.insert-event-nav-btn-label');
    if (label) label.textContent = state.active ? 'Cancel insert' : 'Add event';
    navBtn.title = state.active
      ? 'Insert mode is on \u2014 click to exit'
      : 'Pick a gap between events to add a new one';
  }

  function mountNavButton() {
    var anchor = document.querySelector('[data-theme-switcher]');
    if (!anchor || !anchor.parentElement) return false;
    var parent = anchor.parentElement;
    if (parent.querySelector('.insert-event-nav-btn')) return true;
    navBtn = buildNavButton();
    var tweakerMount = parent.querySelector('[data-tweaker-mount]');
    parent.insertBefore(navBtn, tweakerMount || anchor);
    updateNavButton();
    return true;
  }

  // ─── Modal ──────────────────────────────────────────────────────────
  var modal = null;

  function buildModal() {
    var m = document.createElement('div');
    m.id = 'insert-modal';
    m.className = 'insert-modal';
    m.setAttribute(CHROME_ATTR, '');
    m.hidden = true;

    var quickStartsHtml = STARTER_CHIPS.map(function (c, i) {
      return '<button type="button" class="insert-chip" data-chip-idx="' + i + '">' +
        escHtml(c.label) + '</button>';
    }).join('');

    var scopeChipsHtml = SCOPE_CHIPS.map(function (c) {
      return '<button type="button" class="insert-scope-chip" data-scope="' + c.key + '" aria-pressed="false">' +
        '<span class="insert-scope-chip-label">' + escHtml(c.label) + '</span>' +
        '<span class="insert-scope-chip-sub">' + escHtml(c.sub) + '</span>' +
        '</button>';
    }).join('');

    var tagOptions = ALL_TAGS.map(function (t) {
      var label = t.replace(/_/g, ' ').toLowerCase().replace(/\b./g, function (c) { return c.toUpperCase(); });
      return '<option value="' + t + '">' + label + '</option>';
    }).join('');

    // Redesigned single-panel layout (approved 2026-04-24, Q1–Q8 all Option A).
    // Empty-panel aesthetic, prompt-first, scope-selector, live timeline, demoted
    // quick-starts, 1-primary+2-fallbacks card grid, manual fallback as secondary link.
    m.innerHTML = [
      '<div class="insert-modal-backdrop"></div>',
      '<div class="insert-modal-panel insert-modal-panel--v2" role="dialog" aria-modal="true" aria-labelledby="insert-modal-title">',
      '  <button type="button" class="insert-modal-close" aria-label="Close"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>',
      '  <div class="insert-modal-header">',
      '    <div class="insert-modal-eyebrow" id="insert-modal-eyebrow">ADD EVENT</div>',
      '    <h3 class="insert-modal-title" id="insert-modal-title"></h3>',
      '  </div>',

           // ─── Timeline strip ─────────────────────────────────────
      '  <div class="insert-timeline" id="insert-timeline" aria-label="Gap timeline">',
      '    <div class="insert-timeline-seg insert-timeline-seg--prev" id="insert-timeline-prev">',
      '      <span class="insert-timeline-tag">Prev</span>',
      '      <span class="insert-timeline-title" id="insert-timeline-prev-title"></span>',
      '      <span class="insert-timeline-time" id="insert-timeline-prev-time"></span>',
      '    </div>',
      '    <div class="insert-timeline-seg insert-timeline-seg--gap" id="insert-timeline-gap">',
      '      <span class="insert-timeline-gap-text" id="insert-timeline-gap-text"></span>',
      '    </div>',
      '    <div class="insert-timeline-seg insert-timeline-seg--next" id="insert-timeline-next">',
      '      <span class="insert-timeline-tag">Next</span>',
      '      <span class="insert-timeline-title" id="insert-timeline-next-title"></span>',
      '      <span class="insert-timeline-time" id="insert-timeline-next-time"></span>',
      '    </div>',
      '  </div>',

           // ─── 1x2 split: LEFT criteria / RIGHT results ───────────
      '  <div class="insert-split" id="insert-split">',
      '    <section class="insert-criteria" aria-label="Search criteria">',
      '      <div class="insert-criteria-label">Tell the AI what you want</div>',
      '      <div class="insert-prompt-row">',
      '        <textarea id="insert-chat-input" class="insert-prompt-input" rows="3" placeholder="A specific place like \u201cCheesecake Factory\u201d, or a type like \u201cquiet halal dinner\u201d." autocomplete="off" spellcheck="false"></textarea>',
      '        <button type="button" class="insert-prompt-send" id="insert-chat-send" title="Send (Enter)" aria-label="Ask AI">',
      '          <i class="fa-solid fa-paper-plane" aria-hidden="true"></i>',
      '        </button>',
      '      </div>',
      '      <div class="insert-scope-row" role="radiogroup" aria-label="Search radius">',
      '        <span class="insert-scope-label">Radius</span>',
      '        <div class="insert-scope-chips" id="insert-scope-chips">' + scopeChipsHtml + '</div>',
      '      </div>',
      '      <details class="insert-quickstarts" id="insert-quickstarts">',
      '        <summary><span class="insert-quickstarts-label">Quick starts</span></summary>',
      '        <div class="insert-quickstarts-chips">' + quickStartsHtml + '</div>',
      '      </details>',
      '    </section>',

      '    <section class="insert-results insert-results--v2" aria-label="Candidates" id="insert-results-pane">',
      '      <div class="insert-criteria-label">Results</div>',
      '      <div class="insert-chat-history" id="insert-chat-history" aria-live="polite"></div>',
      '      <div class="insert-results-cards" id="insert-results-cards" hidden></div>',
      '      <div class="insert-results-placeholder" id="insert-results-placeholder">',
      '        <i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i>',
      '        <span>Ask the AI, then pick a result.</span>',
      '      </div>',
      '    </section>',
      '  </div>',

           // ─── Time & Details form (full width, below split) ──────
      '    <div class="insert-picked-form" id="insert-picked-form" hidden>',
      '        <div class="insert-picked-head">',
      '          <span class="insert-picked-label">Time &amp; details</span>',
      '          <span class="insert-picked-hint">Edit start, duration, or notes before saving.</span>',
      '        </div>',
      '        <div class="insert-field-row">',
      '          <div class="insert-field">',
      '            <label class="insert-field-label" for="insert-start">Starts at</label>',
      '            <select id="insert-start" class="insert-field-input"></select>',
      '          </div>',
      '          <div class="insert-field">',
      '            <label class="insert-field-label" for="insert-duration">Duration</label>',
      '            <select id="insert-duration" class="insert-field-input"></select>',
      '          </div>',
      '        </div>',
      '        <div class="insert-live-readout" id="insert-live-readout" aria-live="polite"></div>',
      '        <div class="insert-field">',
      '          <label class="insert-field-label" for="insert-notes">Notes <span class="insert-field-hint">(optional)</span></label>',
      '          <textarea id="insert-notes" class="insert-field-input" rows="2" placeholder="Reservation, heads-up, context\u2026" autocomplete="off" autocorrect="off" spellcheck="false" data-1p-ignore data-lpignore="true"></textarea>',
      '        </div>',
      '      </div>',
             // ─── Manual form (hidden by default) ──────────────
      '      <div class="insert-manual-form" id="insert-manual-form" hidden>',
      '        <div class="insert-manual-head">',
      '          <span class="insert-manual-label">Manual entry</span>',
      '          <button type="button" class="insert-manual-back" id="insert-manual-back"><i class="fa-solid fa-arrow-left" aria-hidden="true"></i>Back to AI</button>',
      '        </div>',
      '        <div class="insert-field">',
      '          <label class="insert-field-label" for="insert-title">Title</label>',
      '          <input type="text" id="insert-title" class="insert-field-input" placeholder="e.g., Coffee at Hidden Grounds" autocomplete="off" spellcheck="false" />',
      '        </div>',
      '        <div class="insert-field-row">',
      '          <div class="insert-field">',
      '            <label class="insert-field-label" for="insert-tag">Type</label>',
      '            <select id="insert-tag" class="insert-field-input">' + tagOptions + '</select>',
      '          </div>',
      '          <div class="insert-field">',
      '            <label class="insert-field-label" for="insert-duration-manual">Duration</label>',
      '            <select id="insert-duration-manual" class="insert-field-input">',
      '              <option value="15">15 min</option>',
      '              <option value="30">30 min</option>',
      '              <option value="45">45 min</option>',
      '              <option value="60" selected>60 min</option>',
      '              <option value="75">75 min</option>',
      '              <option value="90">90 min</option>',
      '              <option value="120">2 hr</option>',
      '              <option value="180">3 hr</option>',
      '            </select>',
      '          </div>',
      '        </div>',
      '        <div class="insert-field">',
      '          <label class="insert-field-label" for="insert-start-manual">Starts at</label>',
      '          <select id="insert-start-manual" class="insert-field-input"></select>',
      '        </div>',
      '        <details class="insert-details" id="insert-destination-details">',
      '          <summary>Destination details <span class="insert-destination-state" id="insert-destination-state"></span></summary>',
      '          <div class="insert-details-body">',
      '            <div class="insert-field">',
      '              <label class="insert-field-label" for="insert-venue">Venue (full address)</label>',
      '              <input type="text" id="insert-venue" class="insert-field-input" placeholder="123 Main St, City, ST 00000" autocomplete="off" />',
      '            </div>',
      '            <div class="insert-field-row">',
      '              <div class="insert-field">',
      '                <label class="insert-field-label" for="insert-phone">Phone</label>',
      '                <input type="text" id="insert-phone" class="insert-field-input" placeholder="(555) 555-1234" autocomplete="off" />',
      '              </div>',
      '              <div class="insert-field">',
      '                <label class="insert-field-label" for="insert-rating">Rating</label>',
      '                <input type="number" id="insert-rating" class="insert-field-input" min="1" max="5" step="0.1" placeholder="4.5" />',
      '              </div>',
      '            </div>',
      '            <div class="insert-field">',
      '              <label class="insert-field-label" for="insert-notes-manual">Notes <span class="insert-field-hint">(optional)</span></label>',
      '              <textarea id="insert-notes-manual" class="insert-field-input" rows="2" placeholder="Reservation, heads-up, context\u2026" autocomplete="off" autocorrect="off" spellcheck="false" data-1p-ignore data-lpignore="true"></textarea>',
      '            </div>',
      '          </div>',
      '        </details>',
      '      </div>',
      '  <div class="insert-modal-error" id="insert-modal-error" hidden></div>',
      '  <div class="insert-modal-actions">',
      '    <a href="#" class="insert-manual-secondary" id="insert-manual-toggle" role="button" tabindex="0">Skip the AI \u2014 add manually</a>',
      '    <span class="insert-modal-actions-spacer"></span>',
      '    <button type="button" class="insert-modal-btn insert-modal-btn--ghost" data-action="cancel">Cancel</button>',
      '    <button type="button" class="insert-modal-btn insert-modal-btn--secondary" data-action="save-exit" disabled>Save &amp; exit</button>',
      '    <button type="button" class="insert-modal-btn insert-modal-btn--primary" data-action="save" disabled>Save</button>',
      '  </div>',
      '</div>',
    ].join('\n');
    document.body.appendChild(m);

    // Event wiring
    m.querySelector('.insert-modal-backdrop').addEventListener('click', closeInsertModal);
    m.querySelector('.insert-modal-close').addEventListener('click', closeInsertModal);
    m.querySelector('[data-action="cancel"]').addEventListener('click', closeInsertModal);
    m.querySelector('[data-action="save"]').addEventListener('click', function () { submitInsert(false); });
    m.querySelector('[data-action="save-exit"]').addEventListener('click', function () { submitInsert(true); });

    // Chips — fill input, don't send
    m.querySelectorAll('.insert-chip').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var i = Number(btn.getAttribute('data-chip-idx'));
        var chip = STARTER_CHIPS[i];
        if (!chip) return;
        var input = m.querySelector('#insert-chat-input');
        input.value = chip.text;
        input.focus();
      });
    });

    // Chat input — Enter to send, Shift+Enter newline
    var input = m.querySelector('#insert-chat-input');
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        sendAiTurn();
      }
    });
    m.querySelector('#insert-chat-send').addEventListener('click', sendAiTurn);

    // Scope radius chips — single-select, stores on state.scopeRadius
    m.querySelectorAll('.insert-scope-chip').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var key = btn.getAttribute('data-scope');
        selectScope(key);
      });
    });

    // Manual mode (now a secondary link in the footer)
    m.querySelector('#insert-manual-toggle').addEventListener('click', function (e) {
      e.preventDefault();
      switchToManual();
    });
    m.querySelector('#insert-manual-back').addEventListener('click', function () {
      switchToAI();
    });

    // Time / duration pickers
    m.querySelector('#insert-start').addEventListener('change', updateReadout);
    m.querySelector('#insert-duration').addEventListener('change', updateReadout);
    m.querySelector('#insert-start-manual').addEventListener('change', function () { /* no-op for manual */ });
    m.querySelector('#insert-tag').addEventListener('change', onTagChange);

    document.addEventListener('keydown', onModalKey);
    return m;
  }

  function onModalKey(e) {
    if (!modal || modal.hidden) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      closeInsertModal();
    }
  }

  // ─── Scope helpers ──────────────────────────────────────────────────
  function selectScope(key) {
    if (!modal) return;
    var match = SCOPE_CHIPS.find(function (c) { return c.key === key; });
    if (!match) return;
    state.scopeRadius = match.key;
    modal.querySelectorAll('.insert-scope-chip').forEach(function (b) {
      var isOn = b.getAttribute('data-scope') === match.key;
      b.classList.toggle('is-selected', isOn);
      b.setAttribute('aria-pressed', isOn ? 'true' : 'false');
    });
  }

  function renderTimeline(ctx) {
    if (!modal) return;
    var gapMin = ctx.winEnd - ctx.winStart;
    modal.querySelector('#insert-timeline-prev-title').textContent = ctx.prevTitle || '\u2014';
    modal.querySelector('#insert-timeline-prev-time').textContent = ctx.prevTitle ? ('ends ' + formatMin(ctx.winStart)) : 'day start';
    modal.querySelector('#insert-timeline-next-title').textContent = ctx.nextTitle || '\u2014';
    modal.querySelector('#insert-timeline-next-time').textContent = ctx.nextTitle ? ('starts ' + formatMin(ctx.winEnd)) : 'day end';
    modal.querySelector('#insert-timeline-gap-text').textContent = formatDuration(gapMin) + ' available';
  }

  // ─── Open / close ───────────────────────────────────────────────────
  function openInsertModal(ctx) {
    if (!modal) modal = buildModal();
    state.modalCtx = ctx;
    state.modalOpen = true;
    state.history = [];
    state.currentCandidates = [];
    state.pickedIdx = null;
    state.manualMode = false;
    state.lastIntent = null;
    state.lastSearchPrompt = null;
    cancelAiInflight();

    modal.querySelector('#insert-modal-eyebrow').textContent =
      'ADD EVENT \u00b7 DAY ' + (ctx.dayIdx + 1);

    var titleText;
    if (ctx.prevTitle && ctx.nextTitle) titleText = 'Between ' + ctx.prevTitle + ' and ' + ctx.nextTitle;
    else if (ctx.nextTitle) titleText = 'Before ' + ctx.nextTitle;
    else if (ctx.prevTitle) titleText = 'After ' + ctx.prevTitle;
    else titleText = 'New event';
    modal.querySelector('#insert-modal-title').textContent = titleText;

    // Timeline strip (prev → gap → next)
    renderTimeline(ctx);

    // Smart scope default per gap size
    var gapMin = ctx.winEnd - ctx.winStart;
    selectScope(defaultScopeForGap(gapMin));

    // Reset views
    modal.querySelector('#insert-chat-history').innerHTML = '';
    modal.querySelector('#insert-chat-input').value = '';
    modal.querySelector('#insert-results-cards').hidden = true;
    modal.querySelector('#insert-results-cards').innerHTML = '';
    modal.querySelector('#insert-picked-form').hidden = true;
    modal.querySelector('#insert-manual-form').hidden = true;
    var ph = modal.querySelector('#insert-results-placeholder');
    if (ph) ph.hidden = false;
    var qs = modal.querySelector('#insert-quickstarts');
    if (qs) qs.removeAttribute('open');
    modal.classList.remove('is-manual', 'is-pending');
    setError(null);

    populateStartOptions('#insert-start', ctx.winStart, ctx.winEnd);
    populateDurationOptions('#insert-duration', ctx.winStart, ctx.winEnd, Number(modal.querySelector('#insert-start').value));
    populateStartOptions('#insert-start-manual', ctx.winStart, ctx.winEnd);
    // Reset manual fields
    modal.querySelector('#insert-title').value = '';
    modal.querySelector('#insert-venue').value = '';
    modal.querySelector('#insert-phone').value = '';
    modal.querySelector('#insert-rating').value = '';
    modal.querySelector('#insert-notes').value = '';
    modal.querySelector('#insert-notes-manual').value = '';
    modal.querySelector('#insert-tag').value = 'DINING';
    modal.querySelector('#insert-duration-manual').value = String(DEFAULT_DURATION_MIN);

    updateSaveButtons();
    onTagChange();

    modal.hidden = false;
    setTimeout(function () {
      var ta = modal.querySelector('#insert-chat-input');
      if (ta) ta.focus();
    }, 40);
  }

  function closeInsertModal() {
    if (!modal) return;
    cancelAiInflight();
    modal.hidden = true;
    state.modalCtx = null;
    state.modalOpen = false;
    state.currentCandidates = [];
    state.pickedIdx = null;
    state.manualMode = false;
    setError(null);
  }

  function setError(msg) {
    if (!modal) return;
    var el = modal.querySelector('#insert-modal-error');
    if (!el) return;
    if (msg) {
      el.textContent = msg;
      el.hidden = false;
    } else {
      el.textContent = '';
      el.hidden = true;
    }
  }

  // ─── Time / duration pickers ────────────────────────────────────────
  function populateStartOptions(selector, winStart, winEnd) {
    var sel = modal.querySelector(selector);
    sel.innerHTML = '';
    var maxStart = winEnd - MIN_DURATION_MIN;
    for (var t = winStart; t <= maxStart; t += 5) {
      var opt = document.createElement('option');
      opt.value = String(t);
      opt.textContent = formatMin(t);
      sel.appendChild(opt);
    }
    var defaultStart = Math.min(maxStart, winStart + BUFFER_AFTER_PREV_MIN);
    defaultStart = Math.max(winStart, defaultStart - (defaultStart % 5));
    sel.value = String(defaultStart);
  }

  function populateDurationOptions(selector, winStart, winEnd, startMin) {
    var sel = modal.querySelector(selector);
    var maxDur = winEnd - startMin;
    var optsArr = [15, 30, 45, 60, 75, 90, 120, 180];
    sel.innerHTML = '';
    var chosen = null;
    optsArr.forEach(function (d) {
      if (d > maxDur) return;
      var opt = document.createElement('option');
      opt.value = String(d);
      opt.textContent = d < 60 ? d + ' min' : (d % 60 === 0 ? (d / 60) + ' hr' : formatDuration(d));
      sel.appendChild(opt);
      if (d === DEFAULT_DURATION_MIN) chosen = String(d);
    });
    if (chosen == null && sel.options.length) chosen = sel.options[sel.options.length - 1].value;
    if (chosen != null) sel.value = chosen;
  }

  function updateReadout() {
    if (!modal || !state.modalCtx) return;
    var startSel = modal.querySelector('#insert-start');
    var durSel = modal.querySelector('#insert-duration');
    var readout = modal.querySelector('#insert-live-readout');
    var startMin = Number(startSel.value);
    if (!Number.isFinite(startMin)) return;
    var maxDur = state.modalCtx.winEnd - startMin;
    Array.prototype.forEach.call(durSel.options, function (o) {
      o.disabled = Number(o.value) > maxDur;
    });
    if (Number(durSel.value) > maxDur) {
      durSel.value = String(maxDur >= MIN_DURATION_MIN ? maxDur : MIN_DURATION_MIN);
    }
    var dur = Number(durSel.value);
    if (!readout) return;
    var endMin = startMin + dur;
    var bufferAfter = state.modalCtx.winEnd - endMin;
    var bufferLabel = bufferAfter > 0
      ? formatDuration(bufferAfter) + ' buffer before next'
      : 'tight \u2014 ends exactly when next begins';
    readout.innerHTML =
      '<span class="insert-live-strong">Your event: ' + escHtml(formatMin(startMin)) +
      ' \u2192 ' + escHtml(formatMin(endMin)) + '</span>' +
      '<span class="insert-live-sub">' + escHtml(bufferLabel) + '</span>';
  }

  function onTagChange() {
    if (!modal) return;
    var tag = modal.querySelector('#insert-tag').value;
    var details = modal.querySelector('#insert-destination-details');
    var stateEl = modal.querySelector('#insert-destination-state');
    if (isDestinationTag(tag)) {
      details.setAttribute('open', '');
      stateEl.textContent = '\u00b7 required';
      stateEl.classList.add('is-required');
    } else {
      stateEl.textContent = '\u00b7 optional';
      stateEl.classList.remove('is-required');
    }
  }

  // ─── Manual mode ────────────────────────────────────────────────────
  function switchToManual() {
    state.manualMode = true;
    state.pickedIdx = null;
    modal.classList.add('is-manual');
    modal.querySelector('#insert-results-cards').hidden = true;
    modal.querySelector('#insert-picked-form').hidden = true;
    modal.querySelector('#insert-manual-form').hidden = false;
    updateSaveButtons();
    setTimeout(function () {
      var t = modal.querySelector('#insert-title');
      if (t) t.focus();
    }, 40);
  }

  function switchToAI() {
    state.manualMode = false;
    modal.classList.remove('is-manual');
    modal.querySelector('#insert-manual-form').hidden = true;
    var hasCards = state.currentCandidates && state.currentCandidates.length;
    modal.querySelector('#insert-results-cards').hidden = !hasCards;
    modal.querySelector('#insert-picked-form').hidden = state.pickedIdx == null;
    updateSaveButtons();
  }

  // ─── AI turn ────────────────────────────────────────────────────────
  function cancelAiInflight() {
    if (state.aiAbortCtrl) {
      try { state.aiAbortCtrl.abort(); } catch (_) {}
      state.aiAbortCtrl = null;
    }
    if (state.aiStatusTimer) {
      clearTimeout(state.aiStatusTimer);
      state.aiStatusTimer = null;
    }
    state.inflight = false;
    modal && modal.classList.remove('is-loading');
  }

  function startStatusCycle(turnEl) {
    if (state.aiStatusTimer) clearTimeout(state.aiStatusTimer);
    var i = 0;
    function tick() {
      var el = turnEl.querySelector('.insert-chat-status');
      if (!el) return;
      i = Math.min(i + 1, PROGRESS_STEPS.length - 1);
      el.classList.add('is-fade');
      setTimeout(function () {
        el.textContent = PROGRESS_STEPS[i];
        el.classList.remove('is-fade');
      }, 180);
      var next = (i === PROGRESS_STEPS.length - 1) ? 9000 : 2600;
      state.aiStatusTimer = setTimeout(tick, next);
    }
    state.aiStatusTimer = setTimeout(tick, 2600);
  }

  function sendAiTurn(opts) {
    if (state.inflight || !state.modalCtx) return;
    opts = opts || {};
    var input = modal.querySelector('#insert-chat-input');
    var message;
    if (opts.retryPrompt) {
      message = opts.retryPrompt;
    } else {
      message = (input.value || '').trim();
      if (!message) {
        input.focus();
        return;
      }
      input.value = '';
    }
    state.lastSearchPrompt = message;
    setError(null);

    var turnId = 'turn-' + Date.now();
    pushUserBubble(opts.retryPrompt ? (message + ' (retry with expanded radius)') : message);
    var aiTurn = pushAiLoadingBubble(turnId);

    var cardsHost = modal.querySelector('#insert-results-cards');
    cardsHost.hidden = false;
    cardsHost.innerHTML = skeletonCardsHtml();
    var ph2 = modal.querySelector('#insert-results-placeholder');
    if (ph2) ph2.hidden = true;
    modal.querySelector('#insert-picked-form').hidden = true;
    state.pickedIdx = null;
    state.currentCandidates = [];
    updateSaveButtons();

    cancelAiInflight();
    state.aiAbortCtrl = new AbortController();
    state.inflight = true;
    modal.classList.add('is-loading');
    startStatusCycle(aiTurn);

    var API_BASE = window.__API_BASE || '';
    var slug = (window.__tripData && window.__tripData.slug) ||
      ((window.__tripContext && window.__tripContext.slug) || '');
    var ctx = state.modalCtx;

    // Two-step pipeline: classify intent (Haiku) → route to sub-prompt (Sonnet).
    var classifyBody = {
      prompt: message,
      tripSlug: slug,
      dayIndex: ctx.dayIdx,
      prevVenue: ctx.prevTitle || null,
      nextVenue: ctx.nextTitle || null,
    };

    fetch(API_BASE + '/api/classify-insert-intent', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(classifyBody),
      signal: state.aiAbortCtrl.signal,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error(data.error || 'intent classification failed');
        var intent = {
          mode: data.mode || 'category_search',
          vendorName: data.vendorName || null,
          categoryHint: data.categoryHint || null,
          confidence: Number.isFinite(data.confidence) ? data.confidence : 0.5,
        };
        state.lastIntent = intent;
        return runSuggestCall(intent, message, aiTurn);
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        console.warn('[SUGGEST-INSERT]', err);
        cardsHost.innerHTML = '';
        cardsHost.hidden = true;
        renderAiError(aiTurn, err.message || String(err));
      })
      .finally(function () {
        state.inflight = false;
        modal.classList.remove('is-loading');
        if (state.aiStatusTimer) {
          clearTimeout(state.aiStatusTimer);
          state.aiStatusTimer = null;
        }
      });
  }

  function runSuggestCall(intent, message, aiTurn) {
    var API_BASE = window.__API_BASE || '';
    var slug = (window.__tripData && window.__tripData.slug) ||
      ((window.__tripContext && window.__tripContext.slug) || '');
    var ctx = state.modalCtx;
    var cardsHost = modal.querySelector('#insert-results-cards');
    var body = {
      tripSlug: slug,
      dayIndex: ctx.dayIdx,
      insertEventIndex: ctx.insertEventIdx,
      window: { start: formatMin(ctx.winStart), end: formatMin(ctx.winEnd) },
      mode: intent.mode,
      vendorName: intent.vendorName,
      categoryHint: intent.categoryHint,
      scopeRadius: state.scopeRadius,
      constraints: { notes: message },
      message: message,
    };
    return fetch(API_BASE + '/api/suggest-insert', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: state.aiAbortCtrl && state.aiAbortCtrl.signal,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error(data.error || 'AI suggestion failed');
        var cands = Array.isArray(data.candidates) ? data.candidates : [];
        state.currentCandidates = cands;
        renderCandidateCards(cands);
        finalizeAiTurn(aiTurn, cands.length, data.windowSummary, intent, data.mode);
      });
  }

  function pushUserBubble(text) {
    var host = modal.querySelector('#insert-chat-history');
    var el = document.createElement('div');
    el.className = 'insert-chat-turn insert-chat-turn--user';
    el.innerHTML =
      '<div class="insert-chat-who">You</div>' +
      '<div class="insert-chat-bubble">' + escHtml(text) + '</div>';
    host.appendChild(el);
    host.scrollTop = host.scrollHeight;
    return el;
  }

  function pushAiLoadingBubble(turnId) {
    var host = modal.querySelector('#insert-chat-history');
    var el = document.createElement('div');
    el.className = 'insert-chat-turn insert-chat-turn--ai is-loading';
    el.setAttribute('data-turn-id', turnId);
    el.innerHTML =
      '<div class="insert-chat-who"><i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i>AI</div>' +
      '<div class="insert-chat-bubble">' +
      '  <div class="insert-chat-progress" aria-hidden="true"><div class="insert-chat-progress-bar"></div></div>' +
      '  <div class="insert-chat-status">' + escHtml(PROGRESS_STEPS[0]) + '</div>' +
      '</div>';
    host.appendChild(el);
    host.scrollTop = host.scrollHeight;
    return el;
  }

  function finalizeAiTurn(turnEl, count, summary, intent, mode) {
    turnEl.classList.remove('is-loading');
    var bubble = turnEl.querySelector('.insert-chat-bubble');
    var body = '';
    var modeLabel = '';
    if (mode === 'exact_vendor' && intent && intent.vendorName) {
      modeLabel = 'Exact match: ' + intent.vendorName;
    } else if (mode === 'chain_locations' && intent && intent.vendorName) {
      modeLabel = 'Locations of: ' + intent.vendorName;
    } else if (mode === 'category_search') {
      modeLabel = 'Category search';
    }
    if (count > 0) {
      body += '<div class="insert-chat-result-head"><i class="fa-solid fa-check" aria-hidden="true"></i>' +
        escHtml(count) + ' option' + (count === 1 ? '' : 's') +
        (modeLabel ? ' \u00b7 ' + escHtml(modeLabel) : '') + '</div>';
    } else {
      body += '<div class="insert-chat-result-head insert-chat-result-head--empty"><i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i>No candidates matched' +
        (modeLabel ? ' \u00b7 ' + escHtml(modeLabel) : '') + '</div>';
    }
    if (summary) {
      body += '<div class="insert-chat-result-sub">' + escHtml(summary) + '</div>';
    }
    bubble.innerHTML = body;
  }

  function renderAiError(turnEl, msg) {
    turnEl.classList.remove('is-loading');
    turnEl.classList.add('is-error');
    var bubble = turnEl.querySelector('.insert-chat-bubble');
    bubble.innerHTML =
      '<div class="insert-chat-result-head insert-chat-result-head--error"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>Couldn\u2019t get suggestions</div>' +
      '<div class="insert-chat-result-sub">' + escHtml(msg) + '</div>';
  }

  function skeletonCardsHtml() {
    var card =
      '<div class="insert-card-skel" aria-hidden="true">' +
      '  <span class="insert-card-skel-line insert-card-skel-line--title"></span>' +
      '  <span class="insert-card-skel-line insert-card-skel-line--meta"></span>' +
      '  <span class="insert-card-skel-line insert-card-skel-line--desc"></span>' +
      '</div>';
    return card + card + card;
  }

  function renderCandidateCards(cands) {
    var host = modal.querySelector('#insert-results-cards');
    host.innerHTML = '';
    if (!cands.length) {
      host.innerHTML = '<div class="insert-results-empty-inline">No candidates this time. Try a different prompt, widen the radius, or use \u201cSkip the AI\u2014 add manually\u201d below.</div>';
      return;
    }

    // Exact-vendor not-found case: the primary card carries isOutOfRange=true.
    // Show a one-click "Expand radius" retry button above the card grid.
    var primaryOutOfRange = cands.find(function (c) { return c.isPrimary && c.isOutOfRange; });
    if (primaryOutOfRange) {
      var banner = document.createElement('div');
      banner.className = 'insert-notfound-banner';
      banner.innerHTML =
        '<div class="insert-notfound-text">' +
        '  <i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>' +
        '  <span><strong>' + escHtml(primaryOutOfRange.event || 'That venue') + '</strong> isn\u2019t reachable within the current radius.</span>' +
        '</div>' +
        '<button type="button" class="insert-notfound-expand" id="insert-notfound-expand">' +
        '  <i class="fa-solid fa-arrows-left-right-to-line" aria-hidden="true"></i> Expand radius and retry' +
        '</button>';
      host.appendChild(banner);
      var expandBtn = banner.querySelector('#insert-notfound-expand');
      if (expandBtn) {
        expandBtn.addEventListener('click', function () {
          selectScope('expand');
          if (state.lastSearchPrompt) {
            sendAiTurn({ retryPrompt: state.lastSearchPrompt });
          }
        });
      }
    }

    cands.forEach(function (c, idx) {
      var card = document.createElement('div');
      card.className = 'insert-card';
      if (c.isPrimary) card.classList.add('insert-card--primary');
      if (c.isOutOfRange) card.classList.add('insert-card--outofrange');
      card.setAttribute('data-cand-idx', String(idx));
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');

      var metaBits = [];
      if (c.category) metaBits.push('<span class="insert-card-chip"><i class="fa-solid fa-tag" aria-hidden="true"></i>' + escHtml(c.category) + '</span>');
      if (Number.isFinite(c.rating)) metaBits.push('<span class="insert-card-chip"><i class="fa-solid fa-star" aria-hidden="true"></i>' + escHtml(String(c.rating)) + '</span>');
      if (Number.isFinite(c.driveMinutes)) metaBits.push('<span class="insert-card-chip"><i class="fa-solid fa-car" aria-hidden="true"></i>' + escHtml(String(c.driveMinutes)) + ' min drive</span>');
      if (Number.isFinite(c.duration_min)) metaBits.push('<span class="insert-card-chip"><i class="fa-solid fa-hourglass-half" aria-hidden="true"></i>' + escHtml(String(c.duration_min)) + ' min stay</span>');

      var primaryBadge = c.isPrimary ? '<span class="insert-card-primary-badge"><i class="fa-solid fa-star" aria-hidden="true"></i>Primary match</span>' : '';
      var outOfRangeBadge = c.isOutOfRange ? '<span class="insert-card-oor-badge">Out of range</span>' : '';

      card.innerHTML =
        '<div class="insert-card-head">' +
        '  <h4 class="insert-card-title">' + escHtml(c.event || '(untitled)') + primaryBadge + outOfRangeBadge + '</h4>' +
        '  <span class="insert-card-time"><i class="fa-solid fa-clock" aria-hidden="true"></i>' + escHtml(c.suggestedStart || '') + '</span>' +
        '</div>' +
        (metaBits.length ? '<div class="insert-card-meta">' + metaBits.join('') + '</div>' : '') +
        (c.venue ? '<div class="insert-card-venue"><i class="fa-solid fa-location-dot" aria-hidden="true"></i>' + escHtml(c.venue) + '</div>' : '') +
        (c.phone ? '<div class="insert-card-phone"><i class="fa-solid fa-phone" aria-hidden="true"></i>' + escHtml(c.phone) + '</div>' : '') +
        (c.rationale ? '<p class="insert-card-rationale">' + escHtml(c.rationale) + '</p>' : '') +
        '<button type="button" class="insert-card-use" data-card-use="' + idx + '">' +
        '  <i class="fa-solid fa-circle-check" aria-hidden="true"></i>' +
        '  <span>Use this</span>' +
        '</button>';

      var useBtn = card.querySelector('.insert-card-use');
      if (useBtn) {
        useBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          pickCandidate(idx);
        });
      }
      card.addEventListener('click', function (e) {
        if (e.target && e.target.closest && e.target.closest('.insert-card-use')) return;
        pickCandidate(idx);
      });
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          pickCandidate(idx);
        }
      });
      host.appendChild(card);
    });

    // Hide the placeholder when cards are present.
    var ph = modal.querySelector('#insert-results-placeholder');
    if (ph) ph.hidden = cands.length > 0;
  }

  function pickCandidate(idx) {
    if (!state.currentCandidates[idx]) return;
    state.pickedIdx = idx;
    // Re-mark selected state on cards
    modal.querySelectorAll('.insert-card').forEach(function (el, i) {
      el.classList.toggle('is-picked', i === idx);
    });
    var cand = state.currentCandidates[idx];

    // Pre-fill time/duration
    var ctx = state.modalCtx;
    var startMin = parseTimeToMin(cand.suggestedStart);
    if (startMin == null || startMin < ctx.winStart) startMin = ctx.winStart + BUFFER_AFTER_PREV_MIN;
    startMin = Math.max(ctx.winStart, Math.min(ctx.winEnd - MIN_DURATION_MIN, startMin - (startMin % 5)));
    var startSel = modal.querySelector('#insert-start');
    populateStartOptions('#insert-start', ctx.winStart, ctx.winEnd);
    if (Array.prototype.some.call(startSel.options, function (o) { return Number(o.value) === startMin; })) {
      startSel.value = String(startMin);
    }
    populateDurationOptions('#insert-duration', ctx.winStart, ctx.winEnd, Number(startSel.value));
    var dur = Number(cand.duration_min);
    if (Number.isFinite(dur)) {
      var durSel = modal.querySelector('#insert-duration');
      if (Array.prototype.some.call(durSel.options, function (o) { return Number(o.value) === dur; })) {
        durSel.value = String(dur);
      }
    }
    updateReadout();

    modal.querySelector('#insert-notes').value = '';
    modal.querySelector('#insert-picked-form').hidden = false;
    updateSaveButtons();
    // Smooth-scroll the form into view on the right pane
    var form = modal.querySelector('#insert-picked-form');
    if (form && typeof form.scrollIntoView === 'function') {
      form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function updateSaveButtons() {
    if (!modal) return;
    var saveBtn = modal.querySelector('[data-action="save"]');
    var saveExitBtn = modal.querySelector('[data-action="save-exit"]');
    var ready = state.manualMode || state.pickedIdx != null;
    saveBtn.disabled = !ready || state.saving;
    saveExitBtn.disabled = !ready || state.saving;
  }

  // ─── Save ───────────────────────────────────────────────────────────
  function submitInsert(alsoExit) {
    if (state.saving || !state.modalCtx) return;

    var ctx = state.modalCtx;
    var newEvent;
    if (state.manualMode) {
      newEvent = readManualForm();
      if (!newEvent) return;
    } else {
      if (state.pickedIdx == null || !state.currentCandidates[state.pickedIdx]) {
        setError('Pick a candidate on the right first.');
        return;
      }
      newEvent = buildEventFromPick(state.currentCandidates[state.pickedIdx]);
      if (!newEvent) return;
    }

    var API_BASE = window.__API_BASE || '';
    var slug = (window.__tripData && window.__tripData.slug) ||
      ((window.__tripContext && window.__tripContext.slug) || '');
    if (!slug) {
      setError('Trip slug unavailable.');
      return;
    }

    state.saving = true;
    modal.classList.add('is-pending');
    updateSaveButtons();

    var saveBody = {
      tripSlug: slug,
      dayIndex: ctx.dayIdx,
      eventIndex: ctx.insertEventIdx,
      event: newEvent,
      meta: {
        intent_mode: state.manualMode ? 'manual' : (state.lastIntent && state.lastIntent.mode) || null,
        scope_radius: state.manualMode ? null : state.scopeRadius,
      },
    };

    fetch(API_BASE + '/api/insert-event', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(saveBody),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          var msg = data.error || 'Insert failed';
          if (Array.isArray(data.errors) && data.errors.length) {
            msg += ' \u2014 ' + data.errors.map(function (e) { return e.reason || e.field || ''; }).filter(Boolean).join('; ');
          }
          throw new Error(msg);
        }
        closeInsertModal();
        var neighborParts = [];
        if (ctx.prevTitle) neighborParts.push(ctx.prevTitle);
        if (ctx.nextTitle) neighborParts.push(ctx.nextTitle);
        var toastMsg = neighborParts.length === 2
          ? 'Added "' + newEvent.event + '" between ' + neighborParts[0] + ' and ' + neighborParts[1] + '.'
          : 'Added "' + newEvent.event + '" to day ' + (ctx.dayIdx + 1) + '.';
        if (window.notify && typeof window.notify.success === 'function') {
          window.notify.success(toastMsg);
        }
        if (typeof window.__refreshItinerary === 'function') {
          window.__refreshItinerary({ preserveState: true }).then(function () {
            if (state.active) renderRailsForAllDays();
            if (alsoExit) deactivate({ silent: true });
          });
        } else if (alsoExit) {
          deactivate({ silent: true });
        }
      })
      .catch(function (err) {
        console.warn('[INSERT-EVENT]', err);
        setError(err.message || String(err));
        if (window.notify && typeof window.notify.error === 'function') {
          window.notify.error('Couldn\u2019t add: ' + (err.message || String(err)));
        }
      })
      .finally(function () {
        state.saving = false;
        if (modal) modal.classList.remove('is-pending');
        updateSaveButtons();
      });
  }

  function buildEventFromPick(cand) {
    var ctx = state.modalCtx;
    var startMin = Number(modal.querySelector('#insert-start').value);
    var dur = Number(modal.querySelector('#insert-duration').value);
    if (!Number.isFinite(startMin) || !Number.isFinite(dur) || dur < MIN_DURATION_MIN) {
      setError('Pick a valid start time and duration.');
      return null;
    }
    if (startMin + dur > ctx.winEnd) {
      setError('Duration extends past the available window.');
      return null;
    }
    var ev = {
      time: formatMin(startMin),
      event: cand.event,
      tag: String(cand.tag || '').toUpperCase(),
      duration_min: dur,
    };
    if (cand.category) ev.category = cand.category;
    if (cand.venue) ev.venue = cand.venue;
    if (cand.phone) ev.phone = cand.phone;
    if (Number.isFinite(cand.rating)) ev.rating = cand.rating;
    // driveMinutes is passed through for server-side validation vs ORS;
    // the server strips it before persisting to trip.yaml.
    if (Number.isFinite(cand.driveMinutes)) ev.driveMinutes = cand.driveMinutes;
    var notes = (modal.querySelector('#insert-notes').value || '').trim();
    if (notes) ev.notes = notes;
    return ev;
  }

  function readManualForm() {
    var ctx = state.modalCtx;
    var title = modal.querySelector('#insert-title').value.trim();
    if (!title) {
      setError('Title is required.');
      modal.querySelector('#insert-title').focus();
      return null;
    }
    var tag = modal.querySelector('#insert-tag').value;
    var startMin = Number(modal.querySelector('#insert-start-manual').value);
    var dur = Number(modal.querySelector('#insert-duration-manual').value);
    if (!Number.isFinite(startMin) || !Number.isFinite(dur) || dur < MIN_DURATION_MIN) {
      setError('Pick a valid start time and duration.');
      return null;
    }
    if (startMin + dur > ctx.winEnd) {
      setError('Duration extends past the available window.');
      return null;
    }
    var venue = modal.querySelector('#insert-venue').value.trim();
    var phone = modal.querySelector('#insert-phone').value.trim();
    var ratingRaw = modal.querySelector('#insert-rating').value.trim();
    var rating = ratingRaw ? Number(ratingRaw) : null;
    var notes = modal.querySelector('#insert-notes-manual').value.trim();

    if (isDestinationTag(tag)) {
      var missing = [];
      if (!venue) missing.push('venue');
      if (!phone) missing.push('phone');
      if (tag !== 'ENGAGEMENT_HIGHLIGHT' && tag !== 'CELEBRATION') {
        if (rating == null || !Number.isFinite(rating) || rating < 1 || rating > 5) missing.push('rating');
      }
      if (missing.length) {
        setError('This type needs ' + missing.join(', ') + '. Either fill them in or pick a non-destination type (Travel / Appointment / Free).');
        modal.querySelector('#insert-destination-details').setAttribute('open', '');
        return null;
      }
    }

    var ev = {
      time: formatMin(startMin),
      event: title,
      tag: tag,
      duration_min: dur,
    };
    if (venue) ev.venue = venue;
    if (phone) ev.phone = phone;
    if (rating != null && Number.isFinite(rating)) ev.rating = rating;
    if (notes) ev.notes = notes;
    return ev;
  }

  // ─── Global listeners ───────────────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (!state.active) return;
    if (e.key === 'Escape' && !state.modalOpen) {
      e.preventDefault();
      deactivate();
    }
  });

  document.addEventListener('click', function (e) {
    if (!state.active || state.modalOpen) return;
    var target = e.target;
    if (!target || !target.closest) return;
    if (target.closest('[' + CHROME_ATTR + ']')) return;
    if (target.closest('.day-card')) return;
    if (target.closest('.nav')) return;
    deactivate();
  });

  // ─── Boot ───────────────────────────────────────────────────────────
  function waitForNav() {
    if (mountNavButton()) return;
    var obs = new MutationObserver(function () {
      if (mountNavButton()) obs.disconnect();
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForNav);
  } else {
    waitForNav();
  }

  // Debug / manual control
  window.__insertEvent = {
    toggle: toggle,
    activate: activate,
    deactivate: deactivate,
    isActive: function () { return state.active; },
  };
})();
