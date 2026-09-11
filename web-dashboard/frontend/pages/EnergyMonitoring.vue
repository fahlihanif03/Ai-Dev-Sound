<script setup>
import { computed } from "vue";
import { state } from "../lib/live-state.js";
import KpiCard from "../components/KpiCard.vue";
import MiniBars from "../components/MiniBars.vue";
import MiniDonut from "../components/MiniDonut.vue";
import AreaChart from "../components/AreaChart.vue";
import AlertBanner from "../components/AlertBanner.vue";

const power = computed(() => state.power);
const overallOk = computed(() => power.value.flag !== "abnormal");
const lastUpdate = computed(() => power.value.history.at(-1)?.t ?? 0);

const powerBars = computed(() => power.value.history.slice(-10).map((p) => p.v));
const currentBars = computed(() => power.value.history.slice(-10).map((p) => p.extra?.current ?? 0));
const voltageBars = computed(() => power.value.history.slice(-10).map((p) => p.extra?.voltage ?? 0));
const pf = computed(() => power.value.extra?.powerFactor ?? 0);

/* "Total load" readout on the hero card: how close current draw sits to
 * the anomaly threshold, as a percentage - a stand-in for a battery/
 * charge-style percentage since this demo kit doesn't have real energy
 * storage to report on. */
const loadPercent = computed(() => {
  const t = power.value.threshold || 1;
  return Math.round(Math.min(100, ((power.value.value ?? 0) / t) * 100));
});

/* Readings arrive with whatever precision the board/simulator happened to
 * compute - always display exactly 2 decimal places. */
function fmt(v) {
  return typeof v === "number" ? v.toFixed(2) : "--";
}
</script>

<template>
  <div class="page">
    <section class="hero">
      <div class="hero-text">
        <span class="eyebrow">Energy Monitoring</span>
        <h1 class="headline">Here&rsquo;s Your Current <span class="accent-text">Power Overview</span></h1>
        <p class="sub">Live status for the monitored circuit &mdash; {{ overallOk ? "everything's running normally." : "attention needed." }}</p>
      </div>

      <div class="hero-visual">
        <div class="badge-cluster">
          <div class="stat-badge stat-badge-primary">
            <span class="stat-badge-value">{{ loadPercent }}%</span>
            <span class="stat-badge-label">Total load</span>
          </div>
          <div class="stat-badge stat-badge-secondary">
            <span class="stat-badge-value">{{ pf.toFixed(2) }}</span>
            <span class="stat-badge-label">Power factor</span>
          </div>
        </div>

        <div class="floating-card">
          <div class="floating-row">
            <span class="floating-label">Total load</span>
            <span class="floating-badge" :class="{ warn: !overallOk }">{{ overallOk ? "Normal" : "Attention" }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: loadPercent + '%' }"></div>
          </div>
          <span class="progress-value">{{ loadPercent }}%</span>
        </div>
      </div>
    </section>

    <AlertBanner
      :active="!overallOk"
      :updated-at="lastUpdate"
      message="Power reading is outside the normal range - check the connected load."
    />

    <section class="kpi-grid">
      <KpiCard label="Current power" :value="fmt(power.value)" unit="kW" :flag="power.flag">
        <MiniBars :values="powerBars" />
      </KpiCard>

      <KpiCard label="Power factor" :value="pf.toFixed(2)" unit="" :flag="power.flag">
        <div class="donut-row">
          <MiniDonut :ratio="pf" />
          <div class="donut-legend">
            <span><i class="dot dot-a"></i>Reactive</span>
            <span><i class="dot dot-b"></i>Real</span>
          </div>
        </div>
      </KpiCard>

      <KpiCard label="Voltage" :value="fmt(power.extra.voltage)" unit="V" flag="normal">
        <MiniBars :values="voltageBars" />
      </KpiCard>

      <KpiCard label="Current" :value="fmt(power.extra.current)" unit="A" flag="normal">
        <MiniBars :values="currentBars" />
      </KpiCard>
    </section>

    <section class="chart-card">
      <h2 class="card-title">Power draw</h2>
      <AreaChart :series="power.history" unit="kW" color="var(--accent)" />
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
  gap: 24px;
  padding: 8px clamp(20px, 4vw, 48px) 56px;
}

.hero {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  align-items: center;
  gap: 32px;
  padding: 8px 4px 16px;
}

.hero-text {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.eyebrow {
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.headline {
  font-size: clamp(32px, 4.2vw, 46px);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.accent-text {
  color: var(--accent-2);
  font-weight: 800;
}

.sub {
  color: var(--text-muted);
  font-size: 15px;
  max-width: 380px;
}

.hero-visual {
  position: relative;
  height: 300px;
  border-radius: var(--radius-xl);
  background: linear-gradient(155deg, var(--accent-soft), rgba(224, 181, 60, 0.16));
  border: 1px solid var(--border-soft);
  overflow: hidden;
}

.badge-cluster {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 22px;
}

.stat-badge {
  width: 128px;
  height: 128px;
  border-radius: 50%;
  background: var(--surface);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  text-align: center;
}

.stat-badge-primary {
  width: 152px;
  height: 152px;
  border: 3px solid var(--accent);
}

.stat-badge-secondary {
  border: 3px solid var(--accent-2);
  margin-top: 36px;
}

.stat-badge-value {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.stat-badge-primary .stat-badge-value {
  font-size: 28px;
}

.stat-badge-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.floating-card {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 180px;
  background: var(--surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.floating-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.floating-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.floating-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 3px 8px;
  border-radius: var(--radius-pill);
}

.floating-badge.warn {
  color: var(--red);
  background: var(--red-soft);
}

.progress-track {
  height: 8px;
  border-radius: var(--radius-pill);
  background: var(--surface-2);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--accent-grad);
  transition: width 0.4s ease;
}

.progress-value {
  font-size: 20px;
  font-weight: 800;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 16px;
}

.donut-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.donut-legend span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}

.dot-a {
  background: var(--accent-2);
}

.dot-b {
  background: var(--accent);
}

.chart-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: clamp(20px, 3vw, 32px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
}

@media (max-width: 860px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero-visual {
    order: -1;
    height: 240px;
  }
}
</style>
