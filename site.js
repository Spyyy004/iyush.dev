/* ============================================================
   iyush.dev — shared behavior
   Theme engine (light/dark + dice themes), floating command shell,
   live telemetry (npm + GitHub), scroll reveals, homepage boot.
   Linked (deferred) by every page.
   ============================================================ */
(function () {
  "use strict";

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Storage that never crashes ---------- */
  var mem = {};
  function storeGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return mem[key] || null; }
  }
  function storeSet(key, val) {
    mem[key] = val;
    try { window.localStorage.setItem(key, val); } catch (e) { /* memory only */ }
  }

  /* ---------- Analytics (Google Analytics 4 / gtag) ---------- */
  // 👉 Paste your GA4 Measurement ID below (format: "G-XXXXXXXXXX") to switch analytics ON.
  //    Empty string = disabled (safe no-op). Auto-skipped on localhost so your own
  //    dev traffic never pollutes the numbers. This is the ONLY place you set it.
  var GA_ID = "G-GKC1N1X7KY";
  function initAnalytics() {
    if (!GA_ID || GA_ID.indexOf("G-") !== 0) return;
    var h = location.hostname;
    if (!h || h === "localhost" || h === "127.0.0.1" || h.slice(-6) === ".local") return;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA_ID);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", GA_ID);
  }
  // Fire a custom event (no-op until GA is configured).
  function track(name, params) {
    try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) { /* ignore */ }
  }

  /* ---------- Themes ---------- */
  // mode drives the light/dark toggle behavior + the OS-default logic.
  var THEMES = {
    dark:      { label: "dark",      mode: "dark",  icon: "☾" },
    light:     { label: "light",     mode: "light", icon: "☀" },
    onepiece:  { label: "one piece", mode: "dark",  icon: "⚓" },
    matrix:    { label: "matrix",    mode: "dark",  icon: "◆" },
    synthwave: { label: "synthwave", mode: "dark",  icon: "◆" },
    dracula:   { label: "dracula",   mode: "dark",  icon: "◆" },
    solarized: { label: "solarized", mode: "light", icon: "☀" }
  };
  function currentTheme() {
    var t = document.documentElement.getAttribute("data-theme");
    return THEMES[t] ? t : "dark";
  }
  function updateToggle(theme) {
    var btn = document.getElementById("themeToggle");
    if (!btn) return;
    var t = THEMES[theme] || THEMES.dark;
    btn.setAttribute("aria-pressed", t.mode === "light" ? "true" : "false");
    btn.setAttribute("aria-label", "Switch light/dark theme (current: " + t.label + ")");
    var icon = btn.querySelector(".tt-icon");
    var label = btn.querySelector(".tt-label");
    if (icon) icon.textContent = t.icon;
    if (label) label.textContent = t.label;
  }
  function applyTheme(theme) {
    if (!THEMES[theme]) theme = "dark";
    document.documentElement.setAttribute("data-theme", theme);
    storeSet("theme", theme);
    updateToggle(theme);
  }
  function toggleTheme() {
    // Always resolve to one of the two base modes.
    var mode = (THEMES[currentTheme()] || THEMES.dark).mode;
    applyTheme(mode === "dark" ? "light" : "dark");
  }
  function rollTheme() {
    var cur = currentTheme();
    var keys = Object.keys(THEMES).filter(function (k) { return k !== cur; });
    var pick = keys[Math.floor(Math.random() * keys.length)];
    applyTheme(pick);
    toast("🎲 rolled: " + THEMES[pick].label);
    track("theme_change", { theme: pick, via: "dice" });
    return pick;
  }

  /* ---------- Toast (theme roll announcements) ---------- */
  var toastEl = null, toastTimer = null;
  function toast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.hidden = false;
    void toastEl.offsetWidth; // reflow so the transition runs
    toastEl.classList.add("show");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.classList.remove("show");
      setTimeout(function () { toastEl.hidden = true; }, reduce ? 0 : 260);
    }, reduce ? 1200 : 1700);
  }

  function injectThemeControls() {
    var toggle = document.getElementById("themeToggle");
    if (toggle && toggle.parentNode && !document.getElementById("diceRoll")) {
      var d = document.createElement("button");
      d.id = "diceRoll";
      d.type = "button";
      d.className = "theme-toggle dice";
      d.setAttribute("aria-label", "Roll a random theme");
      d.title = "Roll a random theme";
      d.innerHTML = '<span class="tt-icon" aria-hidden="true">🎲</span>';
      d.addEventListener("click", rollTheme);
      toggle.parentNode.insertBefore(d, toggle);
    }
    if (!document.getElementById("themeToast")) {
      toastEl = document.createElement("div");
      toastEl.id = "themeToast";
      toastEl.className = "theme-toast";
      toastEl.setAttribute("role", "status");
      toastEl.setAttribute("aria-live", "polite");
      toastEl.hidden = true;
      document.body.appendChild(toastEl);
    } else {
      toastEl = document.getElementById("themeToast");
    }
  }

  // Add the "games" nav link on every page (keeps the shell DRY).
  function injectNav() {
    var nav = document.querySelector(".sb-nav");
    if (!nav || nav.querySelector('a[href="games.html"]')) return;
    var a = document.createElement("a");
    a.href = "games.html";
    a.textContent = "games";
    if (/(^|\/)games\.html$/.test(location.pathname)) a.setAttribute("aria-current", "page");
    var ext = nav.querySelector(".ext");
    nav.insertBefore(a, ext || null);
  }

  /* ---------- Live telemetry (graceful — silent on failure) ---------- */
  var npmWeekly = null; // owthorize weekly downloads, once fetched

  function fmtNum(n) {
    if (n == null) return "—";
    if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, "") + "k";
    return String(n);
  }

  function renderNpm() {
    if (npmWeekly == null) return;
    var card = document.querySelector('a.service[href*="owthorize"]');
    if (!card) return;
    var m = card.querySelector(".live-metric");
    if (!m) {
      m = document.createElement("span");
      m.className = "live-metric";
      var link = card.querySelector(".service__link");
      if (link) card.insertBefore(m, link); else card.appendChild(m);
    }
    m.innerHTML = '<span class="ld" aria-hidden="true"></span><span><b>' +
      fmtNum(npmWeekly) + "</b> installs / week</span>";
  }

  function fetchNpm() {
    try {
      fetch("https://api.npmjs.org/downloads/point/last-week/owthorize")
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (d && typeof d.downloads === "number") { npmWeekly = d.downloads; renderNpm(); }
        })
        .catch(function () {});
    } catch (e) { /* ignore */ }
  }

  var ghState = null; // { days: [counts...], lastPushMs }

  function timeAgo(ms) {
    if (!ms) return "";
    var s = Math.max(1, Math.floor((Date.now() - ms) / 1000));
    if (s < 3600) return Math.floor(s / 60) + "m ago";
    if (s < 86400) return Math.floor(s / 3600) + "h ago";
    return Math.floor(s / 86400) + "d ago";
  }

  function renderGh() {
    if (!ghState) return;
    var inner = document.querySelector(".footer__inner");
    if (!inner) return;
    var sig = document.getElementById("ghSignal");
    if (!sig) {
      sig = document.createElement("span");
      sig.id = "ghSignal";
      sig.className = "gh-signal";
      sig.title = "GitHub push activity — last 14 days";
      inner.insertBefore(sig, inner.firstChild);
    }
    var max = Math.max(1, Math.max.apply(null, ghState.days));
    var bars = ghState.days.map(function (c) {
      var h = c === 0 ? 2 : Math.round(3 + (c / max) * 13);
      var op = c === 0 ? 0.25 : 0.85;
      return '<i style="height:' + h + "px;opacity:" + op + '"></i>';
    }).join("");
    sig.innerHTML = '<span class="gh-label">gh activity</span>' +
      '<span class="gh-bars" aria-hidden="true">' + bars + "</span>" +
      (ghState.lastPushMs ? '<span class="gh-last">push ' + timeAgo(ghState.lastPushMs) + "</span>" : "");
  }

  function fetchGitHub() {
    try {
      fetch("https://api.github.com/users/Spyyy004/events/public?per_page=100")
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (events) {
          if (!Array.isArray(events)) return;
          var days = [], i;
          for (i = 0; i < 14; i++) days.push(0);
          var now = Date.now(), lastPush = 0;
          events.forEach(function (e) {
            var t = Date.parse(e.created_at);
            if (isNaN(t)) return;
            if (e.type === "PushEvent") {
              if (t > lastPush) lastPush = t;
              var idx = 13 - Math.floor((now - t) / 86400000);
              if (idx >= 0 && idx < 14) {
                var commits = (e.payload && e.payload.commits && e.payload.commits.length) || 1;
                days[idx] += commits;
              }
            }
          });
          ghState = { days: days, lastPushMs: lastPush };
          renderGh();
        })
        .catch(function () {});
    } catch (e) { /* ignore */ }
  }

  /* ---------- Command bar / shell ---------- */
  var ROUTES = { home: "index.html", projects: "projects.html", blog: "blog.html", games: "games.html" };
  var OPEN = {
    github: "https://github.com/Spyyy004",
    linkedin: "https://linkedin.com/in/ayush-pawar004",
    email: "mailto:cswithiyush@gmail.com"
  };
  var STACK = ["javascript", "typescript", "node", "react", "python", "postgres", "ml", "dns"];

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function yearsShipping() {
    try { return Math.max(1, new Date().getFullYear() - 2022); } catch (e) { return 3; }
  }

  function resolveRoute(s) {
    var t = s.replace(/^cd\b\s*/, "").replace(/^~\/?/, "").replace(/^\//, "").replace(/\/+$/, "").trim();
    if (t === "" || t === "~" || t === "home" || t === "index") return { label: "home", url: ROUTES.home };
    if (t === "projects" || t === "project" || t === "services") return { label: "projects", url: ROUTES.projects };
    if (t === "blog" || t === "blogs" || t === "posts") return { label: "blog", url: ROUTES.blog };
    if (t === "games" || t === "game" || t === "arcade" || t === "play") return { label: "games", url: ROUTES.games };
    return null;
  }

  function initCommandBar() {
    var bar = document.getElementById("cmdbar");
    var input = document.getElementById("cmdInput");
    var pop = document.getElementById("cmdPop");
    if (!bar || !input || !pop) return;

    var history = [], hIndex = -1, popTimer = null;

    function showPop(html) {
      if (popTimer) { clearTimeout(popTimer); popTimer = null; }
      pop.innerHTML = html;
      pop.hidden = false;
    }
    function autoPop(html) { showPop(html); popTimer = setTimeout(hidePop, 2800); }
    function hidePop() { pop.hidden = true; pop.innerHTML = ""; }
    function flash(msg, isErr) {
      autoPop('<span class="pop-line' + (isErr ? " pop-err" : "") + '">' + msg + "</span>");
    }

    function showHelp() {
      showPop(
        '<div class="pop-h">available commands</div>' +
        '<ul class="pop-list">' +
          "<li><b>cd projects</b> · <b>cd blog</b> · <b>cd home</b><span>navigate</span></li>" +
          "<li><b>ls</b><span>list routes</span></li>" +
          "<li><b>neofetch</b><span>system card</span></li>" +
          "<li><b>top</b><span>projects as processes</span></li>" +
          "<li><b>stack</b><span>loaded modules</span></li>" +
          "<li><b>theme</b> · light · dark · &lt;name&gt;<span>switch appearance</span></li>" +
          "<li><b>roll</b><span>random theme 🎲</span></li>" +
          "<li><b>open</b> github · linkedin · email<span>external links</span></li>" +
          "<li><b>whoami</b> · <b>date</b> · <b>clear</b><span>&nbsp;</span></li>" +
        "</ul>" +
        '<div class="pop-tip">press <kbd>/</kbd> focus · <kbd>↑</kbd><kbd>↓</kbd> history · <kbd>esc</kbd> dismiss</div>'
      );
    }
    function showLs() {
      showPop(
        '<div class="pop-h">routes</div><ul class="pop-list">' +
          "<li><b>~/</b><span>home</span></li>" +
          "<li><b>~/projects</b><span>all services</span></li>" +
          "<li><b>~/blog</b><span>writing</span></li>" +
          "<li><b>~/games</b><span>the arcade</span></li>" +
        "</ul>"
      );
    }
    function showNeofetch() {
      var yrs = yearsShipping();
      var npm = npmWeekly != null ? (fmtNum(npmWeekly) + "/wk on npm") : "on npm";
      var L = function (k, v) { return '<span class="k">' + k + "</span>  " + v; };
      showPop(
        '<pre class="pop-pre">' +
          '<span class="accent">ayush@iyush.dev</span>\n' +
          "---------------\n" +
          L("host    ", "full-stack engineer") + "\n" +
          L("uptime  ", yrs + " yrs (shipping since 2022)") + "\n" +
          L("shipped ", "6 products · 1 acquired") + "\n" +
          L("stack   ", "js · ts · node · react · python") + "\n" +
          L("live    ", '<span class="live">owthorize</span> — ' + npm) + "\n" +
          L("contact ", "cswithiyush@gmail.com") + "\n" +
          L("theme   ", currentTheme() + '  <span class="k">(try: roll)</span>') +
        "</pre>"
      );
    }
    function showTop() {
      var pad = function (s, n) { s = String(s); while (s.length < n) s += " "; return s; };
      var row = function (pid, statusCls, status, name, stat) {
        return pad(pid, 5) + '<span class="' + statusCls + '">' + pad(status, 10) + "</span>" +
          pad(name, 18) + '<span class="k">' + stat + "</span>";
      };
      var owStat = npmWeekly != null ? (fmtNum(npmWeekly) + "/wk") : "live on npm";
      showPop(
        '<pre class="pop-pre">' +
          '<span class="k">tasks: 3 total · 1 live · 1 acquired · 1 shipped</span>\n\n' +
          '<span class="k">' + pad("PID", 5) + pad("STATUS", 10) + pad("PROJECT", 18) + "STAT</span>\n" +
          row("0", "live", "live", "owthorize", owStat) + "\n" +
          row("1", "acquired", "acquired", "snoopsignal", "sold · $3k") + "\n" +
          row("2", "archived", "shipped", "sqlpremierleague", "700+ users") +
        "</pre>"
      );
    }
    function showStack() {
      showPop(
        '<div class="pop-h">loaded modules · lsmod</div>' +
        '<pre class="pop-pre">' + STACK.join("   ") + "</pre>"
      );
    }

    function navigate(url) {
      var go = function () { window.location.assign(url); };
      if (reduce) go(); else setTimeout(go, 220);
    }

    function run(raw) {
      var cmd = (raw || "").trim().replace(/\s+/g, " ");
      if (!cmd) return;
      history.push(cmd); hIndex = history.length;
      var lc = cmd.toLowerCase().replace(/^[>$]\s*/, "");
      track("command", { command: lc.split(" ")[0] || "unknown" });

      if (lc === "clear") { input.value = ""; updateIdle(); hidePop(); return; }
      if (lc === "help" || lc === "?" || lc === "man") { showHelp(); return; }
      if (lc === "ls" || lc === "dir") { showLs(); return; }
      if (lc === "neofetch" || lc === "about") { showNeofetch(); return; }
      if (lc === "top" || lc === "htop" || lc === "ps") { showTop(); return; }
      if (lc === "stack" || lc === "lsmod" || lc === "skills") { showStack(); return; }
      if (lc === "whoami") { flash("ayush pawar — full-stack engineer who ships fast."); return; }
      if (lc === "date" || lc === "uptime") {
        var now = new Date();
        flash("<b>" + esc(now.toString().replace(/\s\(.*\)$/, "")) + "</b> · uptime " + yearsShipping() + "y");
        return;
      }
      if (lc === "roll" || lc === "dice" || lc === "theme random" || lc === "shuffle") {
        var picked = rollTheme(); flash("🎲 rolled: <b>" + esc(THEMES[picked].label) + "</b>"); return;
      }
      if (lc === "theme") { toggleTheme(); flash("theme &rarr; <b>" + currentTheme() + "</b>"); return; }
      if (lc.indexOf("theme ") === 0) {
        var name = lc.slice(6).trim();
        if (THEMES[name]) { applyTheme(name); flash("theme &rarr; <b>" + esc(name) + "</b>"); }
        else { flash("unknown theme: <b>" + esc(name) + "</b> — try 'roll' or theme light/dark", true); }
        return;
      }
      if (lc === "sudo hire-me" || lc === "sudo hire me") {
        flash("permission granted ✓ — opening mail…");
        window.location.href = OPEN.email; return;
      }
      if (lc.indexOf("sudo ") === 0) { flash("nice try — you're not in the sudoers file. 😉"); return; }

      if (lc.indexOf("open ") === 0) {
        var key = lc.slice(5).trim().replace(/^~\//, "");
        if (key === "mail") key = "email";
        if (OPEN[key]) {
          flash("opening <b>" + esc(key) + "</b>…");
          if (key === "email") window.location.href = OPEN[key];
          else window.open(OPEN[key], "_blank", "noopener");
        } else { flash("can't open '" + esc(key) + "' — try github, linkedin, or email", true); }
        return;
      }

      var route = resolveRoute(lc);
      if (route) {
        input.value = ""; updateIdle();
        flash("cd &rarr; <b>~/" + (route.label === "home" ? "" : route.label) + "</b>");
        navigate(route.url); return;
      }

      flash("command not found: <b>" + esc(cmd) + "</b> — try 'help'", true);
    }

    function updateIdle() {
      bar.classList.toggle("idle", document.activeElement !== input && !input.value);
    }

    input.addEventListener("focus", function () { updateIdle(); hidePop(); });
    input.addEventListener("blur", updateIdle);
    input.addEventListener("input", updateIdle);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); run(input.value); }
      else if (e.key === "Escape") { hidePop(); input.blur(); }
      else if (e.key === "ArrowUp") {
        if (history.length) { e.preventDefault(); hIndex = Math.max(0, hIndex - 1); input.value = history[hIndex] || ""; updateIdle(); }
      } else if (e.key === "ArrowDown") {
        if (history.length) {
          e.preventDefault(); hIndex = Math.min(history.length, hIndex + 1);
          input.value = history[hIndex] || ""; updateIdle();
        }
      }
    });

    document.addEventListener("keydown", function (e) {
      var t = e.target;
      var typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      if (e.key === "/" && !typing) { e.preventDefault(); input.focus(); }
      else if (e.key === "Escape" && document.activeElement === input) { hidePop(); input.blur(); }
    });

    updateIdle();
  }

  /* ---------- Scroll reveals ---------- */
  function initReveals() {
    var els = document.querySelectorAll(".service, .reveal");
    if (!els.length) return;
    if (reduce || !("IntersectionObserver" in window)) {
      els.forEach(function (el) { el.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          var i = parseInt(e.target.style.getPropertyValue("--i"), 10) || 0;
          e.target.style.animationDelay = (i * 0.08) + "s";
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0, rootMargin: "0px 0px -12% 0px" }); // threshold 0 so elements taller than the viewport still reveal
    els.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Homepage boot sequence ---------- */
  function typeStatus() {
    var el = document.getElementById("sbStatus");
    if (!el || reduce) return;
    var rest = "online", i = 0;
    el.textContent = "status: ";
    (function tick() {
      if (i <= rest.length) { el.textContent = "status: " + rest.slice(0, i); i++; setTimeout(tick, 55); }
    })();
  }
  function typeRole() {
    var el = document.querySelector(".role");
    if (!el) return;
    var text = el.getAttribute("data-type") || el.textContent.trim();
    if (reduce) { el.style.opacity = 1; return; }
    el.textContent = "";
    var caret = document.createElement("span");
    caret.className = "typed-caret";
    el.appendChild(caret);
    var i = 0;
    (function tick() {
      if (i < text.length) {
        caret.insertAdjacentText("beforebegin", text.charAt(i));
        i++;
        setTimeout(tick, 22 + Math.random() * 26);
      } else {
        setTimeout(function () { if (caret.parentNode) caret.parentNode.removeChild(caret); }, 1400);
      }
    })();
  }
  function counts() {
    document.querySelectorAll(".metric__num").forEach(function (el) {
      var target = parseInt(el.getAttribute("data-count"), 10);
      var vEl = el.querySelector(".v");
      if (reduce || isNaN(target)) { if (vEl) vEl.textContent = target; return; }
      var start = null, dur = 900;
      function step(ts) {
        if (!start) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        vEl.textContent = Math.round(eased * target);
        if (p < 1) requestAnimationFrame(step);
        else vEl.textContent = target;
      }
      requestAnimationFrame(step);
    });
  }
  function initHomeBoot() {
    var hero = document.getElementById("hero");
    if (!hero) return;
    window.addEventListener("load", function () {
      typeStatus();
      hero.classList.add("in");
      if (reduce) { typeRole(); counts(); return; }
      setTimeout(typeRole, 950);
      setTimeout(counts, 1150);
    });
  }

  /* ---------- DevTools easter egg ---------- */
  function consoleGreeting() {
    try {
      console.log("%c ayush@iyush.dev ",
        "background:#3FB950;color:#0A0C10;font-weight:700;padding:2px 6px;border-radius:4px");
      console.log("%cpsst — this site has a shell. press \"/\" then try: %chelp%c · %cneofetch%c · %ctop%c · %croll",
        "color:#8B95A5", "color:#3FB950", "color:#8B95A5",
        "color:#3FB950", "color:#8B95A5", "color:#3FB950", "color:#8B95A5", "color:#D29922");
    } catch (e) { /* ignore */ }
  }

  /* ---------- Wire up ---------- */
  function init() {
    initAnalytics();
    updateToggle(currentTheme());
    injectThemeControls();
    injectNav();
    var btn = document.getElementById("themeToggle");
    if (btn) btn.addEventListener("click", toggleTheme);

    // Follow OS theme changes only while the user hasn't chosen explicitly.
    if (window.matchMedia) {
      try {
        var mq = window.matchMedia("(prefers-color-scheme: light)");
        var onChange = function (e) { if (!storeGet("theme")) applyTheme(e.matches ? "light" : "dark"); };
        if (mq.addEventListener) mq.addEventListener("change", onChange);
        else if (mq.addListener) mq.addListener(onChange);
      } catch (e) { /* ignore */ }
    }

    initCommandBar();
    initReveals();
    initHomeBoot();
    fetchNpm();
    fetchGitHub();
    consoleGreeting();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
