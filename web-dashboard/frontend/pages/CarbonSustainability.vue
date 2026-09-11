<script setup>
import DemoDataBanner from "../components/DemoDataBanner.vue";

/* All figures on this page are placeholder demo data (see DemoDataBanner
 * above) - this board doesn't measure CO2, water use, or renewable-
 * energy share, so there's no real source to wire this page to. Kept
 * as static data rather than computed from anything, so it's obviously
 * not pretending to be live. */
const kpis = [
  { label: "Carbon Intensity", value: "0.619", unit: "kg CO₂/kWh", target: "0.58 kg CO₂/kWh", progress: 100, trend: "-3.2%", color: "var(--green)" },
  { label: "Energy Efficiency", value: "87.3", unit: "%", target: "90 %", progress: 97, trend: "+2.1%", color: "var(--green)" },
  { label: "Renewable Energy", value: "23.5", unit: "%", target: "30 %", progress: 78, trend: "+4.8%", color: "var(--amber)" },
  { label: "Water Efficiency", value: "2.300", unit: "L/kWh", target: "2 L/kWh", progress: 100, trend: "-1.5%", color: "var(--green)" },
];

const trend = [
  { month: "Jan", actual: 320, target: 300 },
  { month: "Feb", actual: 295, target: 290 },
  { month: "Mar", actual: 305, target: 280 },
  { month: "Apr", actual: 270, target: 270 },
  { month: "May", actual: 260, target: 260 },
  { month: "Jun", actual: 245, target: 250 },
];
const trendMax = 320;

const scopes = [
  { label: "Scope 1", sub: "Direct emissions from owned sources", value: "245.8 kg", pct: 8.6, color: "var(--red)" },
  { label: "Scope 2", sub: "Indirect emissions from purchased energy", value: "2601.5 kg", pct: 91.4, color: "var(--amber)" },
  { label: "Scope 3", sub: "Other indirect emissions (future)", value: "0.0 kg", pct: 0, color: "var(--green)" },
];

const goals = [
  { title: "Carbon Neutral by 2030", sub: "Achieve net-zero carbon emissions", progress: 42, target: "12/31/2030" },
  { title: "50% Renewable Energy", sub: "Source 50% energy from renewables", progress: 47, target: "12/31/2027" },
];

const achievements = [
  { title: "Carbon Reduction Target Met", body: "Achieved 12.8% reduction in carbon emissions this year, approaching the 15% target.", tone: "green" },
  { title: "Renewable Energy Milestone", body: "Reached 23.5% renewable energy usage, ahead of schedule for 30% target by 2027.", tone: "blue" },
  { title: "Energy Efficiency Opportunity", body: "Current efficiency at 87.3%. Implementing LED upgrades could reach 90% target.", tone: "amber" },
];
</script>

<template>
  <div class="flex flex-col gap-4 rounded-[var(--radius-xl)] p-2">
    <div class="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
      <div>
        <h1 class="text-lg font-bold">Carbon &amp; Sustainability</h1>
        <p class="mt-1 text-[13px] text-[var(--text-muted)]">Environmental impact monitoring and ESG reporting</p>
      </div>
      <button type="button" disabled class="cursor-not-allowed rounded-lg bg-[var(--accent)] px-4 py-2.5 text-[13px] font-bold text-white opacity-60">
        &#8595; ESG Report
      </button>
    </div>

    <DemoDataBanner />

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div v-for="k in kpis" :key="k.label" class="flex flex-col gap-2 rounded-2xl bg-[var(--surface)] p-5 shadow-sm">
        <div class="flex items-center justify-between">
          <span class="flex h-8 w-8 items-center justify-center rounded-lg" :style="{ background: `${k.color}1a`, color: k.color }">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17 9 11l4 4 8-8" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </span>
          <span class="text-xs font-semibold" :style="{ color: k.color }">{{ k.trend }}</span>
        </div>
        <span class="text-[13px] text-[var(--text-muted)]">{{ k.label }}</span>
        <span class="text-xl font-extrabold">{{ k.value }} <small class="text-xs font-semibold text-[var(--text-muted)]">{{ k.unit }}</small></span>
        <div class="flex items-center justify-between text-[11px] text-[var(--text-muted)]">
          <span>Target: {{ k.target }}</span>
          <span>{{ k.progress }}%</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-[var(--surface-2)]">
          <div class="h-full rounded-full" :style="{ width: `${k.progress}%`, background: k.color }"></div>
        </div>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-base font-bold">Carbon Emissions Trend</h2>
          <div class="flex items-center gap-3 text-xs text-[var(--text-muted)]">
            <span class="inline-flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-[var(--red)]"></span>Actual</span>
            <span class="inline-flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-[var(--green)]"></span>Target</span>
          </div>
        </div>
        <svg viewBox="0 0 600 200" class="w-full">
          <line x1="40" y1="20" x2="40" y2="170" stroke="var(--border-soft)" />
          <line x1="40" y1="170" x2="580" y2="170" stroke="var(--border-soft)" />
          <text v-for="(t, i) in [0, 160, 320]" :key="i" :x="30" :y="170 - (t / trendMax) * 150" text-anchor="end" font-size="11" :fill="'var(--text-muted)'">{{ t }}</text>
          <g v-for="(p, i) in trend" :key="p.month">
            <circle :cx="80 + i * 96" :cy="170 - (p.actual / trendMax) * 150" r="4.5" fill="var(--red)" />
            <circle :cx="80 + i * 96" :cy="170 - (p.target / trendMax) * 150" r="4.5" fill="var(--green)" />
            <text :x="80 + i * 96" y="188" text-anchor="middle" font-size="11" fill="var(--text-muted)">{{ p.month }}</text>
          </g>
        </svg>
      </div>

      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <h2 class="mb-4 text-base font-bold">Emissions by Scope</h2>
        <div class="flex flex-col gap-4">
          <div v-for="s in scopes" :key="s.label">
            <div class="mb-1 flex items-start justify-between gap-2">
              <div class="flex items-start gap-2">
                <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full" :style="{ background: s.color }"></span>
                <div>
                  <div class="text-[13px] font-semibold">{{ s.label }}</div>
                  <div class="text-[11px] text-[var(--text-muted)]">{{ s.sub }}</div>
                </div>
              </div>
              <div class="text-right text-[13px]">
                <div class="font-bold">{{ s.value }}</div>
                <div class="text-[11px] text-[var(--text-muted)]">{{ s.pct }}%</div>
              </div>
            </div>
            <div class="h-1.5 overflow-hidden rounded-full bg-[var(--surface-2)]">
              <div class="h-full rounded-full" :style="{ width: `${s.pct}%`, background: s.color }"></div>
            </div>
          </div>
        </div>
        <div class="mt-4 flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm font-bold">
          <span>Total Emissions</span>
          <span>2847.3 kg CO&#8322;</span>
        </div>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <h2 class="mb-4 text-base font-bold">ESG Goals Progress</h2>
        <div class="flex flex-col gap-4">
          <div v-for="g in goals" :key="g.title" class="rounded-lg border border-[var(--border-soft)] p-4">
            <div class="mb-1 flex items-center justify-between">
              <span class="text-[13px] font-semibold">{{ g.title }}</span>
              <span class="rounded-full bg-[var(--green-soft)] px-2 py-0.5 text-[10px] font-bold text-[var(--green)]">on track</span>
            </div>
            <p class="mb-2 text-[11.5px] text-[var(--text-muted)]">{{ g.sub }}</p>
            <div class="mb-1 flex items-center justify-between text-[11px]"><span>Progress</span><span class="font-bold">{{ g.progress }}%</span></div>
            <div class="h-1.5 overflow-hidden rounded-full bg-[var(--surface-2)]">
              <div class="h-full rounded-full bg-[var(--accent)]" :style="{ width: `${g.progress}%` }"></div>
            </div>
            <span class="mt-1 block text-[10.5px] text-[var(--text-faint)]">Target: {{ g.target }}</span>
          </div>
        </div>
      </div>

      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <h2 class="mb-4 text-base font-bold">Sustainability Achievements</h2>
        <div class="flex flex-col gap-3">
          <div
            v-for="a in achievements" :key="a.title"
            class="rounded-lg p-4"
            :class="a.tone === 'green' ? 'bg-[var(--green-soft)]' : a.tone === 'blue' ? 'bg-blue-50' : 'bg-[var(--amber-soft)]'"
          >
            <span class="text-[13px] font-bold" :class="a.tone === 'green' ? 'text-[var(--green)]' : a.tone === 'blue' ? 'text-blue-700' : 'text-[var(--amber)]'">{{ a.title }}</span>
            <p class="mt-1 text-[12px] text-[var(--text-muted)]">{{ a.body }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
