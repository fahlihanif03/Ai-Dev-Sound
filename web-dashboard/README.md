# Demo Kit Dashboard

Vue 3 + Cloudflare Workers dashboard implementing `prd-web-dashboard-design.pdf` —
two pages (Energy Monitoring as default/main, Predictive Maintenance as
secondary), live via WebSocket, styled in the spec's SunXSolar-inspired
direction (spacious cards, soft shadows, one muted accent color).

## Status

**Working end-to-end, but with simulated data.** The board-to-cloud bridge
(reading the two boards' live UART output and POSTing it here) doesn't exist
yet - see `../fan-anomaly-detector-fw` and `../thermal-monitor-fw` for the
firmware that would feed it. Until that bridge exists, the backend generates
plausible sound/temperature/power readings (with occasional simulated
anomalies) so the dashboard is genuinely live and functional to look at and
demo, not a static mock.

## Architecture

- **Frontend**: Vue 3 (`src/`), built with Vite, no external charting
  library - sparklines and the power chart are hand-rolled inline SVG per
  the design spec's "soft filled area, not sharp bar charts" requirement,
  which also sidesteps needing to pick/tune one of the two chart libraries
  the design PRD left as an open question.
- **Backend**: a single Cloudflare Worker (`worker/index.ts`) serving the
  built frontend as static assets and routing `/api/*` to a Durable Object
  (`worker/dashboard-do.ts`, `DashboardState`) that holds the live
  sound/temperature/power state, persists a short recent window in its
  SQLite storage (per the design PRD's explicit non-goal of long-term
  history), and broadcasts updates to every connected browser over
  WebSocket via `ctx.acceptWebSocket` hibernation.
- No D1/KV: the design PRD's "confirm the Cloudflare-side data layer"
  open question is resolved here as Durable Object storage alone, since the
  PRD explicitly scopes out historical reporting beyond a short window -
  add D1 later if that scope changes.

## Wiring in real data later

POST to `/api/ingest`:
```json
{ "channel": "sound", "value": 0.42, "flag": "normal", "threshold": 0.9324, "unit": "" }
{ "channel": "temperature", "value": 29.4, "flag": "normal", "threshold": 50, "unit": "C" }
{ "channel": "power", "value": 2.3, "flag": "normal", "threshold": 6, "unit": "kW", "extra": { "powerFactor": 0.92, "voltage": 228, "current": 10.6 } }
```
A channel that receives a real ingest stops being simulated for 60s (see
`REAL_DATA_GRACE_MS` in `dashboard-do.ts`), so a bridge can come online one
channel at a time without fighting the simulator. Optional bearer auth via
`INGEST_TOKEN` (`wrangler secret put INGEST_TOKEN`).

## Open items from the design PRD (resolved here with defaults, revisit if needed)

- **Accent color**: a muted teal-green (no Mind Mechatronic/MindnRobotics
  brand color was available) - swap `--accent` etc. in `src/style.css`.
- **Hero illustration**: simple generic line-art (a facility outline for
  Energy, a motor/fan glyph for Predictive Maintenance) rather than a
  commissioned illustration - swap `src/components/HeroIllustration.vue`.
- **Nav badge for the other page's status**: not implemented - the two
  pages are fully independent per the PRD's stated default ("should the two
  pages be fully independent" was left open; this build assumes yes).

## Commands

```bash
npm install
npm run dev          # Vite dev server, frontend only (no live WebSocket data)
npm run worker:dev    # full stack: builds + runs via wrangler dev (what you want for real testing)
npm run worker:check  # type-check the Worker/Durable Object
npm run deploy         # build + wrangler deploy
```
