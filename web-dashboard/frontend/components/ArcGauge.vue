<script setup>
import { computed } from "vue";

/* Bottom-half arc progress, matching the reference's "Total Energy
 * Generated" style card: a big percent readout, a gradient half-donut
 * arc beneath it, and a value label centered under the arc. */
const props = defineProps({
  ratio: { type: Number, default: 0 }, // 0..1
  percentLabel: { type: String, default: "" }, // e.g. "82%" - defaults to ratio if omitted
  valueLabel: { type: String, default: "" }, // e.g. "18.4 kWh"
});

const width = 220;
const height = 110;
const stroke = 14;
const r = width / 2 - stroke;
const cx = width / 2;
const cy = height;
const halfCircumference = Math.PI * r;

const clamped = computed(() => Math.max(0, Math.min(1, props.ratio)));
const dash = computed(() => clamped.value * halfCircumference);
const displayPercent = computed(() => props.percentLabel || `${Math.round(clamped.value * 100)}%`);

// Semicircle path from left to right, arcing over the top.
const arcPath = `M ${stroke / 2} ${cy} A ${r} ${r} 0 0 1 ${width - stroke / 2} ${cy}`;
</script>

<template>
  <div class="arc-gauge">
    <span class="arc-percent">{{ displayPercent }}</span>
    <svg :viewBox="`0 0 ${width} ${height}`" :width="width" :height="height" class="arc-svg">
      <defs>
        <linearGradient id="arcGradient" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="var(--accent)" />
          <stop offset="100%" stop-color="var(--accent-2)" />
        </linearGradient>
      </defs>
      <path :d="arcPath" fill="none" stroke="var(--border-soft-2)" :stroke-width="stroke" stroke-linecap="round" />
      <path
        :d="arcPath" fill="none" stroke="url(#arcGradient)" :stroke-width="stroke" stroke-linecap="round"
        :stroke-dasharray="`${dash} ${halfCircumference}`"
      />
    </svg>
    <span v-if="valueLabel" class="arc-value">{{ valueLabel }}</span>
  </div>
</template>

<style scoped>
.arc-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.arc-percent {
  align-self: flex-start;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.arc-svg {
  display: block;
  margin-top: -4px;
}

.arc-value {
  margin-top: -18px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-muted);
}
</style>
