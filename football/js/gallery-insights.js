/* Football Match Gallery — season rankings and club insights (M4).
   Reads football/data/gallery/{rankings,clubs}_<season>.json, copied by scripts/build_gallery.py from the research
   project's insights (src/gallery/insights.py). Every list, average, median, rate, rank and threshold is displayed as
   stored; this file only formats, sorts table columns on request and pages through long lists. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var KIND = document.querySelector("[data-insights]").getAttribute("data-insights");
  var BASE = "/football/data/gallery/";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var COMP = { EPL: "Premier League", La_Liga: "La Liga", Serie_A: "Serie A", Bundesliga: "Bundesliga", Ligue_1: "Ligue 1",
    UCL: "Champions League", UEL: "Europa League", UECL: "Conference League" };
  var ORDER = ["EPL", "La_Liga", "Serie_A", "Bundesliga", "Ligue_1", "UCL", "UEL", "UECL"];
  var SHOW = 10;
  var cache = {}, INDEX = null, DATA = null;
  var st = { season: null, comp: "", sort: { key: "name", dir: 1 } };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  var CREST_SET = {};
  function crest(cid, name, size, cls) {   // decorative: the club name is always beside it
    if (cid && CREST_SET[cid]) {
      return '<img class="crest ' + (cls || "") + '" src="/football/crests/' + esc(cid.replace(":", "-")) + '.png" width="' + size + '" height="' + size + '" alt="" loading="lazy" decoding="async" />';
    }
    var ini = String(name || "?").replace(/\./g, " ").split(/\s+/).filter(Boolean).slice(0, 2).map(function (w) { return w[0]; }).join("").toUpperCase();
    return '<span class="crest crest--none ' + (cls || "") + '" style="width:' + size + "px;height:" + size + 'px" aria-hidden="true">' + esc(ini) + "</span>";
  }
  function fmtDate(d) { return d ? +d.slice(8, 10) + " " + MONTHS[+d.slice(5, 7) - 1] + " " + d.slice(0, 4) : "Date unknown"; }
  function pct(num, den) { return den ? Math.round(100 * num / den) + "%" : "–"; }
  function getJSON(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
  }
  function load(season) {
    var k = KIND + season;
    if (!cache[k]) cache[k] = getJSON(BASE + KIND + "_" + season + ".json").catch(function (e) { delete cache[k]; throw e; });
    return cache[k];
  }
  function stars(s) {
    return '<span class="gx-stars gi-stars" role="img" aria-label="' + s.toFixed(1) + ' out of 5 stars"><span class="gx-stars__on" style="width:' + (s / 5 * 100) + '%"></span></span>' +
      '<span class="gi-starn num" aria-hidden="true">' + s.toFixed(1) + "</span>";
  }
  function galleryHref(extra) {
    var q = new URLSearchParams();
    if (st.season !== INDEX.default) q.set("season", st.season);
    if (st.comp) q.set("comp", st.comp);
    Object.keys(extra || {}).forEach(function (k) { q.set(k, extra[k]); });
    var s = q.toString();
    return "/football/gallery" + (s ? "?" + s : "");
  }
  function clubLink(id, name) {
    return '<a class="gi-club" href="' + esc(galleryHref({ club: id })) + '">' + crest(id, name, 22, "gi-crest") + "<span>" + esc(name) + "</span></a>";
  }
  function stateBox(kind, title, body, action) {
    var out = $("gi-results");
    out.removeAttribute("aria-busy");
    out.innerHTML = '<div class="state state--' + kind + '"' + (kind === "error" ? ' role="alert"' : "") + '><p class="state__t">' + esc(title) + "</p>" + body + (action || "") + "</div>";
  }

  /* ---------------- shared: controls, context, coverage, URL ---------------- */
  function scopeData() { return DATA.scopes[st.comp || "all"]; }
  function renderControls() {
    $("gi-season").innerHTML = INDEX.seasons.map(function (s) {
      return '<option value="' + s.season + '"' + (s.season === st.season ? " selected" : "") + ">" + esc(s.label) + (s.archive ? " · archive" : "") + "</option>";
    }).join("");
    var comps = ORDER.filter(function (c) { return DATA.scopes[c]; });
    $("gi-comp").innerHTML = '<option value="">All competitions (' + DATA.scopes.all.rated + ")</option>" + comps.map(function (c) {
      return '<option value="' + c + '"' + (c === st.comp ? " selected" : "") + ">" + esc(COMP[c]) + " (" + DATA.scopes[c].rated + ")</option>";
    }).join("");
  }
  function renderContext() {
    var m = DATA.meta, cov = m.coverage, sc = scopeData();
    $("gi-context").textContent = m.season_label + " · " + (st.comp ? COMP[st.comp] : "All competitions") +
      (cov.in_progress ? " · in progress, through " + fmtDate(cov.through) : " · complete season");
    var bits = [sc.rated + " rated matches" + (sc.partial ? " (" + sc.partial + " partial)" : "")];
    if (sc.unrated) bits.push(sc.unrated + " unrated match" + (sc.unrated > 1 ? "es" : "") + " not counted");
    var covered = "Covers " + cov.competitions.map(function (c) { return COMP[c]; }).join(", ") + ".";
    if (cov.not_started.length) covered += " Not started yet: " + cov.not_started.map(function (c) { return COMP[c]; }).join(", ") + ".";
    covered += " Not covered: " + cov.not_covered + ".";
    $("gi-coverage").innerHTML = esc(bits.join(" · ")) + ". " + esc(covered);
    document.querySelectorAll("[data-subnav]").forEach(function (a) {
      var base = { matches: "/football/gallery", rankings: "/football/gallery/rankings", clubs: "/football/gallery/clubs" }[a.getAttribute("data-subnav")];
      var q = new URLSearchParams();
      if (st.season !== INDEX.default) q.set("season", st.season);
      if (st.comp) q.set("comp", st.comp);
      a.setAttribute("href", base + (q.toString() ? "?" + q : ""));
    });
  }
  function writeURL() {
    var q = new URLSearchParams();
    if (st.season !== INDEX.default) q.set("season", st.season);
    if (st.comp) q.set("comp", st.comp);
    history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q : "") + location.hash);
  }

  /* ---------------- rankings ---------------- */
  var LIST_VALUE = {
    highest_scoring: function (v) { return v + " goals"; },
    closest_finishes: function (v) { return "competitiveness " + v.toFixed(2); },
    most_chaotic: function (v) { return v + " chaos events"; },
    most_one_sided: function (v) { return "won by " + v; }
  };
  var LIST_GALLERY = {   // only where the gallery shows the same set of matches
    highest_rated: function () { return {}; },
    hidden_gems: function () { return { label: "Hidden Gem" }; },
    most_chaotic: function () { return { label: "Chaos" }; },
    most_one_sided: function () { return { label: "One-Sided" }; }
  };
  function matchRow(m, rank, key) {
    var sc = m.hg + "–" + m.ag + (m.so ? " (" + m.so[0] + "–" + m.so[1] + " pens)" : m.aet ? " aet" : "");
    var value = m.v != null && LIST_VALUE[key] ? '<span class="gi-row__v num">' + esc(LIST_VALUE[key](m.v)) + "</span>" : "";
    var partial = m.p ? '<span class="gi-partial"><span aria-hidden="true">◐</span> Partial rating</span>' : "";
    var labels = m.lb.length ? '<span class="gi-row__lb">' + m.lb.map(function (l) { return '<span class="gx-tag">' + esc(l) + "</span>"; }).join("") + "</span>" : "";
    return '<li class="gi-row"><a class="gi-row__link" href="/football/gallery/match/' + esc(m.u) + '">' +
      '<span class="gi-row__rank num" aria-label="Rank ' + rank + '">' + rank + "</span>" +
      '<span class="gi-row__main"><span class="gi-row__teams">' + crest(m.hc, m.h, 20, "gi-crest") + esc(m.h) + ' <span class="num gi-row__sc">' + esc(sc) + "</span> " + esc(m.a) + crest(m.ac, m.a, 20, "gi-crest gi-crest--after") + "</span>" +
      '<span class="gi-row__meta">' + esc(COMP[m.c]) + " · " + fmtDate(m.d) + "</span>" + labels + partial + "</span>" +
      '<span class="gi-row__side">' + stars(m.st) + value + "</span></a></li>";
  }
  function renderRankings() {
    var sc = scopeData(), keys = Object.keys(sc.lists), out = $("gi-results");
    if (!sc.rated) { stateBox("empty", "No rated matches yet", "<p>Rankings appear once matches in this season and competition are rated.</p>"); return; }
    var toc = '<nav class="gi-toc" aria-label="Lists on this page"><ul>' + keys.map(function (k) {
      return '<li><a href="#gi-' + k + '">' + esc(sc.lists[k].title) + "</a></li>";
    }).join("") + "</ul></nav>";
    var html = keys.map(function (k) {
      var l = sc.lists[k];
      var head = '<header class="gi-sec__head"><h2 class="gx-h2" id="gi-' + k + '-h">' + esc(l.title) + '</h2><p class="gi-sec__rule">' + esc(l.rule) + "</p>" +
        '<p class="gi-sec__n">' + l.n_eligible + " match" + (l.n_eligible === 1 ? "" : "es") + " qualify" + (l.n_eligible === 1 ? "s" : "") + "</p></header>";
      if (!l.available) {
        return '<section class="gi-sec" id="gi-' + k + '" aria-labelledby="gi-' + k + '-h">' + head +
          '<div class="state state--empty"><p class="state__t">Not enough matches yet</p><p>' + l.n_eligible + " of the " + DATA.meta.thresholds.list +
          " matches needed to show this list.</p></div></section>";
      }
      var rows = l.shown.map(function (m, i) { return matchRow(m, i + 1, k); });
      var more = rows.length > SHOW ? '<button type="button" class="btn btn--ghost gi-more" data-more="' + k + '">Show top ' + rows.length + "</button>" : "";
      var gal = LIST_GALLERY[k] ? '<a class="link-arrow gi-all" href="' + esc(galleryHref(LIST_GALLERY[k]())) + '">All ' + l.n_eligible + " in the gallery <span class=\"arr\" aria-hidden=\"true\">→</span></a>" : "";
      return '<section class="gi-sec" id="gi-' + k + '" aria-labelledby="gi-' + k + '-h">' + head +
        '<ol class="gi-list" data-list="' + k + '">' + rows.map(function (r, i) { return i < SHOW ? r : r.replace('<li class="gi-row"', '<li class="gi-row" hidden'); }).join("") + "</ol>" +
        '<div class="gi-sec__foot">' + more + gal + "</div></section>";
    }).join("");
    out.removeAttribute("aria-busy");
    out.innerHTML = toc + html;
  }

  /* ---------------- clubs ---------------- */
  var BOARD_TEXT = {
    entertaining: "Average match score of the club’s rated matches (0–100, before conversion to stars).",
    chaotic: "Share of the club’s rated matches labelled Chaos.",
    late_drama: "Share of the club’s rated matches labelled Late Drama.",
    one_sided: "Share of the club’s rated matches labelled One-Sided (won or lost by 3 or more).",
    hidden_gems: "Share of the club’s rated matches labelled Hidden Gem (4 stars or more with 2 goals or fewer)."
  };
  function sampleNote(r) {
    return '<span class="gi-n num">' + r.n + " matches" + (r.n_partial ? " · " + r.n_partial + " partial" : "") + "</span>" +
      (r.european_only ? '<span class="gi-eu">European matches only</span>' : "");
  }
  function boardHTML(key, b) {
    var head = '<header class="gi-sec__head"><h2 class="gx-h2" id="gi-' + key + '-h">' + esc(b.title) + '</h2><p class="gi-sec__rule">' + esc(BOARD_TEXT[key]) + "</p>" +
      '<p class="gi-sec__n">' + b.n_qualifying + " club" + (b.n_qualifying === 1 ? "" : "s") + " with at least " + b.threshold + " rated matches · " +
      b.matches_used + " club-matches counted</p></header>";
    var body;
    if (!b.rows.length) {
      var most = b.below[0];
      body = '<div class="state state--insufficient"><p class="state__t">Not enough evidence to rank clubs yet</p><p>A club needs at least ' + b.threshold +
        " rated matches in this selection before it is ranked here." + (most ? " The most so far is " + most.n + " (" + esc(most.name) + ")." : "") + "</p></div>";
    } else {
      var rows = b.rows.map(function (r, i) {
        var val = b.kind === "average"
          ? '<span class="num gi-val">' + r.value.toFixed(1) + '</span><span class="gi-sub num">median ' + r.median.toFixed(1) + "</span>"
          : '<span class="num gi-val">' + r.count + "/" + r.n + " (" + pct(r.count, r.n) + ")</span>";
        return "<tr" + (i >= SHOW ? " hidden" : "") + '><td class="num gi-rank">' + (r.tied ? "=" : "") + r.rank + "</td><th scope=\"row\">" + clubLink(r.club_id, r.name) +
          sampleNote(r) + "</th><td>" + val + "</td></tr>";
      }).join("");
      body = '<div class="gi-tw"><table class="gi-board"><thead><tr><th scope="col">Rank</th><th scope="col">Club</th><th scope="col">' +
        (b.kind === "average" ? "Average match score" : esc(b.label) + " matches") + "</th></tr></thead><tbody>" + rows + "</tbody></table></div>" +
        (b.rows.length > SHOW ? '<div class="gi-sec__foot"><button type="button" class="btn btn--ghost gi-more" data-more="' + key + '">Show all ' + b.rows.length + " clubs</button></div>" : "");
    }
    var below = b.below.length ? '<details class="gi-below"><summary>' + b.below.length + " club" + (b.below.length === 1 ? "" : "s") +
      " below " + b.threshold + " rated matches: not ranked yet</summary><ul>" + b.below.map(function (x) {
        return "<li>" + clubLink(x.club_id, x.name) + ' <span class="num gi-n">' + x.n + " of " + b.threshold + " (needs " + x.needed + " more)</span></li>";
      }).join("") + "</ul></details>" : "";
    var ex = b.european_only_excluded || [];
    var euro = ex.length ? '<details class="gi-below gi-euro"><summary>' + ex.length + " club" + (ex.length === 1 ? "" : "s") +
      " seen only in European matches: not ranked across all competitions</summary><p>Their domestic leagues are not covered, so their figures come from European matches alone and are not like-for-like with league clubs. Choose a European competition above to see them ranked.</p><ul>" +
      ex.map(function (x) { return "<li>" + clubLink(x.club_id, x.name) + ' <span class="num gi-n">' + x.n + " matches</span></li>"; }).join("") + "</ul></details>" : "";
    return '<section class="gi-sec" id="gi-' + key + '" aria-labelledby="gi-' + key + '-h" data-board="' + key + '">' + head + body + below + euro + "</section>";
  }
  var COLS = [
    ["name", "Club"], ["n", "Matches"], ["mean", "Avg"], ["median", "Median"], ["n_4plus", "4★+"],
    ["Thriller", "Thriller"], ["Goal Fest", "Goal Fest"], ["Late Drama", "Late Drama"], ["Comeback", "Comeback"],
    ["Chaos", "Chaos"], ["Hidden Gem", "Hidden Gem"], ["One-Sided", "One-Sided"]
  ];
  function colVal(c, key) {
    if (key === "name") return c.name.toLowerCase();
    if (key in c) return c[key];
    return c.labels[key];
  }
  function clubTable(clubs) {
    var s = st.sort;
    var rows = clubs.slice().sort(function (a, b) {
      var x = colVal(a, s.key), y = colVal(b, s.key);
      return (x < y ? -1 : x > y ? 1 : 0) * s.dir || (a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1) || (a.club_id < b.club_id ? -1 : 1);
    });
    var head = COLS.map(function (c) {
      var on = s.key === c[0];
      return '<th scope="col" aria-sort="' + (on ? (s.dir > 0 ? "ascending" : "descending") : "none") + '"><button type="button" class="gi-sort" data-sort="' + esc(c[0]) + '">' + esc(c[1]) +
        (on ? '<span aria-hidden="true">' + (s.dir > 0 ? " ▲" : " ▼") + "</span>" : "") + "</button></th>";
    }).join("") + '<th scope="col">Best match</th>';
    var body = rows.map(function (c) {
      var labels = ["Thriller", "Goal Fest", "Late Drama", "Comeback", "Chaos", "Hidden Gem", "One-Sided"].map(function (l) {
        return '<td class="num">' + c.labels[l] + "</td>";
      }).join("");
      var b = c.best;
      return '<tr><th scope="row">' + clubLink(c.club_id, c.name) + (c.european_only ? '<span class="gi-eu">European matches only</span>' : "") + "</th>" +
        '<td class="num">' + c.n + (c.n_partial ? '<small> (' + c.n_partial + " partial)</small>" : "") + "</td>" +
        '<td class="num">' + c.mean.toFixed(1) + '</td><td class="num">' + c.median.toFixed(1) + "</td>" +
        '<td class="num">' + c.n_4plus + "/" + c.n + "</td>" + labels +
        '<td><a href="/football/gallery/match/' + esc(b.u) + '">' + esc(b.h) + " " + b.hg + "–" + b.ag + " " + esc(b.a) + "</a> <span class=\"num gi-sub\">" + b.st.toFixed(1) + "★</span></td></tr>";
    }).join("");
    return '<section class="gi-sec" aria-labelledby="gi-all-h"><header class="gi-sec__head"><h2 class="gx-h2" id="gi-all-h">All clubs</h2>' +
      '<p class="gi-sec__rule">Every club with a rated match in this selection. Counts are out of the club’s rated matches; sort any column. Small samples are shown but not ranked above.</p></header>' +
      '<div class="gi-tw gi-tw--wide"><table class="gi-table"><caption class="sr-only">All clubs, ' + rows.length + " rows</caption><thead><tr>" + head + "</tr></thead><tbody>" + body + "</tbody></table></div></section>";
  }
  function renderClubs() {
    var sc = scopeData(), out = $("gi-results");
    if (!sc.rated) { stateBox("empty", "No rated matches yet", "<p>Club insights appear once matches in this season and competition are rated.</p>"); return; }
    var intro = '<aside class="gi-explain"><p><b>What these numbers mean.</b> They describe the matches a club played in, not the club’s quality or style: a high average means its matches were rated as entertaining, whoever made them so. ' +
      "Every figure is out of the club’s rated matches in this season and selection (unrated matches are not counted), and the sample size is shown beside it. " +
      "A club is ranked on average match score from " + DATA.meta.thresholds.average + " rated matches and on label rates from " + DATA.meta.thresholds.label_rate +
      ". Clubs outside the top five leagues appear only through their European matches, so across all competitions they are listed but not ranked. Club crests are trademarks of their clubs; images via ESPN.</p></aside>";
    var boards = Object.keys(sc.leaderboards).map(function (k) { return boardHTML(k, sc.leaderboards[k]); }).join("");
    out.removeAttribute("aria-busy");
    out.innerHTML = intro + '<div class="gi-boards">' + boards + "</div>" + clubTable(sc.clubs);
  }

  /* ---------------- load + events ---------------- */
  function render() {
    renderControls(); renderContext(); writeURL();
    if (KIND === "rankings") renderRankings(); else renderClubs();
  }
  function setControls(on) { ["gi-season", "gi-comp"].forEach(function (id) { $(id).disabled = !on; }); }
  function show(season) {
    $("gi-results").setAttribute("aria-busy", "true");
    $("gi-results").innerHTML = '<div class="state gx-loading" role="status"><p class="state__t">Loading</p><p>Fetching the season’s rankings…</p></div>';
    setControls(false);
    return load(season).then(function (d) {
      if (st.season !== season) return;
      DATA = d;
      CREST_SET = {}; (d.meta.crests || []).forEach(function (c) { CREST_SET[c] = 1; });
      if (st.comp && !DATA.scopes[st.comp]) st.comp = "";
      setControls(true); render();
    }).catch(function () {
      if (st.season !== season) return;
      DATA = null;
      $("gi-context").textContent = "unavailable";
      $("gi-coverage").textContent = "";
      stateBox("error", "We couldn’t load the rankings", "<p>Nothing is shown rather than out-of-date figures. Check your connection and try again.</p>",
        '<button type="button" class="state__retry" data-action="retry">Try again →</button>');
      $("gi-season").disabled = false;
    });
  }
  function init() {
    getJSON(BASE + "index.json").then(function (ix) {
      INDEX = ix;
      var q = new URLSearchParams(location.search);
      st.season = q.get("season") || ix.default;
      if (!ix.seasons.some(function (s) { return s.season === st.season; })) st.season = ix.default;
      st.comp = q.get("comp") || "";
      $("gi-season").innerHTML = ix.seasons.map(function (s) { return '<option value="' + s.season + '">' + esc(s.label) + "</option>"; }).join("");
      show(st.season);
    }).catch(function () {
      stateBox("error", "We couldn’t load the rankings", "<p>Check your connection and try again.</p>",
        '<button type="button" class="state__retry" data-action="retry">Try again →</button>');
    });
  }
  function bind() {
    $("gi-season").addEventListener("change", function () { st.season = this.value; show(st.season); });
    $("gi-comp").addEventListener("change", function () { st.comp = this.value; if (DATA) render(); });
    $("gi-controls").addEventListener("submit", function (e) { e.preventDefault(); });
    $("gi-results").addEventListener("click", function (e) {
      var r = e.target.closest("[data-action=retry]");
      if (r) { if (!INDEX) init(); else show(st.season); return; }
      var more = e.target.closest("[data-more]");
      if (more) {
        var sec = more.closest(".gi-sec");
        var hidden = sec.querySelectorAll("li[hidden], tr[hidden]");
        hidden.forEach(function (el) { el.hidden = false; });
        more.remove();
        var first = hidden[0] && hidden[0].querySelector("a");
        if (first) first.focus();
        return;
      }
      var sort = e.target.closest("[data-sort]");
      if (sort) {
        var key = sort.getAttribute("data-sort");
        st.sort = st.sort.key === key ? { key: key, dir: -st.sort.dir } : { key: key, dir: key === "name" ? 1 : -1 };
        var y = window.scrollY;
        renderClubs(); window.scrollTo(0, y);
        var b = document.querySelector('[data-sort="' + key + '"]'); if (b) b.focus();
      }
    });
  }
  bind(); init();
})();
