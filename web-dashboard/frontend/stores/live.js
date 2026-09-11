import { reactive } from "vue";
import { defineStore } from "pinia";

/* Shared live-data store, fed by the Worker's WebSocket endpoint (see
 * backend/dashboard-do.ts). One connection for the whole app - every page
 * reads from this same store, per the design PRD's "dashboard updates
 * live via WebSocket, no manual refresh" requirement (section 7.1).
 *
 * The Durable Object (backend/dashboard-do.ts) POSTs from the real board
 * bridges (../../bridge/) straight through to every connected client here.
 * A channel that has *never* received real data falls back to a simulated
 * signal generator (so a fresh dashboard doesn't look dead before any
 * board's ever connected) - but once a channel HAS received real data and
 * then goes quiet for REAL_DATA_GRACE_MS, it's marked `offline: true`
 * instead of silently switching to fake data. See docs/ARCHITECTURE.md.
 *
 * Setup-store form (not options-store) - keeps the same reactive-object-
 * plus-functions shape the rest of the app's composition-API code already
 * expects, just moved under Pinia's store/devtools machinery instead of a
 * bare module-level `reactive()`.
 */
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

export const useLiveStore = defineStore("live", () => {
  const state = reactive({
    connected: false,
    sound: emptyChannel(),
    temperature: emptyChannel(),
    power: emptyChannel(),
  });

  let ws = null;
  let reconnectDelay = 1000;

  function connect() {
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
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 30000);
    };

    ws.onerror = () => ws.close();
  }

  return { state, connect };
});
