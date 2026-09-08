import { reactive } from "vue";

/* Shared live-data store, fed by the Worker's WebSocket endpoint (see
 * worker/dashboard-do.ts). One connection for the whole app - both pages
 * read from this same reactive object, per the design PRD's "dashboard
 * updates live via WebSocket, no manual refresh" requirement (section 7.1).
 *
 * NOTE: until the real board->cloud bridge exists (see NEXT_STEPS.md), the
 * Durable Object feeds this with a simulated signal generator so the UI is
 * demonstrably live end-to-end. Swapping in real readings later is just a
 * matter of the bridge POSTing to /api/ingest instead - this store and every
 * component reading from it are unaffected either way.
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
