<script setup>
import { onMounted, onUnmounted, ref, watch } from "vue";

/* Scrolling spectrogram-style visualization driven by the board's real
 * on-device anomaly score (the firmware doesn't expose raw per-frequency
 * FFT bins over UART, only the scalar score - see fan-anomaly-detector-fw's
 * frame_score()). Each new score is spread across a deterministic set of
 * "bands" so louder/more-anomalous moments visibly light up more of the
 * band, which is honest to what's actually measured without pretending
 * this is calibrated per-frequency spectral data. */
const props = defineProps({
  history: { type: Array, default: () => [] }, // [{t, v}]
});

const canvasRef = ref(null);
const BANDS = 28;
let ctx, colW, lastTimestamp = -1;

function bandIntensities(value, seed) {
  const out = new Array(BANDS);
  for (let i = 0; i < BANDS; i++) {
    // deterministic pseudo-random spread, weighted toward lower bands with
    // occasional high-band flare when the score is elevated
    const n = Math.sin((seed + i) * 12.9898) * 43758.5453;
    const noise = n - Math.floor(n);
    const bandFalloff = 1 - i / BANDS;
    const flare = value > 1.5 && i > BANDS * 0.6 ? noise * 0.6 : 0;
    out[i] = Math.min(1, value * 0.35 * bandFalloff * (0.5 + noise * 0.7) + flare);
  }
  return out;
}

function colorFor(intensity) {
  // dark -> amber -> bright yellow, matching the app's accent palette
  const r = Math.round(30 + intensity * 225);
  const g = Math.round(20 + intensity * 140);
  const b = Math.round(30 * (1 - intensity));
  return `rgb(${r},${g},${b})`;
}

function drawColumn(x, value, seed) {
  const bands = bandIntensities(value, seed);
  const bandH = ctx.canvas.height / BANDS;
  for (let i = 0; i < BANDS; i++) {
    ctx.fillStyle = colorFor(bands[i]);
    ctx.fillRect(x, ctx.canvas.height - (i + 1) * bandH, colW, bandH + 0.5);
  }
}

function redrawAll() {
  if (!ctx) return;
  const w = ctx.canvas.width;
  ctx.fillStyle = "#16181c";
  ctx.fillRect(0, 0, w, ctx.canvas.height);
  const pts = props.history.slice(-Math.floor(w / colW));
  pts.forEach((p, i) => drawColumn(i * colW, p.v, p.t));
  lastTimestamp = props.history.at(-1)?.t ?? -1;
}

/* Finds "new" points by timestamp, not by array length/index - the
 * backend caps history at MAX_HISTORY_POINTS (push+shift), so once that
 * cap is hit the array's length stops changing forever even though new
 * points keep arriving at the end. A length-based watch/index (the
 * previous approach) would false-negative from that point on and freeze
 * the spectrogram permanently despite live data still flowing. */
function appendColumns() {
  if (!ctx) return;
  const newPts = props.history.filter((p) => p.t > lastTimestamp);
  if (newPts.length === 0) return;
  lastTimestamp = newPts[newPts.length - 1].t;
  const w = ctx.canvas.width;
  const shift = newPts.length * colW;
  if (shift < w) {
    const img = ctx.getImageData(shift, 0, w - shift, ctx.canvas.height);
    ctx.putImageData(img, 0, 0);
  }
  newPts.forEach((p, i) => drawColumn(w - (newPts.length - i) * colW, p.v, p.t));
}

let resizeObserver;
onMounted(() => {
  const canvas = canvasRef.value;
  const host = canvas.parentElement;
  const setSize = () => {
    canvas.width = host.clientWidth;
    canvas.height = 110;
    colW = 4;
    ctx = canvas.getContext("2d");
    redrawAll(); // also resets lastTimestamp
  };
  setSize();
  resizeObserver = new ResizeObserver(setSize);
  resizeObserver.observe(host);
});
onUnmounted(() => resizeObserver?.disconnect());

// Watches the array reference, not its length - live-state.js replaces
// `history` with a fresh array on every WebSocket update regardless of
// whether its length actually changed (see the comment on appendColumns()).
watch(() => props.history, appendColumns);
</script>

<template>
  <div class="spectro-wrap">
    <canvas ref="canvasRef"></canvas>
    <span class="spectro-caption">Live &mdash; derived from the on-device anomaly score</span>
  </div>
</template>

<style scoped>
.spectro-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

canvas {
  width: 100%;
  height: 110px;
  display: block;
  border-radius: 10px;
}

.spectro-caption {
  font-size: 10.5px;
  color: var(--text-muted);
}
</style>
