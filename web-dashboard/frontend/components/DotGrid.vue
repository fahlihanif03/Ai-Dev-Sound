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
  <!-- overflow-hidden as a hard backstop, but the real fix is capping
       each dot's own size (max-w-[9px], not w-full): with few columns
       (e.g. right after the board reconnects and there's only a
       history point or two), flex-1 makes each column very wide, and
       since dots are aspect-square (height follows width), an
       uncapped w-full dot would balloon way past this container's
       fixed 44px height and spill into whatever sits above the card -
       confirmed live with a 2-3-point history, not just a screenshot
       fluke. -->
  <div class="flex h-11 items-end gap-[5px] overflow-hidden">
    <div v-for="(col, ci) in columns" :key="ci" class="flex flex-1 flex-col-reverse items-center gap-[3px]">
      <span
        v-for="(lit, ri) in col"
        :key="ri"
        class="aspect-square w-full max-w-[9px] min-w-[3px] rounded-full"
        :class="lit ? 'bg-[var(--accent-2)]' : 'bg-[var(--border-soft-2)]'"
      ></span>
    </div>
  </div>
</template>
