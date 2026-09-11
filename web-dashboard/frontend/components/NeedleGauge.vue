<script setup>
import { computed } from "vue";

/* Semicircle needle speedometer, matching the reference's "Power Quality"
 * dial: a fixed arc track, a needle rotating to the current ratio, and a
 * value + qualitative label beneath. Built with Tailwind for layout (new
 * component - see stores/live.js's migration note on why older
 * components keep their existing scoped CSS instead of being rewritten
 * wholesale) and inline SVG for the dial itself. */
const props = defineProps({
  ratio: { type: Number, default: 0 }, // 0..1
});

const width = 140;
const height = 74;
const r = 58;
const cx = width / 2;
const cy = height;

const clamped = computed(() => Math.max(0, Math.min(1, props.ratio)));
// 0 -> pointing left (180deg), 1 -> pointing right (0deg)
const needleAngle = computed(() => Math.PI - clamped.value * Math.PI);
const needleTip = computed(() => ({
  x: cx + Math.cos(needleAngle.value) * (r - 12),
  y: cy - Math.sin(needleAngle.value) * (r - 12),
}));

const trackPath = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" :width="width" :height="height" class="overflow-visible">
    <path :d="trackPath" fill="none" stroke="var(--border-soft-2)" stroke-width="9" stroke-linecap="round" />
    <line :x1="cx" :y1="cy" :x2="needleTip.x" :y2="needleTip.y" stroke="var(--accent)" stroke-width="3" stroke-linecap="round" />
    <circle :cx="cx" :cy="cy" r="4.5" fill="var(--accent)" />
  </svg>
</template>
