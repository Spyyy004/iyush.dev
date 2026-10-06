/* Transfer Calculator (M4). Looks up precomputed Study 5 predictions — nothing is modelled here.
   Data: /football/data/transfer/ (scripts/build_transfer.py runs the research's production model for every
   eligible player × destination club; the "why" terms are the model's own and add up to the prediction). */
(function () {
  "use strict";
  var FB = window.FB, BASE = "/football/data/transfer/";
  var IX, BY_KEY = {}, BY_SLUG = {}, cacheP = {};
  var sel = { key: null, to: null, club: null };
  var $ = function (id) { return document.getElementById(id); };
  var esc = FB.esc, out, form, combo, step = 1;
  var TERM = {
    role: ["Player history", "Baseline for his role group"], last: ["Player history", "Last season's output"],
    level3: ["Player history", "Three-season level"], history: ["Player history", "Seasons of history"],
    origin: ["League move", "Leaving the origin league"], dest: ["League move", "Joining the destination league"],
    age: ["Age", "Age at the move"], minutes: ["Playing time", "Minutes last season"],
    origin_club: ["Club context", "Origin club strength"], dest_club: ["Club context", "Destination club strength"]
  };

  function getJSON(path, cache, key) {
    if (cache && cache[key]) return cache[key];
    var p = fetch(BASE + path).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    if (cache) { cache[key] = p; p.catch(function () { delete cache[key]; }); }
    return p;
  }
  function player(key) { var r = BY_KEY[key]; return r && { key: r[0], name: r[1], team: r[2], league: r[3], role: r[4], slug: r[5], nh: r[6], mins: r[7], pre: r[8] }; }
  function club(i) { var c = IX.clubs[i]; return c && { i: i, league: c[0], name: c[1], s: c[2], promoted: !!c[3], terms: c[4], slug: FB.slug(c[1]) }; }
  function clubsIn(lg) { var a = []; IX.clubs.forEach(function (c, i) { if (c[0] === lg) a.push(i); }); return a; }
  var f2 = function (x) { return Number(x).toFixed(2); }, pct = function (x) { return Math.round(x * 100) + "%"; };

  /* ---------------- URL state ---------------- */
  function readURL() {
    var p = FB.params(), slug = p.get("player"), key = slug && BY_SLUG[slug] || null, pl = player(key);
    var to = FB.leagueFromSlug(p.get("to") || ""), cslug = p.get("club"), ci = null;
    if (pl && (!to || to === pl.league)) to = null;
    if (to && cslug) clubsIn(to).forEach(function (i) { if (club(i).slug === cslug) ci = i; });
    return { slug: slug, key: key, to: to, club: ci };
  }
  function url() {
    var pl = player(sel.key), q = new URLSearchParams();
    if (pl) { q.set("player", pl.slug); q.set("from", FB.LEAGUE_SLUG[pl.league]); }
    if (sel.to) q.set("to", FB.LEAGUE_SLUG[sel.to]);
    if (sel.club != null) q.set("club", club(sel.club).slug);
    return location.pathname + "?" + q.toString();
  }

  /* ---------------- inputs ---------------- */
  function setStep(n) {
    step = n; form.setAttribute("data-step", n);
    FB.$$(".wz-step", form).forEach(function (el) { el.classList.toggle("is-current", +el.getAttribute("data-n") === n); });
    $("wz-count").textContent = "Step " + n + " / 3";
  }
  function fillLeagues() {
    var pl = player(sel.key), s = $("t-to");
    var opts = IX.leagues.filter(function (l) { return !pl || l !== pl.league; });
    if (sel.to && opts.indexOf(sel.to) < 0) sel.to = null;
    s.innerHTML = '<option value="">' + (pl ? "Select a league…" : "Pick a player first") + "</option>" +
      opts.map(function (l) { return '<option value="' + l + '"' + (l === sel.to ? " selected" : "") + ">" + FB.LEAGUE_NAME[l] + "</option>"; }).join("");
    s.disabled = !pl;
  }
  function fillClubs() {
    var s = $("t-club");
    if (!sel.to) { s.innerHTML = '<option value="">Pick a destination league first</option>'; s.disabled = true; sel.club = null; return; }
    var ids = clubsIn(sel.to);
    if (sel.club != null && ids.indexOf(sel.club) < 0) sel.club = null;
    s.innerHTML = '<option value="">Select a club…</option>' + ids.map(function (i) {
      var c = club(i); return '<option value="' + i + '"' + (i === sel.club ? " selected" : "") + ">" + esc(c.name) + "</option>";
    }).join("");
    s.disabled = false;
  }
  function syncForm() {
    var pl = player(sel.key);
    if (pl) combo.set(pl.name);
    $("t-from").textContent = pl ? FB.LEAGUE_NAME[pl.league] : "—";
    $("t-hist").innerHTML = pl ? esc(pl.team) + " · available history: <b>" + pl.nh + " season" + (pl.nh === 1 ? "" : "s") + "</b> · " + IX.pre_season + ": " +
      pl.mins.toLocaleString("en-GB") + " min, " + f2(pl.pre) + " xG + xA per 90 · " + esc(pl.role) : "";
    fillLeagues(); fillClubs();
    ["t-player-err", "t-to-err", "t-club-err"].forEach(function (id) { $(id).hidden = true; });
  }
  function err(id, focus) { $(id).hidden = false; if (focus) $(focus).focus(); return false; }
  function valid() {
    if (!sel.key) { setStep(1); return err("t-player-err", "t-player"); }
    if (!sel.to) { setStep(2); return err("t-to-err", "t-to"); }
    if (sel.club == null) { setStep(3); return err("t-club-err", "t-club"); }
    return true;
  }
  function initForm() {
    form = $("t-form");
    combo = FB.combo($("t-player"), IX.players.map(function (r) {
      return { label: r[1], sub: r[2] + " · " + r[4], tag: FB.LEAGUE_NAME[r[3]], value: r[0] };
    }), function (it) {
      sel.key = it.value; syncForm();
      FB.track("tr_pick", { player: player(sel.key).name });
      if (window.matchMedia("(max-width: 639px)").matches) setStep(2);
    }, { emptyHint: "forwards and midfielders with at least " + IX.min_minutes + " minutes in " + IX.pre_season });
    $("t-player").placeholder = "Search for a player…";
    $("t-player").disabled = false;
    $("t-to").addEventListener("change", function () { sel.to = this.value || null; sel.club = null; fillClubs(); $("t-to-err").hidden = true; });
    $("t-club").addEventListener("change", function () { sel.club = this.value === "" ? null : +this.value; $("t-club-err").hidden = true; });
    FB.$$("[data-next]", form).forEach(function (b) {
      b.addEventListener("click", function () {
        if (step === 1 && !sel.key) return err("t-player-err", "t-player");
        if (step === 2 && !sel.to) return err("t-to-err", "t-to");
        setStep(Math.min(3, step + 1));
      });
    });
    FB.$$("[data-prev]", form).forEach(function (b) { b.addEventListener("click", function () { setStep(Math.max(1, step - 1)); }); });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!valid()) return;
      history.pushState(null, "", url());
      run(true);
    });
    setStep(1);
  }

  /* ---------------- run + result (TransferPrediction) ---------------- */
  function stateBox(kind, title, body, actions) {
    out.removeAttribute("aria-busy");
    out.innerHTML = '<div class="state state--' + kind + '"' + (kind === "error" ? ' role="alert"' : "") + '><p class="state__t">' + esc(title) + "</p>" + body + (actions || "") + "</div>";
  }
  function run(scroll) {
    var pl = player(sel.key), c = club(sel.club);
    if (!pl || !c) return;
    syncForm();
    if (scroll) $("results").scrollIntoView({ block: "start" });
    out.setAttribute("aria-busy", "true");
    out.innerHTML = '<div class="sx-load" role="status"><p class="analysing">Analysing player history…</p><ol>' +
      '<li data-s="1">Player history</li><li data-s="2">League context</li><li data-s="3">Transfer context</li><li data-s="4">Generating prediction</li></ol></div>';
    var t0 = performance.now();
    getJSON("p/" + pl.key + ".json", cacheP, pl.key).then(function (d) {
      ["1", "2", "3"].forEach(function (n) { var li = out.querySelector('li[data-s="' + n + '"]'); if (li) li.classList.add("done"); });
      var pr = d.pred[String(c.i)];
      if (!pr) { stateBox("empty", "No prediction for this move", "<p>The model has no prediction for " + esc(pl.name) + " → " + esc(c.name) + ". Try another club or league.</p>"); return; }
      FB.track("tr_run", { player: pl.name, to: c.league, club: c.name, ms: Math.round(performance.now() - t0) });
      render(pl, c, d, pr);
    }).catch(function () {
      stateBox("error", "We couldn't load this prediction", "<p>Check your connection and try again.</p>", '<button type="button" class="state__retry" id="t-retry">Try again →</button>');
      $("t-retry").addEventListener("click", function () { run(false); });
    });
  }

  function render(pl, c, d, pr) {
    var exp = pr[0], q10 = pr[1], q90 = pr[2], p75 = pr[3], pre = d.pre, ret = exp / pre;
    var top = Math.max(q90, pre) * 1.08, x = function (v) { return (v / top * 100).toFixed(2) + "%"; };
    var dir = ret < 0.95 ? "less than" : ret > 1.05 ? "more than" : "about the same as";
    // drivers: the model's own terms, grouped; they add up to the prediction
    var terms = [];
    Object.keys(d.terms).forEach(function (k) { terms.push({ k: k, v: d.terms[k] }); });
    Object.keys(c.terms).forEach(function (k) { terms.push({ k: k, v: c.terms[k] }); });
    var groups = {}, order = ["Player history", "League move", "Age", "Club context", "Playing time"];
    terms.forEach(function (t) { var g = TERM[t.k][0]; (groups[g] = groups[g] || []).push(t); });
    var gsum = order.map(function (g) { return { g: g, v: (groups[g] || []).reduce(function (s, t) { return s + t.v; }, 0) }; });
    var maxAbs = Math.max.apply(null, terms.map(function (t) { return Math.abs(t.v); }).concat([0.05]));
    var bar = function (v) {
      var w = Math.abs(v) / maxAbs * 50;
      return '<span class="dv-track"><span class="dv-mid"></span><span class="dv-bar ' + (v < 0 ? "dv-bar--neg" : "dv-bar--pos") + '" style="' + (v < 0 ? "right:50%" : "left:50%") + ";width:" + w.toFixed(1) + '%"></span></span>';
    };
    var why = order.map(function (g) {
      return '<div class="dv-g"><p class="dv-gh"><span>' + g + "</span><b>" + FB.signed(gsum.filter(function (z) { return z.g === g; })[0].v, 3) + "</b></p>" +
        (groups[g] || []).map(function (t) {
          return '<div class="dv-row"><span class="dv-l">' + TERM[t.k][1] + (t.k === "dest_club" && c.promoted ? " (promoted club)" : "") + "</span>" + bar(t.v) +
            '<span class="dv-v">' + FB.signed(t.v, 3) + "</span></div>";
        }).join("") + "</div>";
    }).join("");
    var biggestUp = terms.slice().sort(function (a, b) { return b.v - a.v; })[0], biggestDown = terms.slice().sort(function (a, b) { return a.v - b.v; })[0];

    out.removeAttribute("aria-busy");
    out.innerHTML =
      '<div class="sx-head"><div><p class="label">Transfer projection</p><h2 class="sx-h" id="t-h" tabindex="-1">' + esc(pl.name) + "</h2>" +
      '<p class="sx-q"><b>' + FB.LEAGUE_NAME[pl.league] + " → " + FB.LEAGUE_NAME[c.league] + "</b> · " + esc(c.name) + "</p>" +
      '<p class="sx-meta">' + esc(pl.team) + " · " + esc(pl.role) + " · age " + Math.floor(d.age) + " at the move · " + pl.nh + " season" + (pl.nh === 1 ? "" : "s") + " of history</p></div>" +
      '<button type="button" class="share" id="t-share">Copy link</button></div>' +

      '<div class="tr-key"><div><p class="label">Expected attacking output</p><b class="tr-big">' + f2(exp) + '</b><span class="tr-unit">' + FB.term("xg", "xG") + " + " + FB.term("xa", "xA") + " per 90 · first season after the move</span></div>" +
      '<div><p class="label">Expected retention</p><b class="tr-big tr-big--hot">' + pct(ret) + '</b><span class="tr-unit">of his ' + IX.pre_season + " output (" + f2(pre) + ")</span></div></div>" +

      '<section class="tr-sec" aria-labelledby="t-ret"><h3 id="t-ret" class="sr-only">Retention</h3>' +
      '<div class="tr-bars" role="img" aria-label="Pre-transfer ' + f2(pre) + "; expected after the move " + f2(exp) + ", 80% prediction range " + f2(q10) + " to " + f2(q90) + '">' +
      '<div class="tr-bar"><span class="tr-bl">Pre-transfer · ' + IX.pre_season + '</span><span class="tr-tr"><span class="tr-fill tr-fill--pre" style="width:' + x(pre) + '"></span></span><span class="tr-bv">' + f2(pre) + "</span></div>" +
      '<div class="tr-bar"><span class="tr-bl">Post-transfer expected</span><span class="tr-tr"><span class="tr-band" style="left:' + x(q10) + ";width:calc(" + x(q90) + " - " + x(q10) + ')"></span><span class="tr-fill" style="width:' + x(exp) + '"></span></span><span class="tr-bv">' + f2(exp) + "</span></div>" +
      '<div class="tr-axis"><span>0</span><span>' + f2(top / 2) + "</span><span>" + f2(top) + "</span></div></div>" +
      '<p class="chart__summary">The model expects ' + esc(pl.name) + " to produce " + dir + " last season (" + pct(ret) + "), most likely between " + f2(q10) + " and " + f2(q90) + " xG + xA per 90.</p></section>" +

      '<div class="tr-two">' +
      '<section class="tr-card" aria-labelledby="t-p75"><p class="label" id="t-p75">Probability of retaining at least 75% of pre-transfer attacking output</p>' +
      (p75 == null ? '<p class="tr-na">Not shown</p><p class="small muted">His ' + IX.pre_season + " output (" + f2(pre) + ") is below " + f2(IX.ret_floor) + " xG + xA per 90, where Study 5 does not report this probability.</p>"
        : '<b class="tr-mid">' + pct(p75) + '</b><p class="small muted">A chance of keeping three-quarters of his output — not a chance of “success”. ' + FB.term("calibration", "Calibrated") + " at this threshold; Study 5 does not use lower ones.</p>") + "</section>" +
      '<section class="tr-card" aria-labelledby="t-r80"><p class="label" id="t-r80">' + FB.term("range-80", "80% prediction range") + "</p>" +
      '<div class="tr-range" role="img" aria-label="80% prediction range ' + f2(q10) + " to " + f2(q90) + ", point " + f2(exp) + '"><span class="tr-rl">' + f2(q10) + '</span><span class="tr-rt"><span class="tr-rline"></span><span class="tr-rpt" style="left:' + ((exp - q10) / (q90 - q10) * 100).toFixed(1) + '%"><i>▲</i>' + f2(exp) + '</span></span><span class="tr-rl">' + f2(q90) + "</span></div>" +
      '<p class="small muted">Eight times in ten, the first season should land in this range. Typical width ±0.2 xG + xA per 90. This is a prediction range, not a confidence interval.</p></section></div>' +

      '<section class="tr-sec" aria-labelledby="t-why"><h3 id="t-why">Why does the model expect this outcome?</h3>' +
      '<p class="body">Each line is one input times its weight in Study 5\'s final model; together they add up to the prediction (' + f2(exp) + "). The largest push up is <b>" + TERM[biggestUp.k][1].toLowerCase() + "</b>; the largest pull down is <b>" + TERM[biggestDown.k][1].toLowerCase() + "</b>.</p>" +
      '<div class="dv">' + why + '<div class="dv-total"><span>Prediction</span><b>' + f2(exp) + "</b></div></div>" +
      '<p class="source">In the model, last season counts for much less than the three-season level — so a recent jump in output is mostly discounted (Study 5: players coming off a jump drop more). Role, consistency, profile distinctiveness, penalty duties and loans added nothing and are not in the model.</p></section>' +

      '<aside class="sx-disc"><p class="label">Not a verdict on the player</p><p>This estimates attacking output only — xG + xA per 90. It cannot see defending, completed passes, carries, possession or fit, and it does not predict overall quality or career success.</p></aside>';
    FB.share($("t-share"));
    $("t-h").focus({ preventScroll: true });
  }

  function fromURL() {
    var st = readURL();
    sel.key = st.key; sel.to = st.to; sel.club = st.club;
    syncForm();
    if (st.key && st.to && st.club != null) { run(false); return; }
    if (st.slug && !st.key) {
      stateBox("insufficient", "Not covered by the model",
        "<p>No eligible player matches “" + esc(st.slug) + "”. Study 5 covers forwards and midfielders with at least " + IX.min_minutes + " minutes in " + IX.pre_season +
        " (" + IX.scope_roles.join(", ").toLowerCase() + "). Defenders and goalkeepers are out of scope, because the data only sees attacking output.</p>");
    }
  }
  document.addEventListener("DOMContentLoaded", function () {
    out = $("t-out");
    getJSON("index.json").then(function (ix) {
      IX = ix;
      IX.players.forEach(function (r) { BY_KEY[r[0]] = r; BY_SLUG[r[5]] = r[0]; });
      $("t-count").textContent = IX.players.length.toLocaleString("en-GB") + " forwards and midfielders · inputs as of " + IX.pre_season;
      initForm();
      fromURL();
      window.addEventListener("popstate", fromURL);
    }).catch(function () {
      $("t-player").placeholder = "Couldn't load players";
      stateBox("error", "We couldn't load the player list", "<p>Check your connection and try again.</p>", '<button type="button" class="state__retry" onclick="location.reload()">Try again →</button>');
    });
  });
})();
