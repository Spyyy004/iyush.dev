// Shared lookup for the similarity share functions: reads the same precomputed Study 4 files the page uses.
export const LEAGUE_SLUG = { EPL: "premier-league", La_Liga: "la-liga", Serie_A: "serie-a", Bundesliga: "bundesliga", Ligue_1: "ligue-1" };
export const LEAGUE_NAME = { EPL: "Premier League", La_Liga: "La Liga", Serie_A: "Serie A", Bundesliga: "Bundesliga", Ligue_1: "Ligue 1" };
const BY_SLUG = Object.fromEntries(Object.entries(LEAGUE_SLUG).map(([k, v]) => [v, k]));

export async function lookup(reqUrl) {
  const u = new URL(reqUrl), origin = u.origin, q = u.searchParams;
  const slug = (q.get("player") || "").toLowerCase();
  const league = BY_SLUG[q.get("league")] || "Serie_A";
  const n = [1, 2, 3].includes(+q.get("seasons")) ? +q.get("seasons") : 3;
  const as = q.get("as") === "2025" ? "2025" : null;   // the page's season switch: 2025/26, or the latest matches
  const dir = `${origin}/football/data/${as ? "sim-" + as : "sim"}`;
  const players = await (await fetch(dir + "/players.json")).json();
  const me = players.find((r) => r[5] === slug);
  if (!me) return { found: false, league, n, as };
  const out = { found: true, league, n, as, name: me[1], team: me[2], from: me[3], slug };
  const res = await fetch(`${dir}/r/${me[0]}.json`);
  if (res.ok) {
    const rows = ((await res.json()).res[league] || {})["w" + n] || [];
    if (rows.length) {
      const top = players.find((r) => r[0] === rows[0][0]);
      out.top = top && top[1];
      out.topStrong = !!rows[0][3];
    }
  }
  return out;
}
