/* Match Gallery freshness (M5). The line itself is written at build time from the published status.json; this only
   adds a warning when the data should have moved on by now: the next scheduled fixture (as of the last update) plus
   the 72-hour wait for complete data plus a day has passed, and no update has been published since. Breaks with no
   matches therefore never look stale. Nothing here claims the data is live. */
(function () {
  "use strict";
  var el = document.getElementById("gx-fresh");
  if (!el || !el.getAttribute("data-updated")) return;
  var next = el.getAttribute("data-next");
  if (!next) return;
  var due = new Date(next + "T00:00:00Z").getTime() + (3 + 1 + 1) * 864e5;   // fixture day + 72 h + 1 day of slack
  if (Date.now() <= due) return;
  var M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var t = el.getAttribute("data-through");
  el.classList.add("is-stale");
  el.setAttribute("role", "status");
  el.textContent = "Not updated recently: results stop at " + (t ? +t.slice(8, 10) + " " + M[+t.slice(5, 7) - 1] + " " + t.slice(0, 4) : "the last update") +
    ", so newer matches are missing until the next refresh.";
})();
