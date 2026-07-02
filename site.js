/* ============================================================
   iyush.dev — shared behavior
   Theme toggle (+ safe persistence), floating command bar,
   scroll reveals, and the homepage boot sequence.
   Linked (deferred) by every page.
   ============================================================ */
(function () {
  "use strict";

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Storage that never crashes ---------- */
  /* Some environments block localStorage entirely (it can throw on access).
     Fall back to an in-memory value for the session. */
  var mem = { theme: null };
  function storeGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return mem[key] || null; }
  }
  function storeSet(key, val) {
    mem[key] = val;
    try { window.localStorage.setItem(key, val); } catch (e) { /* keep in memory only */ }
  }

  /* ---------- Theme ---------- */
  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }
  function updateToggle(theme) {
    var btn = document.getElementById("themeToggle");
    if (!btn) return;
    var next = theme === "light" ? "dark" : "light";
    btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
    btn.setAttribute("aria-label", "Switch to " + next + " theme");
    var icon = btn.querySelector(".tt-icon");
    var label = btn.querySelector(".tt-label");
    if (icon) icon.textContent = theme === "light" ? "☀" : "☾"; /* ☀ / ☾ */
    if (label) label.textContent = theme;
  }
  function applyTheme(theme) {
    theme = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", theme);
    storeSet("theme", theme);
    updateToggle(theme);
  }
  function toggleTheme() {
    applyTheme(currentTheme() === "light" ? "dark" : "light");
  }

  /* ---------- Command bar ---------- */
  var ROUTES = { home: "index.html", projects: "projects.html", blog: "blog.html" };
  var OPEN = {
    github: "https://github.com/Spyyy004",
    linkedin: "https://linkedin.com/in/ayush-pawar004",
    email: "mailto:i.yush.004@gmail.com"
  };

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function resolveRoute(s) {
    // strip leading "cd", "~", "/" and trailing "/"
    var t = s.replace(/^cd\b\s*/, "").replace(/^~\/?/, "").replace(/^\//, "").replace(/\/+$/, "").trim();
    if (t === "" || t === "~" || t === "home" || t === "index") return { label: "home", url: ROUTES.home };
    if (t === "projects" || t === "project" || t === "services") return { label: "projects", url: ROUTES.projects };
    if (t === "blog" || t === "blogs" || t === "posts") return { label: "blog", url: ROUTES.blog };
    return null;
  }

  function initCommandBar() {
    var bar = document.getElementById("cmdbar");
    var input = document.getElementById("cmdInput");
    var pop = document.getElementById("cmdPop");
    if (!bar || !input || !pop) return;

    var popTimer = null;
    function showPop(html) {
      if (popTimer) { clearTimeout(popTimer); popTimer = null; }
      pop.innerHTML = html;
      pop.hidden = false;
    }
    function autoPop(html) {
      showPop(html);
      popTimer = setTimeout(hidePop, 2800);
    }
    function hidePop() {
      pop.hidden = true;
      pop.innerHTML = "";
    }
    function flash(msg, isErr) {
      autoPop('<span class="pop-line' + (isErr ? " pop-err" : "") + '">' + msg + "</span>");
    }

    function showHelp() {
      showPop(
        '<div class="pop-h">available commands</div>' +
        '<ul class="pop-list">' +
          "<li><b>cd projects</b> · <b>cd blog</b> · <b>cd home</b><span>navigate</span></li>" +
          "<li><b>ls</b><span>list routes</span></li>" +
          "<li><b>theme</b> · light · dark<span>switch appearance</span></li>" +
          "<li><b>open</b> github · linkedin · email<span>external links</span></li>" +
          "<li><b>clear</b><span>reset input</span></li>" +
          "<li><b>help</b><span>this list</span></li>" +
        "</ul>" +
        '<div class="pop-tip">tip: press <kbd>/</kbd> to focus · <kbd>esc</kbd> to dismiss · shorthand ok (just type <b>projects</b>)</div>'
      );
    }
    function showLs() {
      showPop(
        '<div class="pop-h">routes</div>' +
        '<ul class="pop-list">' +
          "<li><b>~/</b><span>home</span></li>" +
          "<li><b>~/projects</b><span>all services</span></li>" +
          "<li><b>~/blog</b><span>writing</span></li>" +
        "</ul>"
      );
    }

    function navigate(url) {
      var go = function () { window.location.assign(url); };
      if (reduce) go(); else setTimeout(go, 220);
    }

    function run(raw) {
      var cmd = (raw || "").trim().replace(/\s+/g, " ");
      if (!cmd) return;
      var lc = cmd.toLowerCase().replace(/^[>$]\s*/, ""); // tolerate a leading prompt symbol

      if (lc === "clear") { input.value = ""; updateIdle(); hidePop(); return; }
      if (lc === "help" || lc === "?") { showHelp(); return; }
      if (lc === "ls" || lc === "dir") { showLs(); return; }

      if (lc === "theme") { toggleTheme(); flash("theme &rarr; <b>" + currentTheme() + "</b>"); return; }
      if (lc === "theme light" || lc === "theme dark") {
        applyTheme(lc.split(" ")[1]); flash("theme &rarr; <b>" + currentTheme() + "</b>"); return;
      }

      if (lc.indexOf("open ") === 0) {
        var key = lc.slice(5).trim().replace(/^~\//, "");
        if (key === "mail") key = "email";
        if (OPEN[key]) {
          flash("opening <b>" + esc(key) + "</b>&hellip;");
          if (key === "email") { window.location.href = OPEN[key]; }
          else { window.open(OPEN[key], "_blank", "noopener"); }
        } else {
          flash("can't open '" + esc(key) + "' — try github, linkedin, or email", true);
        }
        return;
      }

      var route = resolveRoute(lc);
      if (route) {
        input.value = "";
        updateIdle();
        flash("cd &rarr; <b>~/" + (route.label === "home" ? "" : route.label) + "</b>");
        navigate(route.url);
        return;
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
    });

    // Global "/" focuses the bar (like a real tool), Escape blurs it.
    document.addEventListener("keydown", function (e) {
      var t = e.target;
      var typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      if (e.key === "/" && !typing) {
        e.preventDefault();
        input.focus();
      } else if (e.key === "Escape" && document.activeElement === input) {
        hidePop(); input.blur();
      }
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
    }, { threshold: 0.2 });
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

  /* ---------- Wire up ---------- */
  function init() {
    updateToggle(currentTheme());
    var btn = document.getElementById("themeToggle");
    if (btn) btn.addEventListener("click", toggleTheme);

    // React to OS theme changes only when the user hasn't chosen explicitly.
    if (window.matchMedia) {
      try {
        var mq = window.matchMedia("(prefers-color-scheme: light)");
        var onChange = function (e) {
          if (!storeGet("theme")) applyTheme(e.matches ? "light" : "dark");
        };
        if (mq.addEventListener) mq.addEventListener("change", onChange);
        else if (mq.addListener) mq.addListener(onChange);
      } catch (e) { /* ignore */ }
    }

    initCommandBar();
    initReveals();
    initHomeBoot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
