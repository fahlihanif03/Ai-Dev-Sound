<script setup>
/* Flags a page as showing placeholder/demo numbers, not real board
 * readings - used on Carbon & Sustainability and Energy Analytics,
 * which track things (CO2, hourly demand patterns) this board has no
 * way to measure. Kept as its own tiny component so all "mockup first"
 * pages carry the same honest, visible marker instead of each page
 * inventing its own wording. */
</script>

<template>
  <div class="flex items-center gap-2.5 rounded-xl bg-[var(--amber-soft)] px-4 py-2.5 text-[13px] font-medium text-[var(--amber)]">
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke-linecap="round" stroke-linejoin="round" /></svg>
    Demo data &mdash; this page isn't wired to a real data source yet, numbers below are placeholder samples.
  </div>
</template>
