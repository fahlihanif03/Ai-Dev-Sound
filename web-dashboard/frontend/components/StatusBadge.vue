<script setup>
import { computed } from "vue";

const props = defineProps({
  flag: { type: String, default: "normal" }, // "normal" | "abnormal"
  value: { type: [Number, String], default: null },
  unit: { type: String, default: "" },
  threshold: { type: [Number, String], default: null },
  // True once this channel has previously sent real data and has now gone
  // quiet for a while (see backend/dashboard-do.ts's REAL_DATA_GRACE_MS).
  // Takes priority over flag - a stale abnormal/normal reading from before
  // the channel went dark isn't trustworthy enough to keep showing as live.
  offline: { type: Boolean, default: false },
});

const label = computed(() => (props.offline ? "Offline" : props.flag === "abnormal" ? "Attention" : "Normal"));

const colorClasses = computed(() => {
  if (props.offline) return "bg-[var(--surface-2)] text-[var(--text-muted)]";
  if (props.flag === "abnormal") return "bg-[var(--amber-soft)] text-[var(--amber)]";
  return "bg-[var(--accent-soft)] text-[var(--accent)]";
});

function fmt(v) {
  return typeof v === "number" ? v.toFixed(2) : v;
}
</script>

<template>
  <span
    class="inline-flex cursor-default items-center gap-1.5 rounded-[var(--radius-pill)] px-3 py-[5px] text-xs font-semibold tracking-[0.01em]"
    :class="colorClasses"
    :title="!offline && threshold !== null ? `Reading: ${fmt(value)}${unit} · Threshold: ${fmt(threshold)}${unit}` : offline ? 'No data received recently - showing the last known reading' : ''"
  >
    <span class="h-1.5 w-1.5 rounded-full bg-current"></span>
    {{ label }}
  </span>
</template>
