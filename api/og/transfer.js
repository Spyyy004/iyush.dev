// Social card for a transfer prediction (M4 §25), drawn from the precomputed result.
import { ImageResponse } from "@vercel/og";
import { lookup, LEAGUE_NAME } from "../_transfer.js";

export const config = { runtime: "edge" };
const serif = fetch(new URL("../fonts/InstrumentSerif-Regular.ttf", import.meta.url)).then((r) => r.arrayBuffer());
const mono = fetch(new URL("../fonts/JetBrainsMono-Regular.ttf", import.meta.url)).then((r) => r.arrayBuffer());
const h = (type, style, children) => ({ type, props: { style, children } });

export default async function handler(req) {
  const s = await lookup(req.url);
  const C = { bg: "#0b0b0b", ink: "#f2f0ea", ink2: "#a3a3a3", muted: "#858585", red: "#e06a5f", accent: "#b83a3a" };
  const route = s.found && s.to ? [h("span", { color: C.ink }, LEAGUE_NAME[s.from]), h("span", { color: C.red, margin: "0 18px" }, "→"),
    h("span", { color: C.ink }, LEAGUE_NAME[s.to] + (s.club ? " · " + s.club : ""))] : [h("span", {}, "Study 5 · league moves")];
  const tree = h("div", { width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between",
    background: C.bg, padding: "64px 72px", borderLeft: `10px solid ${C.accent}` }, [
    h("div", { fontFamily: "Mono", fontSize: 22, letterSpacing: 4, color: C.muted }, "HOME TURF & HARD OPPONENTS · TRANSFER"),
    h("div", { display: "flex", flexDirection: "column" }, [
      h("div", { fontFamily: "Serif", fontSize: 88, lineHeight: 1, color: C.ink }, "Will his game travel?"),
      h("div", { display: "flex", marginTop: 34, fontFamily: "Mono", fontSize: 32, color: C.ink }, s.found ? s.name : "Pick a player"),
      h("div", { display: "flex", marginTop: 14, fontFamily: "Mono", fontSize: 26, color: C.ink2 }, route),
      s.ret != null ? h("div", { display: "flex", alignItems: "baseline", marginTop: 26, fontFamily: "Mono", color: C.ink2, fontSize: 26 }, [
        h("span", {}, "Expected retention"), h("span", { color: C.red, fontSize: 56, margin: "0 18px" }, Math.round(s.ret * 100) + "%"),
        h("span", {}, `range ${s.q10.toFixed(2)}–${s.q90.toFixed(2)} xG+xA/90`)]) : h("div", {}, "")]),
    h("div", { display: "flex", justifyContent: "space-between", gap: 40, fontFamily: "Mono", fontSize: 20, color: C.muted }, [
      h("span", {}, "Football research by Ayush Pawar"), h("span", {}, "attacking output only · not a verdict")])]);
  return new ImageResponse(tree, { width: 1200, height: 630,
    fonts: [{ name: "Serif", data: await serif, style: "normal" }, { name: "Mono", data: await mono, style: "normal" }],
    headers: { "Cache-Control": "public, max-age=86400, s-maxage=604800" } });
}
