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

const svgRef = ref(null);
const hoverIndex = ref(-1);

const chartData = computed(() => {
  const pts = visible.value;
  if (pts.length < 2) return { linePath: "", areaPath: "", xy: [], pts: [] };

  const values = pts.map((p) => p.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const tMin = pts[0].t;
  const tMax = pts[pts.length - 1].t || tMin + 1;
  const tSpan = tMax - tMin || 1;

  const xy = pts.map((p) => {
    const x = padding + ((p.t - tMin) / tSpan) * (width - padding * 2);
    const y = height - padding - ((p.v - min) / span) * (height - padding * 2);
    return [x, y];
  });

  const line = xy.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${xy[xy.length - 1][0].toFixed(1)},${height - padding} L${xy[0][0].toFixed(1)},${height - padding} Z`;

  return { linePath: line, areaPath: area, xy, pts };
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
        <path :d="chartData.areaPath" fill="url(#areaFill)" stroke="none" />
        <path :d="chartData.linePath" fill="none" :stroke="color" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />

        <g v-if="hoverPoint">
          <line :x1="hoverPoint.x" :x2="hoverPoint.x" y1="0" :y2="height - padding" class="guide-line" />
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
