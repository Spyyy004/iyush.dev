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
    { n: "Discord", c: [["lang","Elixir"],["uses","Rust for the hot paths"],["data","Cassandra → ScyllaDB"],["scale","millions of concurrent WebSockets"],["does","voice & text chat for communities"]] },
    { n: "WhatsApp", c: [["lang","Erlang"],["uses","FreeBSD + a custom XMPP server"],["data","Mnesia"],["scale","2B users on a famously tiny team"],["does","end-to-end encrypted messaging"]] },
    { n: "Instagram", c: [["lang","Python"],["uses","Django"],["data","PostgreSQL + Cassandra"],["scale","billions of photos and reels"],["does","photo & short-video sharing"]] },
    { n: "Shopify", c: [["lang","Ruby"],["uses","Rails, as a modular monolith"],["data","MySQL sharded with Vitess"],["scale","survives Black Friday every year"],["does","hosted online stores"]] },
    { n: "Netflix", c: [["lang","Java"],["uses","Spring Boot microservices"],["data","Cassandra + EVCache"],["scale","~15% of internet traffic, all on AWS"],["does","video streaming"]] },
    { n: "Stack Overflow", a: ["stackoverflow"], c: [["lang","C#"],["uses","ASP.NET, a proud monolith"],["data","SQL Server"],["scale","huge traffic on a handful of servers"],["does","Q&A for programmers"]] },
    { n: "Figma", c: [["lang","C++ compiled to WebAssembly"],["uses","a custom WebGL renderer"],["data","Rust real-time services"],["scale","live multiplayer cursors in the browser"],["does","collaborative interface design"]] },
    { n: "GitHub", c: [["lang","Ruby"],["uses","Ruby on Rails"],["data","MySQL + Elasticsearch"],["scale","100M+ developers' repos"],["does","git hosting & collaboration"]] },
    { n: "Booking.com", a: ["booking"], c: [["lang","Perl"],["uses","one of the largest Perl codebases alive"],["data","MySQL"],["scale","A/B tests on literally everything"],["does","hotel & travel booking"]] },
    { n: "Wikipedia", c: [["lang","PHP"],["uses","MediaWiki"],["data","MariaDB + Varnish caching"],["scale","a top-10 site run by a nonprofit"],["does","the free encyclopedia"]] },
    { n: "Slack", c: [["lang","PHP (Hack)"],["uses","HHVM"],["data","MySQL + Vitess"],["scale","enterprise-grade team messaging"],["does","work chat & channels"]] },
    { n: "Meta", a: ["facebook","fb"], c: [["lang","PHP, then Hack"],["uses","HHVM + React (they built it)"],["data","MySQL behind TAO"],["scale","billions of daily users"],["does","the social network"]] },
    { n: "Reddit", c: [["lang","Python"],["uses","originally the Pylons framework"],["data","PostgreSQL + Cassandra"],["scale","'the front page of the internet'"],["does","link-sharing communities"]] },
    { n: "Airbnb", c: [["lang","Ruby"],["uses","Rails + a React frontend"],["data","MySQL"],["scale","millions of listings worldwide"],["does","book someone's home to stay in"]] },
    { n: "Uber", c: [["lang","Go & Node.js"],["uses","thousands of microservices"],["data","Schemaless on MySQL"],["scale","real-time geospatial dispatch"],["does","ride-hailing"]] },
    { n: "Lyft", c: [["lang","Python & Go"],["uses","Envoy service mesh (they created it)"],["data","MySQL + DynamoDB"],["scale","real-time ride matching"],["does","ride-hailing"]] },
    { n: "LinkedIn", c: [["lang","Java & Scala"],["uses","Kafka (they created it)"],["data","Espresso + Venice"],["scale","the professional graph"],["does","professional networking"]] },
    { n: "Twitter", a: ["x"], c: [["lang","Scala & Java"],["uses","moved off Rails after the 'fail whale'"],["data","Manhattan"],["scale","the global public timeline"],["does","public microblogging"]] },
    { n: "Spotify", c: [["lang","Java & Python"],["uses","microservices + Backstage (they made it)"],["data","runs largely on Google Cloud"],["scale","600M+ listeners"],["does","music & podcast streaming"]] },
    { n: "Dropbox", c: [["lang","Python"],["uses","Rust in performance-critical paths"],["data","MySQL (Edgestore)"],["scale","left AWS to build 'Magic Pocket'"],["does","file sync & storage"]] },
    { n: "Pinterest", c: [["lang","Python"],["uses","Django & Flask"],["data","MySQL + HBase"],["scale","visual discovery at scale"],["does","save & discover images"]] },
    { n: "Stripe", c: [["lang","Ruby"],["uses","Scala & Go for infrastructure"],["data","Mongo early on, plus a custom ledger"],["scale","payments infra for developers"],["does","online payment APIs"]] },
    { n: "Etsy", c: [["lang","PHP"],["uses","pioneered continuous deployment & StatsD"],["data","MySQL"],["scale","a global handmade marketplace"],["does","buy & sell handmade goods"]] },
    { n: "Cloudflare", c: [["lang","Go & Rust"],["uses","Lua/OpenResty at the edge, now Workers"],["data","a global anycast network"],["scale","sits in front of ~20% of the web"],["does","CDN, DNS & edge security"]] },
    { n: "Vercel", c: [["lang","TypeScript / Node.js"],["uses","Next.js (they make it)"],["data","serverless + a global edge network"],["scale","where much of the modern web deploys"],["does","frontend hosting & deployment"]] },
    { n: "Zoom", c: [["lang","C++"],["uses","a heavily optimized native client"],["data","global media routing"],["scale","exploded overnight in 2020"],["does","video conferencing"]] },
    { n: "Google", a: ["googlesearch"], c: [["lang","C++, Java & Go (they created Go)"],["uses","MapReduce → Bigtable → Spanner"],["data","the web index"],["scale","planet-scale, low latency"],["does","web search"]] },
    { n: "Amazon", c: [["lang","Java (and everything else)"],["uses","pioneered service-oriented architecture"],["data","DynamoDB, born in-house"],["scale","runs the store on AWS"],["does","online shopping & cloud"]] },
    { n: "Twitch", c: [["lang","Go"],["uses","Rails in its origins (Justin.tv)"],["data","video ingest at massive concurrency"],["scale","live streaming to millions"],["does","live game streaming"]] },
    { n: "Robinhood", c: [["lang","Python"],["uses","Django"],["data","Kafka-driven pipelines"],["scale","commission-free trading spikes"],["does","stock & crypto trading"]] }
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
      '<button class="gts__share" id="gtsShare" type="button">📋 copy result</button>' +
      '<div class="gts__next">next puzzle in <b id="gtsCountdown">—</b></div>';
    document.getElementById("gtsShare").addEventListener("click", share);
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

  function share() {
    var count = state.marks.length;
    var head = "Guess the Stack #" + puzzleNo + " " + (state.solved ? count + "/" + MAX : "X/" + MAX);
    var text = head + "\n" + gridEmoji() + "\nhttps://iyush.dev/games";
    var done = function () {
      var b = document.getElementById("gtsShare");
      if (b) { b.textContent = "✓ copied"; setTimeout(function () { b.textContent = "📋 copy result"; }, 1600); }
    };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
      } else fallbackCopy(text, done);
    } catch (e) { fallbackCopy(text, done); }
    track("gts_share", { won: state.solved, puzzle: puzzleNo });
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
