<script setup>
import { computed } from "vue";
import { state } from "../lib/live-state.js";
import KpiCard from "../components/KpiCard.vue";
import AreaChart from "../components/AreaChart.vue";
import AlertBanner from "../components/AlertBanner.vue";
import RingGauge from "../components/RingGauge.vue";
import ArcGauge from "../components/ArcGauge.vue";
import DotGrid from "../components/DotGrid.vue";

const power = computed(() => state.power);
const overallOk = computed(() => power.value.flag !== "abnormal");
const lastUpdate = computed(() => power.value.history.at(-1)?.t ?? 0);

const powerBars = computed(() => power.value.history.slice(-14).map((p) => {
  const t = power.value.threshold || 1;
  return Math.max(0, Math.min(1, (p.v ?? 0) / t));
}));
const pf = computed(() => power.value.extra?.powerFactor ?? 0);

/* "Total load" readout: how close current draw sits to the anomaly
 * threshold, as a percentage - a stand-in for a battery/charge-style
 * percentage since this demo kit doesn't have real energy storage to
 * report on. */
const loadRatio = computed(() => {
  const t = power.value.threshold || 1;
  return Math.max(0, Math.min(1, (power.value.value ?? 0) / t));
});
const loadPercent = computed(() => Math.round(loadRatio.value * 100));

/* Normalization constants below are purely to give the two ring gauges a
 * sensible 0..1 fill - they're not hard limits or safety thresholds, this
 * board doesn't define official max values for these two readings. */
const voltageRatio = computed(() => Math.max(0, Math.min(1, (power.value.extra?.voltage ?? 0) / 250)));
const currentRatio = computed(() => Math.max(0, Math.min(1, (power.value.extra?.current ?? 0) / 20)));

/* Readings arrive with whatever precision the board/simulator happened to
 * compute - always display exactly 2 decimal places. */
function fmt(v) {
  return typeof v === "number" ? v.toFixed(2) : "--";
}
</script>

<template>
  <div class="page">
    <AlertBanner
      :active="!overallOk"
      :updated-at="lastUpdate"
      message="Power reading is outside the normal range - check the connected load."
    />

    <section class="top-grid">
      <div class="hero-panel">
        <div class="hero-head">
          <span class="eyebrow">Energy Monitoring</span>
          <span class="status-pill" :class="{ warn: !overallOk }">{{ overallOk ? "Normal" : "Attention" }}</span>
        </div>
        <RingGauge :ratio="loadRatio" :value="`${loadPercent}%`" unit="Total load" color="var(--accent)" />
        <p class="hero-caption">Live status for the monitored circuit &mdash; {{ overallOk ? "everything's running normally." : "attention needed." }}</p>
      </div>

      <div class="right-col">
        <section class="chart-card">
          <div class="card-head">
            <h2 class="card-title">Power draw</h2>
            <span class="card-arrow" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M7 17 17 7M9 7h8v8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <AreaChart :series="power.history" unit="kW" color="var(--accent)" />
        </section>

        <div class="small-grid">
          <KpiCard label="Power factor" :value="pf.toFixed(2)" unit="">
            <ArcGauge :ratio="pf" :percent-label="pf.toFixed(2)" :value-label="`${fmt(power.value)} kW`" />
          </KpiCard>

          <KpiCard label="Load trend" :value="`${loadPercent}%`" unit="">
            <DotGrid :values="powerBars" />
          </KpiCard>
        </div>
      </div>
    </section>

    <section class="bottom-grid">
      <div class="overview-card">
        <div class="card-head">
          <h2 class="card-title">Overview</h2>
          <span class="card-arrow" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M7 17 17 7M9 7h8v8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
        <div class="overview-body">
          <div class="stat-list">
            <div class="stat">
              <span class="stat-label">Current power</span>
              <span class="stat-value">{{ fmt(power.value) }}<small>kW</small></span>
            </div>
            <div class="stat">
              <span class="stat-label">Power factor</span>
              <span class="stat-value">{{ pf.toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Voltage</span>
              <span class="stat-value">{{ fmt(power.extra.voltage) }}<small>V</small></span>
            </div>
            <div class="stat">
              <span class="stat-label">Current</span>
              <span class="stat-value">{{ fmt(power.extra.current) }}<small>A</small></span>
            </div>
          </div>
          <RingGauge :ratio="loadRatio" :value="loadPercent" unit="%" color="var(--accent)" />
        </div>
      </div>

      <div class="overview-card">
        <div class="card-head">
          <h2 class="card-title">Voltage &amp; Current</h2>
          <span class="card-arrow" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M7 17 17 7M9 7h8v8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
        <div class="overview-body">
          <div class="stat-list">
            <div class="stat">
              <span class="stat-label">Avg. voltage</span>
              <span class="stat-value">{{ fmt(power.extra.voltage) }}<small>V</small></span>
            </div>
            <div class="stat">
              <span class="stat-label">Avg. current</span>
              <span class="stat-value">{{ fmt(power.extra.current) }}<small>A</small></span>
            </div>
          </div>
          <RingGauge :ratio="voltageRatio" :value="fmt(power.extra.voltage)" unit="V" color="var(--accent-2)" />
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* The whole app is on this same light theme now (see style.css's :root) -
 * this page just wraps its content in a slightly-off-white rounded panel
 * (var(--bg), distinct from the page-level var(--page-bg) behind it and
 * from cards' var(--surface)) rather than redeclaring the palette itself. */
.page {
  background: var(--bg);
  color: var(--text);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px clamp(20px, 4vw, 48px) 56px;
}

.top-grid {
  display: grid;
  grid-template-columns: 1fr 1.35fr;
  gap: 16px;
  align-items: stretch;
}

.hero-panel {
  background: linear-gradient(155deg, var(--accent-soft), rgba(224, 181, 60, 0.16));
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-xl);
  padding: 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.hero-head {
  align-self: stretch;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.eyebrow {
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.status-pill {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: var(--surface);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-sm);
}

.status-pill.warn {
  color: var(--red);
}

.hero-caption {
  color: var(--text-muted);
  font-size: 13px;
  max-width: 260px;
}

.right-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.chart-card,
.overview-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: clamp(18px, 3vw, 26px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
}

.card-arrow {
  color: var(--text-muted);
  opacity: 0.6;
}

.small-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.overview-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.stat-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
  flex: 1;
  min-width: 160px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.stat-label {
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 600;
}

.stat-value {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.stat-value small {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-left: 2px;
}

@media (max-width: 980px) {
  .top-grid,
  .bottom-grid,
  .small-grid {
    grid-template-columns: 1fr;
  }
}
</style>
