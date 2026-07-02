# iyush.dev

Personal site — a dark (and now light) monitoring-dashboard aesthetic. Vanilla HTML/CSS/JS,
no framework, no build step. Every page is a static file you can deploy as-is.

## File structure

```
index.html        Home — terminal hero + "active services" + boot animation
projects.html     All projects, rendered as service cards
blog.html         Blog index (a "commit log"); posts come from a JS array
blog-post.html    Example article — duplicate this for each real post
styles.css        Shared design system: tokens, both themes, every component
site.js           Shared behavior: theme toggle, command bar, reveals, home boot
README.md         This file
.claude/          launch.json for the local preview server (safe to ignore/delete)
```

The shell (status bar, footer, floating command bar) is the same markup on every page, and
**all** styling/behavior lives in `styles.css` + `site.js` — so the pages can't drift apart.
Both themes are defined as full CSS-variable sets (`:root` = dark, `[data-theme="light"]` = light).

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

## Accessibility & motion

- Visible keyboard focus on every interactive element; the command input and theme toggle have `aria-label`s.
- `prefers-reduced-motion` disables **all** animation and transitions (boot typing, reveals, theme
  fade, blinking carets) and shows content in its final state.
- Status colors were re-tuned (darkened/desaturated, glows removed) for the light theme so both
  themes stay legible and intentional.
