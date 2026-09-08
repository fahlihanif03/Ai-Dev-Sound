<script setup>
import { computed } from "vue";

const props = defineProps({
  points: { type: Array, default: () => [] }, // array of numbers
  color: { type: String, default: "var(--accent)" },
});

const width = 160;
const height = 40;

const path = computed(() => {
  const vals = props.points;
  if (vals.length < 2) return "";
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const step = width / (vals.length - 1);
  return vals
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / range) * (height - 6) - 3;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
});
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="sparkline" preserveAspectRatio="none">
    <path :d="path" fill="none" :stroke="color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>

<style scoped>
.sparkline {
  width: 100%;
  height: 40px;
  display: block;
}
</style>
