<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  series: { type: Array, default: () => [] }, // [{t: epochMs, v: number}]
  unit: { type: String, default: "" },
  color: { type: String, default: "var(--accent)" },
});

const range = ref("1h"); // "1h" | "24h"
const rangeMs = computed(() => (range.value === "1h" ? 3600_000 : 86_400_000));

const visible = computed(() => {
  const cutoff = Date.now() - rangeMs.value;
  return props.series.filter((p) => p.t >= cutoff);
});

const width = 640;
const height = 220;
const padding = 8;
const axisGutter = 46; // left-side room for the y-axis value labels
const plotLeft = padding + axisGutter;

// Rounds the domain out to a "nice" step (1/2/5 * 10^n) so axis labels read
// like 28.5/29.0/29.5 instead of arbitrary decimals - the actual reason the
// old version was hard to read wasn't just "no labels", it was that the
// y-axis silently auto-scaled to whatever the visible min/max happened to
// be, with no indication of what that range even was.
function niceStep(roughStep) {
  if (roughStep <= 0) return 1;
  const mag = 10 ** Math.floor(Math.log10(roughStep));
  const norm = roughStep / mag;
  const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return step * mag;
}

const svgRef = ref(null);
const hoverIndex = ref(-1);

const chartData = computed(() => {
  const pts = visible.value;
  if (pts.length < 2) return { linePath: "", areaPath: "", xy: [], pts: [], yTicks: [] };

  const values = pts.map((p) => p.v);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);

  // Pad the domain ~8% on each side so the line/area never clips flush
  // against the top or bottom edge, then snap tick values to a nice step.
  const rawSpan = rawMax - rawMin || Math.max(Math.abs(rawMax), 1) * 0.1;
  const step = niceStep(rawSpan / 4);
  const min = Math.floor((rawMin - rawSpan * 0.08) / step) * step;
  const max = Math.ceil((rawMax + rawSpan * 0.08) / step) * step;
  const span = max - min || 1;

  const tMin = pts[0].t;
  const tMax = pts[pts.length - 1].t || tMin + 1;
  const tSpan = tMax - tMin || 1;

  const xy = pts.map((p) => {
    const x = plotLeft + ((p.t - tMin) / tSpan) * (width - plotLeft - padding);
    const y = height - padding - ((p.v - min) / span) * (height - padding * 2);
    return [x, y];
  });

  const line = xy.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${xy[xy.length - 1][0].toFixed(1)},${height - padding} L${xy[0][0].toFixed(1)},${height - padding} Z`;

  // 4 evenly-spaced gridlines (min up to max) so there's always a visible
  // scale to read the line against, not just the line itself.
  const tickCount = 4;
  const yTicks = [];
  for (let i = 0; i <= tickCount; i++) {
    const v = min + (span * i) / tickCount;
    const y = height - padding - (i / tickCount) * (height - padding * 2);
    yTicks.push({ v, y });
  }

  return { linePath: line, areaPath: area, xy, pts, yTicks };
});

const hoverPoint = computed(() => {
  if (hoverIndex.value < 0 || !chartData.value.xy[hoverIndex.value]) return null;
  const [x, y] = chartData.value.xy[hoverIndex.value];
  const pt = chartData.value.pts[hoverIndex.value];
  return { x, y, v: pt.v, t: pt.t };
});

function onMove(evt) {
  const xy = chartData.value.xy;
  if (!xy.length || !svgRef.value) return;
  const rect = svgRef.value.getBoundingClientRect();
  const relX = ((evt.clientX - rect.left) / rect.width) * width;
  let closest = 0;
  let bestDist = Infinity;
  for (let i = 0; i < xy.length; i++) {
    const d = Math.abs(xy[i][0] - relX);
    if (d < bestDist) {
      bestDist = d;
      closest = i;
    }
  }
  hoverIndex.value = closest;
}
function onLeave() {
  hoverIndex.value = -1;
}

function timeLabel(t) {
  return new Date(t).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
</script>

<template>
  <div class="area-chart">
    <div class="chart-toolbar">
      <div class="range-toggle">
        <button :class="{ active: range === '1h' }" @click="range = '1h'">Last hour</button>
        <button :class="{ active: range === '24h' }" @click="range = '24h'">Last 24 hours</button>
      </div>
    </div>

    <div v-if="chartData.linePath" class="chart-shell">
      <!-- Y-axis labels as plain HTML, not SVG <text> - the SVG below uses
           preserveAspectRatio="none" so it can stretch to fill the card's
           width independently of its height; SVG text would visibly skew
           under that same non-uniform scaling, plain positioned divs won't. -->
      <div class="y-axis" :style="{ width: `${(axisGutter / width) * 100}%` }">
        <span
          v-for="tick in chartData.yTicks"
          :key="tick.y"
          class="y-axis-label"
          :style="{ top: `${(tick.y / height) * 100}%` }"
        >{{ tick.v.toFixed(1) }}{{ unit }}</span>
      </div>

      <svg
        ref="svgRef"
        :viewBox="`0 0 ${width} ${height}`"
        class="chart-svg"
        preserveAspectRatio="none"
        @mousemove="onMove"
        @mouseleave="onLeave"
      >
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="color" stop-opacity="0.28" />
            <stop offset="100%" :stop-color="color" stop-opacity="0" />
          </linearGradient>
        </defs>

        <!-- Reference gridlines so the line's actual scale is legible at a
             glance, not just on hover. -->
        <line
          v-for="tick in chartData.yTicks"
          :key="tick.y"
          :x1="plotLeft" :x2="width - padding" :y1="tick.y" :y2="tick.y"
          class="grid-line"
        />

        <path :d="chartData.areaPath" fill="url(#areaFill)" stroke="none" />
        <path :d="chartData.linePath" fill="none" :stroke="color" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />

        <g v-if="hoverPoint">
          <line :x1="hoverPoint.x" :x2="hoverPoint.x" :y1="padding" :y2="height - padding" class="guide-line" />
          <circle :cx="hoverPoint.x" :cy="hoverPoint.y" r="4.5" :fill="color" class="guide-dot" />
        </g>
      </svg>

      <div
        v-if="hoverPoint"
        class="tooltip"
        :style="{ left: `${(hoverPoint.x / width) * 100}%` }"
      >
        <span class="tooltip-time">{{ timeLabel(hoverPoint.t) }}</span>
        <span class="tooltip-value">{{ hoverPoint.v.toFixed(2) }}{{ unit }}</span>
      </div>
    </div>
    <div v-else class="chart-empty">Waiting for readings&hellip;</div>
  </div>
</template>

<style scoped>
.area-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.chart-toolbar {
  display: flex;
  justify-content: flex-end;
}

.range-toggle {
  display: flex;
  gap: 2px;
  background: var(--bg);
  border-radius: var(--radius-pill);
  padding: 3px;
}

.range-toggle button {
  border: none;
  background: transparent;
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
}

.range-toggle button.active {
  background: var(--surface-2);
  color: var(--text);
}

.chart-shell {
  position: relative;
  width: 100%;
  min-width: 0;
}

.y-axis {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 8px; /* matches the SVG's own bottom padding */
  pointer-events: none;
}

.y-axis-label {
  position: absolute;
  left: 0;
  transform: translateY(-50%);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
  white-space: nowrap;
}

.grid-line {
  stroke: var(--border-soft-2);
  stroke-width: 1;
  opacity: 0.6;
}

.chart-svg {
  width: 100%;
  height: clamp(140px, 28vw, 220px);
  display: block;
  cursor: crosshair;
}

.guide-line {
  stroke: var(--border-soft-2);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.guide-dot {
  stroke: var(--surface);
  stroke-width: 2;
}

.tooltip {
  position: absolute;
  top: 6px;
  transform: translateX(-50%);
  background: var(--surface-2);
  border: 1px solid var(--border-soft-2);
  border-radius: 10px;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  pointer-events: none;
  white-space: nowrap;
  box-shadow: var(--shadow-sm);
}

.tooltip-time {
  font-size: 10px;
  color: var(--text-muted);
}

.tooltip-value {
  font-size: 12.5px;
  font-weight: 700;
}

.chart-empty {
  height: clamp(140px, 28vw, 220px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
