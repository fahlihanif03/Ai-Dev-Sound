export { DashboardState } from "./dashboard-do";
import { createApp } from "./app";
import type { Env } from "./env";

/* This Worker (deployed via `wrangler deploy` / wrangler.jsonc) is the one
 * that owns the DashboardState Durable Object - see app.ts's comment. Its
 * own /api/* routes still work directly (bridge scripts can keep pointing
 * at this Worker's own URL), but the Pages project
 * (functions/api/[[path]].ts) is now the user-facing *.pages.dev entry
 * point and binds to the same DO cross-script. */
const app = createApp();

/* Everything else (the built frontend's static files) falls through to
 * ASSETS. In production `run_worker_first: ["/api/*"]` means this fetch
 * handler is only actually invoked for /api/* anyway - this fallback is
 * for `wrangler dev` and any path not covered by that pattern. */
app.all("*", (c) => c.env.ASSETS.fetch(c.req.raw));

export default app satisfies ExportedHandler<Env>;
