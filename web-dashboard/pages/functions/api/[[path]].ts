import { handle } from "hono/cloudflare-pages";
import { createApp } from "../../../backend/app";

/* Pages Functions file-based routing: this file matches every path under
 * /api/* (the [[path]] catch-all segment). Everything else in the site is
 * served automatically from the Pages build output (dist/) without ever
 * reaching a Function - unlike the Worker, there's no manual ASSETS
 * fallback to write here.
 *
 * DASHBOARD_STATE is bound to the DashboardState class hosted by the
 * separately-deployed Worker (see ../wrangler.jsonc's `script_name`) -
 * Pages projects can't define their own new Durable Object classes, only
 * bind to one exported by an existing Worker. */
export const onRequest = handle(createApp());
