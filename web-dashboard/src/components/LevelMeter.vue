<script setup>
import { computed } from "vue";

/* VU-meter style level display. The board reports a unitless
 * reconstruction-error score, not a calibrated sound-pressure level, so
 * this maps it onto a dB-like scale via a log curve for a familiar
 * "audio meter" read rather than claiming a calibrated SPL measurement -
 * flagged honestly in the caption. */
const props = defineProps({
  value: { type: Number, default: 0 },
  history: { type: Array, default: () => [] },
  threshold: { type: Number, default: 1 },
});

const BAR_COUNT = 20;

function toScaledDb(v) {
  // maps score 0..~3x threshold onto a 0..100 "dB-ish" scale
  const ratio = Math.max(0.001, v / (props.threshold || 1));
  const db = 40 + 20 * Math.log10(ratio + 0.1) * 2.2;
  return Math.max(0, Math.min(100, db));
}

const currentDb = computed(() => toScaledDb(props.value));
const litBars = computed(() => Math.round((currentDb.value / 100) * BAR_COUNT));

const barTrail = computed(() => {
  const recent = props.history.slice(-BAR_COUNT);
  const padded = new Array(Math.max(0, BAR_COUNT - recent.length)).fill(0).concat(recent.map((p) => toScaledDb(p.v)));
  return padded;
});
</script>

<template>
  <div class="level-meter">
    <div class="level-readout">
      <span class="level-value">{{ currentDb.toFixed(0) }}</span>
      <span class="level-unit">dB (scaled)</span>
    </div>
    <div class="bars">
      <span
        v-for="(db, i) in barTrail"
        :key="i"
        class="bar"
        :class="{ hot: db > 70, warm: db > 45 && db <= 70 }"
        :style="{ height: Math.max(4, db) + '%' }"
      ></span>
    </div>
    <span class="level-caption">Scaled from the anomaly score, not a calibrated SPL reading</span>
  </div>
</template>

<style scoped>
.level-meter {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.level-readout {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.level-value {
  font-size: 22px;
  font-weight: 800;
}

.level-unit {
  font-size: 11px;
  color: var(--text-muted);
}

.bars {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 56px;
  background: var(--stage);
  border-radius: 10px;
  padding: 6px 8px;
}

.bar {
  flex: 1;
  min-height: 4px;
  border-radius: 2px;
  background: #4a4d54;
}

.bar.warm {
  background: var(--accent-2);
}

.bar.hot {
  background: var(--accent);
}

.level-caption {
  font-size: 10.5px;
  color: var(--text-muted);
}
</style>
