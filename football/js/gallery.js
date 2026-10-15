/* Football Match Gallery: browse the season's rated matches.
   Reads football/data/gallery/<season>.json, exported by scripts/build_gallery.py from the research project's
   Match Entertainment Rating output. Ratings, stars and labels are displayed exactly as stored; nothing is rated,
   rescored or filled in here. Unrated matches never get stars.
   Poster art (club colours, the who-led timeline) and the hero headline are presentational: colours come from the
   reviewed scripts/club_colours.csv, the headline from fixed templates over goal events (meta.feature). */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var PAGE = 48, SHELF = 12, SHELF_MIN = 5;
  var BASE = "/football/data/gallery/";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var WHY = {
    not_played: "not played (postponed or abandoned)",
    source_conflict: "the data sources disagree on the result",
    invalid_source_record: "the source record is incomplete",
    goal_timeline_does_not_match_score: "the goal data is incomplete"
  };
  var MISSING = { shots_on_target: "shots on target", red_cards: "red cards", penalties: "penalties" };
  var LABEL_ORDER = ["Thriller", "Late Drama", "Comeback", "Goal Fest", "Upset", "Hidden Gem", "Chaos", "One-Sided"];
  // Collections: each is a stored label (or 5 stars), ordered by the stored match score. Never a new score.
  var SHELVES = [
    { key: "unmissables", title: "The Unmissables", five: true, rule: function (s) { return "Every match rated 5★ in " + s + "."; } },
    { key: "late", title: "Late, Late Drama", label: "Late Drama", rule: function () { return "A result-changing goal at 88′ or later, or in extra time."; } },
    { key: "chaos", title: "Pure Chaos", label: "Chaos", rule: function () { return "Four or more red cards, penalties, equalisers and lead changes."; } },
    { key: "comeback", title: "Comebacks", label: "Comeback", rule: function () { return "The winner was behind after the hour, or a side came back from two down."; } },
    { key: "gems", title: "Hidden Gems", label: "Hidden Gem", rule: function () { return "4★ or better with two goals or fewer: tension over goals."; } },
    { key: "upsets", title: "Upsets", label: "Upset", rule: function () { return "League matches the winner had a 25% chance or less of winning, on the closing odds."; } }
  ];
  var MONO_LIGHT = "#d9d2c6", MONO_DARK = "#2c2724", NEUTRAL = "#4a423b", CLASH = 100;

  var cache = {}, INDEX = null, DATA = null, BYK = {};
  var st = { season: null, sort: "rating", comp: "", label: "", club: "", from: "", to: "", shown: PAGE };

  var CREST_SET = {};
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function crest(cid, name, size, cls, eager) {   // decorative: the club name is always beside it
    if (cid && CREST_SET[cid]) {
      return '<img class="crest ' + (cls || "") + '" src="/football/crests/' + esc(cid.replace(":", "-")) + '.png" width="' + size + '" height="' + size + '" alt=""' + (eager ? "" : ' loading="lazy"') + ' decoding="async" />';
    }
    var ini = String(name || "?").replace(/\./g, " ").split(/\s+/).filter(Boolean).slice(0, 2).map(function (w) { return w[0]; }).join("").toUpperCase();
    return '<span class="crest crest--none ' + (cls || "") + '" style="width:' + size + "px;height:" + size + 'px" aria-hidden="true">' + esc(ini) + "</span>";
  }
  function fmtDate(d) {
    if (!d || !/^\d{4}-\d{2}-\d{2}$/.test(d)) return "Date unknown";
    return +d.slice(8, 10) + " " + MONTHS[+d.slice(5, 7) - 1] + " " + d.slice(0, 4);
  }
  function weekday(d) { return DAYS[new Date(d + "T12:00:00Z").getUTCDay()]; }
  function getJSON(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }
  function loadSeason(season) {
    if (!cache[season]) {
      cache[season] = getJSON(BASE + season + ".json").catch(function (e) { delete cache[season]; throw e; });
    }
    return cache[season];
  }

  /* ---------------- ordering (deterministic: stored score, then date, then the canonical id) ---------------- */
  function byRating(a, b) { return b.sc - a.sc || (a.d < b.d ? 1 : a.d > b.d ? -1 : 0) || (a.k < b.k ? -1 : 1); }
  function byRecent(a, b) {
    var ta = a.t || a.d, tb = b.t || b.d;
    return (ta < tb ? 1 : ta > tb ? -1 : 0) || b.sc - a.sc || (a.k < b.k ? -1 : 1);
  }
  function filtered() {
    return DATA.matches.filter(function (m) {
      return (!st.comp || m.c === st.comp) && (!st.label || m.lb.indexOf(st.label) >= 0) &&
        (!st.club || m.hc === st.club || m.ac === st.club) &&
        (!st.from || m.d >= st.from) && (!st.to || m.d <= st.to);
    }).sort(st.sort === "recent" ? byRecent : byRating);
  }

  /* ---------------- poster paint (mirrors scripts/gallery_pages.py pair_paint) ---------------- */
  function rgb(c) { return [1, 3, 5].map(function (i) { return parseInt(c.slice(i, i + 2), 16); }); }
  function dist(a, b) { var x = rgb(a), y = rgb(b); return Math.sqrt(Math.pow(x[0] - y[0], 2) + Math.pow(x[1] - y[1], 2) + Math.pow(x[2] - y[2], 2)); }
  function light(c) { var x = rgb(c); return (Math.max.apply(null, x) + Math.min.apply(null, x)) / 510; }
  function lineOf(f) { return f === MONO_DARK ? "#8f857a" : f === MONO_LIGHT ? f : null; }
  function pair(hc, ac) {
    var P = DATA.meta.paint || {};
    var h = P[hc] || [NEUTRAL, "#857a6e", null, null], a = P[ac] || [NEUTRAL, "#857a6e", null, null];
    var fa = a[0], la = a[1];
    if (dist(h[0], fa) < CLASH) {
      if (a[2] && dist(h[0], a[2]) >= CLASH) { fa = a[2]; la = a[3]; }
      else { fa = (h[0] === MONO_LIGHT || light(h[0]) > 0.6) ? MONO_DARK : MONO_LIGHT; la = lineOf(fa); }
    }
    return [h[0], h[1], fa, la];
  }
  function goalsOf(m) {
    return (m.g || "").split(" ").filter(Boolean).map(function (t) {
      var p = t.slice(1).split(".");
      return { side: t[0], minute: +p[0], period: +p[1] };
    });
  }
  function minuteLabel(p, m) { var end = { 1: 45, 2: 90, 3: 105, 4: 120 }[p]; return m > end ? end + "+" + (m - end) + "′" : m + "′"; }
  function worm(m, hl, al, H, dots) {   // who led, minute by minute (mirrors gallery_pages.worm_svg)
    var gs = goalsOf(m), W = 400, mid = H / 2;
    var xp = function (g) { return g.period === 1 ? Math.min(g.minute, 46) : g.period === 2 ? Math.max(g.minute, 46) : g.minute; };
    var end = m.aet ? 122 : Math.max.apply(null, [96].concat(gs.map(function (g) { return xp(g) + 3; })));
    var X = function (v) { return Math.round(v / end * W * 10) / 10; };
    var diff = 0, peak = 1;
    gs.forEach(function (g) { diff += g.side === "h" ? 1 : -1; peak = Math.max(peak, Math.abs(diff)); });
    var unit = (mid - 3) / Math.max(2, peak), out = "", x0 = 0;
    diff = 0;
    function seg(x1) {
      if (diff > 0) out += '<rect x="' + X(x0) + '" y="' + (mid - diff * unit).toFixed(1) + '" width="' + (X(x1) - X(x0)).toFixed(1) + '" height="' + (diff * unit).toFixed(1) + '" fill="' + hl + '"/>';
      else if (diff < 0) out += '<rect x="' + X(x0) + '" y="' + mid + '" width="' + (X(x1) - X(x0)).toFixed(1) + '" height="' + (-diff * unit).toFixed(1) + '" fill="' + al + '"/>';
    }
    gs.forEach(function (g) { seg(xp(g)); diff += g.side === "h" ? 1 : -1; x0 = xp(g); });
    seg(end);
    var ticks = [45, 90].concat(m.aet ? [105, 120] : []).map(function (t) { return '<line x1="' + X(t) + '" x2="' + X(t) + '" y1="2" y2="' + (H - 2) + '" class="wm-tick"/>'; }).join("");
    var dot = dots ? gs.map(function (g) { return '<line x1="' + X(xp(g)) + '" x2="' + X(xp(g)) + '" y1="' + (mid - 7) + '" y2="' + (mid + 7) + '" class="wm-goal"/>'; }).join("") : "";
    return '<svg class="wm" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none" aria-hidden="true" focusable="false">' + ticks +
      '<line x1="0" x2="' + W + '" y1="' + mid + '" y2="' + mid + '" class="wm-zero"/>' + out + dot + "</svg>";
  }

  /* ---------------- pieces ---------------- */
  function compOf(code) {
    var cs = DATA.meta.competitions;
    for (var i = 0; i < cs.length; i++) if (cs[i].code === code) return cs[i];
    return { code: code, name: code, short: code };
  }
  function starsHTML(s) {
    var txt = (s % 1 ? s.toFixed(1) : String(s)) + " out of 5 stars";
    return '<span class="gx-stars" role="img" aria-label="' + txt + '"><span class="gx-stars__on" style="width:' + (s / 5 * 100) + '%"></span></span>' +
      '<span class="gx-stars__n num" aria-hidden="true">' + s.toFixed(1) + "</span>";
  }
  function scoreNote(m) {
    var bits = [];
    if (m.so) bits.push("aet · " + m.so[0] + "–" + m.so[1] + " on pens");
    else if (m.aet) bits.push("after extra time");
    if (m.fl) bits.push("agg " + (m.fl[0] + m.hg) + "–" + (m.fl[1] + m.ag));
    return bits.join(" · ");
  }
  function winners(m) {
    return m.so ? [m.so[0] > m.so[1], m.so[1] > m.so[0]] : [m.hg > m.ag, m.ag > m.hg];
  }
  function teamRow(name, goals, win, cid) {
    return '<span class="gx-team' + (win ? " is-win" : "") + '">' + crest(cid, name, 20, "gx-crest") + '<span class="gx-team__n">' + esc(name || "Unknown team") +
      '</span><span class="gx-team__g num">' + (goals == null ? "–" : goals) + "</span></span>";
  }
  function ariaOf(m) {
    var c = compOf(m.c);
    return (m.h || "Unknown") + " " + m.hg + ", " + (m.a || "Unknown") + " " + m.ag + ". " + c.name + ", " + fmtDate(m.d) +
      ". " + (m.st % 1 ? m.st.toFixed(1) : m.st) + " out of 5 stars" + (m.p ? ", partial rating" : "") +
      (m.lb.length ? ". " + m.lb.join(", ") : "") + ". Open match page.";
  }
  // One card for posters (desktop grid, shelves) and numbered rows (phones, the archive list): CSS decides.
  function card(m, rank) {
    var c = compOf(m.c), p = pair(m.hc, m.ac), w = winners(m), note = scoreNote(m);
    var miss = m.p ? m.p.map(function (x) { return MISSING[x] || x; }).join(", ") : "";
    var tags = m.lb.slice(0, 2), more = m.lb.length - tags.length;
    return '<li class="gx-card' + (m.st === 5 ? " is-five" : "") + (m.p ? " is-partial" : "") + '" data-k="' + esc(m.k) + '">' +
      '<a class="gx-card__link" href="/football/gallery/match/' + esc(m.u) + '" aria-label="' + esc(ariaOf(m)) + '">' +
      '<span class="gx-art" style="--fh:' + p[0] + ";--fa:" + p[2] + '" aria-hidden="true">' +
        '<span class="gx-art__comp">' + esc(c.name) + "</span>" +
        '<span class="gx-art__mid">' + crest(m.hc, m.h, 64, "gx-art__crest") + '<span class="gx-art__sc num">' + m.hg + "–" + m.ag + "</span>" + crest(m.ac, m.a, 64, "gx-art__crest") + "</span>" +
        worm(m, p[1], p[3], 30, false) +
      "</span>" +
      '<span class="gx-info">' +
        (rank ? '<span class="gx-rank num" aria-label="Rank ' + rank + '"><span class="gx-rank__h">#</span>' + rank + "</span>" : "") +
        '<span class="gx-score">' + teamRow(m.h, m.hg, w[0], m.hc) + teamRow(m.a, m.ag, w[1], m.ac) + "</span>" +
        '<span class="gx-card__rate">' + starsHTML(m.st) + "</span>" +
        '<span class="gx-ctx"><span class="gx-comp" data-c="' + esc(m.c) + '">' + esc(c.name) + '</span> · <time datetime="' + esc(m.d) + '">' + fmtDate(m.d) + "</time>" +
          (note ? ' · <span class="gx-note">' + esc(note) + "</span>" : "") + (m.lb.length ? '<span class="gx-ctx__lb"> · ' + esc(m.lb.slice(0, 2).join(" · ")) + "</span>" : "") + "</span>" +
        (m.p ? '<span class="gx-partial"><span aria-hidden="true">◐</span> Partial rating <span class="sr-only">(missing ' + esc(miss) + ")</span></span>" : "") +
        (tags.length ? '<span class="gx-tags">' + tags.map(function (l) { return '<span class="gx-tag">' + esc(l) + "</span>"; }).join("") +
          (more ? '<span class="gx-tag gx-tag--more">+' + more + "</span>" : "") + "</span>" : "") +
      "</span></a></li>";
  }
  function setControls(on) {   // filters mean nothing without data: disabled while loading or after a failure
    Array.prototype.forEach.call(document.querySelectorAll("#gx-controls button, #gx-controls select, #gx-controls input"), function (el) { el.disabled = !on; });
  }
  function stateBox(kind, title, body, action) {
    var out = $("gx-results");
    out.removeAttribute("aria-busy");
    out.innerHTML = '<div class="state state--' + kind + '"' + (kind === "error" ? ' role="alert"' : "") + '><p class="state__t">' +
      esc(title) + "</p>" + body + (action || "") + "</div>";
    $("gx-more").hidden = true;
  }

  /* ---------------- hero: the match of the season (same markup as build_gallery.py hero_html) ---------------- */
  function renderHero() {
    var f = DATA.meta.feature, hero = $("gx-hero");
    var m = f && BYK[f.k];
    if (!m || m.p) { hero.hidden = true; hero.innerHTML = ""; hero.removeAttribute("data-k"); return; }   // a partial rating is never headlined
    if (hero.getAttribute("data-k") === m.k && hero.innerHTML.trim()) { hero.hidden = false; return; }   // server-rendered already
    var c = compOf(m.c), p = pair(m.hc, m.ac), w = winners(m), note = scoreNote(m);
    var mins = goalsOf(m).map(function (g) { return minuteLabel(g.period, g.minute); }).join(" · ");
    var current = !INDEX.seasons.filter(function (s) { return s.season === st.season; })[0].archive;
    var side = function (cid, name, win) {
      return '<span class="gx-poster__side' + (win ? " is-win" : "") + '">' + crest(cid, name, 128, "gx-poster__crest", true) + '<span class="gx-poster__name">' + esc(name) + "</span></span>";
    };
    var notes = [];
    if (m.so) notes.push("After extra time · " + m.so[0] + "–" + m.so[1] + " on penalties"); else if (m.aet) notes.push("After extra time");
    if (m.fl) notes.push("Second leg · aggregate " + (m.fl[0] + m.hg) + "–" + (m.fl[1] + m.ag));
    hero.setAttribute("data-k", m.k);
    hero.setAttribute("aria-labelledby", "gx-hero-h");
    hero.hidden = false;
    hero.innerHTML =
      '<div class="gx-hero2__text">' +
        '<p class="gx-kicker"><span class="gx-pill">' + (current ? "Match of the season so far" : "Match of the season") + "</span><span>" + esc(c.name) + " · " + weekday(m.d) + " " + fmtDate(m.d) + "</span></p>" +
        '<h2 class="gx-hero2__h" id="gx-hero-h">' + esc(f.head) + "</h2>" +
        (f.dek ? '<p class="gx-hero2__dek">' + esc(f.dek) + "</p>" : "") +
        '<div class="gx-verdict"><span class="gx-verdict__n num" aria-hidden="true">' + m.st.toFixed(1) + "</span><div>" +
          '<span class="gx-stars" role="img" aria-label="' + m.st.toFixed(1) + ' out of 5 stars"><span class="gx-stars__on" style="width:' + (m.st / 5 * 100) + '%"></span></span>' +
          '<p class="gx-verdict__t">Match score ' + m.sc.toFixed(1) + " out of 100 · No. 1 of " + DATA.meta.rated + " rated matches</p></div></div>" +
        (m.lb.length ? '<ul class="gx-labels" aria-label="Match types">' + m.lb.map(function (l) { return '<li class="gx-tag">' + esc(l) + "</li>"; }).join("") + "</ul>" : "") +
        '<div class="gx-cta"><a class="gx-btn gx-btn--solid" href="/football/gallery/match/' + esc(m.u) + '">Why it rated ' + m.st.toFixed(1) + '★ <span aria-hidden="true">→</span></a>' +
          '<a class="gx-btn" href="#gx-all">Browse all ' + DATA.meta.rated + " matches</a></div>" +
      "</div>" +
      '<a class="gx-poster" href="/football/gallery/match/' + esc(m.u) + '" style="--fh:' + p[0] + ";--fa:" + p[2] + '" aria-label="' + esc(m.h + " " + m.hg + "–" + m.ag + " " + m.a) + ': open the match page">' +
        '<span class="gx-poster__top"><span class="gx-dchip">' + esc(c.name) + '</span><span class="gx-dchip">' + fmtDate(m.d) + "</span></span>" +
        '<span class="gx-poster__match">' + side(m.hc, m.h, w[0]) + '<span class="gx-poster__score num">' + m.hg + '<span aria-hidden="true">–</span>' + m.ag + "</span>" + side(m.ac, m.a, w[1]) + "</span>" +
        notes.map(function (n) { return '<span class="gx-poster__note">' + esc(n) + "</span>"; }).join("") +
        '<span class="gx-poster__strip"><span class="gx-poster__cap"><span>Who led, minute by minute</span><span class="num">' + (esc(mins) || "No goals") + "</span></span>" + worm(m, p[1], p[3], 64, true) + "</span>" +
      "</a>";
  }

  /* ---------------- shelves (collections) ---------------- */
  function renderShelves() {
    var box = $("gx-shelves"), shown = {}, html = "";
    var label = DATA.meta.season_label;
    var pool = DATA.matches.filter(function (m) { return !m.p; }).sort(byRating);   // partial ratings are never headlined
    var f = DATA.meta.feature;
    if (f) shown[f.k] = 1;
    SHELVES.forEach(function (s) {
      var all = DATA.matches.filter(function (m) { return s.five ? m.st === 5 : m.lb.indexOf(s.label) >= 0; });
      var items = pool.filter(function (m) { return (s.five ? m.st === 5 : m.lb.indexOf(s.label) >= 0) && !shown[m.k]; }).slice(0, SHELF);
      if (all.length < SHELF_MIN || items.length < 3) return;
      items.forEach(function (m) { shown[m.k] = 1; });
      var see = s.label
        ? '<a class="gx-shelf__all" href="?label=' + encodeURIComponent(s.label) + '#gx-all" data-label="' + esc(s.label) + '">See all ' + all.length + ' <span aria-hidden="true">→</span></a>'
        : '<a class="gx-shelf__all" href="#gx-all" data-label="">Browse by rating <span aria-hidden="true">→</span></a>';
      html += '<section class="gx-shelf" aria-labelledby="gx-shelf-' + s.key + '-h" data-shelf="' + s.key + '">' +
        '<div class="gx-shelf__head wrap"><div><h2 class="gx-h2" id="gx-shelf-' + s.key + '-h">' + esc(s.title) + '</h2><p class="gx-sub">' + esc(s.rule(label)) +
        (s.five ? " " + all.length + (DATA.meta.season === INDEX.default ? " so far." : " in all.") : "") + "</p></div>" +
        '<div class="gx-shelf__nav">' + see +
        '<button type="button" class="gx-shelf__btn" data-scroll="-1" aria-label="Scroll ' + esc(s.title) + ' back"><span aria-hidden="true">←</span></button>' +
        '<button type="button" class="gx-shelf__btn" data-scroll="1" aria-label="Scroll ' + esc(s.title) + ' forward"><span aria-hidden="true">→</span></button></div></div>' +
        '<ol class="gx-track">' + items.map(function (m) { return card(m, 0); }).join("") + "</ol></section>";
    });
    box.removeAttribute("aria-busy");
    box.innerHTML = html;
  }

  /* ---------------- season leaders ---------------- */
  function renderLeaders() {
    var L = DATA.meta.leaders, box = $("gx-leaders");
    if (!L || !L.rows.length) { box.hidden = true; box.innerHTML = ""; return; }
    var q = st.season !== INDEX.default ? "?season=" + st.season : "";
    box.hidden = false;
    box.innerHTML = '<div class="gx-sechead"><h2 class="gx-h2" id="gx-leaders-h">Season leaders</h2><p class="gx-sub">Clubs whose matches were the most entertaining, by average match score. ' +
      (L.n_qualifying > L.rows.length ? "Top " + L.rows.length + " of " + L.n_qualifying + " clubs" : L.n_qualifying + " club" + (L.n_qualifying === 1 ? "" : "s")) + " with at least " + L.threshold + " rated matches.</p>" +
      '<a class="gx-shelf__all" href="/football/gallery/clubs' + q + '">All club insights <span aria-hidden="true">→</span></a></div>' +
      '<ol class="gx-lead">' + L.rows.map(function (r) {
        return '<li><a class="gx-lead__link" href="?club=' + encodeURIComponent(r.club_id) + (q ? "&season=" + st.season : "") + '#gx-all" data-club="' + esc(r.club_id) + '">' +
          '<span class="gx-lead__rk num">' + (r.tied ? "=" : "") + r.rank + "</span>" + crest(r.club_id, r.name, 44, "gx-lead__crest") +
          '<span class="gx-lead__n">' + esc(r.name) + '<small>' + r.n + " rated matches</small></span>" +
          '<span class="gx-lead__v num">' + r.value.toFixed(1) + "<small>avg score</small></span></a></li>";
      }).join("") + "</ol>";
  }

  /* ---------------- controls + results ---------------- */
  function renderControls() {
    var meta = DATA.meta;
    $("gx-comps").innerHTML = '<button type="button" class="gx-cchip" data-comp="" aria-pressed="true">All <span class="num">' + meta.rated + "</span></button>" +
      meta.competitions.map(function (c) {
        return '<button type="button" class="gx-cchip" data-comp="' + esc(c.code) + '" aria-pressed="false">' + esc(c.name) + ' <span class="num">' + c.n + "</span></button>";
      }).join("");
    $("gx-label").innerHTML = '<option value="">All match types</option>' + meta.labels.map(function (l) {
      return '<option value="' + esc(l.label) + '" title="' + esc(l.rule) + '">' + esc(l.label) + " (" + l.n + ")</option>";
    }).join("");
    ["gx-from", "gx-to"].forEach(function (id) {
      $(id).min = meta.first_date || ""; $(id).max = meta.last_date || "";
    });
  }
  function syncControls() {
    $("gx-season").value = st.season;
    $("gx-label").value = st.label;
    $("gx-from").value = st.from; $("gx-to").value = st.to;
    Array.prototype.forEach.call(document.querySelectorAll("[data-comp]"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-comp") === st.comp ? "true" : "false");
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-sort]"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-sort") === st.sort ? "true" : "false");
    });
    var adv = st.label || st.from || st.to;
    $("gx-adv-toggle").textContent = adv ? "More filters · on" : "More filters";
    var chips = [];
    if (st.comp) chips.push(["comp", "Competition: " + compOf(st.comp).name]);
    if (st.label) chips.push(["label", "Match type: " + st.label]);
    if (st.club) chips.push(["club", "Club: " + (DATA.meta.clubs[st.club] || st.club)]);
    if (st.from || st.to) chips.push(["dates", "Played " + (st.from ? "from " + fmtDate(st.from) : "") + (st.from && st.to ? " " : "") + (st.to ? "to " + fmtDate(st.to) : "")]);
    $("gx-chips").innerHTML = chips.map(function (c) {
      return '<li><button type="button" class="gx-chip" data-clear="' + c[0] + '" aria-label="Remove filter: ' + esc(c[1]) + '">' +
        (c[0] === "club" ? crest(st.club, DATA.meta.clubs[st.club], 18, "crest--chip") : "") + esc(c[1]) + ' <span aria-hidden="true">×</span></button></li>';
    }).join("");
    $("gx-active").hidden = !chips.length;
  }
  function renderResults() {
    var all = filtered(), out = $("gx-results");
    var total = DATA.meta.rated;
    $("gx-count").textContent = all.length === total ? total + " rated matches" : all.length + " of " + total + " rated matches";
    if (!total) {
      stateBox("empty", "No rated matches yet", "<p>No " + esc(DATA.meta.season_label) + " match has been rated yet. Ratings appear once matches are completed.</p>");
      return;
    }
    if (!all.length) {
      stateBox("empty", "No matches for these filters", "<p>Nothing in " + esc(DATA.meta.season_label) + " matches every filter you've chosen. Remove a filter or clear them all.</p>",
        '<button type="button" class="state__retry" data-action="clear">Clear all filters →</button>');
      return;
    }
    var shown = all.slice(0, st.shown);
    out.removeAttribute("aria-busy");
    out.innerHTML = '<ol class="gx-grid' + (st.sort === "rating" ? " is-ranked" : "") + '">' + shown.map(function (m, i) {
      return card(m, st.sort === "rating" ? i + 1 : 0);
    }).join("") + "</ol>";
    $("gx-more").hidden = all.length <= st.shown;
    $("gx-more-btn").textContent = "Show more matches (" + (all.length - st.shown) + " left)";
  }
  function renderUnrated() {
    var un = DATA.unrated, det = $("gx-unrated");
    det.hidden = !un.length;
    if (!un.length) return;
    $("gx-unrated-sum").textContent = un.length + " " + DATA.meta.season_label + " match" + (un.length > 1 ? "es" : "") + " without a rating";
    $("gx-unrated-list").innerHTML = un.map(function (m) {
      return '<li><a href="/football/gallery/match/' + esc(m.u) + '">' + esc(m.h) + " v " + esc(m.a) + "</a> · " + esc(compOf(m.c).name) + " · " + fmtDate(m.d) + " — " + esc(WHY[m.why] || "not rated") + "</li>";
    }).join("");
  }
  function renderMeta() {
    var m = DATA.meta, u = m.uefa_source || {};
    var line = "Ratings through " + fmtDate(m.last_date) + " · method " + m.method_version + " · calibration " + m.calibration_version + " (2025/26, frozen).";
    if (u.stale && m.competitions.some(function (c) { return ["UCL", "UEL", "UECL"].indexOf(c.code) >= 0; })) {
      line += " European results last refreshed " + (u.last_successful_refresh_utc ? fmtDate(u.last_successful_refresh_utc.slice(0, 10)) : "an unknown date") + " and may be behind.";
    }
    $("gx-meta-line").textContent = line;
  }
  function render() {
    syncControls(); renderResults(); writeURL();
  }

  /* ---------------- state <-> URL ---------------- */
  function readURL() {
    var q = new URLSearchParams(location.search);
    st.season = q.get("season") || INDEX.default;
    st.sort = q.get("sort") === "recent" ? "recent" : "rating";
    st.comp = q.get("comp") || ""; st.label = q.get("label") || ""; st.club = q.get("club") || "";
    st.from = q.get("from") || ""; st.to = q.get("to") || "";
    if (!INDEX.seasons.some(function (s) { return s.season === st.season; })) st.season = INDEX.default;
  }
  function validate() {   // drop filters with no data in this season (never offer or keep an empty option)
    var m = DATA.meta;
    if (st.comp && !m.competitions.some(function (c) { return c.code === st.comp; })) st.comp = "";
    if (st.label && !m.labels.some(function (l) { return l.label === st.label; })) st.label = "";
    if (st.club && !(m.clubs && m.clubs[st.club])) st.club = "";   // a club with no rated match this season
    var re = /^\d{4}-\d{2}-\d{2}$/;
    if (st.from && !re.test(st.from)) st.from = "";
    if (st.to && !re.test(st.to)) st.to = "";
    if (st.from && st.to && st.from > st.to) { var t = st.from; st.from = st.to; st.to = t; }
  }
  function writeURL() {
    var q = new URLSearchParams();
    if (st.season !== INDEX.default) q.set("season", st.season);
    if (st.sort !== "rating") q.set("sort", st.sort);
    ["comp", "label", "club", "from", "to"].forEach(function (k) { if (st[k]) q.set(k, st[k]); });
    var s = q.toString();
    history.replaceState(null, "", location.pathname + (s ? "?" + s : "") + (location.hash === "#gx-all" ? location.hash : ""));
    // the Rankings / Clubs tabs keep the season and competition
    var sub = new URLSearchParams();
    if (st.season !== INDEX.default) sub.set("season", st.season);
    if (st.comp) sub.set("comp", st.comp);
    Array.prototype.forEach.call(document.querySelectorAll("[data-subnav]"), function (a) {
      var base = { matches: "/football/gallery", rankings: "/football/gallery/rankings", clubs: "/football/gallery/clubs" }[a.getAttribute("data-subnav")];
      a.setAttribute("href", base + (sub.toString() ? "?" + sub : ""));
    });
  }
  function toBrowse() {   // after a collection or leader link: show the list, focus its heading
    var h = $("gx-all-h");
    h.setAttribute("tabindex", "-1");
    $("gx-all").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    h.focus({ preventScroll: true });
  }

  /* ---------------- load ---------------- */
  function showSeason(season, keepFilters) {
    $("gx-results").setAttribute("aria-busy", "true");
    $("gx-results").innerHTML = '<div class="state gx-loading" role="status"><p class="state__t">Loading matches</p><p>Fetching the season\'s ratings…</p></div>';
    $("gx-count").textContent = "";
    $("gx-more").hidden = true;
    setControls(false);
    return loadSeason(season).then(function (d) {
      if (st.season !== season) return;   // a newer season request won
      DATA = d; BYK = {};
      d.matches.forEach(function (m) { BYK[m.k] = m; });
      CREST_SET = {}; (d.meta.crests || []).forEach(function (c) { CREST_SET[c] = 1; });
      if (!keepFilters) { st.from = ""; st.to = ""; }
      validate();
      renderControls(); setControls(true); renderMeta(); renderHero(); renderShelves(); renderLeaders(); renderUnrated(); st.shown = PAGE; render();
      if (location.hash === "#gx-all" && keepFilters) toBrowse();
    }).catch(function () {
      if (st.season !== season) return;
      DATA = null;
      $("gx-hero").hidden = true;
      $("gx-shelves").innerHTML = ""; $("gx-leaders").hidden = true;
      stateBox("error", "We couldn't load the match ratings", "<p>No ratings are shown rather than out-of-date or partial ones. Check your connection and try again.</p>",
        '<button type="button" class="state__retry" data-action="retry">Try again →</button>');
    });
  }

  function bind() {
    $("gx-season").addEventListener("change", function () { st.season = this.value; st.shown = PAGE; showSeason(st.season, false); });
    $("gx-comps").addEventListener("click", function (e) {
      var b = e.target.closest("[data-comp]"); if (!b || b.disabled) return;
      st.comp = b.getAttribute("data-comp"); st.shown = PAGE; render();
    });
    $("gx-label").addEventListener("change", function () { st.label = this.value; st.shown = PAGE; render(); });
    ["gx-from", "gx-to"].forEach(function (id) {
      $(id).addEventListener("change", function () {
        st[id === "gx-from" ? "from" : "to"] = this.value; validate(); st.shown = PAGE; render();
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-sort]"), function (b) {
      b.addEventListener("click", function () { st.sort = b.getAttribute("data-sort"); st.shown = PAGE; render(); });
    });
    $("gx-adv-toggle").addEventListener("click", function () {
      var open = this.getAttribute("aria-expanded") !== "true";
      this.setAttribute("aria-expanded", open ? "true" : "false");
      $("gx-adv").classList.toggle("is-open", open);
      if (open) $("gx-label").focus();
    });
    $("gx-controls").addEventListener("submit", function (e) { e.preventDefault(); });
    $("gx-chips").addEventListener("click", function (e) {
      var b = e.target.closest("[data-clear]"); if (!b) return;
      var k = b.getAttribute("data-clear");
      if (k === "dates") { st.from = ""; st.to = ""; } else st[k] = "";
      st.shown = PAGE; render();
      var next = document.querySelector("#gx-chips button") || document.querySelector('[data-comp][aria-pressed="true"]');
      next.focus();
    });
    $("gx-clear").addEventListener("click", clearAll);
    $("gx-results").addEventListener("click", function (e) {
      var b = e.target.closest("[data-action]"); if (!b) return;
      if (b.getAttribute("data-action") === "clear") clearAll();
      else if (!INDEX) init(); else showSeason(st.season, true);
    });
    $("gx-more-btn").addEventListener("click", function () {
      var first = st.shown;
      st.shown += PAGE; renderResults();
      var next = document.querySelectorAll("#gx-results .gx-card__link")[first];
      if (next) next.focus();
    });
    $("gx-shelves").addEventListener("click", function (e) {
      var s = e.target.closest("[data-scroll]");
      if (s) {
        var tr = s.closest(".gx-shelf").querySelector(".gx-track");
        tr.scrollBy({ left: +s.getAttribute("data-scroll") * tr.clientWidth * 0.85, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
        return;
      }
      var a = e.target.closest("[data-label]");
      if (a && DATA) {
        e.preventDefault();
        st.comp = ""; st.club = ""; st.from = ""; st.to = ""; st.label = a.getAttribute("data-label"); st.sort = "rating"; st.shown = PAGE;
        render(); toBrowse();
      }
    });
    $("gx-leaders").addEventListener("click", function (e) {
      var a = e.target.closest("[data-club]");
      if (a && DATA) {
        e.preventDefault();
        st.comp = ""; st.label = ""; st.from = ""; st.to = ""; st.club = a.getAttribute("data-club"); st.shown = PAGE;
        render(); toBrowse();
      }
    });
  }
  function clearAll() {
    st.comp = ""; st.label = ""; st.club = ""; st.from = ""; st.to = ""; st.shown = PAGE; render();
    document.querySelector('[data-comp=""]').focus();
  }

  function init() {
    setControls(false);
    getJSON(BASE + "index.json").then(function (ix) {
      INDEX = ix; readURL(); showSeason(st.season, true);
    }).catch(function () {
      stateBox("error", "We couldn't load the match ratings", "<p>No ratings are shown rather than out-of-date or partial ones. Check your connection and try again.</p>",
        '<button type="button" class="state__retry" data-action="retry">Try again →</button>');
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { bind(); init(); });
  else { bind(); init(); }
})();
