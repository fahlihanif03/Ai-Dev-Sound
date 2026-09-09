<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: "--" },
  unit: { type: String, default: "" },
  flag: { type: String, default: "normal" },
});
</script>

<template>
  <div class="kpi-card">
    <div class="kpi-head">
      <span class="kpi-label">{{ label }}</span>
      <span class="kpi-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M7 17 17 7M9 7h8v8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
    </div>

    <div class="kpi-value-row">
      <span class="kpi-value">{{ value }}</span>
      <span class="kpi-unit">{{ unit }}</span>
      <span class="kpi-dot" :class="flag"></span>
    </div>

    <div class="kpi-chart">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.kpi-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.kpi-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kpi-label {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.kpi-arrow {
  color: var(--text-muted);
  opacity: 0.6;
}

.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.kpi-unit {
  font-size: 13px;
  color: var(--text-muted);
}

.kpi-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  margin-left: 2px;
}

.kpi-dot.abnormal {
  background: var(--red);
}

.kpi-chart {
  margin-top: auto;
}
</style>
