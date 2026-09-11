<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: "--" },
  unit: { type: String, default: "" },
  flag: { type: String, default: "normal" },
});
</script>

<template>
  <div class="flex flex-col gap-3.5 rounded-[var(--radius-lg)] bg-[var(--surface)] px-[22px] py-5 shadow-[var(--shadow-sm)]">
    <div class="flex items-center justify-between">
      <span class="text-[13px] font-medium text-[var(--text-muted)]">{{ label }}</span>
      <span class="text-[var(--text-muted)] opacity-60" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M7 17 17 7M9 7h8v8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
    </div>

    <div class="flex items-baseline gap-1.5">
      <span class="text-[28px] font-bold tracking-[-0.02em]">{{ value }}</span>
      <span class="text-[13px] text-[var(--text-muted)]">{{ unit }}</span>
      <span
        class="ml-0.5 h-[7px] w-[7px] rounded-full"
        :class="flag === 'abnormal' ? 'bg-[var(--red)]' : 'bg-[var(--accent)]'"
      ></span>
    </div>

    <div class="mt-auto">
      <slot />
    </div>
  </div>
</template>
