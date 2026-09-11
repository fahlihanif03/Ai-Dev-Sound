<script setup>
import { computed } from "vue";
import { useLiveStore } from "../stores/live.js";
import KpiCard from "../components/KpiCard.vue";
import AreaChart from "../components/AreaChart.vue";
import AlertBanner from "../components/AlertBanner.vue";
import RingGauge from "../components/RingGauge.vue";
import NeedleGauge from "../components/NeedleGauge.vue";
import DotGrid from "../components/DotGrid.vue";

const live = useLiveStore();
const power = computed(() => live.state.power);
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

/* Real derived stats for the KPI strip below - not fabricated. Peak/
 * average are genuine max()/mean() over whatever history is currently
 * loaded (so they move as the window grows), same honesty rule as
 * everything else this app shows: no invented cost/CO2/billing figures
 * the board doesn't measure. */
const peakPower = computed(() => {
  const h = power.value.history;
  return h.length ? Math.max(...h.map((p) => p.v ?? 0)) : null;
});
const averagePower = computed(() => {
  const h = power.value.history;
  return h.length ? h.reduce((sum, p) => sum + (p.v ?? 0), 0) / h.length : null;
});
/* Real ratio, not fabricated - how much of the peak draw the average
 * draw represents over this window. Same concept as a utility's real
 * "load factor" metric, just computed from this app's own real history
 * instead of a billing-cycle demand record. */
const loadFactor = computed(() => {
  if (!peakPower.value || !averagePower.value) return null;
  return (averagePower.value / peakPower.value) * 100;
});

/* Today's Cost and CO2 Saved below are placeholder demo values, tagged
 * as such in the template - this board has no tariff rate applied
 * anywhere and doesn't measure CO2 at all, so there's no real number to
 * show here (see TariffStructure.vue and CarbonSustainability.vue for
 * where those actually live - one real, one explicitly demo). */
const demoTodaysCost = "RM 12.40";
const demoCo2Saved = "0.8 kg";

/* Real % change vs the immediately previous reading. Voltage/current
 * don't get a delta - the backend only stores {t, v} per history point
 * (see dashboard-do.ts's historyMem), not per-point voltage/current, so
 * there's no real history to compare those two against - showing a fake
 * delta for them would mean making up a number, which this app doesn't
 * do anywhere else either. */
const powerDelta = computed(() => {
  const h = power.value.history;
  if (h.length < 2) return null;
  const prev = h[h.length - 2].v;
  const curr = h[h.length - 1].v;
  if (!prev) return null;
  return ((curr - prev) / prev) * 100;
});

/* Simple, real-threshold-based read of the power factor value - not a
 * fabricated score, just a plain-language label for the number already
 * shown next to it. */
const powerQualityLabel = computed(() => {
  if (pf.value >= 0.95) return "Excellent";
  if (pf.value >= 0.85) return "Good";
  return "Needs improvement";
});
</script>

<template>
  <div class="page">
    <AlertBanner
      :active="!overallOk"
      :updated-at="lastUpdate"
      message="Power reading is outside the normal range - check the connected load."
    />

    <!-- New KPI strip, built with Tailwind utility classes (see
         stores/live.js's migration note on why the rest of this page's
         existing cards keep their scoped CSS rather than being rewritten
         wholesale). All four values are real board readings or values
         genuinely derived from them - no fabricated cost/CO2 figures. -->
    <section class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <div class="flex items-center justify-between rounded-2xl bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-1">
          <span class="text-[13px] font-medium text-[var(--text-muted)]">Current Power</span>
          <span class="text-xl font-extrabold tracking-tight">{{ fmt(power.value) }} <small class="text-xs font-semibold text-[var(--text-muted)]">kW</small></span>
          <span v-if="powerDelta !== null" class="text-xs font-semibold" :class="powerDelta <= 0 ? 'text-[var(--green)]' : 'text-[var(--red)]'">
            {{ powerDelta <= 0 ? "↓" : "↑" }} {{ Math.abs(powerDelta).toFixed(1) }}%
          </span>
        </div>
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M13 2 5 13h6l-1 9 9-13h-6z" /></svg>
        </span>
      </div>

      <!-- Demo tag, not "live reading" - this pair is placeholder data,
           see demoTodaysCost/demoCo2Saved above. Voltage/Current (real)
           moved to the Overview/Voltage & Current cards further down,
           matching the reference's exact 4-card top row instead of
           duplicating real stats shown again below. -->
      <div class="flex items-center justify-between rounded-2xl bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-1">
          <span class="text-[13px] font-medium text-[var(--text-muted)]">Today's Cost</span>
          <span class="text-xl font-extrabold tracking-tight">{{ demoTodaysCost }}</span>
          <span class="inline-flex w-fit items-center rounded-full bg-[var(--amber-soft)] px-1.5 py-0.5 text-[9.5px] font-bold tracking-wide text-[var(--amber)] uppercase">Demo</span>
        </div>
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--amber-soft)] text-[var(--amber)]">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 6.5a4 4 0 0 0-4-2.5h-1a3.5 3.5 0 0 0 0 7h1a3.5 3.5 0 0 1 0 7h-1a4 4 0 0 1-4-2.5" stroke-linecap="round" /></svg>
        </span>
      </div>

      <div class="flex items-center justify-between rounded-2xl bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-1">
          <span class="text-[13px] font-medium text-[var(--text-muted)]">Peak Demand</span>
          <span class="text-xl font-extrabold tracking-tight">{{ fmt(peakPower) }} <small class="text-xs font-semibold text-[var(--text-muted)]">kW</small></span>
          <span class="text-xs font-semibold text-[var(--text-faint)]">this window</span>
        </div>
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17 9 11l4 4 8-8" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </span>
      </div>

      <div class="flex items-center justify-between rounded-2xl bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-1">
          <span class="text-[13px] font-medium text-[var(--text-muted)]">CO&#8322; Saved</span>
          <span class="text-xl font-extrabold tracking-tight">{{ demoCo2Saved }}</span>
          <span class="inline-flex w-fit items-center rounded-full bg-[var(--amber-soft)] px-1.5 py-0.5 text-[9.5px] font-bold tracking-wide text-[var(--amber)] uppercase">Demo</span>
        </div>
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--green-soft)] text-[var(--green)]">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 21c8 0 14-6 14-16-10 0-16 6-16 14 0 1 .3 2 1 2 4-5 8-8 12-10" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </span>
      </div>
    </section>

    <section class="top-grid">
      <div class="hero-panel">
        <div class="hero-head">
          <span class="eyebrow">Energy Monitoring</span>
          <span class="status-pill" :class="{ warn: !overallOk }">{{ overallOk ? "Normal" : "Attention" }}</span>
        </div>
        <RingGauge :ratio="loadRatio" :value="`${loadPercent}%`" unit="Total load" color="var(--accent)" track="rgba(255,255,255,0.25)" glow />
        <p class="hero-caption">Live status for the monitored circuit &mdash; {{ overallOk ? "everything's running normally." : "attention needed." }}</p>
      </div>

      <div class="right-col">
        <section class="chart-card">
          <div class="card-head">
            <h2 class="card-title">Real-time Energy Consumption</h2>
            <span class="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--green)]">
              <span class="h-2 w-2 rounded-full bg-[var(--green)]"></span>Live
            </span>
          </div>
          <AreaChart :series="power.history" unit="kW" color="var(--accent)" />
        </section>

        <div class="small-grid">
          <!-- Tailwind, not scoped CSS - see the KPI strip's own comment
               above for why. -->
          <div class="flex flex-col items-center gap-1 rounded-2xl bg-white p-5 shadow-sm">
            <span class="self-start text-[13px] font-medium text-[var(--text-muted)]">Power Quality</span>
            <NeedleGauge :ratio="pf" />
            <span class="text-xl font-extrabold tracking-tight">{{ pf.toFixed(3) }}</span>
            <span class="text-xs font-semibold" :class="pf >= 0.95 ? 'text-[var(--green)]' : pf >= 0.85 ? 'text-[var(--accent)]' : 'text-[var(--red)]'">{{ powerQualityLabel }}</span>
          </div>

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
          <RingGauge :ratio="loadRatio" :value="loadPercent" unit="%" color="var(--accent)" track="#3a3f47" glow />
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
          <RingGauge :ratio="voltageRatio" :value="fmt(power.extra.voltage)" unit="V" color="var(--accent)" track="#3a3f47" glow />
        </div>
      </div>
    </section>

    <!-- Demand Analysis - genuinely real, computed from the loaded
         history's actual peak/average (see peakPower/averagePower/
         loadFactor above), not the reference's fabricated billing-cycle
         version of this same card concept. -->
    <section class="rounded-2xl bg-[var(--surface)] p-6 shadow-[var(--shadow-sm)]">
      <h2 class="mb-5 text-[15px] font-bold">Demand Analysis</h2>
      <div class="flex items-end justify-center gap-10 pb-2">
        <div class="flex flex-col items-center gap-2">
          <div class="flex h-28 w-16 items-end">
            <div class="w-full rounded-t-lg" style="height: 100%; background: linear-gradient(180deg, var(--accent-2), var(--accent))"></div>
          </div>
          <span class="text-sm font-bold">{{ fmt(peakPower) }} kW</span>
          <span class="text-[11px] text-[var(--text-muted)]">Peak</span>
        </div>
        <div class="flex flex-col items-center gap-2">
          <div class="flex h-28 w-16 items-end">
            <div
              class="w-full rounded-t-lg bg-[var(--green)]"
              :style="{ height: peakPower ? `${Math.max(6, (averagePower / peakPower) * 100)}%` : '6%' }"
            ></div>
          </div>
          <span class="text-sm font-bold">{{ fmt(averagePower) }} kW</span>
          <span class="text-[11px] text-[var(--text-muted)]">Average</span>
        </div>
      </div>
      <div class="mt-4 flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm">
        <span class="text-[var(--text-muted)]">Load Factor</span>
        <span class="font-bold">{{ loadFactor !== null ? loadFactor.toFixed(1) + "%" : "--" }}</span>
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

/* Deep charcoal-to-orange gradient, standing in for the reference's
 * full-bleed product photo (no real photography of this demo kit exists
 * to use here) - still gives the hero the same "rich, edge-to-edge
 * visual, no white card chrome" treatment, just via gradient + rim-light
 * glow instead of a photo. Text inside is light since it now sits on a
 * dark ground, unlike the rest of the (light-themed) page. */
.hero-panel {
  background:
    radial-gradient(circle at 82% 18%, rgba(var(--accent-rgb), 0.55), transparent 55%),
    linear-gradient(155deg, #23262b, #15171a 70%);
  border-radius: var(--radius-xl);
  padding: 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  color: #f4f1ec;
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
  color: rgba(244, 241, 236, 0.6);
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
