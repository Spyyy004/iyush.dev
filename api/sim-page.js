// Serves /football/tools/similarity?player=… with result-specific title + social tags (crawlers don't run JS).
// The page itself is the static file; only <head> tags change.
import { lookup, LEAGUE_NAME, LEAGUE_SLUG } from "./_sim.js";

export const config = { runtime: "edge" };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

export default async function handler(req) {
  const u = new URL(req.url);
  const page = await fetch(u.origin + "/football/tools/similarity");
  let html = await page.text();
  try {
    const s = await lookup(req.url);
    if (s.found) {
      const share = `${u.origin}/football/tools/similarity?player=${s.slug}&league=${LEAGUE_SLUG[s.league]}&seasons=${s.n}${s.as ? "&as=" + s.as : ""}`;
      const img = `${u.origin}/api/og/similarity?player=${s.slug}&league=${LEAGUE_SLUG[s.league]}&seasons=${s.n}${s.as ? "&as=" + s.as : ""}`;
      const title = `Who plays like ${s.name}? · ${LEAGUE_NAME[s.league]}`;
      const desc = (s.top ? `Closest adjusted attacking profile in ${LEAGUE_NAME[s.league]}: ${s.top}. ` : "") +
        `${s.n}-season profile, Study 4 similarity model. Describes playing style — not a forecast.`;
      const set = (re, val) => { html = html.replace(re, (m, a) => a + esc(val) + '"'); };
      html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)} · Home Turf &amp; Hard Opponents</title>`);
      set(/(<meta name="description" content=")[^"]*"/, desc);
      set(/(<meta property="og:title" content=")[^"]*"/, title);
      set(/(<meta property="og:description" content=")[^"]*"/, desc);
      set(/(<meta property="og:url" content=")[^"]*"/, share);
      set(/(<meta property="og:image" content=")[^"]*"/, img);
      set(/(<meta name="twitter:title" content=")[^"]*"/, title);
      set(/(<meta name="twitter:description" content=")[^"]*"/, desc);
      set(/(<meta name="twitter:image" content=")[^"]*"/, img);
    }
  } catch (e) { /* fall back to the page's default tags */ }
  return new Response(html, { status: page.status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, s-maxage=3600" } });
}
