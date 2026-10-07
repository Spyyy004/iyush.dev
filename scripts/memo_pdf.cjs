// Print a memo page to an A4 PDF (the print stylesheet in football/memo.css does the layout).
//   node scripts/memo_pdf.cjs /football/research/club-brugge docs/outreach/club-brugge/club-brugge-memo.pdf
// Needs a local server (MEMO_BASE, default http://localhost:4601 — `npx serve -l 4601 .`) and playwright-core
// resolvable via NODE_PATH; CHROMIUM overrides the browser (default: Playwright's cached headless shell).
const path = require("path");
const os = require("os");
const fs = require("fs");
const { chromium } = require("playwright-core");

const [, , route, dest] = process.argv;
const base = process.env.MEMO_BASE || "http://localhost:4601";
const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
const shell = fs.readdirSync(cache).filter((d) => d.startsWith("chromium_headless_shell-")).sort().pop();
const exe = process.env.CHROMIUM || (shell && path.join(cache, shell, fs.readdirSync(path.join(cache, shell)).find((d) => d.startsWith("chrome-headless-shell")), "chrome-headless-shell"));

(async () => {
  const browser = await chromium.launch({ executablePath: exe });
  const page = await browser.newPage();
  await page.goto(base + route, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: dest, format: "A4", printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: "<span></span>",
    footerTemplate: '<div style="width:100%;font:8px JetBrains Mono,monospace;color:#6b6b6b;padding:0 16mm;display:flex;justify-content:space-between"><span>How much of a player\'s game travels? · Ayush Pawar</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
  });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
