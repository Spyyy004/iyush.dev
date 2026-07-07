/* ============================================================
   iyush.dev — arcade
   Frontend-only games. Loaded ONLY on games.html.
   Currently: Typespeed — a shell-command typing speed test.
   Add a game by dropping another IIFE below, guarded on its
   own root element so it no-ops on pages that lack it.
   ============================================================ */

/* ---------- Typespeed ---------- */
(function () {
  "use strict";
  var panel = document.getElementById("typer");
  if (!panel) return;

  var textEl  = document.getElementById("tText");
  var input   = document.getElementById("tInput");
  var hint    = document.getElementById("tHint");
  var result  = document.getElementById("tResult");
  var elWpm   = document.getElementById("tWpm");
  var elAcc   = document.getElementById("tAcc");
  var elTime  = document.getElementById("tTime");
  var elBest  = document.getElementById("tBest");

  var reduce   = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var canHover = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  // Real-ish shell commands — varied length, dev-flavored.
  var COMMANDS = [
    'git commit -m "ship it"',
    "npm install owthorize",
    "cd ~/projects && ls -la",
    "docker compose up -d",
    "git push origin main",
    "npx create-next-app app",
    "vercel --prod",
    "curl -s https://iyush.dev",
    "grep -rn TODO src/",
    "ssh ayush@iyush.dev",
    "python3 -m http.server",
    "git rebase -i HEAD~3",
    "brew install fzf",
    "kubectl get pods -A",
    "rm -rf node_modules && npm i"
  ];

  // Safe persistence for the best score.
  var memBest = 0;
  function bestGet() {
    try { var v = window.localStorage.getItem("typer_best"); return v ? (parseInt(v, 10) || 0) : 0; }
    catch (e) { return memBest; }
  }
  function bestSet(v) {
    memBest = v;
    try { window.localStorage.setItem("typer_best", String(v)); } catch (e) { /* memory only */ }
  }
  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) { /* ignore */ } }
  function now() { return (window.performance && performance.now) ? performance.now() : Date.now(); }
  function escChar(c) {
    return c === "&" ? "&amp;" : c === "<" ? "&lt;" : c === ">" ? "&gt;" : c === '"' ? "&quot;" : c;
  }

  var target = "", lastCmd = null, best = bestGet();
  var started = false, done = false, startMs = 0, prevLen = 0, keystrokes = 0, errors = 0, rafId = 0;

  function pick() {
    var c;
    do { c = COMMANDS[Math.floor(Math.random() * COMMANDS.length)]; } while (c === lastCmd && COMMANDS.length > 1);
    lastCmd = c;
    return c;
  }

  function render() {
    var val = input.value, html = "", i, ch, cls, disp;
    for (i = 0; i < target.length; i++) {
      ch = target.charAt(i);
      cls = "ch" + (ch === " " ? " sp" : "");
      if (i < val.length) cls += (val.charAt(i) === ch) ? " ok" : " bad";
      else if (i === val.length && !done) cls += " cur";
      disp = ch === " " ? "&nbsp;" : escChar(ch);
      html += '<span class="' + cls + '">' + disp + "</span>";
    }
    textEl.innerHTML = html;
  }

  function liveStats() {
    var secs = started ? (now() - startMs) / 1000 : 0;
    elTime.textContent = secs.toFixed(1) + "s";
    var typed = input.value.length;
    elWpm.textContent = secs > 0 ? Math.min(400, Math.round((typed / 5) / (secs / 60))) : 0;
    elAcc.textContent = (keystrokes > 0 ? Math.round(((keystrokes - errors) / keystrokes) * 100) : 100) + "%";
  }

  function startLoop() {
    if (reduce) return;
    (function tick() { liveStats(); rafId = requestAnimationFrame(tick); })();
  }
  function stopLoop() { if (rafId) cancelAnimationFrame(rafId); rafId = 0; }

  function reset(newCmd) {
    if (newCmd || !target) target = pick();
    input.value = ""; prevLen = 0;
    started = false; done = false; startMs = 0; keystrokes = 0; errors = 0;
    panel.classList.remove("done");
    result.hidden = true; result.innerHTML = "";
    hint.style.display = "";
    elWpm.textContent = "0"; elAcc.textContent = "100%"; elTime.textContent = "0.0s";
    elBest.textContent = best ? best + " wpm" : "—";
    stopLoop();
    render();
  }

  function finish() {
    done = true; stopLoop();
    var secs = (now() - startMs) / 1000;
    // Clamp: a legit human tops out ~200 wpm; cap protects against absurd sub-ms timings.
    var wpm = secs > 0 ? Math.min(400, Math.round((target.length / 5) / (secs / 60))) : 0;
    var acc = keystrokes > 0 ? Math.round(((keystrokes - errors) / keystrokes) * 100) : 100;
    elWpm.textContent = wpm; elAcc.textContent = acc + "%"; elTime.textContent = secs.toFixed(1) + "s";
    var isBest = wpm > best;
    if (isBest) { best = wpm; bestSet(best); }
    elBest.textContent = best + " wpm";
    panel.classList.add("done");
    render();
    result.innerHTML =
      '<div class="big">' + wpm + '<span class="unit">wpm</span>' +
        '<span class="sub">· ' + acc + "% acc · " + secs.toFixed(1) + "s</span></div>" +
      (isBest ? '<div class="best-new">◆ new personal best!</div>'
              : (best ? '<div style="margin-top:8px;color:var(--muted)">best: ' + best + " wpm</div>" : "")) +
      '<div class="cta"><span class="retry">press <kbd>enter</kbd> or <b>click</b> to try another →</span></div>';
    result.hidden = false;
    track("game_over", { game: "typing", wpm: wpm, accuracy: acc });
  }

  input.addEventListener("input", function () {
    if (done) return;
    var val = input.value;
    if (val.length > target.length) { input.value = val.slice(0, target.length); val = input.value; }

    if (val.length > prevLen) {
      for (var j = prevLen; j < val.length; j++) {
        keystrokes++;
        if (val.charAt(j) !== target.charAt(j)) errors++;
      }
    }
    prevLen = val.length;

    if (!started && val.length > 0) {
      started = true; startMs = now(); startLoop();
      track("game_start", { game: "typing" });
    }
    render();
    liveStats();
    if (val === target) finish();
  });

  // No paste-to-win.
  input.addEventListener("paste", function (e) { e.preventDefault(); });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); reset(done); focusInput(); }
    else if (e.key === "Escape") { e.preventDefault(); reset(false); } // restart same command
  });

  function focusInput() { try { input.focus({ preventScroll: true }); } catch (e) { input.focus(); } }

  // Tap/click anywhere on the cabinet focuses the (invisible) input; if finished, load a new one.
  panel.addEventListener("mousedown", function (e) {
    if (e.target.closest("a")) return;
    if (done) reset(true);
    setTimeout(focusInput, 0);
  });
  panel.addEventListener("touchstart", function () {
    if (done) reset(true);
    setTimeout(focusInput, 0);
  }, { passive: true });

  // Desktop: focus so you can just start typing. Touch: wait for a tap (don't force the keyboard up).
  reset(true);
  if (canHover) {
    focusInput();
    hint.innerHTML = "just start typing · <kbd>esc</kbd> restarts";
  } else {
    hint.innerHTML = "tap here, then type · <kbd>esc</kbd> restarts";
  }
})();


/* ---------- Guess the Stack (daily) ---------- */
(function () {
  "use strict";
  var root = document.getElementById("gts");
  if (!root) return;

  var cluesEl  = document.getElementById("gtsClues");
  var input    = document.getElementById("gtsInput");
  var sug      = document.getElementById("gtsSug");
  var dotsEl   = document.getElementById("gtsDots");
  var resEl    = document.getElementById("gtsResult");
  var guessBtn = document.getElementById("gtsGuess");
  var skipBtn  = document.getElementById("gtsSkip");
  var playEl   = document.getElementById("gtsPlay");
  var noEl     = document.getElementById("gtsNo");

  var MAX = 5;

  // Ordered clues per company: hardest first (language), easiest last (category).
  var COMPANIES = [
    { n: "Discord", c: [["sector","messaging"],["does","voice & text chat for gaming communities"],["scale","millions of concurrent voice users"],["stack","Rust hot paths, data on ScyllaDB"],["lang","Elixir"]] },
    { n: "WhatsApp", c: [["sector","messaging"],["does","end-to-end encrypted messaging"],["scale","2B users on a famously tiny team"],["stack","FreeBSD + Mnesia"],["lang","Erlang"]] },
    { n: "Instagram", c: [["sector","social"],["does","photo & short-video sharing"],["scale","billions of photos and reels"],["stack","Django + PostgreSQL/Cassandra"],["lang","Python"]] },
    { n: "Shopify", c: [["sector","e-commerce"],["does","hosted online storefronts"],["scale","survives Black Friday every year"],["stack","a Rails monolith + MySQL/Vitess"],["lang","Ruby"]] },
    { n: "Netflix", c: [["sector","video streaming"],["does","movies & TV streaming"],["scale","~15% of internet traffic, all on AWS"],["stack","Spring Boot microservices + Cassandra"],["lang","Java"]] },
    { n: "Stack Overflow", a: ["stackoverflow"], c: [["sector","developer tools"],["does","Q&A for programmers"],["scale","huge traffic on a handful of servers"],["stack","an ASP.NET monolith + SQL Server"],["lang","C#"]] },
    { n: "Figma", c: [["sector","design tools"],["does","collaborative interface design"],["scale","live multiplayer cursors in the browser"],["stack","Rust services + a WebGL renderer"],["lang","C++ compiled to WebAssembly"]] },
    { n: "GitHub", c: [["sector","developer tools"],["does","hosts git repos & pull requests"],["scale","home to 100M+ developers"],["stack","Ruby on Rails + MySQL"],["lang","Ruby"]] },
    { n: "Booking.com", a: ["booking"], c: [["sector","travel"],["does","hotel & travel booking"],["scale","A/B tests literally everything"],["stack","one of the largest Perl codebases + MySQL"],["lang","Perl"]] },
    { n: "Wikipedia", c: [["sector","reference"],["does","the free encyclopedia"],["scale","a top-10 site run by a nonprofit"],["stack","MediaWiki + MariaDB + Varnish"],["lang","PHP"]] },
    { n: "Slack", c: [["sector","messaging"],["does","work chat & channels"],["scale","enterprise team messaging"],["stack","Hack/HHVM + MySQL/Vitess"],["lang","PHP (Hack)"]] },
    { n: "Meta", a: ["facebook","fb"], c: [["sector","social"],["does","the social network"],["scale","billions of daily users"],["stack","React + MySQL behind TAO"],["lang","PHP, then Hack"]] },
    { n: "Reddit", c: [["sector","social"],["does","link-sharing communities"],["scale","'the front page of the internet'"],["stack","originally Pylons + PostgreSQL/Cassandra"],["lang","Python"]] },
    { n: "Airbnb", c: [["sector","travel"],["does","book someone's home to stay in"],["scale","millions of listings worldwide"],["stack","Rails + a React frontend + MySQL"],["lang","Ruby"]] },
    { n: "Uber", c: [["sector","ride-hailing"],["does","ride-hailing & delivery"],["scale","real-time geospatial dispatch"],["stack","thousands of microservices + Schemaless"],["lang","Go & Node.js"]] },
    { n: "Lyft", c: [["sector","ride-hailing"],["does","ride-hailing"],["scale","real-time ride matching"],["stack","Envoy service mesh (they made it)"],["lang","Python & Go"]] },
    { n: "LinkedIn", c: [["sector","social"],["does","professional networking"],["scale","the professional graph"],["stack","Kafka (they made it) + Espresso"],["lang","Java & Scala"]] },
    { n: "Twitter", a: ["x"], c: [["sector","social"],["does","public microblogging"],["scale","the global public timeline"],["stack","moved off Rails, data on Manhattan"],["lang","Scala & Java"]] },
    { n: "Spotify", c: [["sector","music"],["does","music & podcast streaming"],["scale","600M+ listeners"],["stack","microservices + Backstage, on Google Cloud"],["lang","Java & Python"]] },
    { n: "Dropbox", c: [["sector","storage"],["does","file sync & storage"],["scale","left AWS to build 'Magic Pocket'"],["stack","Rust in hot paths + MySQL"],["lang","Python"]] },
    { n: "Pinterest", c: [["sector","social"],["does","save & discover images"],["scale","visual discovery at scale"],["stack","Django/Flask + MySQL/HBase"],["lang","Python"]] },
    { n: "Stripe", c: [["sector","fintech / payments"],["does","online payment APIs"],["scale","payments infra for developers"],["stack","Scala & Go infra + a custom ledger"],["lang","Ruby"]] },
    { n: "Etsy", c: [["sector","e-commerce"],["does","buy & sell handmade goods"],["scale","a global handmade marketplace"],["stack","continuous deployment pioneers + MySQL"],["lang","PHP"]] },
    { n: "Cloudflare", c: [["sector","infrastructure"],["does","CDN, DNS & edge security"],["scale","sits in front of ~20% of the web"],["stack","OpenResty at the edge, now Workers"],["lang","Go & Rust"]] },
    { n: "Vercel", c: [["sector","developer tools"],["does","frontend hosting & deployment"],["scale","where much of the modern web deploys"],["stack","Next.js (they make it) + serverless edge"],["lang","TypeScript / Node.js"]] },
    { n: "Zoom", c: [["sector","video"],["does","video conferencing"],["scale","exploded overnight in 2020"],["stack","a heavily optimized native client"],["lang","C++"]] },
    { n: "Google", a: ["googlesearch"], c: [["sector","search"],["does","web search"],["scale","planet-scale, low latency"],["stack","Bigtable → Spanner, MapReduce"],["lang","C++, Java & Go"]] },
    { n: "Amazon", c: [["sector","e-commerce"],["does","online shopping & cloud"],["scale","earth's biggest store, on AWS"],["stack","service-oriented architecture + DynamoDB"],["lang","Java"]] },
    { n: "Twitch", c: [["sector","video streaming"],["does","live game streaming"],["scale","live video to millions"],["stack","Rails origins (Justin.tv), heavy video ingest"],["lang","Go"]] },
    { n: "Robinhood", c: [["sector","fintech / payments"],["does","stock & crypto trading"],["scale","commission-free trading spikes"],["stack","Django + Kafka pipelines"],["lang","Python"]] }
  ];

  var mem = {};
  function jget(k) { try { var v = window.localStorage.getItem(k); return v ? JSON.parse(v) : (mem[k] || null); } catch (e) { return mem[k] || null; } }
  function jset(k, v) { mem[k] = v; try { window.localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* memory only */ } }
  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) { /* ignore */ } }
  function norm(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, ""); }
  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function keyOf(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return c === "&" ? "&amp;" : c === "<" ? "&lt;" : "&gt;"; }); }

  var today = new Date();
  var todayKey = keyOf(today);
  var EPOCH = Date.UTC(2026, 0, 1);
  var daysSince = Math.floor((Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) - EPOCH) / 86400000);
  var puzzleNo = daysSince + 1;
  var puzzle = COMPANIES[((daysSince % COMPANIES.length) + COMPANIES.length) % COMPANIES.length];
  noEl.textContent = puzzleNo;

  var NAMES = COMPANIES.map(function (c) { return c.n; });
  var curSug = [], activeSug = -1, cdTimer = null;

  var state = jget("gts_state");
  if (!state || state.date !== todayKey) state = { date: todayKey, marks: [], solved: false, over: false };

  function revealsCount() { return Math.min(MAX, 1 + state.marks.length); }

  function renderClues() {
    var n = state.over ? Math.min(MAX, puzzle.c.length) : revealsCount();
    cluesEl.innerHTML = "";
    for (var i = 0; i < n; i++) {
      var li = document.createElement("li");
      li.className = "gts__clue" + (i === n - 1 && !state.over ? " latest" : "");
      li.innerHTML = '<span class="k">' + puzzle.c[i][0] + '</span><span class="v">' + esc(puzzle.c[i][1]) + "</span>";
      cluesEl.appendChild(li);
    }
  }
  function renderDots() {
    dotsEl.innerHTML = "";
    for (var i = 0; i < MAX; i++) {
      var d = document.createElement("i");
      if (state.marks[i]) d.className = state.marks[i];
      dotsEl.appendChild(d);
    }
  }
  function gridEmoji() {
    var map = { solve: "🟩", miss: "🟥", skip: "⬛" }, out = "";
    for (var i = 0; i < MAX; i++) out += state.marks[i] ? map[state.marks[i]] : "⬜";
    return out;
  }

  function showSug(q) {
    var nq = norm(q);
    if (!nq) return hideSug();
    curSug = NAMES.filter(function (name) { return norm(name).indexOf(nq) > -1; }).slice(0, 6);
    if (!curSug.length) return hideSug();
    sug.innerHTML = curSug.map(function (name, i) {
      return '<li role="option" data-i="' + i + '"' + (i === activeSug ? ' class="active"' : "") + ">" + esc(name) + "</li>";
    }).join("");
    sug.hidden = false;
  }
  function hideSug() { sug.hidden = true; sug.innerHTML = ""; curSug = []; activeSug = -1; }

  function winRate(s) { return s && s.played ? Math.round((s.won / s.played) * 100) : 0; }

  function recordStats(won) {
    var s = jget("gts_stats") || { streak: 0, max: 0, played: 0, won: 0, lastDate: null };
    if (s.lastDate === todayKey) return; // already recorded today
    var y = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
    s.played = (s.played || 0) + 1;
    if (won) {
      s.won = (s.won || 0) + 1;
      s.streak = (s.lastDate === keyOf(y) ? (s.streak || 0) + 1 : 1);
    } else {
      s.streak = 0;
    }
    s.max = Math.max(s.max || 0, s.streak);
    s.lastDate = todayKey;
    jset("gts_stats", s);
  }

  function endGame(won) {
    recordStats(won);
    renderClues(); renderDots();
    playEl.style.display = "none";
    var s = jget("gts_stats") || {};
    var count = state.marks.length;
    resEl.hidden = false;
    resEl.innerHTML =
      '<div class="gts__verdict' + (won ? " win" : "") + '">' + (won ? "nailed it · " + count + "/" + MAX : "out of guesses") + "</div>" +
      '<div class="gts__answer">it was <b>' + esc(puzzle.n) + "</b></div>" +
      '<div class="gts__grid" aria-hidden="true">' + gridEmoji() + "</div>" +
      '<div class="gts__statline"><span>streak <b>' + (s.streak || 0) + "</b></span><span>max <b>" + (s.max || 0) +
        "</b></span><span>win rate <b>" + winRate(s) + "%</b></span></div>" +
      '<div class="gts__sharerow">' +
        '<button class="gts__share" id="gtsImg" type="button">🖼 share image</button>' +
        '<button class="gts__share ghost" id="gtsCopy" type="button">📋 copy</button>' +
      "</div>" +
      '<div class="gts__next">next puzzle in <b id="gtsCountdown">—</b></div>';
    document.getElementById("gtsImg").addEventListener("click", shareImage);
    document.getElementById("gtsCopy").addEventListener("click", share);
    startCountdown();
  }

  function doGuess(name) {
    if (state.over) return;
    var g = norm(name);
    if (!g) return;
    if (state.marks.length === 0) track("gts_start", { puzzle: puzzleNo });
    var hit = g === norm(puzzle.n) || (puzzle.a && puzzle.a.some(function (x) { return norm(x) === g; }));
    if (hit) {
      state.marks.push("solve"); state.solved = true; state.over = true;
      jset("gts_state", state);
      track("gts_result", { won: true, guesses: state.marks.length, puzzle: puzzleNo });
      endGame(true);
    } else {
      state.marks.push("miss");
      finishOrContinue();
    }
  }
  function doSkip() {
    if (state.over) return;
    if (state.marks.length === 0) track("gts_start", { puzzle: puzzleNo });
    state.marks.push("skip");
    finishOrContinue();
  }
  function finishOrContinue() {
    if (state.marks.length >= MAX) {
      state.over = true; jset("gts_state", state);
      track("gts_result", { won: false, guesses: MAX, puzzle: puzzleNo });
      endGame(false);
    } else {
      jset("gts_state", state);
      input.value = ""; hideSug();
      renderClues(); renderDots();
    }
  }

  function shareText() {
    var count = state.marks.length;
    var head = "Guess the Stack #" + puzzleNo + " " + (state.solved ? count + "/" + MAX : "X/" + MAX);
    return head + "\n" + gridEmoji() + "\nhttps://iyush.dev/games";
  }

  function share() {
    var text = shareText();
    var done = function () {
      var b = document.getElementById("gtsCopy");
      if (b) { b.textContent = "✓ copied"; setTimeout(function () { b.textContent = "📋 copy"; }, 1600); }
    };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
      } else fallbackCopy(text, done);
    } catch (e) { fallbackCopy(text, done); }
    track("gts_share", { won: state.solved, puzzle: puzzleNo });
  }

  /* ---- Share card (canvas → PNG), themed with the current palette ---- */
  function cssVar(cs, name, fb) { var x = cs.getPropertyValue(name).trim(); return x || fb; }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }
  function drawCard() {
    return new Promise(function (resolve) {
      var W = 1200, H = 630, S = 2;
      var canvas = document.createElement("canvas");
      canvas.width = W * S; canvas.height = H * S;
      var ctx = canvas.getContext("2d"); ctx.scale(S, S);
      var cs = getComputedStyle(document.documentElement);
      var C = {
        bg: cssVar(cs, "--bg", "#0A0C10"), surf: cssVar(cs, "--surface", "#101319"),
        text: cssVar(cs, "--text", "#E8EBF0"), muted: cssVar(cs, "--muted", "#6B7482"),
        mutedB: cssVar(cs, "--muted-bright", "#8B95A5"), border: cssVar(cs, "--border", "#1C2230"),
        live: cssVar(cs, "--live", "#3FB950"), deploy: cssVar(cs, "--deploy", "#D29922"),
        archived: cssVar(cs, "--archived", "#545E70")
      };
      function paint() {
        ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
        ctx.strokeStyle = "rgba(127,127,127,0.05)"; ctx.lineWidth = 1;
        var g;
        for (g = 0; g <= W; g += 60) { ctx.beginPath(); ctx.moveTo(g, 0); ctx.lineTo(g, H); ctx.stroke(); }
        for (g = 0; g <= H; g += 60) { ctx.beginPath(); ctx.moveTo(0, g); ctx.lineTo(W, g); ctx.stroke(); }
        ctx.fillStyle = C.live; ctx.fillRect(0, 0, 6, H);
        var padX = 80;
        ctx.textBaseline = "middle"; ctx.textAlign = "left";
        ctx.fillStyle = C.live; ctx.beginPath(); ctx.arc(padX + 9, 92, 8, 0, Math.PI * 2); ctx.fill();
        ctx.font = '500 26px "JetBrains Mono", monospace';
        ctx.fillStyle = C.text; ctx.fillText("iyush.dev", padX + 30, 93);
        ctx.fillStyle = C.muted; ctx.textAlign = "right"; ctx.fillText("guess the stack", W - padX, 93); ctx.textAlign = "left";
        ctx.fillStyle = state.solved ? C.live : C.text;
        ctx.font = '700 74px "Space Grotesk", sans-serif';
        ctx.fillText(state.solved ? "Nailed it." : "Out of guesses.", padX, 206);
        var count = state.marks.length;
        ctx.font = '400 30px "JetBrains Mono", monospace'; ctx.fillStyle = C.mutedB;
        ctx.fillText("Guess the Stack #" + puzzleNo + "   ·   " + (state.solved ? count + "/" + MAX : "X/" + MAX), padX, 262);
        var sz = 88, gap = 16, top = 312, i, m, col, x;
        for (i = 0; i < MAX; i++) {
          m = state.marks[i];
          col = m === "solve" ? C.live : m === "miss" ? C.deploy : m === "skip" ? C.archived : C.surf;
          x = padX + i * (sz + gap);
          roundRect(ctx, x, top, sz, sz, 12); ctx.fillStyle = col; ctx.fill();
          if (!m) { ctx.lineWidth = 1.5; ctx.strokeStyle = C.border; roundRect(ctx, x, top, sz, sz, 12); ctx.stroke(); }
        }
        var s = jget("gts_stats") || {};
        ctx.font = '400 26px "JetBrains Mono", monospace'; ctx.fillStyle = C.muted;
        ctx.fillText("streak " + (s.streak || 0) + "     ·     max " + (s.max || 0) + "     ·     win rate " + winRate(s) + "%", padX, 468);
        ctx.strokeStyle = C.border; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(padX, 528); ctx.lineTo(W - padX, 528); ctx.stroke();
        ctx.font = '500 26px "JetBrains Mono", monospace';
        ctx.fillStyle = C.live; ctx.fillText("$", padX, 566);
        ctx.fillStyle = C.mutedB; ctx.fillText("iyush.dev/games", padX + 28, 566);
        ctx.fillStyle = C.muted; ctx.textAlign = "right"; ctx.fillText("play today →", W - padX, 566); ctx.textAlign = "left";
        resolve(canvas);
      }
      if (document.fonts && document.fonts.load) {
        Promise.all([
          document.fonts.load('700 74px "Space Grotesk"'),
          document.fonts.load('500 26px "JetBrains Mono"'),
          document.fonts.load('400 30px "JetBrains Mono"')
        ]).then(paint, paint);
      } else { paint(); }
    });
  }
  function downloadBlob(blob) {
    try {
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a"); a.href = url; a.download = "guess-the-stack-" + puzzleNo + ".png";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
    } catch (e) { /* ignore */ }
  }
  function resetImgBtn() { var b = document.getElementById("gtsImg"); if (b) { b.textContent = "🖼 share image"; b.disabled = false; } }
  function shareImage() {
    var btn = document.getElementById("gtsImg");
    if (btn) { btn.textContent = "rendering…"; btn.disabled = true; }
    drawCard().then(function (canvas) {
      var handle = function (blob) {
        if (!blob) { resetImgBtn(); return; }
        var file = null;
        try { file = new File([blob], "guess-the-stack-" + puzzleNo + ".png", { type: "image/png" }); } catch (e) { /* File ctor unsupported */ }
        if (file && navigator.canShare && navigator.canShare({ files: [file] }) && navigator.share) {
          navigator.share({ files: [file], title: "Guess the Stack #" + puzzleNo, text: shareText() })
            .then(resetImgBtn, function () { downloadBlob(blob); resetImgBtn(); });
        } else {
          downloadBlob(blob); resetImgBtn();
        }
        track("gts_share_image", { won: state.solved, puzzle: puzzleNo });
      };
      if (canvas.toBlob) canvas.toBlob(handle, "image/png");
      else { resetImgBtn(); }
    }).catch(function () { resetImgBtn(); });
  }
  function fallbackCopy(text, done) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.focus(); ta.select();
      document.execCommand("copy"); document.body.removeChild(ta);
      done && done();
    } catch (e) { /* ignore */ }
  }

  function startCountdown() {
    var el = document.getElementById("gtsCountdown");
    if (!el) return;
    function tick() {
      var n = new Date();
      var next = new Date(n.getFullYear(), n.getMonth(), n.getDate() + 1, 0, 0, 0, 0);
      var ms = Math.max(0, next - n);
      el.textContent = pad(Math.floor(ms / 3600000)) + ":" + pad(Math.floor((ms % 3600000) / 60000)) + ":" + pad(Math.floor((ms % 60000) / 1000));
    }
    tick();
    if (cdTimer) clearInterval(cdTimer);
    cdTimer = setInterval(tick, 1000);
  }

  guessBtn.addEventListener("click", function () { doGuess(input.value); });
  skipBtn.addEventListener("click", doSkip);
  input.addEventListener("input", function () { activeSug = -1; showSug(input.value); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown" && curSug.length) { e.preventDefault(); activeSug = Math.min(curSug.length - 1, activeSug + 1); showSug(input.value); }
    else if (e.key === "ArrowUp" && curSug.length) { e.preventDefault(); activeSug = Math.max(0, activeSug - 1); showSug(input.value); }
    else if (e.key === "Enter") { e.preventDefault(); doGuess(activeSug >= 0 && curSug[activeSug] ? curSug[activeSug] : input.value); }
    else if (e.key === "Escape") { hideSug(); }
  });
  sug.addEventListener("mousedown", function (e) {
    var li = e.target.closest("li"); if (!li) return;
    e.preventDefault();
    doGuess(curSug[parseInt(li.getAttribute("data-i"), 10)]);
  });
  input.addEventListener("blur", function () { setTimeout(hideSug, 120); });

  // Boot
  renderClues();
  renderDots();
  if (state.over) endGame(state.solved);
})();
