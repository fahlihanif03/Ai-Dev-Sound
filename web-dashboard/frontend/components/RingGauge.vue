<script setup>
import { computed } from "vue";

/* Circular tick-ring gauge, matching the reference's "Overview"/rotor-hub
 * style dial: a ring of small tick marks around the edge, a colored arc
 * showing the current ratio, and a big value centered in the middle. */
const props = defineProps({
  ratio: { type: Number, default: 0 }, // 0..1
  value: { type: [String, Number], default: "--" },
  unit: { type: String, default: "" },
  color: { type: String, default: "var(--accent)" },
  tickCount: { type: Number, default: 24 },
  // Darker track for a dial sitting on a white card (the default light
  // track is for a gauge sitting on a colored/gradient hero panel, where
  // a dark track would look muddy instead of legible).
  track: { type: String, default: "var(--border-soft-2)" },
  // Soft radial glow behind the center value, like a lit gauge hub.
  glow: { type: Boolean, default: false },
});

const size = 168;
const stroke = 10;
const r = (size - stroke) / 2;
const circumference = 2 * Math.PI * r;
const clamped = computed(() => Math.max(0, Math.min(1, props.ratio)));
const dash = computed(() => clamped.value * circumference);

const ticks = computed(() => {
  const out = [];
  for (let i = 0; i < props.tickCount; i++) {
    const angle = (i / props.tickCount) * 2 * Math.PI - Math.PI / 2;
    const lit = i / props.tickCount <= clamped.value;
    const x1 = size / 2 + Math.cos(angle) * (r + stroke / 2 + 3);
    const y1 = size / 2 + Math.sin(angle) * (r + stroke / 2 + 3);
    const x2 = size / 2 + Math.cos(angle) * (r + stroke / 2 + 8);
    const y2 = size / 2 + Math.sin(angle) * (r + stroke / 2 + 8);
    out.push({ x1, y1, x2, y2, lit });
  }
  return out;
});

// The glow needs a runtime color (the `color` prop), which color-mix()
// can't take from a Tailwind class - computed here and applied via
// :style instead, same effect as the old scoped-CSS ".ring-center.glow"
// rule, just without needing a <style> block for one dynamic value.
const glowStyle = computed(() =>
  props.glow
    ? { background: `radial-gradient(circle, color-mix(in srgb, ${props.color} 22%, transparent) 0%, transparent 72%)` }
    : null
);
</script>

<template>
  <div class="relative flex items-center justify-center" :style="{ width: `${size + 20}px`, height: `${size + 20}px` }">
    <svg :viewBox="`0 0 ${size} ${size}`" :width="size" :height="size" class="overflow-visible">
      <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" :stroke="track" :stroke-width="stroke" />
      <circle
        :cx="size / 2" :cy="size / 2" :r="r" fill="none" :stroke="color" :stroke-width="stroke"
        :stroke-dasharray="`${dash} ${circumference}`"
        stroke-linecap="round"
        :transform="`rotate(-90 ${size / 2} ${size / 2})`"
      />
      <line
        v-for="(t, i) in ticks" :key="i"
        :x1="t.x1" :y1="t.y1" :x2="t.x2" :y2="t.y2"
        :stroke="t.lit ? 'var(--accent-2)' : 'var(--border-soft-2)'"
        stroke-width="1.6"
      />
    </svg>
    <div class="absolute inset-0 flex flex-col items-center justify-center gap-px rounded-full" :style="glowStyle">
      <span class="text-[22px] font-extrabold tracking-[-0.02em]">{{ value }}</span>
      <span v-if="unit" class="text-[11px] font-semibold text-[var(--text-muted)]">{{ unit }}</span>
    </div>
  </div>
</template>
