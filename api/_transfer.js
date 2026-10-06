// Shared lookup for the transfer share functions: reads the calculator's precomputed Study 5 predictions.
import { LEAGUE_SLUG, LEAGUE_NAME } from "./_sim.js";
export { LEAGUE_SLUG, LEAGUE_NAME };
const BY_SLUG = Object.fromEntries(Object.entries(LEAGUE_SLUG).map(([k, v]) => [v, k]));
const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export async function lookup(reqUrl) {
  const u = new URL(reqUrl), origin = u.origin, q = u.searchParams;
  const ix = await (await fetch(origin + "/football/data/transfer/index.json")).json();
  const me = ix.players.find((r) => r[5] === (q.get("player") || "").toLowerCase());
  if (!me) return { found: false };
  const to = BY_SLUG[q.get("to")];
  const out = { found: true, name: me[1], from: me[3], slug: me[5], to: to && to !== me[3] ? to : null };
  if (!out.to) return out;
  const ci = ix.clubs.findIndex((c) => c[0] === out.to && slug(c[1]) === q.get("club"));
  if (ci < 0) return out;
  const d = await (await fetch(`${origin}/football/data/transfer/p/${me[0]}.json`)).json();
  const pr = d.pred[String(ci)];
  if (pr) Object.assign(out, { club: ix.clubs[ci][1], clubSlug: slug(ix.clubs[ci][1]), pred: pr[0], q10: pr[1], q90: pr[2], ret: pr[0] / d.pre });
  return out;
}
