// Shared tool links (/football/tools/{similarity,transfer}?player=…) need result-specific <head> tags for crawlers.
// vercel.json rewrites can't do this: the static page matches the path first. Middleware runs before the filesystem,
// so links with ?player= go to the share-page functions; everything else is served as-is.
import { next, rewrite } from "@vercel/functions";

export const config = { matcher: ["/football/tools/similarity", "/football/tools/transfer"] };

export default function middleware(req) {
  const u = new URL(req.url);
  if (!u.searchParams.get("player")) return next();
  const dest = new URL(u.pathname.endsWith("/similarity") ? "/api/sim-page" : "/api/transfer-page", u.origin);
  dest.search = u.search;
  return rewrite(dest);
}
