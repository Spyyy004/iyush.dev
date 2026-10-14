/* Football Match Gallery (M2): browse the season's rated matches.
   Reads football/data/gallery/<season>.json, exported by scripts/build_gallery.py from the research project's
   Match Entertainment Rating output. Ratings, stars and labels are displayed exactly as stored; nothing is rated,
   rescored or filled in here. Unrated matches never get stars. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var PAGE = 48, FEATURED = 4;
  var BASE = "/football/data/gallery/";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var WHY = {
    not_played: "not played (postponed or abandoned)",
    source_conflict: "the data sources disagree on the result",
    invalid_source_record: "the source record is incomplete",
    goal_timeline_does_not_match_score: "the goal data is incomplete"
  };
  var MISSING = { shots_on_target: "shots on target", red_cards: "red cards", penalties: "penalties" };

  var cache = {}, INDEX = null, DATA = null;
  var st = { season: null, sort: "rating", comp: "", label: "", club: "", from: "", to: "", shown: PAGE };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmtDate(d) {
    if (!d || !/^\d{4}-\d{2}-\d{2}$/.test(d)) return "Date unknown";
    return +d.slice(8, 10) + " " + MONTHS[+d.slice(5, 7) - 1] + " " + d.slice(0, 4);
  }
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
  function featured() {   // complete ratings only: a partial rating is never headlined
    return DATA.matches.filter(function (m) { return !m.p; }).sort(byRating).slice(0, FEATURED);
  }
  function isDefaultView() { return st.sort === "rating" && !st.comp && !st.label && !st.club && !st.from && !st.to; }
  function filtered() {
    return DATA.matches.filter(function (m) {
      return (!st.comp || m.c === st.comp) && (!st.label || m.lb.indexOf(st.label) >= 0) &&
        (!st.club || m.hc === st.club || m.ac === st.club) &&
        (!st.from || m.d >= st.from) && (!st.to || m.d <= st.to);
    }).sort(st.sort === "recent" ? byRecent : byRating);
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
    if (m.so) bits.push("aet · " + m.so[0] + "–" + m.so[1] + " on penalties");
    else if (m.aet) bits.push("after extra time");
    if (m.fl) bits.push("2nd leg · agg " + (m.fl[0] + m.hg) + "–" + (m.fl[1] + m.ag));
    return bits.length ? '<p class="gx-card__note">' + esc(bits.join(" · ")) + "</p>" : "";
  }
  function teamRow(name, goals, win) {
    return '<div class="gx-team' + (win ? " is-win" : "") + '"><span class="gx-team__n">' + esc(name || "Unknown team") +
      '</span><span class="gx-team__g num">' + (goals == null ? "–" : goals) + "</span></div>";
  }
  function card(m, rank, big) {
    var c = compOf(m.c);
    var homeWin = m.so ? m.so[0] > m.so[1] : m.hg > m.ag, awayWin = m.so ? m.so[1] > m.so[0] : m.ag > m.hg;
    var labels = m.lb.map(function (l) { return '<li class="gx-tag">' + esc(l) + "</li>"; }).join("");
    var partial = m.p ? '<p class="gx-partial" title="Missing: ' + esc(m.p.map(function (x) { return MISSING[x] || x; }).join(", ")) +
      '"><span aria-hidden="true">◐</span> Partial rating <span class="sr-only">(missing ' +
      esc(m.p.map(function (x) { return MISSING[x] || x; }).join(", ")) + ")</span></p>" : "";
    var aria = (m.h || "Unknown") + " " + m.hg + ", " + (m.a || "Unknown") + " " + m.ag + ". " + c.name + ", " + fmtDate(m.d) +
      ". " + (m.st % 1 ? m.st.toFixed(1) : m.st) + " out of 5 stars" + (m.p ? ", partial rating" : "") + ".";
    return '<li class="gx-card' + (big ? " gx-card--feat" : "") + (m.p ? " is-partial" : "") + '" data-k="' + esc(m.k) + '">' +
      '<a class="gx-card__link" href="/football/gallery/match/' + esc(m.u) + '" aria-label="' + esc(aria + " Open match page.") + '">' +
      '<article>' +
      '<header class="gx-card__top"><span class="gx-comp" data-c="' + esc(m.c) + '">' + esc(c.name) + "</span>" +
      (rank ? '<span class="gx-rank num" aria-label="Rank ' + rank + '">#' + rank + "</span>" : "") +
      '<time class="gx-date" datetime="' + esc(m.d) + '">' + fmtDate(m.d) + "</time></header>" +
      '<div class="gx-score">' + teamRow(m.h, m.hg, homeWin) + teamRow(m.a, m.ag, awayWin) + "</div>" + scoreNote(m) +
      '<div class="gx-card__rate">' + starsHTML(m.st) + "</div>" + partial +
      (labels ? '<ul class="gx-tags" aria-label="Match types">' + labels + "</ul>" : "") +
      "</article></a></li>";
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

  /* ---------------- render ---------------- */
  function renderFeatured() {
    var f = featured(), ol = $("gx-feat");
    $("gx-feat-sub").textContent = f.length ? "The highest-rated matches of " + DATA.meta.season_label + " so far." : "";
    ol.innerHTML = f.length ? f.map(function (m, i) { return card(m, i + 1, true); }).join("")
      : '<li class="gx-feat__empty">No rated matches yet this season.</li>';
  }
  function renderControls() {
    var meta = DATA.meta;
    $("gx-comp").innerHTML = '<option value="">All competitions</option>' + meta.competitions.map(function (c) {
      return '<option value="' + esc(c.code) + '">' + esc(c.name) + " (" + c.n + ")</option>";
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
    $("gx-comp").value = st.comp; $("gx-label").value = st.label;
    $("gx-from").value = st.from; $("gx-to").value = st.to;
    Array.prototype.forEach.call(document.querySelectorAll("[data-sort]"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-sort") === st.sort ? "true" : "false");
    });
    var chips = [];
    if (st.comp) chips.push(["comp", "Competition: " + compOf(st.comp).name]);
    if (st.label) chips.push(["label", "Match type: " + st.label]);
    if (st.club) chips.push(["club", "Club: " + (DATA.meta.clubs[st.club] || st.club)]);
    if (st.from || st.to) chips.push(["dates", "Played " + (st.from ? "from " + fmtDate(st.from) : "") + (st.from && st.to ? " " : "") + (st.to ? "to " + fmtDate(st.to) : "")]);
    $("gx-chips").innerHTML = chips.map(function (c) {
      return '<li><button type="button" class="gx-chip" data-clear="' + c[0] + '" aria-label="Remove filter: ' + esc(c[1]) + '">' +
        esc(c[1]) + ' <span aria-hidden="true">×</span></button></li>';
    }).join("");
    $("gx-active").hidden = !chips.length;
  }
  function renderResults() {
    var all = filtered(), out = $("gx-results");
    var skip = {}, list = all;
    if (isDefaultView()) {   // the top matches are already featured above: continue the ranking below them
      featured().forEach(function (m) { skip[m.k] = 1; });
      list = all.filter(function (m) { return !skip[m.k]; });
    }
    var total = DATA.meta.rated;
    $("gx-count").textContent = all.length === total
      ? total + " rated matches" + (isDefaultView() && list.length < all.length ? " · the top " + (all.length - list.length) + " are featured above" : "")
      : all.length + " of " + total + " rated matches";
    if (!total) {
      stateBox("empty", "No rated matches yet", "<p>No " + esc(DATA.meta.season_label) + " match has been rated yet. Ratings appear once matches are completed.</p>");
      return;
    }
    if (!all.length) {
      stateBox("empty", "No matches for these filters", "<p>Nothing in " + esc(DATA.meta.season_label) + " matches every filter you've chosen. Remove a filter or clear them all.</p>",
        '<button type="button" class="state__retry" data-action="clear">Clear all filters →</button>');
      return;
    }
    var offset = all.length - list.length;
    var shown = list.slice(0, st.shown);
    out.removeAttribute("aria-busy");
    out.innerHTML = '<ol class="gx-grid" start="' + (offset + 1) + '">' + shown.map(function (m, i) {
      return card(m, st.sort === "rating" ? offset + i + 1 : 0, false);
    }).join("") + "</ol>";
    $("gx-more").hidden = list.length <= st.shown;
    $("gx-more-btn").textContent = "Show more matches (" + (list.length - st.shown) + " left)";
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
    $("gx-eyebrow-season").textContent = m.season_label;
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
    history.replaceState(null, "", location.pathname + (s ? "?" + s : ""));
    // the Rankings / Clubs tabs keep the season and competition
    var sub = new URLSearchParams();
    if (st.season !== INDEX.default) sub.set("season", st.season);
    if (st.comp) sub.set("comp", st.comp);
    Array.prototype.forEach.call(document.querySelectorAll("[data-subnav]"), function (a) {
      var base = { matches: "/football/gallery", rankings: "/football/gallery/rankings", clubs: "/football/gallery/clubs" }[a.getAttribute("data-subnav")];
      a.setAttribute("href", base + (sub.toString() ? "?" + sub : ""));
    });
  }

  /* ---------------- load ---------------- */
  function showSeason(season, keepFilters) {
    $("gx-results").setAttribute("aria-busy", "true");
    $("gx-results").innerHTML = '<div class="state gx-loading" role="status"><p class="state__t">Loading matches</p><p>Fetching the season\'s ratings…</p></div>';
    $("gx-feat").innerHTML = "";
    $("gx-count").textContent = "";
    $("gx-more").hidden = true;
    setControls(false);
    return loadSeason(season).then(function (d) {
      if (st.season !== season) return;   // a newer season request won
      DATA = d;
      if (!keepFilters) { st.from = ""; st.to = ""; }
      validate();
      renderControls(); setControls(true); renderMeta(); renderFeatured(); renderUnrated(); st.shown = PAGE; render();
    }).catch(function () {
      if (st.season !== season) return;
      DATA = null;
      $("gx-feat").innerHTML = '<li class="gx-feat__empty">Featured matches are unavailable right now.</li>';
      stateBox("error", "We couldn't load the match ratings", "<p>No ratings are shown rather than out-of-date or partial ones. Check your connection and try again.</p>",
        '<button type="button" class="state__retry" data-action="retry">Try again →</button>');
    });
  }

  function bind() {
    $("gx-season").addEventListener("change", function () { st.season = this.value; st.shown = PAGE; showSeason(st.season, false); });
    $("gx-comp").addEventListener("change", function () { st.comp = this.value; st.shown = PAGE; render(); });
    $("gx-label").addEventListener("change", function () { st.label = this.value; st.shown = PAGE; render(); });
    ["gx-from", "gx-to"].forEach(function (id) {
      $(id).addEventListener("change", function () {
        st[id === "gx-from" ? "from" : "to"] = this.value; validate(); st.shown = PAGE; render();
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-sort]"), function (b) {
      b.addEventListener("click", function () { st.sort = b.getAttribute("data-sort"); st.shown = PAGE; render(); });
    });
    $("gx-controls").addEventListener("submit", function (e) { e.preventDefault(); });
    $("gx-chips").addEventListener("click", function (e) {
      var b = e.target.closest("[data-clear]"); if (!b) return;
      var k = b.getAttribute("data-clear");
      if (k === "dates") { st.from = ""; st.to = ""; } else st[k] = "";
      st.shown = PAGE; render();
      var next = document.querySelector("#gx-chips button") || $("gx-comp");
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
  }
  function clearAll() {
    st.comp = ""; st.label = ""; st.club = ""; st.from = ""; st.to = ""; st.shown = PAGE; render(); $("gx-comp").focus();
  }

  function init() {
    setControls(false);
    getJSON(BASE + "index.json").then(function (ix) {
      INDEX = ix; readURL(); showSeason(st.season, true);
    }).catch(function () {
      $("gx-feat").innerHTML = '<li class="gx-feat__empty">Featured matches are unavailable right now.</li>';
      stateBox("error", "We couldn't load the match ratings", "<p>No ratings are shown rather than out-of-date or partial ones. Check your connection and try again.</p>",
        '<button type="button" class="state__retry" data-action="retry">Try again →</button>');
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { bind(); init(); });
  else { bind(); init(); }
})();
