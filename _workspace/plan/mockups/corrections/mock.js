/* Behaviour for the PROPOSED correction panel mock. Sample data only; nothing here
   talks to a server. It exists so the design can be pressed, not just looked at. */
(function () {
  "use strict";

  var root = document.documentElement;
  var $ = function (id) { return document.getElementById(id); };
  var body = $("mk-body");
  var selbar = $("mk-selbar");
  var panel = $("mk-panel");
  var scrim = $("mk-scrim");
  var cardsEl = $("mk-cards");

  /* ---- Who is looking ---------------------------------------------------- */
  var PEOPLE = {
    "moderator-layla": { name: "Layla", label: "Moderator", canCorrect: true, admin: false },
    "moderator-omar": { name: "Omar", label: "Moderator", canCorrect: true, admin: false },
    admin: { name: "Asif", label: "Admin", canCorrect: true, admin: true },
    reader: { name: null, label: "Reader", canCorrect: false, admin: false },
  };
  function me() { return PEOPLE[root.getAttribute("data-role")]; }

  /* ---- Sample corrections (illustrative — not from any book in the library) - */
  var corrections = [
    {
      id: "c-omar", by: "Omar", status: "open", kind: "meaning", when: "2 hours ago",
      original: "the teacher said to him that patience in study is the first door",
      proposed: "the teacher wrote to him that patience in study is the first door",
      why: "The scanned source has <b>وَكَتَبَ</b> — “wrote”, not “said”. See p. 14, line 3.",
      ai: { verdict: "supports", label: "Supports this", conf: "High confidence",
        text: "The scanned source reads <b>وَكَتَبَ</b> (“wrote”) at exactly this point, and the extracted text agrees. The book reports the teacher’s words in the third person, and that stays the same.",
        checks: [["ok","Quote found once in the chapter"],["ok","Source span found · p. 14"],["ok","Narrator’s voice unchanged"],["ok","No overlapping correction"]] },
    },
    {
      id: "c-layla", by: "Layla", status: "open", kind: "other", when: "yesterday",
      original: "The student returned to his books that same evening and read until the lamp burned low.",
      proposed: "The student returned to his books that evening and read until the lamp burned low.",
      why: "“same” is not in the source; it reads as an addition.",
      ai: { verdict: "human", label: "Needs a person", conf: "Can’t confirm",
        text: "The scan is cut off at the foot of p. 15, so the source for this sentence isn’t on the page. The extracted text has no matching word for “same”, which points the same way, but it isn’t enough to be sure.",
        checks: [["ok","Quote found once in the chapter"],["warn","Source span not found in the scan"],["ok","No overlapping correction"]] },
    },
    {
      id: "c-acc", by: "Omar", status: "accepted", kind: "citation", when: "3 days ago", decidedBy: "Asif",
      original: "the quality every later virtue in the book is said to depend upon",
      proposed: "the quality every later virtue in the book is said to rest upon",
      why: "Closer to the wording of the source.",
      ai: { verdict: "supports", label: "Supports this", conf: "High confidence",
        text: "The source word means “rests on” rather than “depends on”. Small, safe change.",
        checks: [["ok","Quote found once in the chapter"],["ok","Source span found · p. 16"],["ok","No overlapping correction"]] },
    },
  ];
  var filter = "all";
  var editing = null; // id of the correction being revised, or null for a new one
  var pending = null; // { text, paragraph, inTarget }

  /* ---- Word-level diff, so the change is legible before it is submitted ---- */
  function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function diffHtml(a, b) {
    var x = a.split(/(\s+)/).filter(Boolean), y = b.split(/(\s+)/).filter(Boolean);
    var n = x.length, m = y.length, t = [], i, j;
    for (i = 0; i <= n; i++) { t[i] = []; for (j = 0; j <= m; j++) t[i][j] = 0; }
    for (i = n - 1; i >= 0; i--) for (j = m - 1; j >= 0; j--)
      t[i][j] = x[i] === y[j] ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
    var out = [], del = [], ins = [];
    function flush() {
      if (del.length) out.push("<del>" + esc(del.join("")) + "</del>");
      if (ins.length) out.push("<ins>" + esc(ins.join("")) + "</ins>");
      del = []; ins = [];
    }
    i = 0; j = 0;
    while (i < n && j < m) {
      if (x[i] === y[j]) { flush(); out.push(esc(x[i])); i++; j++; }
      else if (t[i + 1][j] >= t[i][j + 1]) { del.push(x[i++]); }
      else { ins.push(y[j++]); }
    }
    while (i < n) del.push(x[i++]);
    while (j < m) ins.push(y[j++]);
    flush();
    return out.join("");
  }

  /* ---- The shared list, with the authority table applied ------------------- */
  // Reading is shared. Writing is owned. Admin overrides both.
  function authority(card) {
    var p = me();
    if (p.admin) return "full";
    if (p.name && card.by === p.name && card.status === "open") return "own";
    return "none";
  }
  var CHECK = { ok: "✓", warn: "!", no: "✕" };
  function aiBlock(c) {
    if (!c.ai) {
      return '<div class="cx-ai cx-ai--pending"><span class="cx-ai__badge">AI review</span> <span class="cx-ai__pending">Queued — the next review run picks this up</span></div>';
    }
    var checks = c.ai.checks.map(function (k) {
      return '<li class="cx-ai__check cx-ai__check--' + k[0] + '"><span aria-hidden="true">' + CHECK[k[0]] + "</span> " + k[1] + "</li>";
    }).join("");
    return '<details class="cx-ai" data-verdict="' + c.ai.verdict + '">' +
      '<summary><span class="cx-ai__badge">AI review</span><strong>' + c.ai.label + "</strong>" +
      '<span class="cx-ai__conf">' + c.ai.conf + "</span></summary>" +
      '<p class="cx-ai__text">' + c.ai.text + "</p>" +
      '<ul class="cx-ai__checks">' + checks + "</ul>" +
      '<p class="cx-ai__note">Advisory only. An admin decides.</p></details>';
  }
  function render() {
    var p = me(), shown = corrections.filter(function (c) {
      if (filter === "all") return true;
      if (filter === "mine") return c.by === p.name;
      return c.status === filter;
    });
    $("mk-count").textContent = corrections.length;
    $("mk-tab-count").textContent = corrections.filter(function (c) { return c.status === "open"; }).length;
    cardsEl.textContent = "";
    if (!shown.length) {
      var e = document.createElement("p");
      e.className = "cx-idle__lead"; e.textContent = "Nothing here yet.";
      cardsEl.appendChild(e);
    }
    shown.forEach(function (c) {
      var auth = authority(c);
      var el = document.createElement("article");
      el.className = "cx-card"; el.id = "card-" + c.id;
      el.setAttribute("data-status", c.status);
      el.setAttribute("data-mine", String(c.by === p.name));
      var foot = "";
      if (auth === "full") {
        if (c.status === "open")
          foot += '<button class="pf-button pf-button--sm cx-btn-ok" data-act="accept" data-id="' + c.id + '">Accept</button>' +
                  '<button class="pf-button pf-button--sm pf-button--ghost" data-act="dismiss" data-id="' + c.id + '">Dismiss</button>';
        foot += '<button class="pf-button pf-button--sm pf-button--ghost" data-act="edit" data-id="' + c.id + '">Edit</button>' +
                '<span class="cx-card__spacer"></span>' +
                '<button class="pf-button pf-button--sm pf-button--ghost cx-btn-danger" data-act="delete" data-id="' + c.id + '">Delete</button>';
      } else if (auth === "own") {
        foot += '<button class="pf-button pf-button--sm pf-button--ghost" data-act="edit" data-id="' + c.id + '">Edit</button>' +
                '<button class="pf-button pf-button--sm pf-button--ghost" data-act="withdraw" data-id="' + c.id + '">Withdraw</button>';
      } else {
        var why = c.by === p.name
          ? "Locked while an admin decides"
          : "Raised by " + c.by + " — only they or an admin can change this";
        foot += '<span class="cx-lock"><svg class="mk-ico" viewBox="0 0 448 512" aria-hidden="true"><path fill="currentColor" d="M144 144v48H304V144c0-44.2-35.8-80-80-80s-80 35.8-80 80zM80 192V144C80 64.5 144.5 0 224 0s144 64.5 144 144v48h16c35.3 0 64 28.7 64 64V448c0 35.3-28.7 64-64 64H64c-35.3 0-64-28.7-64-64V256c0-35.3 28.7-64 64-64H80z"/></svg>' + why + "</span>";
      }
      el.innerHTML =
        '<div class="cx-card__top">' +
          '<span class="cx-avatar" aria-hidden="true">' + c.by[0] + "</span>" +
          '<span class="cx-card__who">' + (c.by === p.name ? "You" : c.by) + "</span>" +
          "<span>· " + c.when + "</span>" +
          '<span class="cx-kind">' + c.kind + "</span>" +
        "</div>" +
        '<p class="cx-card__change">' + diffHtml(c.original, c.proposed) + "</p>" +
        (c.why ? '<p class="cx-card__why">' + c.why + "</p>" : "") +
        aiBlock(c) +
        '<div class="cx-card__foot">' +
          '<span class="cx-status cx-status--' + c.status + '">' +
            (c.status === "accepted" ? "Accepted by " + c.decidedBy + " · waits for the next republish" :
             c.status === "dismissed" ? "Dismissed" : "Open") + "</span>" +
          foot +
        "</div>";
      cardsEl.appendChild(el);
    });
  }

  // Scroll ONLY the panel. scrollIntoView would also move the document, and the
  // panel is fixed — the page behind it must not jump when a card is revealed.
  function panelScrollTo(el) {
    var b = panel.querySelector(".pf-drawer__body");
    b.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top - b.getBoundingClientRect().top + b.scrollTop - 12), behavior: "smooth" });
  }

  /* ---- Panel open / close ---------------------------------------------------- */
  function openPanel() {
    if (!me().canCorrect) return;
    panel.hidden = false;
    $("mk-tab").setAttribute("aria-expanded", "true");
    $("mk-tab").hidden = true;
    scrim.hidden = false;
    document.body.classList.add("pf-shell", "pf-shell--docked");
    $("mk-role-chip").textContent = me().label;
  }
  function closePanel() {
    panel.hidden = true; scrim.hidden = true;
    $("mk-tab").hidden = false;
    document.body.classList.remove("pf-shell", "pf-shell--docked");
    endCompose();
  }
  function endCompose() {
    $("mk-compose").hidden = true; $("mk-idle").hidden = false;
    editing = null; pending = null;
  }
  function toast(msg) {
    var t = $("mk-toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._h); toast._h = setTimeout(function () { t.hidden = true; }, 2600);
  }

  /* ---- Selection bar --------------------------------------------------------- */
  function hideBar() { selbar.hidden = true; }
  document.addEventListener("pointerup", function (ev) {
    if (selbar.contains(ev.target)) return;
    var mark = ev.target.closest && ev.target.closest(".mk-c");
    if (mark && me().canCorrect) { // tap a passage that already carries a correction
      openPanel(); hideBar();
      var card = $("card-" + mark.getAttribute("data-c"));
      if (card) { panelScrollTo(card); card.classList.add("cx-flash"); }
      return;
    }
    setTimeout(function () {
      var sel = window.getSelection();
      if (!sel || sel.isCollapsed || !body.contains(sel.anchorNode)) { hideBar(); return; }
      var text = sel.toString().trim();
      if (!text) { hideBar(); return; }
      var r = sel.getRangeAt(0), rect = r.getBoundingClientRect();
      var para = (r.commonAncestorContainer.nodeType === 1 ? r.commonAncestorContainer : r.commonAncestorContainer.parentElement).closest("p");
      pending = { text: text, paragraph: para ? para.textContent : text, inTarget: !!(para && para.id === "mk-target") };
      selbar.style.setProperty("--sel-top", rect.top + window.scrollY + "px");
      selbar.style.setProperty("--sel-left", rect.left + window.scrollX + rect.width / 2 + "px");
      selbar.hidden = false;
    }, 0);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { hideBar(); if (!panel.hidden) closePanel(); }
  });
  window.addEventListener("scroll", hideBar, { passive: true });

  /* ---- Compose --------------------------------------------------------------- */
  function startCompose(text, paragraph, inTarget, existing) {
    openPanel();
    editing = existing ? existing.id : null;
    $("mk-idle").hidden = true; $("mk-compose").hidden = false;

    var i = paragraph.indexOf(text);
    var q = $("mk-quote");
    if (i >= 0 && paragraph.length > text.length + 4) {
      var pre = paragraph.slice(Math.max(0, i - 60), i), post = paragraph.slice(i + text.length, i + text.length + 60);
      q.innerHTML = (i > 60 ? "…" : "") + esc(pre) + '<mark class="pf-hl pf-hl--gold">' + esc(text) + "</mark>" + esc(post) + (i + text.length + 60 < paragraph.length ? "…" : "");
    } else { q.innerHTML = '<mark class="pf-hl pf-hl--gold">' + esc(text) + "</mark>"; }

    var hasMatch = inTarget || (existing && existing.id === "c-omar");
    $("mk-src-ocr").hidden = false; $("mk-src-txt").hidden = true;
    document.querySelectorAll(".cx-source__tabs button").forEach(function (b) { b.setAttribute("aria-selected", b.dataset.src === "ocr" ? "true" : "false"); });
    $("mk-source").classList.toggle("cx-nomatch", !hasMatch);
    $("mk-loc").textContent = "Chapter 4 · " + (hasMatch ? "paragraph 2" : "paragraph " + (paragraph.indexOf("teacher") >= 0 ? 2 : "—"));

    $("mk-proposed").value = existing ? existing.proposed : text;
    $("mk-why").innerHTML = existing ? existing.why : "";
    $("mk-why-ph").hidden = !!(existing && existing.why);
    $("mk-submit").textContent = existing ? "Save changes" : "Submit correction";
    setKind(existing ? existing.kind : "meaning");
    updateDiff();
    panelScrollTo($("mk-compose"));
    $("mk-proposed").focus();
    window.getSelection().removeAllRanges();
    hideBar();
  }
  function updateDiff() {
    var orig = editing ? corrections.filter(function (c) { return c.id === editing; })[0].original : (pending ? pending.text : $("mk-quote").textContent);
    var next = $("mk-proposed").value;
    $("mk-diff").innerHTML = next === orig ? '<span class="cx-hint">No change yet — edit the text above.</span>' : diffHtml(orig, next);
  }
  function setKind(k) {
    document.querySelectorAll(".cx-kinds button").forEach(function (b) { b.setAttribute("aria-checked", b.dataset.kind === k ? "true" : "false"); });
  }
  function kind() { var b = document.querySelector('.cx-kinds [aria-checked="true"]'); return b ? b.dataset.kind : "other"; }

  $("mk-correct").addEventListener("click", function () {
    if (pending) startCompose(pending.text, pending.paragraph, pending.inTarget, null);
  });
  $("mk-proposed").addEventListener("input", updateDiff);
  document.querySelector(".cx-kinds").addEventListener("click", function (e) { if (e.target.dataset.kind) setKind(e.target.dataset.kind); });
  document.querySelector(".cx-source__tabs").addEventListener("click", function (e) {
    var s = e.target.dataset.src; if (!s) return;
    document.querySelectorAll(".cx-source__tabs button").forEach(function (b) { b.setAttribute("aria-selected", b === e.target ? "true" : "false"); });
    $("mk-src-ocr").hidden = s !== "ocr"; $("mk-src-txt").hidden = s !== "txt";
  });
  $("mk-use-src").addEventListener("click", function () {
    var sel = window.getSelection(), t = sel ? sel.toString().trim() : "";
    if (!t) { toast("Select some words in the source first."); return; }
    var ta = $("mk-proposed"), a = ta.selectionStart, b = ta.selectionEnd;
    ta.value = ta.value.slice(0, a) + t + ta.value.slice(b);
    updateDiff(); ta.focus();
  });
  $("mk-why").addEventListener("input", function () { $("mk-why-ph").hidden = $("mk-why").textContent.length > 0; });
  document.querySelector(".pf-rte__toolbar").addEventListener("mousedown", function (e) {
    var b = e.target.closest("[data-cmd]"); if (!b) return;
    e.preventDefault(); $("mk-why").focus();
    document.execCommand(b.dataset.cmd, false, b.dataset.arg || null);
  });
  $("mk-cancel").addEventListener("click", endCompose);
  $("mk-submit").addEventListener("click", function () {
    var next = $("mk-proposed").value.trim();
    if (!next) { toast("The replacement can’t be empty."); return; }
    var why = $("mk-why").innerHTML.trim();
    if (editing) {
      var c = corrections.filter(function (x) { return x.id === editing; })[0];
      c.proposed = next; c.kind = kind(); c.why = why; toast("Correction updated.");
    } else {
      if (next === pending.text) { toast("Change the text first — nothing differs from the book."); return; }
      corrections.unshift({ id: "c-" + Date.now(), by: me().name, status: "open", kind: kind(), when: "just now", original: pending.text, proposed: next, why: why });
      toast("Correction submitted — everyone with this role can see it.");
    }
    endCompose(); render();
  });

  /* ---- Card actions (the authority table, pressed) --------------------------- */
  cardsEl.addEventListener("click", function (e) {
    var b = e.target.closest("[data-act]"); if (!b) return;
    var c = corrections.filter(function (x) { return x.id === b.dataset.id; })[0];
    if (!c || authority(c) === "none") return; // the UI never decides; the server refuses too
    var act = b.dataset.act;
    if (act === "accept") { c.status = "accepted"; c.decidedBy = me().name; toast("Accepted. It reaches the book at the next republish."); }
    else if (act === "dismiss") { c.status = "dismissed"; toast("Dismissed."); }
    else if (act === "withdraw") { corrections.splice(corrections.indexOf(c), 1); toast("Withdrawn."); }
    else if (act === "delete") { corrections.splice(corrections.indexOf(c), 1); toast("Deleted — kept in the audit record, gone from every view."); }
    else if (act === "edit") { startCompose(c.original, c.original, c.id === "c-omar", c); return; }
    render();
  });
  document.querySelector(".cx-filter").addEventListener("click", function (e) {
    var f = e.target.dataset.f; if (!f) return; filter = f;
    document.querySelectorAll(".cx-filter button").forEach(function (b) { b.setAttribute("aria-pressed", b === e.target ? "true" : "false"); });
    render();
  });

  /* ---- Chrome ---------------------------------------------------------------- */
  $("mk-tab").addEventListener("click", openPanel);
  $("mk-close").addEventListener("click", closePanel);
  scrim.addEventListener("click", closePanel);
  $("mk-role").addEventListener("change", function (e) {
    root.setAttribute("data-role", e.target.value);
    hideBar(); if (!me().canCorrect) closePanel(); else $("mk-role-chip").textContent = me().label;
    render();
  });
  $("mk-theme").addEventListener("change", function (e) { root.setAttribute("data-theme", e.target.value); });

  var qs = new URLSearchParams(location.search);
  if (qs.get("theme")) { root.setAttribute("data-theme", qs.get("theme")); $("mk-theme").value = qs.get("theme"); }
  if (qs.get("role")) { root.setAttribute("data-role", qs.get("role")); $("mk-role").value = qs.get("role"); }
  render();
  if (qs.get("open") === "1") openPanel();

  /* ?demo=bar|compose|list — puts the mock in a given state, so it can be captured
     without clicking. Prototype convenience only. */
  function demo(kind) {
    var p = $("mk-target"), tn = p.querySelector(".mk-c").firstChild;
    var r = document.createRange(); r.setStart(tn, 0); r.setEnd(tn, tn.textContent.length);
    var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
    body.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    setTimeout(function () {
      if (kind === "compose") {
        $("mk-correct").click();
        var ta = $("mk-proposed"); ta.value = ta.value.replace("teacher said", "teacher wrote"); updateDiff();
        $("mk-why").innerHTML = "The scanned source reads <b>وَكَتَبَ</b> — “wrote”. See p. 14, line 3."; $("mk-why-ph").hidden = true;
      }
      if (kind === "list") {
        openPanel(); hideBar();
        document.querySelectorAll(".cx-ai").forEach(function (d, i) { if (i < 2) d.open = true; });
        var b = panel.querySelector(".pf-drawer__body");
        b.scrollTop = $("mk-idle").offsetHeight + 8;
      }
    }, 60);
  }
  if (qs.get("demo")) demo(qs.get("demo"));
})();
