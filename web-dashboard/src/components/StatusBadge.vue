<script setup>
import { computed } from "vue";

const props = defineProps({
  flag: { type: String, default: "normal" }, // "normal" | "abnormal"
  value: { type: [Number, String], default: null },
  unit: { type: String, default: "" },
  threshold: { type: [Number, String], default: null },
});

const label = computed(() => (props.flag === "abnormal" ? "Attention" : "Normal"));
</script>

<template>
  <span class="badge" :class="flag" :title="threshold !== null ? `Reading: ${value}${unit} · Threshold: ${threshold}${unit}` : ''">
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

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>
