<script setup>
import { computed, ref } from "vue";
import { useLiveStore } from "../stores/live.js";
import DeviceIllustration from "../components/DeviceIllustration.vue";
import StatusBadge from "../components/StatusBadge.vue";
import Spectrogram from "../components/Spectrogram.vue";
import LevelMeter from "../components/LevelMeter.vue";
import AreaChart from "../components/AreaChart.vue";
import AlertBanner from "../components/AlertBanner.vue";
import PowerToggle from "../components/PowerToggle.vue";

const live = useLiveStore();
const sound = computed(() => live.state.sound);
const temperature = computed(() => live.state.temperature);

/* Board / per-signal power toggles. These are display-layer only: the
 * bridge scripts and firmware keep running and reporting regardless -
 * there's no remote-control channel back to the hardware in this demo kit.
 * Turning a signal "off" here just stops showing/implying a live reading
 * for it in the browser; it never reaches the board. */
const boardOn = ref(true);
const audioOn = ref(true);
const tempOn = ref(true);

const audioEffective = computed(() => boardOn.value && audioOn.value);
const tempEffective = computed(() => boardOn.value && tempOn.value);

// A channel that's gone offline keeps whatever flag/value it last had
// before going quiet (see dashboard-do.ts's announceOffline()) - that's
// stale, not a live problem, so it's excluded from the abnormal/alert
// checks below rather than double-counted as both offline and attention.
const soundOffline = computed(() => audioEffective.value && sound.value.offline);
const tempOffline = computed(() => tempEffective.value && temperature.value.offline);
const anyOffline = computed(() => soundOffline.value || tempOffline.value);

const overallOk = computed(() => {
  if (!boardOn.value) return true;
  const soundBad = audioEffective.value && !sound.value.offline && sound.value.flag === "abnormal";
  const tempBad = tempEffective.value && !temperature.value.offline && temperature.value.flag === "abnormal";
  return !soundBad && !tempBad;
});

const topStatus = computed(() => {
  if (!boardOn.value) return "Board off";
  if (anyOffline.value) return "Offline";
  return overallOk.value ? "Normal" : "Attention";
});

const alertMessage = computed(() => {
  const bad = [];
  if (audioEffective.value && !sound.value.offline && sound.value.flag === "abnormal") bad.push("sound");
  if (tempEffective.value && !temperature.value.offline && temperature.value.flag === "abnormal") bad.push("temperature");
  if (bad.length === 0) return "";
  return `${bad.join(" and ")} reading${bad.length > 1 ? "s are" : " is"} outside the normal range.`;
});

const lastUpdate = computed(() =>
  Math.max(sound.value.history.at(-1)?.t ?? 0, temperature.value.history.at(-1)?.t ?? 0)
);

const tempSeries = computed(() => temperature.value.history);

/* Readings arrive with whatever precision the board/simulator happened to
 * compute (e.g. 70.7417) - always display exactly 2 decimal places. */
function fmt(v) {
  return typeof v === "number" ? v.toFixed(2) : "--";
}

const pulse = ref(false);
const showReadout = ref(false);
function onCaseSelect() {
  if (!boardOn.value) return;
  showReadout.value = !showReadout.value;
  pulse.value = false;
  requestAnimationFrame(() => {
    pulse.value = true;
    setTimeout(() => (pulse.value = false), 700);
  });
}
</script>

<template>
  <div class="page">
    <div class="topbar">
      <div class="topbar-left">
        <span class="eyebrow">Predictive Maintenance</span>
        <span class="status-pill" :class="{ warn: boardOn && !anyOffline && !overallOk, offline: boardOn && anyOffline }">{{ topStatus }}</span>
      </div>
      <PowerToggle v-model="boardOn" on-label="Board on" off-label="Board off" />
    </div>

    <AlertBanner :active="boardOn && !overallOk" :updated-at="lastUpdate" :message="alertMessage" />

    <section class="layout" :class="{ paused: !boardOn }">
      <div class="cards-col" :class="{ pulse }">
        <div class="signal-card" :class="{ dim: !audioEffective }">
          <div class="signal-head">
            <h2 class="card-title">Sound</h2>
            <div class="head-right">
              <StatusBadge v-if="audioEffective" :flag="sound.flag" :value="sound.value" unit="" :threshold="sound.threshold" :offline="sound.offline" />
              <PowerToggle v-model="audioOn" size="sm" :disabled="!boardOn" on-label="On" off-label="Off" />
            </div>
          </div>

          <template v-if="audioEffective">
            <div class="signal-value-row">
              <span class="signal-value">{{ fmt(sound.value) }}</span>
              <span class="signal-unit">anomaly score</span>
            </div>
            <div class="chart-row">
              <div class="chart-col wide">
                <span class="chart-label">Spectrogram</span>
                <Spectrogram :history="sound.history" />
              </div>
              <div class="chart-col">
                <span class="chart-label">Level</span>
                <LevelMeter :value="sound.value ?? 0" :history="sound.history" :threshold="sound.threshold || 1" />
              </div>
            </div>
          </template>
          <div v-else class="off-state">Sound monitoring is off</div>
        </div>

        <div class="signal-card" :class="{ dim: !tempEffective }">
          <div class="signal-head">
            <h2 class="card-title">Temperature</h2>
            <div class="head-right">
              <StatusBadge v-if="tempEffective" :flag="temperature.flag" :value="temperature.value" unit="&deg;C" :threshold="temperature.threshold" :offline="temperature.offline" />
              <PowerToggle v-model="tempOn" size="sm" :disabled="!boardOn" on-label="On" off-label="Off" />
            </div>
          </div>

          <template v-if="tempEffective">
            <div class="signal-value-row">
              <span class="signal-value">{{ fmt(temperature.value) }}</span>
              <span class="signal-unit">&deg;C</span>
            </div>
            <AreaChart :series="tempSeries" unit="&deg;C" color="var(--accent)" />
          </template>
          <div v-else class="off-state">Temperature monitoring is off</div>
        </div>
      </div>

      <div class="pc-col">
        <DeviceIllustration @select="onCaseSelect" />

        <Transition name="pop">
          <div v-if="showReadout" class="readout-card">
            <div class="readout-row">
              <span class="readout-label">Temperature</span>
              <StatusBadge v-if="tempEffective" :flag="temperature.flag" :value="temperature.value" unit="&deg;C" :threshold="temperature.threshold" :offline="temperature.offline" />
            </div>
            <span class="readout-value">
              <template v-if="tempEffective">{{ fmt(temperature.value) }}&deg;C</template>
              <template v-else>Off</template>
            </span>

            <div class="readout-divider"></div>

            <div class="readout-row">
              <span class="readout-label">Sound</span>
              <StatusBadge v-if="audioEffective" :flag="sound.flag" :value="sound.value" unit="" :threshold="sound.threshold" :offline="sound.offline" />
            </div>
            <span class="readout-value small">
              <template v-if="audioEffective">{{ fmt(sound.value) }}</template>
              <template v-else>Off</template>
            </span>
          </div>
          <button v-else class="hint-pill" type="button" @click="onCaseSelect">
            Click the PC to see the temperature
          </button>
        </Transition>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* The whole app is on this same light theme now (see style.css's :root),
 * --stage/--stage-2 included - those stay dark globally on purpose, so
 * the device illustration below keeps its dark "stage" backdrop even
 * though everything around it is light, mirroring how Energy
 * Monitoring's own hero panel stays a distinct accent-colored panel
 * rather than plain white. This page just wraps its content in the
 * same slightly-off-white rounded panel Energy Monitoring uses
 * (var(--bg), distinct from var(--page-bg) behind it). */
.page {
  background: var(--bg);
  color: var(--text);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 8px clamp(20px, 4vw, 48px) 56px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.eyebrow {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.status-pill {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 4px 12px;
  border-radius: var(--radius-pill);
}

.status-pill.warn {
  color: var(--red);
  background: var(--red-soft);
}

.status-pill.offline {
  color: var(--text-muted);
  background: var(--surface-2);
}

.layout {
  display: grid;
  grid-template-columns: 1fr 1.05fr;
  gap: 18px;
  align-items: stretch;
  transition: opacity 0.25s ease;
  min-width: 0;
}

.layout.paused {
  opacity: 0.5;
}

.cards-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.cards-col.pulse .signal-card {
  animation: card-pulse 0.7s ease;
}

@keyframes card-pulse {
  /* rgba(var(--accent-rgb)), not a hardcoded orange triplet - this page
   * now runs a green/gold light theme (see .page above), and the old
   * hardcoded orange no longer matches --accent. */
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.4); }
  60% { box-shadow: 0 0 0 10px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}

.signal-card {
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  transition: opacity 0.2s ease;
}

.signal-card.dim {
  opacity: 0.7;
}

.signal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.head-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-title {
  font-size: 14.5px;
  font-weight: 700;
}

.signal-value-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.signal-value {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.signal-unit {
  font-size: 13px;
  color: var(--text-muted);
}

.chart-row {
  display: flex;
  gap: 14px;
  min-width: 0;
}

.chart-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.chart-col.wide {
  flex: 2;
}

.chart-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.off-state {
  padding: 28px 0;
  text-align: center;
  color: var(--text-faint);
  font-size: 13px;
  border: 1px dashed var(--border-soft-2);
  border-radius: var(--radius-md);
}

.pc-col {
  position: relative;
  border-radius: var(--radius-xl);
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 30%, rgba(255, 138, 61, 0.18), transparent 58%),
    radial-gradient(circle at 50% 45%, var(--stage-2) 0%, var(--stage) 68%, #060607 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), var(--shadow);
  min-height: 420px;
  min-width: 0;
}

.readout-card {
  position: absolute;
  right: 16px;
  bottom: 16px;
  width: 200px;
  background: rgba(24, 25, 28, 0.88);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-soft-2);
  border-radius: var(--radius-md);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: var(--shadow);
}

.readout-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.readout-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.readout-value {
  font-size: 24px;
  font-weight: 800;
}

.readout-value.small {
  font-size: 20px;
}

.readout-divider {
  height: 1px;
  background: var(--border-soft);
  margin: 2px 0;
}

.hint-pill {
  position: absolute;
  right: 16px;
  bottom: 16px;
  border: 1px solid var(--border-soft-2);
  background: rgba(24, 25, 28, 0.88);
  backdrop-filter: blur(10px);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  padding: 10px 16px;
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow);
  cursor: pointer;
  animation: pulse-hint 2.2s ease-in-out infinite;
}

@keyframes pulse-hint {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.04); }
}

.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: scale(0.92);
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .pc-col {
    order: -1;
    min-height: 320px;
  }
  .chart-row {
    flex-direction: column;
  }
}
</style>
