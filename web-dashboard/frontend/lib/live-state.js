import { reactive } from "vue";

/* Shared live-data store, fed by the Worker's WebSocket endpoint (see
 * backend/dashboard-do.ts). One connection for the whole app - both pages
 * read from this same reactive object, per the design PRD's "dashboard
 * updates live via WebSocket, no manual refresh" requirement (section 7.1).
 *
 * The Durable Object (backend/dashboard-do.ts) POSTs from the real board
 * bridges (../../bridge/) straight through to every connected client here.
 * A channel that has *never* received real data falls back to a simulated
 * signal generator (so a fresh dashboard doesn't look dead before any
 * board's ever connected) - but once a channel HAS received real data and
 * then goes quiet for REAL_DATA_GRACE_MS, it's marked `offline: true`
 * instead of silently switching to fake data. See docs/ARCHITECTURE.md.
 */
export const state = reactive({
  connected: false,
  sound: emptyChannel(),
  temperature: emptyChannel(),
  power: emptyChannel(),
});

function emptyChannel() {
  return {
    value: null,
    flag: "normal",
    threshold: null,
    unit: "",
    extra: {},
    offline: false,
    history: [],
  };
}

let ws = null;
let reconnectDelay = 1000;

export function connectLiveState() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/api/ws`);

  ws.onopen = () => {
    state.connected = true;
    reconnectDelay = 1000;
  };

  ws.onmessage = (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    if (msg.type === "snapshot") {
      Object.assign(state.sound, msg.data.sound);
      Object.assign(state.temperature, msg.data.temperature);
      Object.assign(state.power, msg.data.power);
    } else if (msg.type === "update" && state[msg.channel]) {
      Object.assign(state[msg.channel], msg.reading);
    }
  };

  ws.onclose = () => {
    state.connected = false;
    setTimeout(connectLiveState, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  };

  ws.onerror = () => ws.close();
}
