<script setup>
import { computed, ref, onMounted, onUnmounted } from "vue";
import { state } from "../lib/live-state.js";

const now = ref(new Date());
let timer;
onMounted(() => {
  timer = setInterval(() => (now.value = new Date()), 1000);
});
onUnmounted(() => clearInterval(timer));

const dateTimeLabel = computed(() =>
  now.value.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
);
</script>

<template>
  <header class="topbar">
    <div class="status-cluster">
      <span class="datetime">{{ dateTimeLabel }}</span>
      <span class="conn" :class="{ online: state.connected }">
        <span class="dot"></span>
        {{ state.connected ? "Online" : "Offline" }}
      </span>
    </div>

    <div class="icon-cluster">
      <button class="icon-btn" type="button" aria-label="Notifications">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" stroke-linecap="round" />
        </svg>
      </button>
      <span class="avatar" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="8" r="3.4" />
          <path d="M5 20c1.4-3.6 4.2-5.5 7-5.5s5.6 1.9 7 5.5" stroke-linecap="round" />
        </svg>
      </span>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px clamp(20px, 4vw, 48px) 0;
}

.status-cluster {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: var(--text-muted);
}

.conn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.conn.online .dot {
  background: var(--accent);
}

.icon-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-btn,
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--surface);
  color: var(--text-muted);
  box-shadow: var(--shadow-sm);
}

.icon-btn {
  cursor: default;
}

.avatar {
  background: var(--accent-soft);
  color: var(--accent);
}

@media (max-width: 720px) {
  .topbar {
    flex-wrap: wrap;
    row-gap: 12px;
  }
}
</style>
