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

/* "Online" here means the physical board, not this browser tab's own
 * WebSocket connection to the server - that distinction was the actual
 * bug: this badge used to just read live.state.connected, which stays
 * true almost the entire time a tab is open regardless of whether any
 * board was ever connected, since it only reflects this tab's own link
 * to our server. Requires the WS to genuinely be up too (not just a
 * stale `real: true` left over in the store from before a disconnect -
 * see dashboard-do.ts's Reading.real for where the per-channel flag
 * comes from). */
const boardOnline = computed(
  () => live.state.connected && (live.state.sound.real || live.state.temperature.real || live.state.power.real)
);
</script>

<template>
  <header class="flex items-center justify-between gap-4 px-6 pt-4 pb-1">
    <div class="flex items-center gap-4 text-[13px] text-[var(--text-muted)]">
      <span>{{ dateTimeLabel }}</span>
      <span class="inline-flex items-center gap-1.5" title="Whether the physical board currently has a live connection, not just this browser tab">
        <span class="h-2 w-2 rounded-full" :class="boardOnline ? 'bg-[var(--accent)]' : 'bg-[var(--text-muted)]'"></span>
        {{ boardOnline ? "Online" : "Offline" }}
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
