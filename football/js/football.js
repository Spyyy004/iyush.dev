/* ============================================================
   iyush.dev/football — shared behaviour (every /football page)
   Analytics · nav · Fan/Analyst mode · glossary popovers ·
   data loader · PlayerSearch combobox · share · LiveMetric ·
   small dependency-free SVG charts.
   Exposes window.FB. Never fabricates numbers: everything
   rendered from data comes from /football/data/*.json.
   ============================================================ */
(function () {
  "use strict";

  var FB = window.FB = window.FB || {};
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  FB.reduce = reduce;

  /* ---------- storage that never throws ---------- */
  var mem = {};
  FB.get = function (k) { try { return window.localStorage.getItem(k); } catch (e) { return mem[k] || null; } };
  FB.set = function (k, v) { mem[k] = v; try { window.localStorage.setItem(k, v); } catch (e) { /* memory only */ } };

  /* ---------- analytics (same GA4 property as the parent site) ---------- */
  var GA_ID = "G-GKC1N1X7KY";
  (function () {
    var h = location.hostname;
    if (!h || h === "localhost" || h === "127.0.0.1" || h.slice(-6) === ".local") return;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", GA_ID);
  })();
  FB.track = function (name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) { /* ignore */ } };

  /* ---------- helpers ---------- */
  FB.$ = function (s, r) { return (r || document).querySelector(s); };
  FB.$$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  FB.esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
  FB.LEAGUES = ["EPL", "La_Liga", "Serie_A", "Bundesliga", "Ligue_1"];
  FB.LEAGUE_NAME = { EPL: "Premier League", La_Liga: "La Liga", Serie_A: "Serie A", Bundesliga: "Bundesliga", Ligue_1: "Ligue 1" };
  FB.LEAGUE_SLUG = { EPL: "premier-league", La_Liga: "la-liga", Serie_A: "serie-a", Bundesliga: "bundesliga", Ligue_1: "ligue-1" };
  FB.leagueFromSlug = function (slug) { for (var k in FB.LEAGUE_SLUG) if (FB.LEAGUE_SLUG[k] === slug) return k; return null; };
  FB.slug = function (s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  };
  FB.fold = function (s) { return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); };
  // ratio 1.266 -> "+26.6%"; pct -13.84 -> "−13.8%"
  FB.ratioPct = function (r, d) { return FB.signed((r - 1) * 100, d == null ? 1 : d) + "%"; };
  FB.signed = function (x, d) { var v = Number(x).toFixed(d == null ? 1 : d); return (x > 0 ? "+" : x < 0 ? "−" : "") + v.replace("-", ""); };
  FB.pct = function (x, d) { return (x * 100).toFixed(d == null ? 0 : d) + "%"; };
  FB.fix = function (x, d) { return Number(x).toFixed(d == null ? 2 : d); };
  FB.date = function (iso) {
    var d = new Date(iso + (iso.length === 10 ? "T12:00:00Z" : ""));
    return isNaN(d) ? iso : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  };

  /* ---------- data loader (cached; datasets are precomputed outputs only) ---------- */
  var cache = {};
  FB.load = function (name) {
    if (!cache[name]) {
      cache[name] = fetch("/football/data/" + name + ".json", { cache: "no-cache" }).then(function (r) {
        if (!r.ok) throw new Error("Could not load " + name + " (" + r.status + ")");
        return r.json();
      });
      cache[name].catch(function () { delete cache[name]; });
    }
    return cache[name];
  };
  /* ChartContainer states (M1 §23). kind: loading | empty | error | insufficient.
     opts.text overrides the body copy; opts.retry (function) adds "Try again →" to the error state. */
  var STATES = {
    empty: ["No result", "No result for this combination. Try another player or season."],
    error: ["Couldn’t load", "Something went wrong loading this result."],
    insufficient: ["Insufficient data", "This comparison doesn’t meet the minimum sample required by the model."]
  };
  FB.state = function (el, kind, opts) {
    if (!el) return;
    opts = opts || {};
    el.removeAttribute("aria-busy");
    if (kind === "loading") {
      el.setAttribute("aria-busy", "true");
      el.innerHTML = opts.text ? '<p class="analysing">' + FB.esc(opts.text) + "</p>"
        : '<div class="skel" aria-hidden="true"><i></i><i></i><i></i><i></i></div><span class="sr-only">Loading…</span>';
      return;
    }
    var c = STATES[kind];
    el.innerHTML = '<div class="state state--' + kind + '"' + (kind === "error" ? ' role="alert"' : "") + '>' +
      '<p class="state__t">' + c[0] + "</p><p>" + FB.esc(opts.text || c[1]) + "</p>" +
      (kind === "error" && opts.retry ? '<button type="button" class="state__retry">Try again →</button>' : "") + "</div>";
    if (kind === "error" && opts.retry) el.querySelector(".state__retry").addEventListener("click", opts.retry);
  };
  FB.fail = function (el, err, retry) {
    if (window.console) console.warn("[football]", err);
    FB.state(el, "error", { retry: retry || function () { location.reload(); } });
  };
  // Run fn once el scrolls near the viewport (lazy-load heavy datasets / charts).
  FB.whenNear = function (el, fn) {
    if (!el) return;
    if (!("IntersectionObserver" in window)) { fn(); return; }
    var io = new IntersectionObserver(function (es) {
      if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); fn(); }
    }, { rootMargin: "400px 0px" });
    io.observe(el);
  };

  /* ---------- mobile nav ---------- */
  /* full-screen overlay below 640px (M1 §9); focus stays inside while open */
  function initNav() {
    var btn = FB.$(".navbtn"), nav = FB.$(".fnav");
    if (!btn || !nav) return;
    var txt = FB.$(".navbtn__t", btn);
    function set(open) {
      nav.classList.toggle("open", open);
      document.documentElement.classList.toggle("nav-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      if (txt) txt.textContent = open ? "Close" : "Menu";
      if (open) { var first = FB.$("a", nav); if (first) first.focus(); }
    }
    btn.addEventListener("click", function () { set(!nav.classList.contains("open")); });
    nav.addEventListener("click", function (e) { if (e.target.closest("a")) set(false); });
    document.addEventListener("keydown", function (e) {
      if (!nav.classList.contains("open")) return;
      if (e.key === "Escape") { set(false); btn.focus(); return; }
      if (e.key === "Tab") {
        var f = [btn].concat(FB.$$("a", nav)), i = f.indexOf(document.activeElement);
        if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
      }
    });
    window.matchMedia("(min-width: 640px)").addEventListener("change", function (m) { if (m.matches) set(false); });
  }

  /* ---------- Fan / Analyst mode (M0 §19 — default Fan) ---------- */
  FB.mode = function () { return document.documentElement.getAttribute("data-mode") === "analyst" ? "analyst" : "fan"; };
  function setMode(m) {
    document.documentElement.setAttribute("data-mode", m);
    FB.set("fb-mode", m);
    FB.$$("[data-mode-toggle] button").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-set") === m ? "true" : "false"); });
    document.dispatchEvent(new CustomEvent("fb:mode", { detail: m }));
  }
  function initMode() {
    if (!document.documentElement.getAttribute("data-mode")) document.documentElement.setAttribute("data-mode", FB.get("fb-mode") === "analyst" ? "analyst" : "fan");
    FB.$$("[data-mode-toggle]").forEach(function (box) {
      box.classList.add("mode");
      box.setAttribute("role", "group");
      box.setAttribute("aria-label", "Explanation level");
      box.innerHTML = '<button type="button" data-set="fan">Fan</button><button type="button" data-set="analyst">Analyst</button>';
      box.addEventListener("click", function (e) {
        var b = e.target.closest("button[data-set]");
        if (!b) return;
        setMode(b.getAttribute("data-set"));
        FB.track("mode_change", { mode: b.getAttribute("data-set") });
      });
    });
    setMode(FB.mode());
  }

  /* ---------- scroll reveal (M2 §30): study number, charts draw, counters count — once ---------- */
  function initReveal() {
    var els = FB.$$("[data-reveal]");
    if (!els.length || !("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    document.documentElement.classList.add("fx");
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        e.target.classList.add("in");
        FB.$$(".count[data-to]", e.target).forEach(countUp);
      });
    }, { rootMargin: "0px 0px -12% 0px" });
    els.forEach(function (el) { io.observe(el); });
  }
  function countUp(el) {
    var to = parseInt(String(el.getAttribute("data-to")).replace(/,/g, ""), 10);
    if (!(to > 0)) return;
    var t0 = null, dur = 900;
    function step(t) {
      t0 = t0 || t;
      var k = Math.min(1, (t - t0) / dur), v = Math.round(to * (1 - Math.pow(1 - k, 3)));
      el.textContent = v.toLocaleString("en-GB");
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  /* ---------- glossary popover / bottom sheet (M0 §18) ---------- */
  var pop, scrim, lastTerm;
  function glossary() { return window.FB_GLOSSARY || {}; }
  function closePop() {
    if (!pop || pop.hidden) return;
    pop.hidden = true; scrim.hidden = true;
    if (lastTerm) { lastTerm.setAttribute("aria-expanded", "false"); lastTerm.focus({ preventScroll: true }); }
  }
  function openPop(btn) {
    var key = btn.getAttribute("data-term"), g = glossary()[key];
    if (!g) return;
    if (!pop) {
      pop = document.createElement("div");
      pop.className = "gpop"; pop.id = "gpop"; pop.setAttribute("role", "dialog"); pop.setAttribute("aria-modal", "false"); pop.hidden = true;
      scrim = document.createElement("div"); scrim.className = "gscrim"; scrim.hidden = true;
      scrim.addEventListener("click", closePop);
      document.body.appendChild(scrim); document.body.appendChild(pop);
    }
    // M1 §26: plain definition first, the technical one underneath (progressive disclosure)
    pop.setAttribute("aria-label", g.full || g.term);
    pop.innerHTML = '<p class="gpop__term">' + FB.esc(g.full || g.term) + "</p>" +
      '<p class="gpop__def">' + FB.esc(g.short) + "</p>" +
      (g.analyst ? '<p class="gpop__tech"><span class="label">Technical</span>' + FB.esc(g.analyst) + "</p>" : "") +
      '<a class="link-arrow" href="/football/glossary#' + key + '">View glossary <span class="arr" aria-hidden="true">→</span></a>' +
      '<button type="button" class="gpop__close" aria-label="Close definition">×</button>';
    pop.querySelector(".gpop__close").addEventListener("click", closePop);
    pop.hidden = false;
    var mobile = window.matchMedia("(max-width: 640px)").matches;
    scrim.hidden = !mobile;
    if (!mobile) {
      var r = btn.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
      var left = Math.min(Math.max(16, r.left), window.innerWidth - w - 16);
      var top = r.bottom + 8;
      if (top + h > window.innerHeight - 12) top = Math.max(12, r.top - h - 8);
      pop.style.left = left + "px"; pop.style.top = top + "px";
    }
    if (lastTerm && lastTerm !== btn) lastTerm.setAttribute("aria-expanded", "false");
    lastTerm = btn;
    btn.setAttribute("aria-expanded", "true");
    btn.setAttribute("aria-controls", "gpop");
    FB.track("glossary_open", { term: key });
    if (mobile) pop.querySelector(".gpop__close").focus({ preventScroll: true });
  }
  function initGlossary() {
    FB.$$(".term[data-term]").forEach(function (b) { if (b.tagName === "BUTTON") b.type = "button"; b.setAttribute("aria-haspopup", "dialog"); b.setAttribute("aria-expanded", "false"); });
    document.addEventListener("click", function (e) {
      var t = e.target.closest(".term[data-term]");
      if (t) { e.preventDefault(); if (lastTerm === t && pop && !pop.hidden) closePop(); else openPop(t); return; }
      if (pop && !pop.hidden && !e.target.closest(".gpop")) closePop();
    });
    var hoverTimer;
    document.addEventListener("mouseover", function (e) {
      if (!window.matchMedia("(hover: hover) and (min-width: 641px)").matches) return;
      var t = e.target.closest(".term[data-term]");
      if (!t) return;
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(function () { openPop(t); }, 220);
    });
    document.addEventListener("mouseout", function (e) {
      if (e.target.closest(".term[data-term]")) clearTimeout(hoverTimer);
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closePop(); });
    window.addEventListener("scroll", function () { if (pop && !pop.hidden && !window.matchMedia("(max-width: 640px)").matches) closePop(); }, { passive: true });
  }
  // Inline term markup for JS-rendered text.
  FB.term = function (key, label) { return '<button type="button" class="term" data-term="' + key + '" aria-haspopup="dialog" aria-expanded="false">' + FB.esc(label) + "</button>"; };

  /* ---------- ShareButton: serialised URL state (M0 §21) ---------- */
  FB.share = function (btn, getTitle) {
    if (!btn) return;
    btn.addEventListener("click", function () {
      var url = location.href, title = (getTitle && getTitle()) || document.title;
      FB.track("share", { path: location.pathname });
      var done = function () {
        btn.setAttribute("data-state", "copied");
        var old = btn.getAttribute("data-label") || btn.textContent;
        btn.setAttribute("data-label", old);
        btn.textContent = "Link copied";
        setTimeout(function () { btn.removeAttribute("data-state"); btn.textContent = old; }, 1800);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () { window.prompt("Copy this link", url); });
      else window.prompt("Copy this link", url);
    });
  };
  FB.params = function () { return new URLSearchParams(location.search); };
  FB.setParams = function (obj) {
    var p = new URLSearchParams();
    Object.keys(obj).forEach(function (k) { if (obj[k] != null && obj[k] !== "") p.set(k, obj[k]); });
    var q = p.toString();
    history.replaceState(null, "", location.pathname + (q ? "?" + q : "") + location.hash);
  };

  /* ---------- PlayerSearch combobox (accessible, diacritic-insensitive) ---------- */
  // items: [{label, sub, tag, value}] ; onPick(item)
  FB.combo = function (input, items, onPick, opts) {
    opts = opts || {};
    var list = document.createElement("ul");
    var id = (input.id || "combo") + "-list";
    list.className = "combo__list"; list.id = id; list.setAttribute("role", "listbox"); list.hidden = true;
    input.parentNode.appendChild(list);
    input.setAttribute("role", "combobox"); input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", id); input.setAttribute("aria-expanded", "false"); input.setAttribute("autocomplete", "off");
    var shown = [], active = -1, max = opts.max || 12;
    var folded = items.map(function (it) { return FB.fold(it.label); });
    function render(q) {
      var f = FB.fold(q.trim());
      shown = [];
      if (f.length >= (opts.minChars || 1)) {
        var starts = [], has = [];
        for (var i = 0; i < items.length; i++) {
          var s = folded[i], idx = s.indexOf(f);
          if (idx < 0) continue;
          var word = idx === 0 || s.charAt(idx - 1) === " " || s.charAt(idx - 1) === "-";
          (word ? starts : has).push(i);
        }
        shown = starts.concat(has).slice(0, max);
      }
      active = shown.length ? 0 : -1;
      if (!f) { list.hidden = true; input.setAttribute("aria-expanded", "false"); return; }
      list.innerHTML = shown.length ? shown.map(function (i, n) {
        var it = items[i], s = folded[i], idx = s.indexOf(f);
        var nm = FB.esc(it.label.slice(0, idx)) + "<mark>" + FB.esc(it.label.slice(idx, idx + f.length)) + "</mark>" + FB.esc(it.label.slice(idx + f.length));
        return '<li role="option" id="' + id + "-" + n + '" aria-selected="' + (n === active) + '" data-i="' + i + '"><span class="nm">' + nm + "</span>" +
          (it.tag ? '<span class="lg">' + FB.esc(it.tag) + "</span>" : "") + (it.sub ? '<span class="sub">' + FB.esc(it.sub) + "</span>" : "") + "</li>";
      }).join("") : '<li class="empty" role="option" aria-disabled="true">No match in this dataset — ' + FB.esc(opts.emptyHint || "try another spelling") + "</li>";
      list.hidden = false; input.setAttribute("aria-expanded", "true");
      input.setAttribute("aria-activedescendant", active >= 0 ? id + "-" + active : "");
    }
    function move(d) {
      if (!shown.length) return;
      active = (active + d + shown.length) % shown.length;
      FB.$$("li", list).forEach(function (li, n) { li.setAttribute("aria-selected", n === active ? "true" : "false"); });
      input.setAttribute("aria-activedescendant", id + "-" + active);
      var el = document.getElementById(id + "-" + active); if (el) el.scrollIntoView({ block: "nearest" });
    }
    function pick(i) {
      var it = items[i]; if (!it) return;
      input.value = it.label; list.hidden = true; input.setAttribute("aria-expanded", "false");
      onPick(it);
    }
    input.addEventListener("input", function () { render(input.value); });
    input.addEventListener("focus", function () { if (input.value && input.getAttribute("data-picked") !== input.value) render(input.value); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); if (list.hidden) render(input.value); else move(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
      else if (e.key === "Enter") { if (!list.hidden && active >= 0) { e.preventDefault(); pick(shown[active]); } }
      else if (e.key === "Escape") { list.hidden = true; input.setAttribute("aria-expanded", "false"); }
    });
    list.addEventListener("mousedown", function (e) { var li = e.target.closest("li[data-i]"); if (li) { e.preventDefault(); pick(+li.getAttribute("data-i")); } });
    document.addEventListener("click", function (e) { if (e.target !== input && !list.contains(e.target)) { list.hidden = true; input.setAttribute("aria-expanded", "false"); } });
    return { set: function (label) { input.value = label; input.setAttribute("data-picked", label); } };
  };

  /* ---------- LiveMetric / LiveComparison (M0 §12) ---------- */
  // kind: "home_edge" (ratios) or "opposition" (% per SD). metric: "xg" etc.
  FB.liveRows = function (tracker, kind, metric) {
    var rows = [], seasons = tracker && tracker.seasons || {};
    var frozen = null;
    Object.keys(seasons).sort().forEach(function (k) {
      var s = seasons[k], m = s[kind] && s[kind][metric];
      if (!m) return;
      if (frozen == null) frozen = m.frozen;
      rows.push(kind === "home_edge"
        ? { label: s.label, sub: s.in_progress ? "in progress · to " + FB.date(s.through) : "complete", v: (m.ratio - 1) * 100, lo: (m.lo - 1) * 100, hi: (m.hi - 1) * 100, live: true }
        : { label: s.label, sub: s.in_progress ? "in progress · to " + FB.date(s.through) : "complete", v: m.pct_sd, lo: m.lo, hi: m.hi, live: true });
    });
    if (frozen != null) rows.unshift({ label: "Frozen", sub: "2015/16–2024/25", v: kind === "home_edge" ? (frozen - 1) * 100 : frozen, frozen: true });
    return rows;
  };
  FB.renderLive = function (el, rows, opts) {
    opts = opts || {};
    var vals = []; rows.forEach(function (r) { vals.push(r.v); if (r.lo != null) { vals.push(r.lo, r.hi); } });
    var lo = Math.min(0, Math.min.apply(null, vals)), hi = Math.max(0, Math.max.apply(null, vals));
    var pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    var x = function (v) { return ((v - lo) / (hi - lo) * 100).toFixed(2) + "%"; };
    var frozen = rows.filter(function (r) { return r.frozen; })[0];
    el.innerHTML = rows.map(function (r) {
      var bar = '<span class="zero" style="left:' + x(0) + '"></span>' +
        (frozen && !r.frozen ? '<span class="ref" style="left:' + x(frozen.v) + '"></span>' : "") +
        (r.lo != null ? '<span class="ci grow" style="left:' + x(Math.min(r.lo, r.hi)) + ';width:calc(' + x(Math.max(r.lo, r.hi)) + " - " + x(Math.min(r.lo, r.hi)) + ')"></span>' : "") +
        '<span class="dot grow' + (r.frozen ? " dot--frozen" : "") + '" style="left:' + x(r.v) + '"></span>';
      var ci = r.lo != null ? " 95% interval " + FB.signed(Math.min(r.lo, r.hi), 0) + "% to " + FB.signed(Math.max(r.lo, r.hi), 0) + "%." : "";
      return '<div class="live__row' + (r.frozen ? " live__row--frozen" : "") + '"><span class="who">' + FB.esc(r.label) + "<small>" + FB.esc(r.sub) + "</small></span>" +
        '<span class="live__bar" role="img" aria-label="' + FB.esc(r.label + ": " + FB.signed(r.v, 1) + "%." + ci) + '">' + bar + "</span>" +
        '<span class="v">' + FB.signed(r.v, 1) + "%</span></div>";
    }).join("") + (opts.legend === false ? "" :
      '<div class="legend"><span><i class="sw" style="--c:var(--accent);border-radius:50%"></i>Live season</span><span><i class="sw sw--dash" style="--c:var(--frozen)"></i>Frozen estimate</span><span><i class="sw" style="--c:var(--ink-2);height:2px;opacity:.6"></i>95% interval</span></div>');
  };

  /* ---------- small SVG charts (ChartContainer bodies) ---------- */
  var NS = "http://www.w3.org/2000/svg";
  FB.svg = function (w, h, label) {
    var s = document.createElementNS(NS, "svg");
    s.setAttribute("viewBox", "0 0 " + w + " " + h); s.setAttribute("width", "100%"); s.setAttribute("role", "img");
    if (label) s.setAttribute("aria-label", label);
    s.style.minWidth = Math.min(w, 520) + "px";
    return s;
  };
  FB.el = function (tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  };
  // Horizontal dot + interval chart. rows: [{label, v, lo, hi, series}] ; series → colour + marker
  // opts: {unit:"%", ref: number, refLabel, series: {key: {color, label, shape}}, fmt}
  FB.dotChart = function (host, rows, opts) {
    opts = opts || {};
    var labels = []; rows.forEach(function (r) { if (labels.indexOf(r.label) < 0) labels.push(r.label); });
    var seriesKeys = []; rows.forEach(function (r) { var k = r.series || "_"; if (seriesKeys.indexOf(k) < 0) seriesKeys.push(k); });
    var rowH = 22 * Math.max(1, seriesKeys.length) + 14, L = opts.labelW || 130, W = 640, R = 56, T = 8, H = T + labels.length * rowH + 30;
    var vals = [0]; rows.forEach(function (r) { vals.push(r.v); if (r.lo != null) vals.push(r.lo, r.hi); }); if (opts.ref != null) vals.push(opts.ref);
    var lo = opts.min != null ? opts.min : Math.min.apply(null, vals), hi = opts.max != null ? opts.max : Math.max.apply(null, vals);
    var pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
    var X = function (v) { return L + (v - lo) / (hi - lo) * (W - L - R); };
    var fmt = opts.fmt || function (v) { return FB.signed(v, 0) + (opts.unit || ""); };
    var s = FB.svg(W, H, opts.label);
    var ticks = niceTicks(lo, hi, 5);
    ticks.forEach(function (t) {
      FB.el("line", { x1: X(t), x2: X(t), y1: T, y2: H - 24, class: t === 0 ? "axis-l" : "grid-l" }, s);
      FB.el("text", { x: X(t), y: H - 8, "text-anchor": "middle", class: "tick" }, s, fmt(t));
    });
    if (opts.ref != null) {
      FB.el("line", { x1: X(opts.ref), x2: X(opts.ref), y1: T, y2: H - 24, stroke: "var(--frozen)", "stroke-dasharray": "4 3" }, s);
      if (opts.refLabel) FB.el("text", { x: X(opts.ref) + 4, y: T + 10, class: "tick" }, s, opts.refLabel);
    }
    labels.forEach(function (lab, i) {
      var y0 = T + i * rowH;
      FB.el("text", { x: 0, y: y0 + rowH / 2 + 4, class: "lab" }, s, lab);
      seriesKeys.forEach(function (k, j) {
        var r = rows.filter(function (q) { return q.label === lab && (q.series || "_") === k; })[0];
        if (!r) return;
        var sv = (opts.series || {})[k] || {}, c = sv.color || "var(--accent)";
        var y = y0 + 7 + 11 + j * 22;
        if (r.lo != null) FB.el("line", { x1: X(Math.min(r.lo, r.hi)), x2: X(Math.max(r.lo, r.hi)), y1: y, y2: y, stroke: c, "stroke-width": 2, opacity: 0.55 }, s);
        if (sv.shape === "diamond") FB.el("rect", { x: X(r.v) - 5, y: y - 5, width: 10, height: 10, fill: "var(--surface)", stroke: c, "stroke-width": 2, transform: "rotate(45 " + X(r.v) + " " + y + ")" }, s);
        else if (sv.shape === "ring") FB.el("circle", { cx: X(r.v), cy: y, r: 5, fill: "var(--surface)", stroke: c, "stroke-width": 2 }, s);
        else FB.el("circle", { cx: X(r.v), cy: y, r: 5.5, fill: c }, s);
        FB.el("text", { x: W - R + 8, y: y + 4, class: "val" }, s, fmt(r.v));
      });
    });
    host.innerHTML = ""; host.appendChild(s);
    if (opts.series && seriesKeys.length > 1) host.insertAdjacentHTML("beforeend", legendHtml(seriesKeys.map(function (k) { return opts.series[k]; })));
  };
  // Vertical bar chart. rows: [{label, values: {seriesKey: v}}]
  FB.barChart = function (host, rows, opts) {
    opts = opts || {};
    var keys = opts.keys, W = 640, H = opts.height || 260, L = 44, B = 40, T = 12, R = 8;
    var vals = [0]; rows.forEach(function (r) { keys.forEach(function (k) { if (r.values[k] != null) vals.push(r.values[k]); }); });
    var lo = opts.min != null ? opts.min : Math.min.apply(null, vals), hi = opts.max != null ? opts.max : Math.max.apply(null, vals) * 1.08;
    var Y = function (v) { return T + (hi - v) / (hi - lo) * (H - T - B); };
    var fmt = opts.fmt || function (v) { return String(v); };
    var s = FB.svg(W, H, opts.label);
    niceTicks(lo, hi, 4).forEach(function (t) {
      FB.el("line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), class: t === 0 ? "axis-l" : "grid-l" }, s);
      FB.el("text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end", class: "tick" }, s, fmt(t));
    });
    if (opts.ref != null) FB.el("line", { x1: L, x2: W - R, y1: Y(opts.ref), y2: Y(opts.ref), stroke: "var(--frozen)", "stroke-dasharray": "4 3" }, s);
    var band = (W - L - R) / rows.length, bw = Math.min(28, band * 0.7 / keys.length);
    rows.forEach(function (r, i) {
      var cx = L + band * i + band / 2;
      keys.forEach(function (k, j) {
        var v = r.values[k]; if (v == null) return;
        var x = cx - (keys.length * bw) / 2 + j * bw, y = Y(Math.max(v, 0)), h = Math.abs(Y(v) - Y(0));
        FB.el("rect", { x: x + 1, y: y, width: bw - 2, height: Math.max(1, h), fill: (opts.colors || {})[k] || "var(--accent)", rx: 1 }, s);
        if (opts.showValues) FB.el("text", { x: x + bw / 2, y: y - 5, "text-anchor": "middle", class: "val", "font-size": 10.5 }, s, fmt(v));
      });
      FB.el("text", { x: cx, y: H - B + 18, "text-anchor": "middle", class: "lab" }, s, r.label);
    });
    host.innerHTML = ""; host.appendChild(s);
    if (opts.legend) host.insertAdjacentHTML("beforeend", legendHtml(opts.legend));
  };
  // Line chart. series: [{label, color, points:[[x,y,lo,hi]], dashed}]
  FB.lineChart = function (host, series, opts) {
    opts = opts || {};
    var W = 640, H = opts.height || 260, L = 48, B = 34, T = 12, R = 16;
    var xs = [], ys = [];
    series.forEach(function (s) { s.points.forEach(function (p) { xs.push(p[0]); ys.push(p[1]); if (p[2] != null) ys.push(p[2], p[3]); }); });
    if (opts.ref != null) ys.push(opts.ref);
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var y0 = opts.min != null ? opts.min : Math.min.apply(null, ys), y1 = opts.max != null ? opts.max : Math.max.apply(null, ys);
    var pad = (y1 - y0) * 0.08; y0 -= pad; y1 += pad;
    var X = function (v) { return L + (x1 === x0 ? 0.5 : (v - x0) / (x1 - x0)) * (W - L - R); };
    var Y = function (v) { return T + (y1 - v) / (y1 - y0) * (H - T - B); };
    var fmtY = opts.fmtY || function (v) { return String(v); }, fmtX = opts.fmtX || function (v) { return String(v); };
    var s = FB.svg(W, H, opts.label);
    niceTicks(y0, y1, 4).forEach(function (t) {
      FB.el("line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), class: "grid-l" }, s);
      FB.el("text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end", class: "tick" }, s, fmtY(t));
    });
    var xt = opts.xTicks || Array.from(new Set(xs)).sort(function (a, b) { return a - b; });
    xt.forEach(function (t) { FB.el("text", { x: X(t), y: H - 10, "text-anchor": "middle", class: "tick" }, s, fmtX(t)); });
    if (opts.ref != null) FB.el("line", { x1: L, x2: W - R, y1: Y(opts.ref), y2: Y(opts.ref), stroke: "var(--frozen)", "stroke-dasharray": "4 3" }, s);
    series.forEach(function (sr) {
      var band = sr.points.filter(function (p) { return p[2] != null; });
      if (band.length > 1) {
        var d = band.map(function (p, i) { return (i ? "L" : "M") + X(p[0]) + " " + Y(p[3]); }).join("") +
          band.slice().reverse().map(function (p) { return "L" + X(p[0]) + " " + Y(p[2]); }).join("") + "Z";
        FB.el("path", { d: d, fill: sr.color, opacity: 0.12 }, s);
      }
      var line = sr.points.map(function (p, i) { return (i ? "L" : "M") + X(p[0]) + " " + Y(p[1]); }).join("");
      FB.el("path", { d: line, fill: "none", stroke: sr.color, "stroke-width": 2, "stroke-dasharray": sr.dashed ? "5 4" : "" }, s);
      sr.points.forEach(function (p) { FB.el("circle", { cx: X(p[0]), cy: Y(p[1]), r: 3, fill: sr.color }, s); });
    });
    host.innerHTML = ""; host.appendChild(s);
    if (series.length > 1 || opts.legend) host.insertAdjacentHTML("beforeend", legendHtml(opts.legend || series.map(function (sr) { return { label: sr.label, color: sr.color, line: true }; })));
  };
  function legendHtml(items) {
    return '<div class="legend">' + items.map(function (it) {
      var cls = it.line ? "sw" : it.shape === "ring" ? "sw sw--ring" : it.shape === "dash" ? "sw sw--dash" : "sw";
      var st = it.line ? "height:2px;width:16px;" : it.shape === "diamond" ? "transform:rotate(45deg) scale(.8);background:none;border:2px solid " + it.color + ";" : "";
      return '<span><i class="' + cls + '" style="--c:' + it.color + ";" + st + '"></i>' + FB.esc(it.label) + "</span>";
    }).join("") + "</div>";
  }
  FB.legend = legendHtml;
  function niceTicks(lo, hi, n) {
    var span = hi - lo; if (!(span > 0)) return [lo];
    var step = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step;
    step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
    var out = []; for (var t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(+t.toFixed(10));
    return out;
  }
  FB.niceTicks = niceTicks;

  /* ---------- boot ---------- */
  // keep the current study visible in the swipeable study nav on narrow screens
  function initStudyNav() {
    var cur = FB.$(".snav [aria-current]"), ol = cur && cur.closest("ol");
    if (ol && ol.scrollWidth > ol.clientWidth) ol.scrollLeft = Math.max(0, cur.offsetLeft - 16);
  }
  function boot() { initNav(); initMode(); initGlossary(); initReveal(); initStudyNav(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
