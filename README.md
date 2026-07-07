# iyush.dev

Personal site — a dark (and now light) monitoring-dashboard aesthetic. Vanilla HTML/CSS/JS,
no framework, no build step. Every page is a static file you can deploy as-is.

## File structure

```
index.html        Home — terminal hero + "active services" + boot animation
projects.html     All projects, rendered as service cards
blog.html         Blog index (a "commit log"); posts come from a JS array
blog-post.html    Example article — duplicate this for each real post
games.html        Arcade page (Typespeed typing test); room for more games
games.js          Game logic — loaded ONLY on games.html
styles.css        Shared design system: tokens, both themes, every component
site.js           Shared behavior: theme toggle, command bar, reveals, home boot
og.png            1200×630 social-share image
robots.txt · sitemap.xml · llms.txt   Crawler + answer-engine files
README.md         This file
.claude/          launch.json for the local preview server (safe to ignore/delete)
```

The shell (status bar, footer, floating command bar) is the same markup on every page, and
**all** styling/behavior lives in `styles.css` + `site.js` — so the pages can't drift apart.
Both themes are defined as full CSS-variable sets (`:root` = dark, `[data-theme="light"]` = light).

## Arcade (`/games`)

`games.html` is a terminal "cabinet" that hosts small, frontend-only games. It ships with
**Typespeed** — a shell-command typing speed test (WPM + live accuracy, best score saved via the
crash-proof storage wrapper, keyboard + touch, GA `game_start`/`game_over` events). Reachable from
the nav, and from the command bar (`cd games`, `games`, or `play`).

**To add a game:** in `games.html`, add another terminal section with a uniquely-`id`'d root
element; in `games.js`, add an IIFE guarded on that id (`var root = document.getElementById('x'); if (!root) return;`)
so it no-ops elsewhere. Style it with the theme variables so it works in every theme.

## Running locally

It's static, so anything that serves files works:

```bash
python3 -m http.server 4599   # then open http://localhost:4599
# or: npx serve .
```

(Opening `index.html` directly via `file://` mostly works too, but a server is more faithful.)

## The command bar

Fixed at the bottom of every page. Press **`/`** anywhere to focus it, **Esc** to blur, **Enter** to run.

| Command | Does |
| --- | --- |
| `cd projects` / `projects` | go to Projects (shorthand works — no `cd` needed) |
| `cd blog` / `blog` | go to Blog |
| `cd home` / `cd ~` / `~` | go Home |
| `ls` | list routes in the popover |
| `help` | show all commands |
| `neofetch` / `about` | print a system-info identity card |
| `top` / `ps` | list projects as processes (real status + live metrics) |
| `stack` / `lsmod` | list the tech stack (no fake percentages) |
| `theme` / `theme light` / `theme dark` / `theme <name>` | toggle or set a theme |
| `roll` / `dice` | jump to a random theme 🎲 |
| `whoami` / `date` / `uptime` | quick facts |
| `open github` / `open linkedin` / `open email` | open external links |
| `sudo hire-me` | 😉 |
| `clear` | clear the input |

Case- and whitespace-insensitive. **↑ / ↓** walk command history. Unknown input replies
`command not found: X — try 'help'`.

## Themes + the dice

- **Base themes:** `dark` (default) and `light`. The **toggle** in the status bar flips between
  these two; first visit follows your OS `prefers-color-scheme`.
- **Dice themes:** the **🎲 button** (or `roll`) jumps to a random theme from a wider pool —
  `onepiece`, `matrix`, `synthwave`, `dracula`, `solarized`. Set one directly with `theme matrix`, etc.
- Add a theme by copying a `[data-theme="…"]` block in `styles.css` (define the full variable set)
  and adding one line to the `THEMES` map in `site.js`.
- The choice is saved to `localStorage`; if storage is blocked it falls back to in-memory for the
  session and never throws. Colors transition smoothly unless `prefers-reduced-motion` is set.

## Live telemetry

Two real, client-side signals (no backend, no keys) that degrade silently if the APIs are unreachable:

- **npm installs/week** for `owthorize` on the Owthorize card — `api.npmjs.org`.
- **GitHub push activity** (14-day sparkline + "last push") in the footer — `api.github.com`
  public events for `Spyyy004`.

Both are also surfaced inside `neofetch` and `top`.

## How to add a blog post

1. **Copy `blog-post.html`** to a new filename — e.g. `posts/my-post.html` (create the folder if you like).
2. **Write the article.** Update its `<title>`, `<meta name="description">`, the `.article__meta`
   line (date · read time · tag), the `<h1>`, and the body. Use the pre-styled elements:
   `<h2>`/`<h3>`, `<p>`, `<ul>`/`<ol>`, `<blockquote>`, `<pre><code>…</code></pre>`, and inline
   `<code>`. For lightly "highlighted" code, wrap tokens in `<span class="tok-c">` (comment),
   `tok-k` (keyword), `tok-s` (string), or `tok-f` (function/attr).
3. **Register it** in the `POSTS` array near the bottom of `blog.html`:

   ```js
   {
     title: "My real post",
     date: "2026-07-01",            // ISO; list auto-sorts newest-first
     excerpt: "One line that sells the read.",
     slug: "posts/my-post.html",     // path to the file from step 1
     readTime: "5 min"
     // drop `sample: true` — that's only for the placeholder posts
   }
   ```

The `POSTS` array currently ships **empty**, so the blog shows a tidy "no posts yet" state until you
add your first entry. `blog-post.html` remains as a ready-to-duplicate article template.

## How to add a project

Open `projects.html` and copy one `<article class="service s-XXX">` block inside the `.grid`.

- **Status class → color:** `s-live` (green), `s-deploy` (amber, pulsing dot),
  `s-acquired` (violet), `s-archived` (muted — use for "shipped"/archived). Same semantics as home.
- Set `style="--i:N"` (N = its index) so the scroll-reveal staggers in order.
- Fill in `.service__status` text, `.service__tag`, `.service__name`, `.service__desc`,
  the `.chips` (mono tech tags), and an optional `.service__link`.

To also show a project on the home page, mirror the same block into the `.grid` in `index.html`.

> **Verify the placeholder metrics.** A few numbers in `projects.html` (e.g. SQLPremierLeague's
> DAU) are placeholders from the brief and are flagged with `<!-- VERIFY ... -->` comments.
> Replace `href="#"` links with real URLs as they go live.

## Deploying to iyush.dev

No build command, no framework — just publish the folder. On all three hosts below, set the
**build command to empty/none** and the **output/publish directory to the project root** (`.`).

### Vercel
```bash
npm i -g vercel
vercel          # preview
vercel --prod   # production
```
Then in the dashboard: **Project → Settings → Domains → add `iyush.dev`** and point your registrar's
DNS at Vercel (an `A` record to `76.76.21.21`, or a `CNAME` to `cname.vercel-dns.com` for `www`).
Optional: create a `vercel.json` for clean URLs (drops the `.html`):
```json
{ "cleanUrls": true }
```

### Netlify
Drag-and-drop the folder at app.netlify.com, or:
```bash
npm i -g netlify-cli
netlify deploy --prod --dir .
```
Add the domain under **Site settings → Domain management → add `iyush.dev`** and follow Netlify's
DNS instructions. Clean URLs work automatically; a `netlify.toml` is optional.

### Cloudflare Pages
Connect the repo (or `npx wrangler pages deploy .`). Build command: none. Output dir: `/`.
Add `iyush.dev` under **Custom domains** — if your DNS is already on Cloudflare it's one click.

### A note on links
Internal links use relative `.html` filenames (`projects.html`, `blog.html`) so the site works
both locally and when deployed. If you enable clean URLs (e.g. `cleanUrls` on Vercel), `/projects`
and `/blog` will also resolve — the in-page nav and command bar will keep working either way.

## SEO & AEO (answer-engine optimization)

Built to rank in search **and** get cited by AI answer engines.

- **`robots.txt`** — allows all crawlers and explicitly welcomes AI bots (GPTBot, ClaudeBot,
  PerplexityBot, Google-Extended, etc.); points to the sitemap.
- **`sitemap.xml`** — lists `/`, `/projects`, `/blog`. **Add a `<url>` here whenever you add a page.**
- **`llms.txt`** — a clean, structured Markdown summary of who you are and what you've built, at
  `/llms.txt` (the [llmstxt.org](https://llmstxt.org) convention). Keep it factual and update it
  when projects change — this is what LLMs read to answer "who is Ayush Pawar?".
- **Structured data (JSON-LD)** — `Person` + `WebSite` + `ProfilePage` on the home page, an
  `ItemList` of projects (incl. `SoftwareApplication` for Owthorize) on `/projects`, and `Blog`
  on `/blog`. All share one `Person` entity (`#person`) so engines link the pages to one identity.
- **Open Graph + Twitter cards** on every page → rich link previews. Shared image: **`og.png`** (1200×630).
- **Canonical URLs** on every page; the stale sample post (`blog-post.html`) is `noindex` and kept
  out of the sitemap so it doesn't dilute quality.

Maintenance:
- **New page?** Add it to `sitemap.xml`, give it canonical + OG tags, and (if it's a project/post)
  add matching JSON-LD.
- **Regenerate `og.png`** (if you restyle it): recreate the 1200×630 HTML card and screenshot it
  headless, e.g. `chrome --headless --window-size=1200,630 --screenshot=og.png file://card.html`.
- **After deploy:** submit `https://iyush.dev/sitemap.xml` in [Google Search Console](https://search.google.com/search-console)
  and [Bing Webmaster Tools](https://www.bing.com/webmasters); validate rich results at
  [search.google.com/test/rich-results](https://search.google.com/test/rich-results).

## Analytics (Google Analytics 4)

Wired but **off until you add your ID** — a safe no-op otherwise.

1. Create a **GA4 property** at [analytics.google.com](https://analytics.google.com) → copy the
   **Measurement ID** (looks like `G-XXXXXXXXXX`).
2. Open `site.js`, find `var GA_ID = "";` near the top, and paste it: `var GA_ID = "G-XXXXXXXXXX";`
3. Commit + push. That's the only change — the tag loads on every page automatically.

Details:
- The ID lives in **one place** (`site.js`), not in every HTML file.
- **Localhost is auto-skipped** (`localhost`, `127.0.0.1`, `*.local`) so your own dev visits aren't counted.
- Beyond pageviews, two **custom events** fire: `command` (which shell command was run) and
  `theme_change` (which theme was rolled) — so you can see how people play with the terminal + dice
  in GA4 → Reports → Engagement → Events.
- **Search Console tip:** once GA is live, you can verify `iyush.dev` in Search Console via the
  "Google Analytics" method in one click (same Google account) — no extra meta tag needed.

## Accessibility & motion

- Visible keyboard focus on every interactive element; the command input and theme toggle have `aria-label`s.
- `prefers-reduced-motion` disables **all** animation and transitions (boot typing, reveals, theme
  fade, blinking carets) and shows content in its final state.
- Status colors were re-tuned (darkened/desaturated, glows removed) for the light theme so both
  themes stay legible and intentional.
