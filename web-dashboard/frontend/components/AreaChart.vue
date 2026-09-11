<script setup>
import { computed, onUnmounted, ref, watch } from "vue";

const props = defineProps({
  series: { type: Array, default: () => [] }, // [{t: epochMs, v: number}]
  unit: { type: String, default: "" },
  color: { type: String, default: "var(--accent)" },
});

const range = ref("1h"); // "10m" | "1h" | "24h"
const RANGE_MS = { "10m": 600_000, "1h": 3600_000, "24h": 86_400_000 };
const rangeMs = computed(() => RANGE_MS[range.value]);

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
const chartShellRef = ref(null);
const hoverIndex = ref(-1);

// The SVG's viewBox is a fixed 640 units wide but the card it renders
// into (and therefore each viewBox unit's real on-screen size) varies
// with the page's responsive layout - a gap that reads fine on a wide
// desktop card can be zero pixels on a narrow one. Tracking the real
// rendered width lets the x-axis label spacing below convert a real
// "labels need ~64px apart" rule into the right number of viewBox units
// for whatever width this instance actually has.
const renderedWidth = ref(width);
let resizeObserver;
// chart-shell only exists once there's data to plot (v-if="chartData.
// linePath"), so it can mount well after this component's own onMounted
// already ran - watching the template ref itself (rather than a one-shot
// onMounted) means the observer attaches whenever that div first
// actually appears, including if it wasn't there yet on first render.
watch(
  chartShellRef,
  (el) => {
    resizeObserver?.disconnect();
    if (!el) return;
    renderedWidth.value = el.clientWidth || width;
    resizeObserver = new ResizeObserver(() => {
      renderedWidth.value = el.clientWidth || width;
    });
    resizeObserver.observe(el);
  },
  { immediate: true },
);
onUnmounted(() => resizeObserver?.disconnect());

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

  // Time-axis labels (HH:MM) - readings now arrive once a minute (see
  // telemetry.c's *_SEND_INTERVAL_MS), so labeling by clock time rather
  // than just showing the line is what actually makes the 1-per-minute
  // cadence legible. Picked by index across the visible points rather
  // than by even time spacing, since real readings aren't perfectly
  // metronomic (retries, brief drops) - this still spreads labels evenly
  // across the plotted width either way.
  //
  // One candidate tick per point, not a fixed cap - a short window (e.g.
  // ~10 points at 1/minute) should get a label on every single point
  // ("12:54, 12:55, 12:56, ..."), while a long window (a full "Last 24
  // hours" at 1440 points) obviously can't. The gap-collision filtering
  // right below is what actually decides how many of these survive to
  // render, based on the card's real width - this just stops
  // pre-emptively throwing away candidates a short/wide-enough window
  // could actually fit.
  const rawTickCount = xy.length - 1;
  const rawXTicks = [];
  for (let i = 0; i <= rawTickCount; i++) {
    const idx = Math.round((i / rawTickCount) * (xy.length - 1));
    rawXTicks.push({ x: xy[idx][0], t: pts[idx].t });
  }

  // Drop ticks that would render too close together to read (e.g. early
  // on, with few points yet, several evenly-spaced-by-index ticks can
  // round to nearly the same x and their "10:20 AM"-ish labels overlap
  // into an unreadable smear). Always keep the last tick's position -
  // pop the previous one instead if it's the one crowding it, so the
  // range's actual end time is never the one that gets dropped.
  // ~64 real screen px is roughly a "10:39 AM" label's width plus a
  // little breathing room - converted from viewBox units (640 wide) to
  // whatever this card's actual rendered width currently is, since a
  // gap that's fine on a wide desktop card can be zero px on a narrow
  // one (see renderedWidth above).
  const minLabelGapPx = 64 * (width / renderedWidth.value);
  const xTicks = [];
  for (let i = 0; i < rawXTicks.length; i++) {
    const tick = rawXTicks[i];
    const isLast = i === rawXTicks.length - 1;
    if (xTicks.length === 0) {
      xTicks.push(tick);
    } else if (tick.x - xTicks[xTicks.length - 1].x >= minLabelGapPx) {
      xTicks.push(tick);
    } else if (isLast) {
      xTicks[xTicks.length - 1] = tick;
    }
  }

  // Small unlabeled tick marks at every point - one per minute at the
  // firmware's actual send cadence (see telemetry.c's *_SEND_INTERVAL_MS)
  // - so the axis visibly reads as "every minute" even though most of
  // those minutes don't get a text label (see xTicks above: labeling
  // every single one would overlap into an unreadable smear at any
  // realistic card width). This is the same label/gridline split the
  // y-axis already uses - text where there's room, marks everywhere.
  const xMinorTicks = xy.map(([x]) => x);

  return { linePath: line, areaPath: area, xy, pts, yTicks, xTicks, xMinorTicks };
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
        <button :class="{ active: range === '10m' }" @click="range = '10m'">Last 10 min</button>
        <button :class="{ active: range === '1h' }" @click="range = '1h'">Last hour</button>
        <button :class="{ active: range === '24h' }" @click="range = '24h'">Last 24 hours</button>
      </div>
    </div>

    <div v-if="chartData.linePath" ref="chartShellRef" class="chart-shell">
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

        <!-- One short unlabeled tick per reading (1/minute, see xMinorTicks
             above) along the bottom edge - shows the axis's real per-minute
             granularity even though only a few of those minutes get a text
             label below (see .x-axis-label). -->
        <line
          v-for="x in chartData.xMinorTicks"
          :key="`minor-${x}`"
          :x1="x" :x2="x" :y1="height - padding" :y2="height - padding + 4"
          class="minor-tick"
        />

        <g v-if="hoverPoint">
          <line :x1="hoverPoint.x" :x2="hoverPoint.x" :y1="padding" :y2="height - padding" class="guide-line" />
          <circle :cx="hoverPoint.x" :cy="hoverPoint.y" r="4.5" :fill="color" class="guide-dot" />
        </g>
      </svg>

      <!-- X-axis time labels, same plain-HTML-overlay approach as the
           y-axis above (and for the same reason - SVG <text> would skew
           under the SVG's non-uniform preserveAspectRatio scaling). First
           and last labels anchor to their edge instead of centering so
           they don't get clipped by the chart's edges. -->
      <div class="x-axis">
        <span
          v-for="(tick, i) in chartData.xTicks"
          :key="tick.x"
          class="x-axis-label"
          :class="{ 'align-start': i === 0, 'align-end': i === chartData.xTicks.length - 1 }"
          :style="{ left: `${(tick.x / width) * 100}%` }"
        >{{ timeLabel(tick.t) }}</span>
      </div>

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

.minor-tick {
  stroke: var(--border-soft-2);
  stroke-width: 1;
  opacity: 0.8;
}

.x-axis {
  position: relative;
  height: 16px;
  margin-top: 2px;
}

.x-axis-label {
  position: absolute;
  transform: translateX(-50%);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
  white-space: nowrap;
}

.x-axis-label.align-start {
  transform: translateX(0);
}

.x-axis-label.align-end {
  transform: translateX(-100%);
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
