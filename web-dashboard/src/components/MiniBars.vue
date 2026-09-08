<script setup>
import { computed } from "vue";

const props = defineProps({
  values: { type: Array, default: () => [] },
  highlightIndex: { type: Number, default: -1 }, // -1 = highlight the last bar
});

const bars = computed(() => {
  const vals = props.values.length ? props.values : [0.2, 0.4, 0.3, 0.6, 0.5, 0.8, 0.4, 0.7, 0.5, 0.9];
  const max = Math.max(...vals, 0.001);
  const hi = props.highlightIndex === -1 ? vals.length - 1 : props.highlightIndex;
  return vals.map((v, i) => ({ h: Math.max(6, (v / max) * 100), active: i === hi }));
});
</script>

<template>
  <div class="mini-bars">
    <span v-for="(b, i) in bars" :key="i" class="bar" :class="{ active: b.active }" :style="{ height: b.h + '%' }"></span>
  </div>
</template>

<style scoped>
.mini-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 44px;
}

.bar {
  flex: 1;
  min-width: 3px;
  border-radius: 4px;
  background: var(--border-soft);
}

.bar.active {
  background: var(--accent-grad);
}
</style>
