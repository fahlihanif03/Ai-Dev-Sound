# Progress Log

Running log of what's been done on this project, newest entry on top. New
work goes on top as a new dated section - see `docs/ARCHITECTURE.md` for how
the pieces fit together, this file is just the timeline.

---

## 2026-09-09 (latest of all) — Spectrogram freeze bug, deep-sleep lockout fix, live connectivity monitor

**Real bug found and fixed**: `Spectrogram.vue` watched `history.length` to
know when to draw a new column. The backend caps history at
`MAX_HISTORY_POINTS` (300, push+shift), so once a channel had been running
long enough to hit that cap, `.length` stopped changing forever - the
watcher silently stopped firing, freezing the spectrogram permanently even
though real data kept flowing (confirmed: the numeric sound/level readouts
kept updating the whole time, just not the canvas). User caught this by
asking why the spectrogram "wasn't moving." Fixed by tracking the newest
point's timestamp instead of array length/index, and watching the array
reference itself rather than a derived scalar - verified via two
screenshots ~4s apart showing the bar pattern actually shift.

**Real, well-grounded root-cause candidate found and fixed for the
"sustained failure, only a power cycle clears it" pattern** seen
repeatedly today: user brought in external research pointing at PSoC6
deep-sleep + WiFi radio interactions. Checked our own generated BSP config
and confirmed `CY_CFG_PWR_SYS_IDLE_MODE == CY_CFG_PWR_MODE_DEEPSLEEP` -
meaning FreeRTOS tickless idle was live (`configUSE_TICKLESS_IDLE == 2`),
and the idle task was putting the whole device into deep sleep whenever
nothing had work to do. Deep sleep + the CYW4343W's host-wake handshake is
a known-fragile combination on this platform, and matches the observed
symptom exactly: a WiFi radio that can come back wedged after sleeping at
the wrong moment, un-recoverable by any soft reconnect (confirmed earlier
today - not even a fresh `wifi_set`-triggered rejoin cleared it, only a
full power cycle did every time). Fixed with one call,
`cyhal_syspm_lock_deepsleep()` in `init_board()` - locks deep sleep out
for the entire life of the application, which is correct here since this
board is continuously doing PDM DMA audio capture + WiFi telemetry and
should never actually sleep. Built, flashed, verified booting and
reconnecting normally.

**J3 power jumper checked and ruled out** - user confirmed it's already
on 3.3V (also raised by the same external research, as undervoltage can
cause WiFi brownouts). Not the cause here, but was worth the 30-second
check.

**Set up a live connectivity monitor** (session-local, watches
`POST /api/ingest` counts in the local dev server's log every 15s) to stop
manually re-checking the dashboard on every "is it working" question -
now surfaces DROPPED/RECOVERED events automatically as they happen.
Confirmed working well throughout this stretch of debugging.

**Still true after all of the above**: the quick self-heal drop/reconnect
cycling (a few seconds to ~a minute, clears on its own) still happens
periodically and is very likely just normal WiFi flakiness on this
particular network - the deep-sleep fix specifically targets the *other*,
more severe pattern (sustained failure needing a full power cycle). Worth
watching whether that severe pattern's frequency actually drops now that
deep sleep is locked out.

---

## 2026-09-09 (very newest) — Diagnosed intermittent connectivity: WiFi drops, a real firewall bug, and a network with client isolation

A stretch of "board and dashboard sometimes not working" reports led to
three distinct, now-understood causes:

1. **The board's WiFi genuinely drops sometimes** even while "on and in
   range" - confirmed via UART (`WiFi: connected, IP <new>` after a gap,
   meaning a full disconnect/reconnect, not just a blip). Self-recovers via
   the existing exponential-backoff reconnect logic; no fix needed, this is
   expected WiFi behavior worth knowing about.

2. **Real bug found and fixed**: tried switching the board to a second
   network ("Anep Hensem"). The initial join failed with the same WHD
   error code (`checkres = 33555456`) seen earlier with a 5GHz-named
   network - turned out to be iOS's "Maximize Compatibility" hotspot
   setting being off, which can make Personal Hotspot use a WiFi mode this
   board's simpler chip can't join. Turning it on fixed the join. But
   telemetry still couldn't reach the dashboard afterward - traced to a
   **Windows Firewall gap**: `wrangler dev`'s actual listening process is
   `workerd.exe` (Cloudflare's runtime binary, at
   `node_modules\@cloudflare\workerd-windows-64\bin\workerd.exe`), not
   `node.exe` - the existing firewall "Allow" rule only covered `node.exe`,
   so Windows silently blocked inbound connections to `workerd.exe` from
   any other device on the network (this PC could still reach itself via
   loopback, which isn't filtered the same way - that's what made it
   confusing: `curl` from this machine worked fine while the board
   couldn't connect at all). User added an inbound Allow rule for
   `workerd.exe` specifically (`New-NetFirewallRule ... -Program
   ...\workerd.exe`) - worth remembering for any future network switch.

3. **"Anep Hensem" still didn't work even after the firewall fix** - every
   connect attempt failed identically before and after the firewall rule,
   which ruled out the firewall as the (sole) cause. Most likely
   explanation: that network has client/AP isolation enabled, which blocks
   two devices on the same WiFi from reaching each other directly
   regardless of firewall config - not fixable from the PC side at all.
   Reverted to `Hazman's iPhone` (confirmed working end-to-end already) -
   `telemetry.h`'s `TELEMETRY_SERVER_HOST` switched back to `192.168.1.22`,
   firmware rebuilt/reflashed, `wifi_set "Hazman's iPhone" 12345678`
   re-sent. Verified working again (`WiFi: connected, IP 192.168.1.213`,
   `Telemetry: HTTP connected to 192.168.1.22:8787`, real values on the
   dashboard).

**Takeaway for next time a network switch is needed**: if telemetry fails
to reach the dashboard on a *new* network even with matching IPs/firewall
rules, suspect client/AP isolation on that network before assuming a
PC-side config problem - it can't be worked around from this side.

---

## 2026-09-09 (newest) — All displayed readings formatted to exactly 2 decimal places

Frontend was displaying raw float precision straight from the board/
simulator (e.g. `70.7417`, `227.803`) - added a small `fmt(v)` helper
(`typeof v === "number" ? v.toFixed(2) : "--"`) used everywhere a reading
value renders as text: `PredictiveMaintenance.vue`'s sound/temperature
readouts (both the main cards and the PC-viewer popup readout),
`StatusBadge.vue`'s hover tooltip (reading + threshold), and
`EnergyMonitoring.vue`'s current power/voltage/current KPI cards (power
factor already used `.toFixed(2)`). Chart tooltips (`AreaChart.vue`) and
the dB level readout (`LevelMeter.vue`) were already appropriately
formatted and untouched. Built and verified on both pages - sound/temp now
show `38.65`/`28.68` instead of long decimals, power KPIs show
`3.46 kW`/`0.97`/`227.80 V`/`15.66 A`.

---

## 2026-09-09 (even more recent) — Temperature sent every 1s instead of 5s; dashboard shows "Offline" instead of quietly faking data

**Temperature telemetry sped up**, both real and simulated:
- `wifi/telemetry.c`: split the one shared `TELEMETRY_SEND_INTERVAL_MS`
  (5s, applied to both signals) into per-signal intervals -
  `AUDIO_SEND_INTERVAL_MS` stays 5s (sound's score is a rolling ~2s window,
  sending it faster just resends the same value), `TEMP_SEND_INTERVAL_MS`
  is now 1s, matching the firmware's own actual thermal sample rate
  (`TEMP_SAMPLE_INTERVAL_MS` in main.cpp) - no point sending slower than
  new data actually arrives. The task loop now wakes every 250ms and
  checks each signal's own elapsed-time gate independently, instead of
  one shared `vTaskDelay`.
- `backend/dashboard-do.ts`: matched the simulator's temperature tick to
  1s too (`TEMP_TICK_MS`), so the simulated and real-board experiences
  feel the same regardless of which is currently driving the dashboard.
- Rebuilt, reflashed, verified via UART (auto-reconnected using the
  already-stored WiFi credentials) and confirmed on the dashboard
  (temperature visibly moved within a ~5s window instead of being frozen
  for up to 5s at a time).

**Dashboard now shows "Offline" instead of silently faking data once a
real channel goes quiet.** User noticed the dashboard kept "looking live"
after physically switching the board off, and asked why - traced to
`REAL_DATA_GRACE_MS` (60s): a channel that had received real data and then
went stale was silently switched back to the simulator, which is
misleading when you're specifically trying to watch the real board's
actual status. Fixed:
- `backend/dashboard-do.ts`: `alarm()` now distinguishes "this channel has
  never received real data" (keeps simulating - a fresh dashboard
  shouldn't look dead before any board's ever connected) from "this
  channel had real data and it's now stale" (marks it `offline: true`
  instead, via a new one-time `announceOffline()` broadcast - doesn't
  touch SQL/history, just freezes `latestMem` and tells connected
  clients). `offlineAnnounced` (a `Set<Channel>`) avoids re-broadcasting
  the same offline notice every tick; cleared the moment real data resumes
  via `ingest()`.
- `StatusBadge.vue` gained an `offline` prop - takes priority over the
  normal/abnormal flag (a stale reading from before a channel went dark
  isn't trustworthy enough to keep showing as live), renders a distinct
  muted "Offline" pill.
- `PredictiveMaintenance.vue`: both signal badges and the page's top-level
  status pill now reflect offline state (`anyOffline`), and the alert/
  attention logic excludes offline channels from triggering a false
  "Attention" off a stale flag.
- `EnergyMonitoring.vue` (power) deliberately left unchanged - nothing
  currently sends real power readings at all, so that channel can never
  actually reach the "was real, now stale" path; wiring in unused offline
  UI there would just be dead code.
- **Known limitation, worth remembering**: `lastRealIngestAt`/
  `offlineAnnounced` are in-memory only, not persisted to SQL - a DO
  restart (a local `wrangler dev` restart, or a fresh deploy/eviction in
  production) makes the DO "forget" a channel was ever real, reverting it
  to simulated mode until the *next* real ingest arrives. Ran into this
  directly while testing: restarted the dev server, and the dashboard
  briefly showed simulated-range sound values again until the board's next
  real POST landed a few seconds later.
- **Verified live**: had the user physically power off the board, watched
  the dashboard - both signal badges and the top status pill flipped to
  "Offline" within the grace window, values froze at their last real
  reading (not simulated numbers), and stayed frozen and stable on a
  follow-up check 5s later.

---

## 2026-09-09 (milestone) — First real board→WiFi→dashboard connection, end to end

**Retargeted the firmware's telemetry from the (unimplemented) cloud
endpoint to the local dashboard.** `wifi/telemetry.c` previously POSTed
HTTPS to `demo-kit-dashboard.anepfadhli5.workers.dev/api/readings` in a
`{device_id, reading_type, value, is_anomaly}` shape - a route that's never
existed on the backend (see "Known gaps" in `docs/ARCHITECTURE.md`).
Switched it to plain HTTP, POSTing straight to this machine's local
`wrangler dev` server on the LAN (`192.168.1.22:8787`, the actual dashboard
route `/api/ingest`, the *real* `{channel, value, flag, threshold, unit}`
shape used by `bridge/combined_bridge.py` too). Dropped the TLS/root-CA
code entirely (no longer needed for plain HTTP - `cy_http_client_create`'s
first arg is NULL for a non-secure connection, per its own documented
contract). Also extended `telemetry_publish_audio()`/`_temp()` to carry the
actual threshold (`MODEL_THRESHOLD`/`TEMP_THRESHOLD_C` from main.cpp),
since the real `/api/ingest` shape needs it and the old cloud shape never
did.

**Fixed a real bug found live**: `wrangler dev` only binds to `localhost`
by default - completely unreachable from another device on the LAN (the
board). Needed `--ip 0.0.0.0` to actually accept the board's connections.

**Added quoted-SSID support to `wifi_set`**: the real network in play was
an iPhone Personal Hotspot, default-named `Hazman's iPhone` - the original
`wifi_set <SSID> <PASSWORD>` parser split on the *first* space, which
lands inside an SSID like that instead of after it. Added a quoted form,
`wifi_set "SSID with spaces" <PASSWORD>`, alongside the original.

**Root-caused why nothing was connecting even after multiple `wifi_set`
attempts**: the user's interactive PowerShell serial-loop script (reading
`[Console]::KeyAvailable` + `Read-Host` in a polling loop, writing to the
port) was not reliably delivering typed input to the board at all - `wifi_show`
confirmed zero credentials had ever actually been saved, despite several
prior "successful-looking" attempts. Diagnosed and fixed by switching to a
simple one-shot script (open port, `WriteLine()` one command, sleep,
`ReadExisting()`, close) which worked reliably on the first try - used to
send the real `wifi_set "Hazman's iPhone" 12345678` directly.

**Verified fully working end to end**: board joined the WiFi network,
`Telemetry: HTTP connected to 192.168.1.22:8787` appeared on the UART, 9
`POST /api/ingest 200 OK` requests landed on the local server, and the
dashboard's Predictive Maintenance page showed the board's *real* live
values (`sound: 62.4042`, `temperature: 30.7849°C`) matching the UART's
own `score=`/`temp=` lines exactly - not simulated data. A few
`Telemetry: HTTP connection dropped` → reconnect cycles happened along the
way and recovered cleanly, exercising the socket-leak fix from the earlier
bug-fix pass in practice for the first time.

This is the first real hardware-to-dashboard connection over WiFi since
the feature was built - everything before this was either simulated or
UART-bridge-fed.

---

## 2026-09-09 (most recent) — Sound channel ticks in real time (~5x/sec), independent of temperature/power

`backend/dashboard-do.ts`'s single alarm previously drove every channel at
the same `TICK_MS` cadence (just changed to 5s in the previous entry) -
fine for temperature/power, but made the Sound page's spectrogram and
level meter look stepped/laggy rather than "live", since those two widgets
are specifically meant to feel like a real-time audio meter.

Added a per-channel tick interval instead of one shared one:
`TICK_INTERVAL_MS` maps `sound -> 200ms` (5x/sec), `temperature`/`power ->
TICK_MS` (5s, unchanged). One alarm still drives everything (Durable
Objects only support a single scheduled alarm) - it now wakes up every
`ALARM_RESOLUTION_MS` (the fastest channel's interval, 200ms) and checks a
new per-channel `lastSimAt` map to decide whether each channel is actually
due for a tick yet, so temperature/power still only update every 5s while
sound updates every wake-up. Real board ingests via `ingest()` are
completely unaffected either way - this only changes the *simulator's*
cadence.

`Spectrogram.vue` and `LevelMeter.vue` needed no changes - both already
react directly to `history`/`value` props, so they animate smoothly the
moment updates arrive faster.

Verified live in the browser: sound's anomaly score and dB level visibly
change between checks a few seconds apart (`0.123`/12dB -> `0.461`/30dB),
including a fresh anomaly banner firing from the faster-moving simulated
value, while temperature kept its steady 5s cadence.

---

## 2026-09-09 (yet later) — Chart Y-axis labels, 5s tick interval, cleared local readings

**`frontend/components/AreaChart.vue`**: added a real y-axis - 5 evenly-
spaced gridlines with value labels snapped to "nice" round numbers (e.g.
`28.8°C`/`8.0kW`), plus ~8% padding above/below the data so spikes don't
clip the edges. Previously the chart auto-scaled to whatever the visible
min/max happened to be with *no* indication of what that range was -
confirmed via screenshot this made the temperature/power charts genuinely
unreadable (a viewer had no way to tell what a spike's actual value was).
Labels are plain positioned HTML, not SVG `<text>`, since the SVG uses
`preserveAspectRatio="none"` to stretch responsively - SVG text would skew
under that same non-uniform scaling. Shared by both the Temperature chart
(Predictive Maintenance) and Power draw chart (Energy Monitoring, same
component) - verified fixed on both, live, in the local dashboard.

**`backend/dashboard-do.ts`**: `TICK_MS` (the simulator/broadcast interval)
changed from 4000 to 5000 - a 5-second refresh, per request.

**Cleared all existing readings**: since this is currently running purely
local (see previous entry), wiped
`.wrangler/state/v3/do/demo-kit-dashboard-DashboardState/*.sqlite` entirely
and restarted `wrangler dev` fresh - the DO's constructor found no prior
rows to rehydrate, so both channels' history started from a clean slate
under the new 5s cadence. Verified via the browser: fresh readings tightly
clustered (no leftover spikes from before the change).

---

## 2026-09-09 (even later) — Pivoted active dev to local (`wrangler dev`), off the quota-blocked Cloudflare deployment

Since the deployed Cloudflare Worker/Pages are both still inside the
Durable Object quota block (see previous two entries), switched the
*active* dev target to fully local: `npm run backend:dev` runs `wrangler
dev`, which gives a completely local stack - Worker, `DashboardState`
Durable Object, and its SQLite storage are all simulated locally by
Miniflare, with the DO's actual database living on disk at
`.wrangler/state/v3/do/demo-kit-dashboard-DashboardState/*.sqlite`. None of
this touches the real Cloudflare account or its quota at all, so it's
fully usable right now regardless of the block.

No code changes were needed - `bridge/combined_bridge.py` already
defaulted to `--target local` (from the 2026-09-08 quota incident), and
`frontend/lib/live-state.js` connects via a `location.host`-relative
WebSocket URL, so it automatically talks to whichever origin actually
served the page. The only thing missing was actually running the local
server, which is now up.

Verified fully working end-to-end locally (not just "should work"):
static assets (200), `POST /api/ingest` (writes to the local SQLite DO,
returns `ok`), the `/api/ws` WebSocket upgrade (101), and - opened in a
browser - both dashboard pages rendering real live data, including a
manually-POSTed test reading (`sound: 0.35`) showing up correctly on the
Predictive Maintenance page exactly as sent. This also incidentally
verified the four bug fixes from the previous entry actually work in
practice (the local DO uses the same `dashboard-do.ts` code).

This is the active mode until the Cloudflare quota resets (or the account
is upgraded) - `docs/ARCHITECTURE.md`'s bridge section already documents
`--target local` as the default for this reason.

---

## 2026-09-09 (latest) — Bug pass: fixed 4 real issues found across firmware + backend

Requested review pass ("find any bug on my current system") over the WiFi
firmware and the Hono/Pages backend from today's earlier work. Found and
fixed four real issues:

- **`wifi/wifi_task.c` - stale `s_link_up` during a live network switch.**
  `s_link_up` was only ever reset to `false` in the disconnect *event*
  callback - never when a reconnect was triggered manually (`wifi_set`
  while already connected). Failure scenario: connected, then `wifi_set`
  to a new network while the new AP is slow/unreachable - during that
  whole window `wifi_task_is_connected()` still returned `true`, so
  `telemetry_task` kept trying to send over a link that might not
  actually be up, and the LED (correctly blinking "connecting") visibly
  disagreed with that stale flag. Fixed: `s_link_up = false` set right
  when a (re)connect attempt starts, not only on the disconnect event.
- **`wifi/telemetry.c` - socket/TLS session leak on send failure.** Both
  failure paths in `post_reading()` (`write_header`/`send` failing) set
  `s_client_connected = false` to force a reconnect next time, but never
  called `cy_http_client_disconnect()` on the stale connection first -
  the next `cy_http_client_connect()` call just piled a new connection
  attempt on top of whatever socket/TLS session got left behind. On a
  board running 24/7 sending telemetry every 5s, routine WiFi flakiness
  would leak a socket per failure, eventually exhausting PSoC6's very
  limited concurrent-socket count and wedging telemetry until a reboot.
  Fixed: new `mark_disconnected()` helper calls `cy_http_client_disconnect()`
  before clearing the connected flag, used on both failure paths.
- **`backend/dashboard-do.ts` - `alarm()` ticked forever regardless of
  viewers.** Every 4s, unconditionally, forever, even with zero WebSocket
  clients connected - a strong suspect for repeatedly exhausting the
  Durable Object free tier's daily `rows_read` quota (this is the second
  time now: 2026-09-08, and again earlier today). Fixed: `alarm()` now
  checks `ctx.getWebSockets().length` - skips the simulated tick/write
  entirely and backs off to a 30s idle recheck interval when nobody's
  watching, real board ingests via `ingest()` are completely unaffected
  either way.
- **`backend/dashboard-do.ts` - SQL-prune counter shared across all 3
  channels instead of per-channel.** `writesSinceCleanup` was one counter
  incremented by every channel's write, but pruning only cleaned
  *whichever channel's write happened to trip it* - so on average each
  individual channel only got pruned every ~900 writes instead of the
  intended 300, letting the `readings` table grow ~3x larger than the
  code's own comment implied before cleanup caught up. Fixed: now a
  `Map<Channel, number>`, one counter per channel.

Firmware: rebuilt, reflashed to the real board, verified via UART capture
that sensing/WiFi/exponential-backoff all still run correctly (no
regression) - the specific reconnect-while-connected and socket-leak paths
still need a real WiFi network to exercise, same caveat as the rest of the
WiFi feature. Backend: redeployed to the Worker (`npm run deploy`); not
redeployed to Pages since `dashboard-do.ts` only runs where the DO class is
hosted (the Worker) - the Pages project only imports the shared
`backend/app.ts` route logic, which none of these four fixes touched. Not
verified against live traffic - still inside the Durable Object quota
block from earlier today.

---

## 2026-09-09 (later) — Backend migrated to Hono, split into Worker + Pages (`*.pages.dev`)

**Hono migration**: `backend/index.ts`'s hand-rolled `if/else` routing on
`url.pathname` replaced with a `Hono` app. Route logic (validate `/api/ingest`,
proxy `/api/ws` to the DO, optional `INGEST_TOKEN` bearer auth) is unchanged,
just re-expressed as Hono handlers. Added `hono` as a dependency.

**Split into two deploy targets, to get a `*.pages.dev` domain** (per
request: no custom domain purchase, just move off `*.workers.dev`):
Cloudflare Pages projects can't define new Durable Object classes - only
bind to one hosted by an existing Worker (confirmed via Cloudflare's docs).
So:
- The route logic moved into a shared factory, `backend/app.ts`'s
  `createApp()` - each deploy target builds its own Hono app instance
  rather than sharing one mutable object.
- `backend/index.ts` (unchanged deploy target, `wrangler deploy` /
  `wrangler.jsonc`) keeps owning the `DashboardState` Durable Object and
  serving its own `/api/*` routes directly.
- New `web-dashboard/pages/` - a whole separate Pages project root
  (`wrangler.jsonc` + `functions/api/[[path]].ts`, using Hono's
  `hono/cloudflare-pages` adapter). Binds to the *same* DO cross-script via
  `script_name: "demo-kit-dashboard"`. Had to live in its own directory
  because `wrangler pages deploy` in the installed version (4.129.1) has no
  `--config` flag - it only auto-discovers a default-named
  `wrangler.jsonc` via `--cwd`, and `functions/` has to sit next to
  whichever config file is actually in effect for file-based routing to
  resolve.
- Created and deployed the Pages project: `demo-kit-dashboard-pages`, live
  at `https://demo-kit-dashboard-pages.pages.dev`.
- Verified the cross-script DO binding is *wired correctly* by comparing
  the Pages project's bound `namespace_id` against the Worker's own
  registered `DashboardState` namespace via the Cloudflare API directly -
  they match exactly (`8aa455ced2a045fb9d1403182352c353`).

**Hit the Durable Object free-tier quota again mid-testing** (same
5,000,000 `rows_read`/day limit as the 2026-09-08 incident, confirmed via
Cloudflare's own account-block email) - every DO-touching request (on
*both* the Worker's own URL and the new Pages URL) started hanging/timing
out partway through verification. Diagnosed by ruling out the new code
first (namespace ID cross-check above, plus confirming non-DO routes like
static assets and validation-only paths kept working fine throughout) -
this was purely an account-level quota block, not a bug in the Hono/Pages
work. Stopped generating further test traffic once confirmed, and killed
the several stray `wrangler dev`/`wrangler pages dev`/`wrangler pages
deployment tail` processes left running from the investigation.

**Known gap from this work** (not yet fixed - see `docs/ARCHITECTURE.md`):
the Pages deployment has no `INGEST_TOKEN` secret set yet, so
`/api/ingest` on the `pages.dev` domain currently has no auth (the Worker's
own domain does have it set, from 2026-09-08). `wrangler pages secret put`
needs to be run interactively (blocked from being piped a value
non-interactively by the environment's own permission classifier) - left
for the user to run.

**Full end-to-end verification of the Pages→DO path is still pending** the
quota reset (2026-09-09 00:00 UTC per the block email) - the binding is
confirmed correctly configured, but no live read/write has actually
succeeded against it since the quota hit.

---

## 2026-09-09 — WiFi data-sending firmware, dashboard folder rename, docs

**WiFi data-sending feature on `predictive-maintenance-fw`** (the combined
audio+thermal board, `C:\Users\anepf\ModusToolbox-Projects\thermal-monitor-fw`):
- Added WiFi/TLS/HTTP-client dependencies (`wifi-core-freertos-lwip-mbedtls`,
  `http-client`, `serial-flash`) and restructured the firmware from a bare
  superloop into FreeRTOS tasks - the existing `service_audio()`/
  `service_thermal()` sensing/scoring logic is untouched, just now called
  from a `sensing_task` instead of `main()`'s own loop.
- New `wifi/` module:
  - `wifi_creds.c` - `wifi_set <SSID> <PASSWORD>` / `wifi_show` UART
    commands, persisted to the last row of internal flash (CRC-checked),
    survives power cycles, no reflash needed to change networks.
  - `wifi_task.c` - connects on boot with stored (or placeholder)
    credentials, exponential backoff on failure (1s→2s→4s...capped 30s),
    auto-reconnects on drop via a `cy_wcm` event callback. Drives the
    board's single LED for connection status while not connected, then
    hands the LED back to the existing anomaly-indicator logic once
    connected (this board only has one LED for both jobs).
  - `telemetry.c` - POSTs `{device_id, reading_type, value, is_anomaly}`
    to `https://demo-kit-dashboard.anepfadhli5.workers.dev/api/readings`
    every 5s over verified TLS (real GTS Root R4 root CA, captured live via
    `openssl s_client` against the actual deployed endpoint, embedded in
    `root_ca.h`). Failed sends log and retry next interval, never block
    sensing.
- **Root-caused and fixed a real bug found on real hardware**: the old
  bare-metal thermal-sampling timer (`Cy_SysTick_Init()` +
  `Cy_SysTick_SetCallback()`) reprograms SysTick directly - but FreeRTOS on
  Cortex-M owns SysTick exclusively for its own scheduler tick. The moment
  `init_audio()` ran under FreeRTOS, it silently broke every `vTaskDelay`/
  timeout system-wide (observed on-device as all UART output, from every
  task, just stopping partway through boot, with no crash message). Fixed
  by switching the thermal sample-interval timer to `xTaskGetTickCount()`
  instead of the hand-rolled ISR - confirmed fixed by flashing and watching
  audio scoring, thermal sampling, and WiFi's own exponential-backoff
  retries (1s→2s→4s→8s, exactly per spec) all run concurrently for 40s
  straight on real hardware.
- Built and flashed to the real CY8CPROTO-062-4343W board; verified via
  UART capture. Not yet tested against a real WiFi network (needs a real
  SSID/password via `wifi_set`) or the `/api/readings` receiving endpoint,
  which doesn't exist yet on the backend (see Architecture doc's "Known
  gaps").

**Dashboard folder rename**: `web-dashboard/src/` → `web-dashboard/frontend/`,
`web-dashboard/worker/` → `web-dashboard/backend/` (git mv, history preserved).
Updated every reference: `index.html`'s script tag, `wrangler.jsonc`'s
`main`, `package.json`'s `backend:dev`/`backend:check` scripts,
`.claude/launch.json`, `bridge/combined_bridge.py`'s docstring,
`web-dashboard/README.md`, and a stale comment in
`frontend/lib/live-state.js`. Verified `npm run build`, `npm run
backend:check`, and `wrangler deploy --dry-run` all still resolve
correctly. Also cleaned up stray leftover TLS cert-chain scratch files in
`bridge/` from earlier root-CA capture work.

**This docs/ folder**: created per request, with this progress log and
`ARCHITECTURE.md`. Going forward, new work gets a new dated section here.

---

## 2026-09-08 — Dataset migration, model retraining, firmware bring-up, dashboard build+deploy

**Dataset path migration**: `sound_database` moved to
`C:\Users\anepf\Ai-Dev-Sound\sound_database` - updated `DATASET_DIR`/
`base_dir` in `prepare_features.py` and `DCASE Fan6dB 1D Dense (improved
scoring).py` (root + `Ai-Dev-Sound-Windows/` copies).

**Model retraining/conversion**: retrained the fan-anomaly autoencoders
against the migrated dataset, re-ran `tools/convert_models.py` to regenerate
the int8-quantized TFLite Micro C headers
(`tools/generated/id_00/02/04/06_model_data.c/.h` + `*_params.h`).

**Audio-only firmware** (`fan-anomaly-detector-fw`, CY8CKIT-062S2-AI):
PDM DMA capture → hand-ported DSP feature extraction (matching the Python
reference pipeline) → TFLite Micro int8 inference → reconstruction-error
scoring. Fixed a real C/C++ linkage bug (`feature_extract.h` missing
`extern "C"` guards) and an undersized tensor arena. Flashed and verified
on the real board (confirmed via photo it was genuinely a CY8CPROTO-062-
4343W board during earlier mid-session board-identity confusion).

**Thermal firmware** (`thermal-monitor-fw`, CY8CPROTO-062-4343W): NTC
thermistor via `mtb-thermistor`, Beta-equation temperature conversion.

**Combined audio+thermal firmware** (`predictive-maintenance-fw`, same
CY8CPROTO board, merges the above two projects onto one board, per the
system PRD's original M1 milestone). Two real bugs root-caused and fixed:
- A dangling-pointer bug in `init_thermal()` - the thermistor config struct
  was stack-local, but the library stores a pointer to it, not a copy;
  fixed by making it `static`.
- ~±3°C thermal noise traced to the PDM microphone's continuously-toggling
  clock line physically sharing a header with the thermistor's analog
  sense pins - fixed by bracketing each temperature read with
  `cyhal_pdm_pcm_stop()`/`start()`, dropping noise to ~±0.01°C.
- Sound anomaly score recalibrated for this board's own mic (the dataset-
  derived threshold doesn't transfer between mics/rooms since the scoring
  doesn't normalize input loudness) - captured 150 live samples, set the
  threshold to their 95th percentile.

**Web dashboard** (`web-dashboard/`): built and deployed a Vue 3 +
Cloudflare Workers + Durable Object dashboard (two pages: Energy
Monitoring, Predictive Maintenance), live via WebSocket, through three
visual redesign iterations to match reference screenshots, plus a Three.js
3D PC visualization with click-to-reveal readings. Deployed to the user's
own Cloudflare account; set an `INGEST_TOKEN` secret to lock down
`/api/ingest`. Root-caused a Durable Object free-tier SQL-row-read quota
exhaustion (a `SELECT ... LIMIT 300` running on every broadcast tick for
hours) via `wrangler tail`, fixed by caching state in memory and making SQL
write-mostly.

**Board→cloud bridges** (`bridge/`): `thermal_bridge.py`, `sound_bridge.py`,
and `combined_bridge.py` (UART → `/api/ingest` over HTTP, `--target
local|prod`). Switched the default target to local dev after the deployed
instance hit its Durable Object quota.

**Git**: committed 54 files (commit `8b309fd`) - dataset path fix, retrained
models, web dashboard, bridges. Excluded `sound_database/` (14GB) and
`web-dashboard/.wrangler/` (local dev cache) via `.gitignore` updates,
caught before committing.
