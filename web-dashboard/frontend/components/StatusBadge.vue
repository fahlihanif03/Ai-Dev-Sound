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

function fmt(v) {
  return typeof v === "number" ? v.toFixed(2) : v;
}
</script>

<template>
  <span
    class="badge"
    :class="offline ? 'offline' : flag"
    :title="!offline && threshold !== null ? `Reading: ${fmt(value)}${unit} · Threshold: ${fmt(threshold)}${unit}` : offline ? 'No data received recently - showing the last known reading' : ''"
  >
    <span class="dot"></span>
    {{ label }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: default;
  background: var(--accent-soft);
  color: var(--accent);
}

.badge.abnormal {
  background: var(--amber-soft);
  color: var(--amber);
}

.badge.offline {
  background: var(--surface-2);
  color: var(--text-muted);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>
