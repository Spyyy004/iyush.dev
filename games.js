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
