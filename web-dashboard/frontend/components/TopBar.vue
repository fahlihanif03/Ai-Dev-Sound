<script setup>
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useLiveStore } from "../stores/live.js";

const live = useLiveStore();
const now = ref(new Date());
let timer;
onMounted(() => {
  timer = setInterval(() => (now.value = new Date()), 1000);
});
onUnmounted(() => clearInterval(timer));

const dateTimeLabel = computed(() =>
  now.value.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
);
</script>

<template>
  <header class="flex items-center justify-between gap-4 px-6 pt-4 pb-1">
    <div class="flex items-center gap-4 text-[13px] text-[var(--text-muted)]">
      <span>{{ dateTimeLabel }}</span>
      <span class="inline-flex items-center gap-1.5">
        <span class="h-2 w-2 rounded-full" :class="live.state.connected ? 'bg-[var(--accent)]' : 'bg-[var(--text-muted)]'"></span>
        {{ live.state.connected ? "Online" : "Offline" }}
      </span>
    </div>

    <div class="flex items-center gap-2.5">
      <button class="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--surface)] text-[var(--text-muted)] shadow-[var(--shadow-sm)]" type="button" aria-label="Notifications">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" stroke-linecap="round" />
        </svg>
      </button>
      <span class="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)] shadow-[var(--shadow-sm)]" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="8" r="3.4" />
          <path d="M5 20c1.4-3.6 4.2-5.5 7-5.5s5.6 1.9 7 5.5" stroke-linecap="round" />
        </svg>
      </span>
    </div>
  </header>
</template>
