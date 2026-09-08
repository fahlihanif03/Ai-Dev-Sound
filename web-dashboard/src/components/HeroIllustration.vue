<script setup>
defineProps({
  variant: { type: String, default: "facility" }, // "facility" | "machine"
});
</script>

<template>
  <svg v-if="variant === 'facility'" viewBox="0 0 320 200" class="hero-svg" aria-hidden="true">
    <circle cx="256" cy="56" r="30" fill="var(--accent-soft)" />
    <path d="M40 160 L40 100 L90 70 L140 100 L140 160 Z" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round" />
    <rect x="60" y="120" width="20" height="40" fill="none" stroke="var(--accent)" stroke-width="2.5" />
    <rect x="100" y="118" width="16" height="16" fill="none" stroke="var(--accent)" stroke-width="2.5" />
    <path d="M150 160 L150 90 L190 90 L190 60 L230 60 L230 160 Z" fill="none" stroke="var(--text-muted)" stroke-width="3" stroke-linejoin="round" />
    <line x1="20" y1="160" x2="300" y2="160" stroke="var(--border-soft)" stroke-width="3" stroke-linecap="round" />
    <path d="M170 60 L170 40 M182 60 L182 34 M194 60 L194 42" stroke="var(--text-muted)" stroke-width="2.5" stroke-linecap="round" />
  </svg>

  <svg v-else viewBox="0 0 320 200" class="hero-svg" aria-hidden="true">
    <circle cx="160" cy="100" r="46" fill="var(--accent-soft)" />
    <circle cx="160" cy="100" r="46" fill="none" stroke="var(--accent)" stroke-width="3" />
    <path d="M160 62 C176 62 190 76 190 92" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round" />
    <path d="M160 138 C144 138 130 124 130 108" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round" />
    <circle cx="160" cy="100" r="8" fill="var(--accent)" />
    <path d="M60 150 Q90 120 120 150 T180 150 T240 150 T300 150" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" opacity="0.5" />
  </svg>
</template>

<style scoped>
.hero-svg {
  width: 100%;
  max-width: 320px;
  height: auto;
  display: block;
}
</style>
