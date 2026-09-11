<script setup>
import { computed } from "vue";

/* Dot-matrix bar chart, matching the reference's "System Efficiency"
 * card: each column is a stack of dots, lit from the bottom up to that
 * column's value - a dotted alternative to MiniBars' solid bars. */
const props = defineProps({
  values: { type: Array, default: () => [] }, // 0..1 per column
  rows: { type: Number, default: 6 },
});

const columns = computed(() => {
  const vals = props.values.length ? props.values : new Array(14).fill(0).map((_, i) => (Math.sin(i) + 1) / 2);
  return vals.map((v) => {
    const lit = Math.round(Math.max(0, Math.min(1, v)) * props.rows);
    return new Array(props.rows).fill(0).map((_, i) => i >= props.rows - lit);
  });
});
</script>

<template>
  <div class="dot-grid">
    <div v-for="(col, ci) in columns" :key="ci" class="dot-col">
      <span v-for="(lit, ri) in col" :key="ri" class="dot" :class="{ lit }"></span>
    </div>
  </div>
</template>

<style scoped>
.dot-grid {
  display: flex;
  align-items: flex-end;
  gap: 5px;
  height: 44px;
}

.dot-col {
  display: flex;
  flex-direction: column-reverse;
  gap: 3px;
  flex: 1;
}

.dot {
  width: 100%;
  aspect-ratio: 1;
  min-width: 3px;
  border-radius: 50%;
  background: var(--border-soft-2);
}

.dot.lit {
  background: var(--accent-2);
}
</style>
