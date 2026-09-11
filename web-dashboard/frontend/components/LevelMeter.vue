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
  <div class="flex flex-col gap-2">
    <div class="flex items-baseline gap-1.5">
      <span class="text-[22px] font-extrabold">{{ currentDb.toFixed(0) }}</span>
      <span class="text-[11px] text-[var(--text-muted)]">dB (scaled)</span>
    </div>
    <div class="flex h-14 items-end gap-[3px] rounded-[10px] bg-[var(--stage)] px-2 py-1.5">
      <span
        v-for="(db, i) in barTrail"
        :key="i"
        class="min-h-1 flex-1 rounded-sm"
        :class="db > 70 ? 'bg-[var(--accent)]' : db > 45 ? 'bg-[var(--accent-2)]' : 'bg-[#4a4d54]'"
        :style="{ height: Math.max(4, db) + '%' }"
      ></span>
    </div>
    <span class="text-[10.5px] text-[var(--text-muted)]">Scaled from the anomaly score, not a calibrated SPL reading</span>
  </div>
</template>
