<script setup>
/* Flat SVG stand-in for the old Three.js 3D PC model (PCViewer.vue,
 * removed per explicit request to drop all Three.js from the app - see
 * docs/PROGRESS.md). Same interface (emits "select" on click) so this
 * drops straight into PredictiveMaintenance.vue's existing click-to-
 * reveal-readings interaction without touching that logic at all - just
 * a plain, dependency-free illustration instead of a 3D scene. */
const emit = defineEmits(["select"]);
</script>

<template>
  <button type="button" class="flex h-full w-full cursor-pointer items-center justify-center border-none bg-transparent p-0" @click="emit('select')" aria-label="Show current readings">
    <svg viewBox="0 0 220 220" width="220" height="220" class="max-w-[70%]">
      <rect x="30" y="20" width="120" height="180" rx="14" fill="#1c1e22" stroke="var(--accent)" stroke-opacity="0.35" stroke-width="1.5" />
      <rect x="44" y="36" width="92" height="46" rx="6" fill="#26292e" />
      <circle v-for="(cy, i) in [110, 148, 186]" :key="i" :cx="90" :cy="cy" r="20" fill="none" stroke="var(--accent)" stroke-width="3" stroke-opacity="0.85" />
      <circle v-for="(cy, i) in [110, 148, 186]" :key="`h-${i}`" :cx="90" :cy="cy" r="4" fill="var(--accent)" />
      <rect x="160" y="60" width="10" height="120" rx="5" fill="#26292e" />
    </svg>
  </button>
</template>
