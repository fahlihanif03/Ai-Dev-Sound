export { DashboardState } from "./dashboard-do";
import type { Env } from "./env";

const VALID_CHANNELS = new Set(["sound", "temperature", "power"]);

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/api/ws") {
      const stub = env.DASHBOARD_STATE.get(env.DASHBOARD_STATE.idFromName("global"));
      return stub.fetch(request);
    }

    if (url.pathname === "/api/ingest" && request.method === "POST") {
      return handleIngest(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};

/* Real board->cloud bridge target. Body shape:
 *   { channel: "sound"|"temperature"|"power", value, flag, threshold, unit, extra? }
 * Optional bearer auth via INGEST_TOKEN (set with `wrangler secret put INGEST_TOKEN`). */
async function handleIngest(request: Request, env: Env): Promise<Response> {
  if (env.INGEST_TOKEN) {
    const auth = request.headers.get("Authorization");
    if (auth !== `Bearer ${env.INGEST_TOKEN}`) {
      return new Response("unauthorized", { status: 401 });
    }
  }

  let body: any;
  try {
    body = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }

  if (!VALID_CHANNELS.has(body?.channel)) {
    return new Response("invalid channel", { status: 400 });
  }
  if (typeof body.value !== "number") {
    return new Response("value must be a number", { status: 400 });
  }

  const stub = env.DASHBOARD_STATE.get(env.DASHBOARD_STATE.idFromName("global"));
  await stub.ingest(body.channel, {
    value: body.value,
    flag: body.flag === "abnormal" ? "abnormal" : "normal",
    threshold: typeof body.threshold === "number" ? body.threshold : 0,
    unit: typeof body.unit === "string" ? body.unit : "",
    extra: typeof body.extra === "object" && body.extra !== null ? body.extra : {},
  });

  return new Response("ok");
}
