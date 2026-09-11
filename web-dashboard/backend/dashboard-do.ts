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
 * Data source: real board ingests only, via /api/ingest (see ingest()
 * below) - a bridge (../../bridge/) or the firmware's own WiFi client
 * POSTs a reading in the Reading shape. Used to fall back to a
 * simulated signal generator for any channel that had never received a
 * real ingest, so the dashboard looked alive before any board was
 * connected - removed per explicit feedback that showing fake data
 * (even clearly labeled as simulated, see Reading.real) wasn't wanted at
 * all. A channel with no real data now just stays empty (value: null)
 * until one actually arrives - see latestFor().
 */

type Channel = "sound" | "temperature" | "power";

interface Reading {
  // null before this channel has ever received a real ingest - see
  // latestFor(). Never fabricated.
  value: number | null;
  flag: "normal" | "abnormal";
  threshold: number | null;
  unit: string;
  extra?: Record<string, number>;
  /* True once a channel that has previously received a real ingest goes
   * quiet for REAL_DATA_GRACE_MS - see alarm(). Channels that have never
   * received a real ingest keep simulating instead (untouched demo mode). */
  offline?: boolean;
  /* True only while this channel is currently backed by a real board
   * ingest within REAL_DATA_GRACE_MS - false both for simulated data
   * (never received a real ingest) and for stale/offline data. Lets the
   * client tell "genuinely live" apart from "still showing something
   * plausible" - see recordAndBroadcast()'s isReal(). Added because the
   * dashboard's own WebSocket-connected status was being read as "the
   * board is online", when it only ever meant "this browser tab has a
   * live connection to our own server" - true almost all the time
   * regardless of whether any physical board was ever connected. */
  real?: boolean;
}

/* A Reading that's actually been measured - value/threshold narrowed to
 * non-null. ingest()/recordAndBroadcast() only ever deal in these; the
 * nullable Reading above exists solely to represent latestFor()'s
 * synthetic "never received real data" placeholder. */
type RealReading = Reading & { value: number; threshold: number };

// Now the only thing the alarm exists for is noticing a real channel has
// gone stale (see alarm()) - no simulation cadence to serve anymore, so
// this just needs to be comfortably finer-grained than REAL_DATA_GRACE_MS
// below, not tied to any signal's own sample rate.
const ALARM_RESOLUTION_MS = 10_000;
const IDLE_TICK_MS = 30_000; // alarm interval while no dashboard is connected - just checks back for reconnects
// 1440 = 24h worth of real readings at the firmware's 1-reading/minute
// cadence (see wifi/telemetry.c's AUDIO_SEND_INTERVAL_MS/
// TEMP_SEND_INTERVAL_MS) - raised from 300 (5h) so the dashboard's "Last
// 24 hours" range toggle (see AreaChart.vue) actually has 24h of real
// data to show instead of silently truncating to whatever the cap allowed.
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

export class DashboardState extends DurableObject<Env> {
  private lastRealIngestAt = new Map<Channel, number>();
  private latestMem = new Map<Channel, RealReading>();
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
      if (!alarm) await this.ctx.storage.setAlarm(Date.now() + ALARM_RESOLUTION_MS);
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
  async ingest(channel: Channel, reading: RealReading) {
    await this.ready;
    this.lastRealIngestAt.set(channel, Date.now());
    this.offlineAnnounced.delete(channel); // back online - re-arm the offline announcement for next time
    this.recordAndBroadcast(channel, reading);
  }

  async alarm() {
    await this.ready;

    // Nobody's watching - no point checking for staleness transitions
    // nobody will see, just check back later in case someone (re)connects.
    // Real board ingests still land immediately via ingest() regardless.
    if (this.ctx.getWebSockets().length === 0) {
      await this.ctx.storage.setAlarm(Date.now() + IDLE_TICK_MS);
      return;
    }

    // Only job left: notice a channel that WAS real has gone quiet for
    // too long, and announce it as offline (once) instead of just
    // leaving its last real reading looking perpetually current.
    // Channels that have never received a real ingest at all don't need
    // anything here - latestFor() already reports them as empty on
    // every read, nothing to transition.
    const now = Date.now();
    for (const channel of CHANNELS) {
      const lastReal = this.lastRealIngestAt.get(channel);
      if (lastReal === undefined) continue;

      if (now - lastReal > REAL_DATA_GRACE_MS) {
        if (!this.offlineAnnounced.has(channel)) {
          this.offlineAnnounced.add(channel);
          this.announceOffline(channel);
        }
      }
      // else: real data is still fresh - nothing to do, ingest() already broadcast it.
    }
    await this.ctx.storage.setAlarm(now + ALARM_RESOLUTION_MS);
  }

  /* True only while `channel` currently has a real ingest within
   * REAL_DATA_GRACE_MS - see Reading.real's comment for why this exists
   * as its own field rather than being inferred from `offline`/WS state
   * client-side. */
  private isReal(channel: Channel): boolean {
    const lastReal = this.lastRealIngestAt.get(channel);
    return lastReal !== undefined && Date.now() - lastReal <= REAL_DATA_GRACE_MS;
  }

  private recordAndBroadcast(channel: Channel, reading: RealReading) {
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
        real: this.isReal(channel),
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
    const offlineReading: RealReading = { ...last, offline: true };
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
        real: false,
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
    const reading = this.latestMem.get(channel);
    const history = this.historyMem.get(channel) ?? [];
    if (!reading) {
      // Never received a real ingest for this channel - stay honestly
      // empty rather than inventing a plausible-looking number.
      return { value: null, flag: "normal", threshold: null, unit: "", extra: {}, offline: false, real: false, history };
    }
    // real recomputed fresh here (not read off the stored reading) since
    // it can go stale between writes - e.g. a page loads and calls this
    // well after the last ingest, past REAL_DATA_GRACE_MS, without any
    // new broadcast having fired to update a stored flag.
    return { ...reading, real: this.isReal(channel), history };
  }

  private buildSnapshot() {
    return {
      sound: this.latestFor("sound"),
      temperature: this.latestFor("temperature"),
      power: this.latestFor("power"),
    };
  }
}

