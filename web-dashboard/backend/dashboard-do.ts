import { DurableObject } from "cloudflare:workers";
import type { Env } from "./env";

/* DashboardState: single Durable Object (one global instance, idFromName("global"))
 * holding live readings for the three signals (sound, temperature, power) and
 * broadcasting updates to every connected dashboard over WebSocket.
 *
 * State lives in memory (this.latestMem / this.historyMem), not re-queried
 * from SQL on every tick - an earlier version called a `SELECT ... LIMIT 300`
 * on every single broadcast (every ~4s, x3 channels, for hours), which blew
 * through the Durable Object free tier's daily SQL-row-read quota and then
 * made every request to this DO fail (including real board ingests) until
 * the quota reset. SQL is now write-mostly: one INSERT per reading for
 * durability across DO restarts, and a full re-read from SQL only happens
 * once, in the constructor, to rehydrate memory after a cold start.
 *
 * Data source: simulated (see simulateTick()) so the dashboard is
 * demonstrably live end-to-end before/alongside the real board->cloud
 * bridge (see ../../bridge/). A real bridge POSTs to /api/ingest in the
 * same shape simulateTick() produces - see ingest() below. A channel that
 * received a real ingest in the last REAL_DATA_GRACE_MS stops being
 * simulated, so a bridge can come online one channel at a time.
 */

type Channel = "sound" | "temperature" | "power";

interface Reading {
  value: number;
  flag: "normal" | "abnormal";
  threshold: number;
  unit: string;
  extra?: Record<string, number>;
  /* True once a channel that has previously received a real ingest goes
   * quiet for REAL_DATA_GRACE_MS - see alarm(). Channels that have never
   * received a real ingest keep simulating instead (untouched demo mode). */
  offline?: boolean;
}

const TICK_MS = 5000; // power cadence
// 200ms turned out to be too aggressive for a Durable Object alarm in
// practice - Miniflare threw "SQLite alarm handler canceled with
// requestScheduledAlarm" + an uncaught internal error once the alarm was
// being rescheduled every 200ms, risking the DO instance itself getting
// torn down/restarted (which would have disrupted real board ingests too,
// not just the simulator). 1s is still 5x faster than power and
// comfortably clear of whatever internal minimum tripped that error - also
// matches the firmware's own real send cadence for these two signals (see
// wifi/telemetry.c's AUDIO_SEND_INTERVAL_MS/TEMP_SEND_INTERVAL_MS), so the
// simulated and real-board experiences feel the same.
const SOUND_TICK_MS = 1000;
const TEMP_TICK_MS = 1000;
const ALARM_RESOLUTION_MS = Math.min(TICK_MS, SOUND_TICK_MS, TEMP_TICK_MS); // how often the single alarm actually has to wake up to serve the fastest channel
const IDLE_TICK_MS = 30_000; // alarm interval while no dashboard is connected - just checks back for reconnects
// 1440 = 24h worth of real readings at the firmware's 1-reading/minute
// cadence (see wifi/telemetry.c's AUDIO_SEND_INTERVAL_MS/
// TEMP_SEND_INTERVAL_MS) - raised from 300 (5h) so the dashboard's "Last
// 24 hours" range toggle (see AreaChart.vue) actually has 24h of real
// data to show instead of silently truncating to whatever the cap
// allowed. Note this is real-data-only math: the simulator (SOUND_TICK_MS/
// TEMP_TICK_MS, used only when no board has ever sent real data for a
// channel) still ticks once a second, so demo-mode history only spans
// ~24 simulated minutes - a pre-existing simulator/real-cadence mismatch,
// unrelated to this change.
const MAX_HISTORY_POINTS = 1440; // per channel, in memory
// Must stay comfortably above the firmware's own send interval (60s, see
// wifi/telemetry.c's AUDIO_SEND_INTERVAL_MS/TEMP_SEND_INTERVAL_MS) - a
// grace period equal to the send interval races normal network jitter
// (one slightly slow POST is enough to trip it) and flashes "offline" on
// a board that never actually stopped sending. 2.5x gives room for a
// couple of missed/delayed sends before actually flagging it.
const REAL_DATA_GRACE_MS = 150_000;
const SQL_PRUNE_EVERY_N_WRITES = 300; // batches SQL cleanup instead of doing it every write

const CHANNELS: Channel[] = ["sound", "temperature", "power"];
const TICK_INTERVAL_MS: Record<Channel, number> = {
  sound: SOUND_TICK_MS,
  temperature: TEMP_TICK_MS,
  power: TICK_MS,
};

export class DashboardState extends DurableObject<Env> {
  private lastRealIngestAt = new Map<Channel, number>();
  private lastSimAt = new Map<Channel, number>(); // per-channel simulated-tick cadence, see TICK_INTERVAL_MS
  private latestMem = new Map<Channel, Reading>();
  private historyMem = new Map<Channel, { t: number; v: number }[]>();
  // Per-channel, not shared - a shared counter only prunes whichever
  // channel's write happens to trip it, leaving the other channels'
  // tables to grow ~3x past MAX_HISTORY_POINTS before their turn comes.
  private writesSinceCleanup = new Map<Channel, number>();
  // Which channels have already had their one-time "went offline" update
  // broadcast, so we don't resend it every tick while it stays stale -
  // cleared the moment real data resumes for that channel (see ingest()).
  private offlineAnnounced = new Set<Channel>();
  private ready: Promise<void>;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS readings (
        channel TEXT NOT NULL,
        t INTEGER NOT NULL,
        value REAL NOT NULL,
        flag TEXT NOT NULL,
        threshold REAL,
        unit TEXT,
        extra TEXT
      )
    `);
    this.ctx.storage.sql.exec(`
      CREATE INDEX IF NOT EXISTS idx_readings_channel_t ON readings (channel, t)
    `);

    for (const channel of CHANNELS) {
      this.historyMem.set(channel, []);
      this.writesSinceCleanup.set(channel, 0);
    }

    // One-time rehydration from SQL on cold start - the only bulk SQL read
    // this DO ever does.
    this.ready = this.ctx.blockConcurrencyWhile(async () => {
      for (const channel of CHANNELS) {
        const rows = this.ctx.storage.sql
          .exec("SELECT t, value, flag, threshold, unit, extra FROM readings WHERE channel = ? ORDER BY t DESC LIMIT ?", channel, MAX_HISTORY_POINTS)
          .toArray() as { t: number; value: number; flag: string; threshold: number; unit: string; extra: string }[];
        if (rows.length > 0) {
          this.historyMem.set(channel, rows.map((r) => ({ t: r.t, v: r.value })).reverse());
          const latest = rows[0];
          this.latestMem.set(channel, {
            value: latest.value,
            flag: latest.flag as "normal" | "abnormal",
            threshold: latest.threshold,
            unit: latest.unit,
            extra: JSON.parse(latest.extra || "{}"),
          });
        }
      }

      const alarm = await this.ctx.storage.getAlarm();
      if (!alarm) await this.ctx.storage.setAlarm(Date.now() + TICK_MS);
    });
  }

  async fetch(request: Request): Promise<Response> {
    await this.ready;
    const upgrade = request.headers.get("Upgrade");
    if (upgrade !== "websocket") {
      return new Response("expected websocket", { status: 426 });
    }
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.ctx.acceptWebSocket(server);
    server.send(JSON.stringify({ type: "snapshot", data: this.buildSnapshot() }));
    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage() {
    /* No client->server messages expected yet; reserved for future use
     * (e.g. requesting a wider history backfill). */
  }

  async webSocketClose(ws: WebSocket) {
    try {
      ws.close();
    } catch {
      /* already closing */
    }
  }

  /** Real bridge entry point - same shape/effect as a simulated tick. */
  async ingest(channel: Channel, reading: Reading) {
    await this.ready;
    this.lastRealIngestAt.set(channel, Date.now());
    this.offlineAnnounced.delete(channel); // back online - re-arm the offline announcement for next time
    this.recordAndBroadcast(channel, reading);
  }

  async alarm() {
    await this.ready;

    // Nobody's watching - skip simulated writes entirely (they only exist
    // to keep the dashboard visibly live) and just check back later in
    // case someone (re)connects. Real board ingests still land immediately
    // via ingest() regardless of this - this only affects the simulator.
    // The DO's alarm previously ticked every TICK_MS forever, unconditionally,
    // which was a real contributor to exhausting the Durable Object free
    // tier's daily rows_read quota twice now (see docs/PROGRESS.md).
    if (this.ctx.getWebSockets().length === 0) {
      await this.ctx.storage.setAlarm(Date.now() + IDLE_TICK_MS);
      return;
    }

    // One alarm serving multiple cadences: it wakes up every
    // ALARM_RESOLUTION_MS (the fastest channel's interval), but each
    // channel only actually ticks once its own TICK_INTERVAL_MS has
    // elapsed since its last tick - sound gets a fresh simulated point
    // ~5x/sec, temperature/power stay at their slower TICK_MS cadence.
    const now = Date.now();
    for (const channel of CHANNELS) {
      const interval = TICK_INTERVAL_MS[channel];
      const lastSim = this.lastSimAt.get(channel) ?? 0;
      if (now - lastSim < interval) continue;
      this.lastSimAt.set(channel, now);

      const lastReal = this.lastRealIngestAt.get(channel);
      if (lastReal === undefined) {
        // Never received a real ingest for this channel - keep the demo
        // simulator running so a fresh dashboard doesn't look dead before
        // any board/bridge has ever connected to it.
        this.recordAndBroadcast(channel, simulateTick(channel));
        continue;
      }

      if (now - lastReal > REAL_DATA_GRACE_MS) {
        // Was real, now stale: show it as offline instead of quietly
        // switching to fake data - silently simulating here used to make
        // turning the real board off look identical to it still running,
        // which defeats the point of watching a real board's status.
        if (!this.offlineAnnounced.has(channel)) {
          this.offlineAnnounced.add(channel);
          this.announceOffline(channel);
        }
      }
      // else: real data is still fresh - nothing to do, ingest() already broadcast it.
    }
    await this.ctx.storage.setAlarm(now + ALARM_RESOLUTION_MS);
  }

  private recordAndBroadcast(channel: Channel, reading: Reading) {
    const t = Date.now();

    this.latestMem.set(channel, reading);
    const hist = this.historyMem.get(channel)!;
    hist.push({ t, v: reading.value });
    if (hist.length > MAX_HISTORY_POINTS) hist.shift();

    // Write-only: no read-back. Durability for DO restarts, not a query path.
    this.ctx.storage.sql.exec(
      "INSERT INTO readings (channel, t, value, flag, threshold, unit, extra) VALUES (?, ?, ?, ?, ?, ?, ?)",
      channel,
      t,
      reading.value,
      reading.flag,
      reading.threshold,
      reading.unit,
      JSON.stringify(reading.extra ?? {})
    );

    // Per-channel counter - a single counter shared across all 3 channels
    // would only prune whichever channel's write happened to trip it,
    // leaving the other channels' tables to grow ~3x past
    // MAX_HISTORY_POINTS before their turn came around.
    const writes = (this.writesSinceCleanup.get(channel) ?? 0) + 1;
    if (writes >= SQL_PRUNE_EVERY_N_WRITES) {
      this.writesSinceCleanup.set(channel, 0);
      const oldestKept = hist[0]?.t ?? 0;
      // Direct comparison, no correlated subquery - cheap prune, run rarely.
      this.ctx.storage.sql.exec("DELETE FROM readings WHERE channel = ? AND t < ?", channel, oldestKept);
    } else {
      this.writesSinceCleanup.set(channel, writes);
    }

    const payload = JSON.stringify({
      type: "update",
      channel,
      reading: {
        value: reading.value,
        flag: reading.flag,
        threshold: reading.threshold,
        unit: reading.unit,
        extra: reading.extra ?? {},
        offline: false, // a normal broadcast always means "not offline", clearing any earlier offline state client-side
        history: hist,
      },
    });
    this.broadcast(payload);
  }

  /** One-time notice that a previously-real channel has gone stale - see
   * alarm(). Doesn't touch SQL/history (an "offline" marker isn't a
   * measurement), just updates the in-memory latest state and tells
   * connected clients, so a fresh page load also sees it via buildSnapshot(). */
  private announceOffline(channel: Channel) {
    const last = this.latestMem.get(channel);
    if (!last) return; // nothing has ever been recorded for this channel - nothing to mark offline
    const offlineReading: Reading = { ...last, offline: true };
    this.latestMem.set(channel, offlineReading);
    const hist = this.historyMem.get(channel) ?? [];
    const payload = JSON.stringify({
      type: "update",
      channel,
      reading: {
        value: offlineReading.value,
        flag: offlineReading.flag,
        threshold: offlineReading.threshold,
        unit: offlineReading.unit,
        extra: offlineReading.extra ?? {},
        offline: true,
        history: hist,
      },
    });
    this.broadcast(payload);
  }

  private broadcast(payload: string) {
    for (const ws of this.ctx.getWebSockets()) {
      try {
        ws.send(payload);
      } catch {
        /* dead socket, ignore - hibernation API cleans these up */
      }
    }
  }

  private latestFor(channel: Channel): Reading & { history: { t: number; v: number }[] } {
    const reading = this.latestMem.get(channel) ?? simulateTick(channel);
    return { ...reading, history: this.historyMem.get(channel) ?? [] };
  }

  private buildSnapshot() {
    return {
      sound: this.latestFor("sound"),
      temperature: this.latestFor("temperature"),
      power: this.latestFor("power"),
    };
  }
}

/* --- Simulated signal generator ---
 * Plausible ranges/behavior per channel, with occasional anomaly bursts, so
 * the dashboard has something real to show before the UART->cloud bridge
 * exists. Replace by having a bridge POST to /api/ingest instead. */
let soundBase = 0.3;
let tempBase = 29.2;
let powerBase = 2.4;

function simulateTick(channel: Channel): Reading {
  const jitter = (n: number) => (Math.random() - 0.5) * n;
  const burst = Math.random() < 0.04; // occasional anomaly

  if (channel === "sound") {
    soundBase = clamp(soundBase + jitter(0.05), 0.1, 0.6);
    const value = round(burst ? soundBase + 1.2 + Math.random() * 0.8 : soundBase, 3);
    const threshold = 0.9324; // matches id_00_params.h's recalibrated threshold
    return { value, flag: value > threshold ? "abnormal" : "normal", threshold, unit: "" };
  }

  if (channel === "temperature") {
    tempBase = clamp(tempBase + jitter(0.15), 26, 33);
    const value = round(burst ? tempBase + 6 + Math.random() * 4 : tempBase, 2);
    const threshold = 50.0;
    return { value, flag: value > threshold ? "abnormal" : "normal", threshold, unit: "C" };
  }

  // power
  powerBase = clamp(powerBase + jitter(0.2), 1.2, 4.5);
  const value = round(burst ? powerBase + 3 + Math.random() * 2 : powerBase, 2);
  const threshold = 6.0;
  const powerFactor = round(0.9 + Math.random() * 0.08, 2);
  const voltage = round(228 + jitter(4), 1);
  const current = round((value * 1000) / (voltage * powerFactor), 2);
  return {
    value,
    flag: value > threshold ? "abnormal" : "normal",
    threshold,
    unit: "kW",
    extra: { powerFactor, voltage, current },
  };
}

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v));
}
function round(v: number, dp: number) {
  const f = 10 ** dp;
  return Math.round(v * f) / f;
}
