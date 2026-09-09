import { Hono } from "hono";
import type { Env } from "./env";

/* The actual /api/* route logic, shared between two deployment targets:
 *  - the Worker (index.ts, deployed via `wrangler deploy`) - the one that
 *    OWNS the DashboardState Durable Object, since only a Worker can define
 *    a new DO class (Pages projects can only bind to one hosted elsewhere).
 *  - the Pages project (functions/api/[[path]].ts, deployed via
 *    `wrangler pages deploy`, gives the *.pages.dev domain) - binds to the
 *    same DO class cross-script via wrangler.pages.jsonc's `script_name`.
 * Both bind DASHBOARD_STATE the same way (see Env), so this one app works
 * unmodified under either binding source. */

const VALID_CHANNELS = new Set(["sound", "temperature", "power"]);

/* A factory, not a shared instance - each deploy target (index.ts for the
 * Worker, functions/api/[[path]].ts for Pages) builds its own Hono app so
 * neither can accidentally see routes the other one registered on it. */
export function createApp() {
  const app = new Hono<{ Bindings: Env }>();

  app.get("/api/ws", (c) => {
    const stub = c.env.DASHBOARD_STATE.get(c.env.DASHBOARD_STATE.idFromName("global"));
    return stub.fetch(c.req.raw);
  });

  /* Real board->cloud bridge target. Body shape:
   *   { channel: "sound"|"temperature"|"power", value, flag, threshold, unit, extra? }
   * Optional bearer auth via INGEST_TOKEN (set with `wrangler secret put INGEST_TOKEN`
   * for the Worker, or `wrangler pages secret put INGEST_TOKEN` for the Pages project). */
  app.post("/api/ingest", async (c) => {
    if (c.env.INGEST_TOKEN) {
      const auth = c.req.header("Authorization");
      if (auth !== `Bearer ${c.env.INGEST_TOKEN}`) {
        return c.text("unauthorized", 401);
      }
    }

    let body: any;
    try {
      body = await c.req.json();
    } catch {
      return c.text("invalid json", 400);
    }

    if (!VALID_CHANNELS.has(body?.channel)) {
      return c.text("invalid channel", 400);
    }
    if (typeof body.value !== "number") {
      return c.text("value must be a number", 400);
    }

    const stub = c.env.DASHBOARD_STATE.get(c.env.DASHBOARD_STATE.idFromName("global"));
    await stub.ingest(body.channel, {
      value: body.value,
      flag: body.flag === "abnormal" ? "abnormal" : "normal",
      threshold: typeof body.threshold === "number" ? body.threshold : 0,
      unit: typeof body.unit === "string" ? body.unit : "",
      extra: typeof body.extra === "object" && body.extra !== null ? body.extra : {},
    });

    return c.text("ok");
  });

  return app;
}
