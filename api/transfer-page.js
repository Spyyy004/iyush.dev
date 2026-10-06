// Serves /football/tools/transfer?player=… with result-specific title + social tags (crawlers don't run JS).
import { lookup, LEAGUE_NAME, LEAGUE_SLUG } from "./_transfer.js";

export const config = { runtime: "edge" };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

export default async function handler(req) {
  const u = new URL(req.url);
  const page = await fetch(u.origin + "/football/tools/transfer");
  let html = await page.text();
  try {
    const s = await lookup(req.url);
    if (s.found && s.to && s.club) {
      const qs = `player=${s.slug}&from=${LEAGUE_SLUG[s.from]}&to=${LEAGUE_SLUG[s.to]}&club=${s.clubSlug}`;
      const title = `Will ${s.name}'s game travel? · ${LEAGUE_NAME[s.from]} → ${LEAGUE_NAME[s.to]}`;
      const desc = `Study 5 model: expected retention ${Math.round(s.ret * 100)}% of attacking output at ${s.club} ` +
        `(80% range ${s.q10.toFixed(2)}–${s.q90.toFixed(2)} xG + xA per 90). Attacking output only — not a verdict on the player.`;
      const set = (re, val) => { html = html.replace(re, (m, a) => a + esc(val) + '"'); };
      html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)} · Home Turf &amp; Hard Opponents</title>`);
      set(/(<meta name="description" content=")[^"]*"/, desc);
      set(/(<meta property="og:title" content=")[^"]*"/, title);
      set(/(<meta property="og:description" content=")[^"]*"/, desc);
      set(/(<meta property="og:url" content=")[^"]*"/, `${u.origin}/football/tools/transfer?${qs}`);
      set(/(<meta property="og:image" content=")[^"]*"/, `${u.origin}/api/og/transfer?${qs}`);
      set(/(<meta name="twitter:title" content=")[^"]*"/, title);
      set(/(<meta name="twitter:description" content=")[^"]*"/, desc);
      set(/(<meta name="twitter:image" content=")[^"]*"/, `${u.origin}/api/og/transfer?${qs}`);
    }
  } catch (e) { /* default tags */ }
  return new Response(html, { status: page.status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, s-maxage=3600" } });
}
