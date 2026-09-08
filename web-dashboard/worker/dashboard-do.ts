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
}

const TICK_MS = 4000;
const MAX_HISTORY_POINTS = 300; // per channel, in memory - short recent window only, per PRD non-goals
const REAL_DATA_GRACE_MS = 60_000;
const SQL_PRUNE_EVERY_N_WRITES = 300; // batches SQL cleanup instead of doing it every write

const CHANNELS: Channel[] = ["sound", "temperature", "power"];

export class DashboardState extends DurableObject<Env> {
  private lastRealIngestAt = new Map<Channel, number>();
  private latestMem = new Map<Channel, Reading>();
  private historyMem = new Map<Channel, { t: number; v: number }[]>();
  private writesSinceCleanup = 0;
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

    for (const channel of CHANNELS) this.historyMem.set(channel, []);

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
    this.recordAndBroadcast(channel, reading);
  }

  async alarm() {
    await this.ready;
    for (const channel of CHANNELS) {
      const lastReal = this.lastRealIngestAt.get(channel) ?? 0;
      if (Date.now() - lastReal > REAL_DATA_GRACE_MS) {
        this.recordAndBroadcast(channel, simulateTick(channel));
      }
    }
    await this.ctx.storage.setAlarm(Date.now() + TICK_MS);
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

    this.writesSinceCleanup++;
    if (this.writesSinceCleanup >= SQL_PRUNE_EVERY_N_WRITES) {
      this.writesSinceCleanup = 0;
      const oldestKept = hist[0]?.t ?? 0;
      // Direct comparison, no correlated subquery - cheap prune, run rarely.
      this.ctx.storage.sql.exec("DELETE FROM readings WHERE channel = ? AND t < ?", channel, oldestKept);
    }

    const payload = JSON.stringify({
      type: "update",
      channel,
      reading: { value: reading.value, flag: reading.flag, threshold: reading.threshold, unit: reading.unit, extra: reading.extra ?? {}, history: hist },
    });
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
