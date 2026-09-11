<script setup>
import { useRoute } from "vue-router";

const route = useRoute();

/* Only the first two entries are real, working pages - the rest mirror
 * categories from the reference sidebar (Executive Overview, Tariff &
 * Cost, Carbon & Sustainability, etc.) that this board has no way to
 * back with real data (billing/tariffs, CO2, a settings/config system
 * that doesn't exist here) - see the Tailwind-migration commit's note on
 * the same tradeoff for the Energy Analytics/Carbon/Tariff pages that
 * were skipped outright. Rather than silently omitting them (losing the
 * full sidebar the reference shows) or faking them as clickable, they're
 * shown disabled with a "Soon" tag - honest about what's actually here
 * without giving up the visual.
 * Colors are per-category (mirroring the reference's own varied icon
 * chips), not the app's single accent - the active item still gets the
 * accent treatment regardless of its own category color, same as the
 * reference's own active "Reports & Benchmarking" row. */
const items = [
  {
    to: "/",
    title: "Dashboard",
    subtitle: "Real-time monitoring",
    color: "#2563eb",
    icon: 'M13 2 5 13h6l-1 9 9-13h-6z',
  },
  {
    to: "/predictive-maintenance",
    title: "Predictive Maintenance",
    subtitle: "Sound & thermal anomalies",
    color: "#7c3aed",
    icon: 'M4 4h16v16H4z|M9 9h6v6H9z',
  },
  { title: "Executive Overview", subtitle: "KPIs and trends", color: "#0d9488", icon: "M3 17 9 11l4 4 8-8", soon: true },
  { title: "Load Analytics", subtitle: "Demand analysis", color: "#4f46e5", icon: "M3 12h4l2-7 4 14 2-7h6", soon: true },
  { title: "Tariff & Cost", subtitle: "ETOU & billing", color: "#16a34a", icon: "$", soon: true },
  { title: "Carbon & Sustainability", subtitle: "ESG reporting", color: "#059669", icon: "leaf", soon: true },
  { title: "Alarms & Health", subtitle: "System status", color: "#dc2626", icon: "warn", soon: true },
  { title: "Settings", subtitle: "System config", color: "#64748b", icon: "gear", soon: true },
];

function isActive(item) {
  return item.to && route.path === item.to;
}
</script>

<template>
  <aside class="flex min-h-screen w-64 shrink-0 flex-col gap-1 border-r border-[var(--border-soft)] bg-[var(--surface)] p-4">
    <!-- App identity, not a fake logged-in user - this dashboard has no
         login system, so a "System Administrator" profile block would be
         fabricating an account that doesn't exist. -->
    <div class="flex items-center gap-3 rounded-xl px-2 py-3">
      <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor"><path d="M13 2 5 13h6l-1 9 9-13h-6z" /></svg>
      </span>
      <div class="flex flex-col">
        <span class="text-sm font-bold">Demo Kit</span>
        <span class="text-xs text-[var(--text-muted)]">Local dashboard</span>
      </div>
    </div>

    <div class="my-1.5 h-px bg-[var(--border-soft)]"></div>

    <nav class="flex flex-col gap-1">
      <component
        :is="item.to ? 'router-link' : 'div'"
        v-for="item in items"
        :key="item.title"
        :to="item.to"
        class="group flex items-start gap-3 rounded-xl border-l-[3px] px-3 py-2.5 transition-colors"
        :class="[
          item.to ? 'cursor-pointer' : 'cursor-default opacity-60',
          isActive(item)
            ? 'border-l-[var(--accent)] bg-[var(--accent-soft)]'
            : 'border-l-transparent hover:bg-[var(--surface-2)]',
        ]"
      >
        <span
          class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          :style="isActive(item)
            ? { background: 'var(--accent-soft)', color: 'var(--accent)' }
            : { background: `${item.color}1a`, color: item.color }"
        >
          <svg v-if="item.icon === '$'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 6.5a4 4 0 0 0-4-2.5h-1a3.5 3.5 0 0 0 0 7h1a3.5 3.5 0 0 1 0 7h-1a4 4 0 0 1-4-2.5" stroke-linecap="round" /></svg>
          <svg v-else-if="item.icon === 'leaf'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 21c8 0 14-6 14-16-10 0-16 6-16 14 0 1 .3 2 1 2 4-5 8-8 12-10" stroke-linecap="round" stroke-linejoin="round" /></svg>
          <svg v-else-if="item.icon === 'warn'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3 2 20h20z" stroke-linejoin="round" /><path d="M12 10v4M12 17h.01" stroke-linecap="round" /></svg>
          <svg v-else-if="item.icon === 'gear'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" stroke-linecap="round" stroke-linejoin="round" /></svg>
          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8">
            <path v-for="(seg, i) in item.icon.split('|')" :key="i" :d="seg" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </span>
        <div class="flex min-w-0 flex-col">
          <span class="flex items-center gap-1.5 text-[13.5px] font-semibold" :class="isActive(item) ? 'text-[var(--accent)]' : 'text-[var(--text)]'">
            {{ item.title }}
            <span v-if="item.soon" class="rounded-full bg-[var(--surface-2)] px-1.5 py-0.5 text-[9.5px] font-bold tracking-wide text-[var(--text-faint)] uppercase">Soon</span>
          </span>
          <span class="truncate text-[11.5px] text-[var(--text-muted)]">{{ item.subtitle }}</span>
        </div>
      </component>
    </nav>
  </aside>
</template>
