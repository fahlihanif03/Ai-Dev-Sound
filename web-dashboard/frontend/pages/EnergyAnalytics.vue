<script setup>
import { computed } from "vue";
import DemoDataBanner from "../components/DemoDataBanner.vue";

/* Placeholder demo data (see DemoDataBanner) - a real hourly consumption
 * pattern would need the backend to retain per-hour history well beyond
 * what this app currently stores (see dashboard-do.ts's MAX_HISTORY_POINTS),
 * and cost/charge figures need a real tariff rate applied over real
 * usage, which nothing here currently computes. */
const pattern = [
  { hour: "00:00", kw: 180 }, { hour: "02:00", kw: 165 }, { hour: "04:00", kw: 155 },
  { hour: "06:00", kw: 220 }, { hour: "08:00", kw: 280 }, { hour: "10:00", kw: 320 },
  { hour: "12:00", kw: 310 }, { hour: "14:00", kw: 290 }, { hour: "16:00", kw: 340 },
  { hour: "18:00", kw: 380 }, { hour: "20:00", kw: 350 }, { hour: "22:00", kw: 240 },
];
const maxKw = 380;
const barWidth = 100 / pattern.length;

const peakHours = [
  { label: "Morning Peak (8-10 AM)", value: "300 kW", color: "var(--amber)" },
  { label: "Evening Peak (6-8 PM)", value: "380 kW", color: "var(--red)" },
  { label: "Off-Peak Average", value: "165 kW", color: "var(--green)" },
];
const efficiency = [
  { label: "Load Factor", value: "68.4%", color: "var(--green)" },
  { label: "Power Factor", value: "0.92", color: "var(--green)" },
  { label: "Energy Efficiency", value: "85.2%", color: "var(--accent)" },
];
const cost = [
  { label: "Peak Charges", value: "RM 2,340", color: "var(--red)" },
  { label: "Off-Peak Charges", value: "RM 1,245", color: "var(--green)" },
  { label: "Potential Savings", value: "RM 456", color: "var(--accent)" },
];
</script>

<template>
  <div class="flex flex-col gap-4 rounded-[var(--radius-xl)] p-2">
    <div class="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
      <div>
        <h1 class="text-lg font-bold">Energy Analytics</h1>
        <p class="mt-1 text-[13px] text-[var(--text-muted)]">Comprehensive analysis of your energy consumption patterns</p>
      </div>
      <button type="button" disabled class="cursor-not-allowed rounded-lg bg-[var(--accent)] px-4 py-2.5 text-[13px] font-bold text-white opacity-60">
        &#8595; Export
      </button>
    </div>

    <DemoDataBanner />

    <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-base font-bold">Energy Consumption Pattern</h2>
        <span class="text-xs text-[var(--text-muted)]">Last 24 Hours</span>
      </div>
      <div class="flex h-64 items-end gap-2 border-b border-[var(--border-soft)] pb-1">
        <div v-for="p in pattern" :key="p.hour" class="flex flex-1 flex-col items-center gap-1">
          <span class="text-[11px] font-semibold text-[var(--text-muted)]">{{ p.kw }}</span>
          <div
            class="w-full rounded-t-md"
            :style="{ height: `${(p.kw / maxKw) * 180}px`, background: 'linear-gradient(180deg, var(--accent-2), var(--accent))' }"
          ></div>
        </div>
      </div>
      <div class="mt-2 flex gap-2">
        <span v-for="p in pattern" :key="p.hour" class="flex-1 text-center text-[10.5px] text-[var(--text-muted)]">{{ p.hour }}</span>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-3">
      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <h2 class="mb-3 text-sm font-bold">Peak Hours Analysis</h2>
        <div class="flex flex-col gap-2.5">
          <div v-for="p in peakHours" :key="p.label" class="flex items-center justify-between text-[13px]">
            <span class="text-[var(--text-muted)]">{{ p.label }}</span>
            <span class="font-bold" :style="{ color: p.color }">{{ p.value }}</span>
          </div>
        </div>
      </div>
      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <h2 class="mb-3 text-sm font-bold">Efficiency Metrics</h2>
        <div class="flex flex-col gap-2.5">
          <div v-for="p in efficiency" :key="p.label" class="flex items-center justify-between text-[13px]">
            <span class="text-[var(--text-muted)]">{{ p.label }}</span>
            <span class="font-bold" :style="{ color: p.color }">{{ p.value }}</span>
          </div>
        </div>
      </div>
      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <h2 class="mb-3 text-sm font-bold">Cost Impact</h2>
        <div class="flex flex-col gap-2.5">
          <div v-for="p in cost" :key="p.label" class="flex items-center justify-between text-[13px]">
            <span class="text-[var(--text-muted)]">{{ p.label }}</span>
            <span class="font-bold" :style="{ color: p.color }">{{ p.value }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
