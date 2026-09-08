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
  <header class="app-header">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
          <path d="M12 2 L4 13h6l-1 9 9-13h-6z" fill="#ff6a1a" />
        </svg>
      </span>
      <span class="brand-name">Demo Kit</span>
    </div>

    <nav class="nav">
      <router-link to="/" class="nav-link">Energy</router-link>
      <router-link to="/predictive-maintenance" class="nav-link">Predictive Maintenance</router-link>
    </nav>

    <div class="status-cluster">
      <span class="datetime">{{ dateTimeLabel }}</span>
      <span class="conn" :class="{ online: state.connected }">
        <span class="dot"></span>
        {{ state.connected ? "Online" : "Offline" }}
      </span>
      <button class="icon-btn" type="button" aria-label="Notifications">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" stroke-linecap="round" />
        </svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 22px clamp(20px, 4vw, 48px) 8px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 15px;
}

.brand-mark {
  display: inline-flex;
  width: 28px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: var(--accent-soft);
}

.nav {
  display: flex;
  gap: 2px;
  background: var(--surface);
  border-radius: var(--radius-pill);
  padding: 5px;
  box-shadow: var(--shadow-sm);
}

.nav-link {
  padding: 9px 18px;
  border-radius: var(--radius-pill);
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-link.router-link-exact-active {
  background: var(--accent-grad);
  color: #fff;
}

.status-cluster {
  margin-left: auto;
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

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-sm);
  cursor: default;
}

@media (max-width: 720px) {
  .app-header {
    flex-wrap: wrap;
    row-gap: 12px;
  }
  .status-cluster {
    margin-left: 0;
    width: 100%;
    justify-content: space-between;
  }
}
</style>
