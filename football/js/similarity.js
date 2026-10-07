/* Similarity Explorer (M3). Looks up precomputed Study 4 results — nothing is calculated here.
   Data: /football/data/sim/ (profiles as of the latest matches, rebuilt weekly) or /football/data/sim-2025/ (?as=2025);
   scripts/build_similarity.py runs the research engine for every query.
   The only arithmetic in this file is presentation: per-metric gaps between two published z-scores, labelled with the
   Study 4 case study's own thresholds (meta.rules). */
(function () {
  "use strict";
  var AS = new URLSearchParams(location.search).get("as") === "2025" ? "2025" : "";   // season switch: "" = latest
  var FB = window.FB, BASE = "/football/data/" + (AS ? "sim-" + AS : "sim") + "/";
  var WIN = { 1: "w1", 2: "w2", 3: "w3" };
  var GROUP_LABEL = { "chance creation": "Chance creation", "involvement": "Involvement", "shooting volume": "Shooting volume", "shot profile": "Shot profile" };
  var META, PLAYERS, BY_KEY = {}, BY_SLUG = {}, cacheR = {}, cacheZ = {};
  var sel = { key: null, league: "Serie_A", seasons: 3 }, view = null;
  var $ = function (id) { return document.getElementById(id); };
  var esc = FB.esc;

  /* ---------------- data ---------------- */
  function getJSON(path, cache, key) {
    if (cache && cache[key]) return cache[key];
    var p = fetch(BASE + path).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    if (cache) { cache[key] = p; p.catch(function () { delete cache[key]; }); }
    return p;
  }
  function player(key) { var r = BY_KEY[key]; return r && { key: r[0], name: r[1], team: r[2], league: r[3], role: META.roles[r[4]], slug: r[5], mins: r[6] }; }

  /* ---------------- research language (Study 4 case-study rules) ---------------- */
  function verdict(absd) { return absd <= META.rules.similar ? "strong" : absd <= META.rules.moderate ? "moderate" : "diverge"; }
  var VERDICT = { strong: "Strong match", moderate: "Moderate match", diverge: "Divergence" };
  function groups(qz, cz) {
    return Object.keys(META.groups).map(function (g) {
      var ix = META.groups[g], sa = 0, sd = 0;
      ix.forEach(function (i) { sa += Math.abs(cz[i] - qz[i]); sd += cz[i] - qz[i]; });
      var ma = sa / ix.length, md = sd / ix.length;
      return { name: g, label: GROUP_LABEL[g], absd: ma, d: md, v: verdict(ma), close: ma <= META.rules.group_close,
               dir: Math.abs(md) > META.rules.group_diff ? (md > 0 ? "higher" : "lower") : null };
    });
  }
  function why(gs) {
    var close = gs.filter(function (g) { return g.close; }).map(function (g) { return g.name; });
    var diffs = gs.filter(function (g) { return g.dir; }).map(function (g) { return g.dir + " " + g.name; });
    return "Closest on " + (close.length ? close.join(", ") : "overall shape") + (diffs.length ? "; " + diffs.join(", ") : "") + ".";
  }
  function matchLevel(row) {   // row = [key, median score, min score, robust, limited]
    if (row[3]) return { cls: "strong", t: "Strong profile match", d: "Holds across most of the model's eight checks." };
    if (row[1] >= META.rules.robust_score) return { cls: "moderate", t: "Moderate profile match", d: "Close in this window, but not across the model's other checks." };
    return { cls: "weak", t: "Weaker profile match", d: "Among the closest in this pool, but not close under most checks." };
  }
  function list(arr) { return arr.length < 2 ? arr.join("") : arr.slice(0, -1).join(", ") + " and " + arr[arr.length - 1]; }

  /* ---------------- URL state (M3 §21) ---------------- */
  function readURL() {
    var p = FB.params(), s = p.get("player"), lg = FB.leagueFromSlug(p.get("league") || ""), n = parseInt(p.get("seasons"), 10);
    if (!n && p.get("profile")) n = parseInt(p.get("profile"), 10); // older links: profile=3y
    return { key: s && BY_SLUG[s] || null, slug: s, league: lg || "Serie_A", seasons: WIN[n] ? n : 3, compare: p.get("compare") };
  }
  function url(st) {
    var q = new URLSearchParams();
    var pl = player(st.key);
    if (pl) q.set("player", pl.slug);
    q.set("league", FB.LEAGUE_SLUG[st.league]);
    q.set("seasons", st.seasons);
    if (AS) q.set("as", AS);
    if (st.compare) q.set("compare", st.compare);
    return location.pathname + "?" + q.toString();
  }

  /* ---------------- query form (SimilarityQuery) ---------------- */
  var combo, form, step = 1;
  function setStep(n) {
    step = n;
    form.setAttribute("data-step", n);
    FB.$$(".wz-step", form).forEach(function (el) { el.hidden = false; el.classList.toggle("is-current", +el.getAttribute("data-n") === n); });
    $("wz-count").textContent = "Step " + n + " / 3";
  }
  function syncForm() {
    var pl = player(sel.key);
    $("q-league").value = sel.league;
    FB.$$("#q-window button").forEach(function (b) {
      var n = +b.getAttribute("data-n"), w = WIN[n], m = pl && pl.mins[w];
      b.setAttribute("aria-pressed", n === sel.seasons ? "true" : "false");
      b.querySelector("small").textContent = !pl ? "" : m ? m.toLocaleString("en-GB") + " min" : "not enough minutes";
    });
    if (pl) combo.set(pl.name);
    $("q-player-err").hidden = true;
    $("q-player").removeAttribute("aria-invalid");
  }
  function initForm() {
    form = $("q-form");
    combo = FB.combo($("q-player"), PLAYERS.map(function (r) {
      return { label: r[1], sub: r[2] + " · " + META.roles[r[4]], tag: FB.LEAGUE_NAME[r[3]], value: r[0] };
    }), function (it) {
      sel.key = it.value; syncForm();
      FB.track("similarity_started", { player: player(sel.key).name });
      if (window.matchMedia("(max-width: 639px)").matches) setStep(2);
    }, { emptyHint: "players with at least " + META.min_minutes + " minutes in " + META.season });
    $("q-player").placeholder = "Search for a player…";
    $("q-player").disabled = false;
    $("q-league").addEventListener("change", function () { sel.league = this.value; });
    $("q-window").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-n]"); if (!b) return;
      sel.seasons = +b.getAttribute("data-n"); syncForm();
    });
    FB.$$("[data-next]", form).forEach(function (b) {
      b.addEventListener("click", function () {
        if (step === 1 && !sel.key) return invalid();
        setStep(Math.min(3, step + 1));
      });
    });
    FB.$$("[data-prev]", form).forEach(function (b) { b.addEventListener("click", function () { setStep(Math.max(1, step - 1)); }); });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!sel.key) { setStep(1); return invalid(); }
      sel.compare = null;
      history.pushState(null, "", url(sel));
      run(true);
    });
    setStep(1);
  }
  function invalid() {
    $("q-player-err").hidden = false;
    $("q-player").setAttribute("aria-invalid", "true");
    $("q-player").focus();
  }

  /* ---------------- results (SimilarityResults) ---------------- */
  var out;
  function loading() {
    out.setAttribute("aria-busy", "true");
    out.innerHTML = '<div class="sx-load" role="status"><p class="analysing">Comparing profile…</p><ol>' +
      '<li data-s="1">9 dimensions</li><li data-s="2">Context adjusted</li><li data-s="3">Role normalized</li></ol></div>';
  }
  function tick(n) { var li = out.querySelector('.sx-load li[data-s="' + n + '"]'); if (li) li.classList.add("done"); }
  function stateBox(kind, title, body, actions) {
    out.removeAttribute("aria-busy");
    out.innerHTML = '<div class="state state--' + kind + '"' + (kind === "error" ? ' role="alert"' : "") + '><p class="state__t">' + esc(title) + "</p>" + body + (actions || "") + "</div>";
  }

  function run(scroll) {
    var pl = player(sel.key), w = WIN[sel.seasons];
    if (!pl) return;
    syncForm();
    if (scroll) $("results").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    if (!pl.mins[w]) {
      stateBox("insufficient", "Not enough data",
        "<p>" + esc(pl.name) + " does not meet the minimum profile requirement for a " + sel.seasons + "-season comparison: at least " + META.min_minutes +
        " minutes in the window. " + (pl.mins.w1 || pl.mins.w2 ? "Try a shorter profile window." : "") + "</p>");
      return;
    }
    loading();
    var t0 = performance.now();
    var pr = getJSON("r/" + pl.key + ".json", cacheR, pl.key);
    pr.then(function () { tick(1); });
    var zq = getJSON("z/" + pl.league + "_" + w + ".json", cacheZ, pl.league + w);
    var zt = getJSON("z/" + sel.league + "_" + w + ".json", cacheZ, sel.league + w);
    Promise.all([zq, zt]).then(function () { tick(2); });
    Promise.all([pr, zq, zt]).then(function (d) {
      tick(3);
      var res = d[0].res[sel.league] || {}, rows = res[w] || [], qz = d[1][pl.key], Z = d[2];
      FB.track("similarity_completed", { player: pl.name, league: sel.league, seasons: sel.seasons, ms: Math.round(performance.now() - t0) });
      if (!rows.length) {
        stateBox("empty", "No comparable profiles found",
          "<p>No " + esc(pl.role) + " in " + FB.LEAGUE_NAME[sel.league] + " has a " + sel.seasons + "-season profile to compare with. Try:</p>" +
          '<ul class="sx-tips"><li>a different league</li><li>a longer profile window</li><li>another player</li></ul>');
        return;
      }
      view = { pl: pl, w: w, res: res, rows: rows, qz: qz, Z: Z };
      out.removeAttribute("aria-busy");
      var cmp = sel.compare && BY_SLUG[sel.compare];
      if (cmp && rows.some(function (r) { return r[0] === cmp; })) renderCompare(cmp); else renderResults();
    }).catch(function () {
      stateBox("error", "We couldn't calculate this comparison", "<p>Check your connection and try again.</p>",
        '<button type="button" class="state__retry" id="sx-retry">Try again →</button>');
      $("sx-retry").addEventListener("click", function () { run(false); });
    });
  }

  function head(pl, extra) {
    return '<div class="sx-head"><div><p class="label">Similarity result</p><h2 class="sx-h" id="sx-h" tabindex="-1">' + esc(pl.name) + "</h2>" +
      '<p class="sx-meta">' + esc(pl.team) + " · " + FB.LEAGUE_NAME[pl.league] + ' · Role: ' + esc(pl.role) +
      ' <button type="button" class="term" data-term="role">model-assigned</button></p>' +
      '<p class="sx-q"><b>→ ' + FB.LEAGUE_NAME[sel.league] + "</b> · " + sel.seasons + "-season profile · as of " + META.season + "</p></div>" +
      '<button type="button" class="share" id="sx-share">Copy link</button></div>' + (extra || "");
  }

  function renderResults() {
    var v = view, pl = v.pl;
    var cards = v.rows.map(function (r, i) {
      var c = player(r[0]), cz = v.Z[r[0]], gs = groups(v.qz, cz), m = matchLevel(r);
      return { r: r, c: c, gs: gs, m: m, i: i };
    });
    // a pattern, not a special case: a group where none of the top three reaches the player's level
    var lead = "";
    Object.keys(META.groups).forEach(function (g) {
      var top = cards.slice(0, 3);
      if (top.length === 3 && top.every(function (k) { return k.gs.filter(function (x) { return x.name === g; })[0].dir === "lower"; }))
        lead = "None of the top three matches " + esc(pl.name) + "'s " + g + " at the same level.";
    });
    var html = head(pl) +
      '<p class="sx-sum">Top comparable profiles among <b>' + v.res[v.w + "_pool"] + "</b> " + esc(pl.role).toLowerCase() + " profiles in " + FB.LEAGUE_NAME[sel.league] +
      " with at least " + META.min_minutes + " minutes. Ranked the way Study 4 ranks: matches that hold across the model's checks first, then by similarity in this window.</p>" +
      (v.res.small ? '<p class="sx-flag">Small pool: fewer than 20 profiles in at least one check — treat the ranking with extra care.</p>' : "") +
      (lead ? '<p class="callout sx-lead"><strong>' + lead + "</strong></p>" : "") +
      '<ol class="sx-list">' + cards.map(card).join("") + "</ol>" + disclaimer();
    out.innerHTML = html;
    FB.share($("sx-share"));
  }
  function groupChips(gs) {
    return '<ul class="sx-groups">' + gs.map(function (g) {
      return '<li class="v-' + g.v + '"><span>' + g.label + "</span><b>" + VERDICT[g.v] + (g.dir ? " · " + g.dir : "") + "</b></li>";
    }).join("") + "</ul>";
  }
  function card(k) {
    var c = k.c, r = k.r;
    return '<li class="sx-card fade-in" data-key="' + c.key + '"><div class="sx-card__top"><span class="sx-rank">' + String(k.i + 1).padStart(2, "0") + "</span>" +
      '<div class="sx-who"><h3>' + esc(c.name) + "</h3><p>" + esc(c.team) + " · " + FB.LEAGUE_NAME[c.league] + "</p></div>" +
      '<div class="sx-level"><span class="sx-badge sx-badge--' + k.m.cls + '">' + k.m.t + "</span>" +
      (r[4] ? '<span class="sx-lim">limited evidence</span>' : "") +
      '<span class="sx-score" title="' + esc(k.m.d) + '">Profile similarity ' + Math.round(r[1]) + '<small> · closer than ' + Math.round(r[1]) + "% of the pool</small></span></div></div>" +
      groupChips(k.gs) +
      '<div class="sx-actions"><button type="button" class="link-arrow link-arrow--plain sx-why" aria-expanded="false" data-why="' + c.key + '">Why this player? <span class="arr" aria-hidden="true">↓</span></button>' +
      '<button type="button" class="link-arrow sx-cmp" data-cmp="' + c.key + '">Compare <span class="arr" aria-hidden="true">→</span></button></div>' +
      '<div class="sx-whybox" id="why-' + c.key + '" hidden></div></li>';
  }
  function onListClick(e) {
    var w = e.target.closest("[data-why]"), c = e.target.closest("[data-cmp]");
    if (w) {
      var key = w.getAttribute("data-why"), box = $("why-" + key), open = box.hidden;
      box.hidden = !open; w.setAttribute("aria-expanded", open ? "true" : "false");
      if (open && !box.innerHTML) box.innerHTML = drivers(key);
    }
    if (c) {
      sel.compare = player(c.getAttribute("data-cmp")).slug;
      history.pushState(null, "", url(sel));
      renderCompare(c.getAttribute("data-cmp"));
      FB.track("similarity_compare", { cand: player(c.getAttribute("data-cmp")).name });
    }
  }
  function drivers(key) {   // SimilarityDrivers
    var v = view, c = player(key), cz = v.Z[key];
    var rows = META.metrics.map(function (m, i) { var d = cz[i] - v.qz[i]; return { m: m, d: d, v: verdict(Math.abs(d)) }; });
    var gs = groups(v.qz, cz);
    return '<p class="sx-whyline">' + esc(why(gs)) + "</p>" +
      '<table class="sx-drv"><caption class="sr-only">Similarity drivers, ' + esc(c.name) + " vs " + esc(v.pl.name) + "</caption><thead><tr><th scope=\"col\">Metric</th><th scope=\"col\">Match</th><th scope=\"col\">" + esc(short(c.name)) + " vs " + esc(short(v.pl.name)) + "</th></tr></thead><tbody>" +
      rows.map(function (r) {
        return "<tr><th scope=\"row\">" + esc(r.m) + '</th><td class="v-' + r.v + '">' + VERDICT[r.v] + "</td><td>" + (Math.abs(r.d) < 0.05 ? "level" : (r.d > 0 ? "higher" : "lower") + " by " + Math.abs(r.d).toFixed(1) + " SD") + "</td></tr>";
      }).join("") + "</tbody></table>" +
      '<p class="source">Gaps in standard deviations within the role, adjusted profiles. Strong ≤ ' + META.rules.similar + " SD · Moderate ≤ " + META.rules.moderate + " SD · Divergence above.</p>";
  }
  function short(n) { return n.split(" ").slice(-1)[0]; }

  /* ---------------- compare mode (SimilarityComparison) ---------------- */
  function zbar(z, cls) {
    var c = Math.max(-3, Math.min(3, z)), x = (c + 3) / 6 * 100, left = Math.min(50, x), width = Math.abs(x - 50);
    return '<span class="zb ' + cls + '" style="left:' + left.toFixed(2) + "%;width:" + width.toFixed(2) + '%"></span>' + (Math.abs(z) > 3 ? '<span class="zb-over ' + cls + '" style="left:' + (z > 0 ? "calc(100% - 4px)" : "0") + '"></span>' : "");
  }
  function renderCompare(key) {
    var v = view, pl = v.pl, c = player(key), cz = v.Z[key], row = v.rows.filter(function (r) { return r[0] === key; })[0];
    var rank = v.rows.indexOf(row) + 1, gs = groups(v.qz, cz), m = matchLevel(row);
    var mets = META.metrics.map(function (name, i) { return { name: name, i: i, q: v.qz[i], c: cz[i], d: cz[i] - v.qz[i] }; });
    var big = mets.slice().sort(function (a, b) { return Math.abs(b.d) - Math.abs(a.d); }).slice(0, 3);
    var close = gs.filter(function (g) { return g.close; }).map(function (g) { return g.name; });
    var far = gs.filter(function (g) { return g.v === "diverge" || g.dir; }).map(function (g) { return g.name; });
    var a = short(pl.name), b = short(c.name);
    var profile = Object.keys(META.groups).map(function (g) {
      return '<div class="cp-g"><p class="label">' + GROUP_LABEL[g] + "</p>" + META.groups[g].map(function (i) {
        var mm = mets[i];
        return '<div class="cp-row"><span class="cp-m">' + esc(mm.name) + '</span><span class="cp-track"><span class="cp-mid"></span>' + zbar(mm.q, "zb--a") + "</span>" +
          '<span class="cp-v">' + FB.signed(mm.q, 1) + '</span><span class="cp-track">' + '<span class="cp-mid"></span>' + zbar(mm.c, "zb--b") + '</span><span class="cp-v">' + FB.signed(mm.c, 1) + "</span></div>";
      }).join("") + "</div>";
    }).join("");
    var shape = gs.map(function (g) {
      var ix = META.groups[g.name], qa = 0, ca = 0;
      ix.forEach(function (i) { qa += v.qz[i]; ca += cz[i]; });
      qa /= ix.length; ca /= ix.length;
      return '<div class="cp-row"><span class="cp-m">' + g.label + '</span><span class="cp-track"><span class="cp-mid"></span>' + zbar(qa, "zb--a") + '</span><span class="cp-v">' + FB.signed(qa, 1) + '</span><span class="cp-track"><span class="cp-mid"></span>' + zbar(ca, "zb--b") + '</span><span class="cp-v">' + FB.signed(ca, 1) + "</span></div>";
    }).join("");
    var bigMax = Math.max.apply(null, big.map(function (x) { return Math.abs(x.d); }).concat([1]));
    var breakSentence = esc(b) + (close.length ? " resembles " + esc(a) + " in " + list(close) : " shares " + esc(a) + "'s overall profile shape") +
      (far.length ? ", but diverges more strongly in " + list(far) + "." : ", with no group-level divergence above the model's thresholds.");
    var bottom = esc(c.name) + " is " + (rank <= 3 ? "one of the closest" : "among the ten closest") + " statistical profiles to " + esc(pl.name) + " in " +
      FB.LEAGUE_NAME[sel.league] + "'s " + esc(pl.role).toLowerCase() + " pool (" + sel.seasons + "-season window)" +
      (row[3] ? ", and the match holds across most of the model's checks" : ", but the match does not hold across most of the model's other checks") + ". " +
      (close.length ? "The resemblance is strongest in " + list(close) + ". " : "") +
      (far.length ? "The profiles diverge meaningfully in " + list(far) + ", so this is a similarity lead rather than a like-for-like equivalent." :
        "Even so, a similar profile is a lead to investigate, not a like-for-like equivalent.") +
      " It says nothing about how " + esc(b) + " would perform after a move.";
    out.innerHTML =
      '<div class="cp-bar"><button type="button" class="link-arrow link-arrow--plain" id="cp-back"><span aria-hidden="true">←</span> Back to results</button>' +
      '<p class="cp-vs"><b>' + esc(pl.name) + '</b><span>vs</span><b class="cp-b">' + esc(c.name) + "</b></p>" +
      '<button type="button" class="share" id="sx-share">Copy link</button></div>' +
      '<h2 class="sx-h" id="sx-h" tabindex="-1">Why does ' + esc(b) + " look similar?</h2>" +
      '<p class="sx-meta"><span class="sx-badge sx-badge--' + m.cls + '">' + m.t + "</span> " + esc(m.d) + " Rank " + rank + " of " + v.rows.length + " shown · profile similarity " + Math.round(row[1]) + ' (closer than ' + Math.round(row[1]) + '% of the pool, not a probability)</p>' +

      '<section class="cp-sec" aria-labelledby="cp-p"><h3 id="cp-p">Profile</h3><p class="label cp-tag">Adjusted · role-normalized · z-scores within the role</p>' +
      '<div class="cp-legend"><span><i class="sw sw--a"></i>' + esc(pl.name) + '</span><span><i class="sw sw--b"></i>' + esc(c.name) + "</span></div>" +
      '<div class="cp-grid" role="img" aria-label="' + esc(mets.map(function (x) { return x.name + ": " + a + " " + x.q.toFixed(1) + ", " + b + " " + x.c.toFixed(1); }).join("; ")) + '">' +
      '<div class="cp-row cp-row--h"><span></span><span>' + esc(a) + '</span><span></span><span>' + esc(b) + "</span><span></span></div>" + profile + "</div>" +
      '<p class="source">0 = the role average; each step is one standard deviation within the role. Bars clipped at ±3.</p></section>' +

      '<section class="cp-sec" aria-labelledby="cp-s"><h3 id="cp-s">Profile shape</h3><div class="cp-grid">' + shape + "</div></section>" +

      '<section class="cp-sec" aria-labelledby="cp-d"><h3 id="cp-d">Similarity drivers</h3>' + drivers(key) + "</section>" +

      '<section class="cp-sec cp-sec--break" aria-labelledby="cp-x"><h3 id="cp-x">Where the similarity breaks down</h3><p class="lead">' + breakSentence + "</p>" +
      '<p class="label">Biggest differences</p><div class="hbar">' + big.map(function (x) {
        return '<div class="hbar__row"><span class="hbar__lbl">' + esc(x.name) + '</span><span class="track"><span class="bar bar--hot" style="left:0;width:' + (Math.abs(x.d) / bigMax * 100).toFixed(1) + '%"></span></span><span class="hbar__v">' + Math.abs(x.d).toFixed(1) + " SD</span></div>";
      }).join("") + "</div></section>" +

      '<section class="cp-sec" aria-labelledby="cp-c"><h3 id="cp-c">Context</h3><dl class="cp-ctx">' +
      "<div><dt>Role</dt><dd>" + esc(pl.role) + " (both, model-assigned)</dd></div>" +
      "<div><dt>Minutes in window</dt><dd>" + esc(a) + " " + pl.mins[v.w].toLocaleString("en-GB") + " · " + esc(b) + " " + (c.mins[v.w] || 0).toLocaleString("en-GB") + "</dd></div>" +
      "<div><dt>Pool</dt><dd>" + v.res[v.w + "_pool"] + " " + FB.LEAGUE_NAME[sel.league] + " profiles in this role</dd></div>" +
      "<div><dt>Checks</dt><dd>" + (row[3] ? "Robust: top 10 and closer than 90% of the pool in at least two-thirds of " : "Not robust across ") + v.res.checks + " window × algorithm checks" + (row[4] ? " · limited evidence (few windows in this league)" : "") + "</dd></div>" +
      "<div><dt>Season</dt><dd>Profiles as of " + META.season + "; clubs as of that season</dd></div></dl></section>" +

      '<section class="cp-sec cp-sec--bottom" aria-labelledby="cp-b"><h3 id="cp-b">Bottom line</h3><p>' + bottom + "</p></section>" + disclaimer();
    FB.share($("sx-share"));
    $("cp-back").addEventListener("click", function () { history.back(); });
    $("sx-h").focus({ preventScroll: true });
    $("results").scrollIntoView({ block: "start" });
  }

  function disclaimer() {
    var pl = view.pl;
    return '<aside class="sx-disc"><p class="label">Similarity ≠ predicted performance</p><p>This model describes how similar two attacking profiles are. It does not estimate how well the player would perform after changing leagues or clubs.</p>' +
      '<p><b>Want to estimate that?</b> <a class="link-arrow" href="/football/tools/transfer?player=' + pl.slug + "&amp;from=" + FB.LEAGUE_SLUG[pl.league] + "&amp;to=" + FB.LEAGUE_SLUG[sel.league] + '">Try the Transfer Calculator <span class="arr" aria-hidden="true">→</span></a></p></aside>';
  }

  /* ---------------- season switch: reloads with the other dataset, keeping player / league / window ---------------- */
  function initAsOf() {
    FB.$$("#q-asof button").forEach(function (b) {
      var v = b.getAttribute("data-as");
      b.setAttribute("aria-pressed", v === AS ? "true" : "false");
      b.addEventListener("click", function () {
        if (v === AS) return;
        var q = new URLSearchParams(location.search);
        if (v) q.set("as", v); else q.delete("as");
        q.delete("compare");
        location.href = location.pathname + (q.toString() ? "?" + q.toString() : "");
      });
    });
  }

  /* ---------------- boot ---------------- */
  function fromURL() {
    var st = readURL();
    sel.league = st.league; sel.seasons = st.seasons; sel.compare = st.compare;
    if (st.key) { sel.key = st.key; run(false); }
    else if (st.slug) { stateBox("empty", "Player not found", "<p>No player matches “" + esc(st.slug) + "” in the profiles as of " + META.season + ". Search for a player above" + (AS ? ", or switch to the latest matches" : ", or switch to 2025/26") + ".</p>"); syncForm(); }
    else syncForm();
  }
  document.addEventListener("DOMContentLoaded", function () {
    out = $("sx-out");
    out.addEventListener("click", function (e) { if (out.querySelector(".sx-list")) onListClick(e); });
    Promise.all([getJSON("meta.json"), getJSON("players.json")]).then(function (d) {
      META = d[0]; PLAYERS = d[1];
      PLAYERS.forEach(function (r) { BY_KEY[r[0]] = r; BY_SLUG[r[5]] = r[0]; });
      $("q-count").textContent = PLAYERS.length.toLocaleString("en-GB") + " players · profiles as of " + META.season +
        (META.through ? " (through " + new Date(META.through + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) + ")" : "");
      initAsOf();
      initForm();
      fromURL();
      window.addEventListener("popstate", fromURL);
    }).catch(function () {
      $("q-player").placeholder = "Couldn't load players";
      stateBox("error", "We couldn't load the player list", "<p>Check your connection and try again.</p>", '<button type="button" class="state__retry" onclick="location.reload()">Try again →</button>');
    });
  });
})();
