<script setup>
import { computed } from "vue";

const props = defineProps({
  ratio: { type: Number, default: 0.5 }, // 0..1, share of the first segment
});

const size = 84;
const stroke = 9;
const r = (size - stroke) / 2;
const circumference = 2 * Math.PI * r;

const seg1 = computed(() => Math.max(0, Math.min(1, props.ratio)) * circumference);
const seg2 = computed(() => circumference - seg1.value);
</script>

<template>
  <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="block">
    <circle
      :cx="size / 2" :cy="size / 2" :r="r"
      fill="none" stroke="var(--accent-2)" :stroke-width="stroke"
      :stroke-dasharray="`${seg2} ${circumference}`"
      :stroke-dashoffset="-seg1"
      stroke-linecap="round"
      :transform="`rotate(-90 ${size / 2} ${size / 2})`"
    />
    <circle
      :cx="size / 2" :cy="size / 2" :r="r"
      fill="none" stroke="var(--accent)" :stroke-width="stroke"
      :stroke-dasharray="`${seg1} ${circumference}`"
      stroke-linecap="round"
      :transform="`rotate(-90 ${size / 2} ${size / 2})`"
    />
  </svg>
</template>
