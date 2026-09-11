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
  now.value.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
);
</script>

<template>
  <header class="topnav">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
          <path d="M12 2 L4 13h6l-1 9 9-13h-6z" fill="var(--accent)" />
        </svg>
      </span>
      <span class="brand-name">Demo Kit</span>
    </div>

    <nav class="pill-nav">
      <router-link to="/" class="pill-link">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M13 2 5 13h6l-1 9 9-13h-6z" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        Energy Monitoring
      </router-link>
      <router-link to="/predictive-maintenance" class="pill-link">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="4" y="4" width="16" height="16" rx="2.5" />
          <path d="M9 9h6v6H9z" />
        </svg>
        Predictive Maintenance
      </router-link>
    </nav>

    <div class="right-cluster">
      <span class="datetime">{{ dateTimeLabel }}</span>
      <span class="conn" :class="{ online: state.connected }">
        <span class="dot"></span>
        {{ state.connected ? "Online" : "Offline" }}
      </span>
      <button class="icon-btn" type="button" aria-label="Notifications">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" stroke-linecap="round" />
        </svg>
      </button>
      <span class="avatar" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="8" r="3.4" />
          <path d="M5 20c1.4-3.6 4.2-5.5 7-5.5s5.6 1.9 7 5.5" stroke-linecap="round" />
        </svg>
      </span>
    </div>
  </header>
</template>

<style scoped>
.topnav {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px clamp(20px, 4vw, 40px) 4px;
  flex-wrap: wrap;
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

.pill-nav {
  margin: 0 auto;
  display: flex;
  gap: 2px;
  background: var(--surface);
  border-radius: var(--radius-pill);
  padding: 5px;
  box-shadow: var(--shadow-sm);
}

.pill-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 18px;
  border-radius: var(--radius-pill);
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  transition: background 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.pill-link.router-link-exact-active {
  background: var(--nav-active);
  color: #fff;
}

.right-cluster {
  display: flex;
  align-items: center;
  gap: 14px;
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

@media (max-width: 860px) {
  .topnav {
    justify-content: center;
  }
  .pill-nav {
    order: 3;
    width: 100%;
    justify-content: center;
  }
  .right-cluster {
    margin-left: auto;
  }
}
</style>
