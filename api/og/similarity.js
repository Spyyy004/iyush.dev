// Social card for a similarity result (M3 §22), drawn from the precomputed result state.
import { ImageResponse } from "@vercel/og";
import { lookup, LEAGUE_NAME } from "../_sim.js";

export const config = { runtime: "edge" };

const serif = fetch(new URL("../fonts/InstrumentSerif-Regular.ttf", import.meta.url)).then((r) => r.arrayBuffer());
const mono = fetch(new URL("../fonts/JetBrainsMono-Regular.ttf", import.meta.url)).then((r) => r.arrayBuffer());
const h = (type, style, children) => ({ type, props: { style, children } });

export default async function handler(req) {
  const s = await lookup(req.url);
  const C = { bg: "#0b0b0b", ink: "#f2f0ea", ink2: "#a3a3a3", muted: "#858585", red: "#e06a5f", line: "#242424", accent: "#b83a3a" };
  const lines = s.found
    ? [h("div", { fontFamily: "Serif", fontSize: 84, lineHeight: 1.0, color: C.ink, letterSpacing: -1 }, `Who plays like ${s.name}?`),
       h("div", { display: "flex", marginTop: 40, fontFamily: "Mono", fontSize: 30, color: C.ink2 },
         [h("span", { color: C.ink }, s.name), h("span", { color: C.red, margin: "0 18px" }, "→"), h("span", { color: C.ink }, LEAGUE_NAME[s.league])]),
       s.top ? h("div", { display: "flex", marginTop: 18, fontFamily: "Mono", fontSize: 30, color: C.ink2 },
         [h("span", {}, "Top comparable:"), h("span", { color: C.ink, marginLeft: 16 }, s.top)]) : h("div", {}, "")]
    : [h("div", { fontFamily: "Serif", fontSize: 92, color: C.ink }, "Who plays like him?")];
  const tree = h("div", { width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between",
    background: C.bg, padding: "64px 72px", borderLeft: `10px solid ${C.accent}` }, [
    h("div", { fontFamily: "Mono", fontSize: 22, letterSpacing: 4, color: C.muted }, "HOME TURF & HARD OPPONENTS · SIMILARITY"),
    h("div", { display: "flex", flexDirection: "column" }, lines),
    h("div", { display: "flex", justifyContent: "space-between", gap: 40, fontFamily: "Mono", fontSize: 20, color: C.muted }, [
      h("span", {}, "Football research by Ayush Pawar"),
      h("span", {}, s.found ? `${s.n}-season profile · not a forecast` : "Study 4 · iyush.dev/football")])]);
  return new ImageResponse(tree, {
    width: 1200, height: 630,
    fonts: [{ name: "Serif", data: await serif, style: "normal" }, { name: "Mono", data: await mono, style: "normal" }],
    headers: { "Cache-Control": "public, max-age=86400, s-maxage=604800" },
  });
}
