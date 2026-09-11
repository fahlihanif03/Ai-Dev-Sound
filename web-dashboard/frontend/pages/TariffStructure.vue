<script setup>
import { ref, computed } from "vue";

/* Real TNB (Tenaga Nasional Berhad) commercial/industrial tariff rates,
 * RP4 (2025-2027) schedule for Peninsular Malaysia - sourced 2026-09-11
 * via web search + direct page fetches (trexon.my/guides/tnb-tariff-2026,
 * mytnb.com.my/business/special-schemes/enhanced-time-of-use). Flat-rate
 * C1/C2/E1 figures and the ETOU C1 MV three-tier rates were confirmed
 * directly from a fetched rate table. The exact official clock
 * boundaries for ETOU's Peak/Mid-Peak/Off-Peak windows could NOT be
 * confirmed from any source reachable during that research - only their
 * durations (4h/10h/10h on weekdays) were confirmed, cited in the ETOU
 * card below. Rather than invent specific times and present them as
 * fact, the exact boundaries are left unspecified with a note to verify
 * against your actual TNB ETOU agreement - this is real, sourced data
 * where confirmed, honestly incomplete where it isn't. TNB tariffs are
 * also revised periodically (ICPT surcharge every 6 months, base rates
 * per regulatory period) - verify current rates against your bill or
 * mytnb.com.my before using this for real billing decisions. */
const TARIFFS = {
  c1: {
    label: "C1",
    name: "Commercial Tariff C1",
    desc: "Same charge for peak and off-peak energy usage",
    type: "flat",
    energyRate: 0.365, // RM/kWh
    demandRate: 30.30, // RM/kW
  },
  c2: {
    label: "C2",
    name: "Commercial Tariff C2",
    desc: "Same charge for peak and off-peak energy usage",
    type: "flat",
    energyRate: 0.365,
    demandRate: 29.60,
  },
  e1: {
    label: "E1",
    name: "Enhanced Tariff E1",
    desc: "Flat industrial energy rate, no time-of-use split",
    type: "flat",
    energyRate: 0.337,
    demandRate: 29.60,
  },
  e2: {
    label: "E2",
    name: "Enhanced Tariff E2 (ETOU)",
    desc: "Three-tier time-of-use pricing - Peak, Mid-Peak, Off-Peak",
    type: "etou",
    peakRate: 0.584,
    midPeakRate: 0.357,
    offPeakRate: 0.281,
    demandRate: 37.00,
  },
};

const selected = ref("c1");
const tariff = computed(() => TARIFFS[selected.value]);

const peakKwh = ref("");
const offPeakKwh = ref("");
const midPeakKwh = ref("");
const maxDemand = ref("");
const billResult = ref(null);

function calculateBill() {
  const peak = Number(peakKwh.value) || 0;
  const offPeak = Number(offPeakKwh.value) || 0;
  const midPeak = Number(midPeakKwh.value) || 0;
  const demand = Number(maxDemand.value) || 0;

  let energyCost;
  if (tariff.value.type === "flat") {
    energyCost = (peak + offPeak) * tariff.value.energyRate;
  } else {
    energyCost = peak * tariff.value.peakRate + midPeak * tariff.value.midPeakRate + offPeak * tariff.value.offPeakRate;
  }
  const demandCost = demand * tariff.value.demandRate;
  billResult.value = { energyCost, demandCost, total: energyCost + demandCost };
}
</script>

<template>
  <div class="flex flex-col gap-4 rounded-[var(--radius-xl)] p-2">
    <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
      <h1 class="text-lg font-bold">Tariff Structure Analysis</h1>
      <p class="mt-1 text-[13px] text-[var(--text-muted)]">Understanding factors that impact electrical usage billing &mdash; real TNB (Peninsular Malaysia) RP4 rates</p>
    </div>

    <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
      <h2 class="mb-3 text-sm font-semibold text-[var(--text-muted)]">Select Tariff Type</h2>
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <button
          v-for="(t, key) in TARIFFS"
          :key="key"
          type="button"
          class="rounded-xl border-2 px-4 py-4 text-center transition-colors"
          :class="selected === key ? 'border-[var(--accent)] bg-[var(--accent-soft)]' : 'border-[var(--border-soft)] hover:border-[var(--border-soft-2)]'"
          @click="selected = key; billResult = null"
        >
          <div class="text-base font-bold">{{ t.label }}</div>
          <div class="text-[11px] text-[var(--text-muted)]">{{ t.name }}</div>
        </button>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <div class="mb-1 flex items-center gap-2">
          <span class="text-[var(--accent)]">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 6.5a4 4 0 0 0-4-2.5h-1a3.5 3.5 0 0 0 0 7h1a3.5 3.5 0 0 1 0 7h-1a4 4 0 0 1-4-2.5" stroke-linecap="round" /></svg>
          </span>
          <h2 class="text-base font-bold">{{ tariff.name }}</h2>
        </div>
        <p class="mb-4 text-[13px] text-[var(--text-muted)]">{{ tariff.desc }}</p>

        <div v-if="tariff.type === 'flat'" class="flex flex-col gap-2">
          <div class="flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm">
            <span>Energy Charge (all hours)</span>
            <span class="font-bold text-[var(--accent)]">RM {{ tariff.energyRate.toFixed(3) }} per kWh</span>
          </div>
          <div class="flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm">
            <span>Maximum Demand</span>
            <span class="font-bold text-[var(--accent)]">RM {{ tariff.demandRate.toFixed(2) }} per kW</span>
          </div>
        </div>
        <div v-else class="flex flex-col gap-2">
          <div class="flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm">
            <span>Peak Energy</span>
            <span class="font-bold text-[var(--accent)]">RM {{ tariff.peakRate.toFixed(3) }} per kWh</span>
          </div>
          <div class="flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm">
            <span>Mid-Peak Energy</span>
            <span class="font-bold text-[var(--accent)]">RM {{ tariff.midPeakRate.toFixed(3) }} per kWh</span>
          </div>
          <div class="flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm">
            <span>Off-Peak Energy</span>
            <span class="font-bold text-[var(--accent)]">RM {{ tariff.offPeakRate.toFixed(3) }} per kWh</span>
          </div>
          <div class="flex items-center justify-between rounded-lg bg-[var(--surface-2)] px-4 py-3 text-sm">
            <span>Maximum Demand</span>
            <span class="font-bold text-[var(--accent)]">RM {{ tariff.demandRate.toFixed(2) }} per kW</span>
          </div>
        </div>
      </div>

      <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
        <div class="mb-4 flex items-center gap-2">
          <span class="text-[var(--accent)]">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M8 6h8M8 10h2M12 10h2M16 10h2M8 14h2M12 14h2M16 14h2M8 18h2M12 18h2" stroke-linecap="round" /></svg>
          </span>
          <h2 class="text-base font-bold">Cost Calculator</h2>
        </div>

        <div class="flex flex-col gap-3">
          <label class="flex flex-col gap-1.5 text-[13px] font-medium">
            {{ tariff.type === "flat" ? "Energy Consumption (kWh)" : "Peak Energy Consumption (kWh)" }}
            <input v-model="peakKwh" type="number" min="0" placeholder="e.g., 1500" class="rounded-lg border border-[var(--border-soft-2)] px-3.5 py-2.5 text-sm outline-none focus:border-[var(--accent)]" />
          </label>
          <label v-if="tariff.type === 'etou'" class="flex flex-col gap-1.5 text-[13px] font-medium">
            Mid-Peak Energy Consumption (kWh)
            <input v-model="midPeakKwh" type="number" min="0" placeholder="e.g., 800" class="rounded-lg border border-[var(--border-soft-2)] px-3.5 py-2.5 text-sm outline-none focus:border-[var(--accent)]" />
          </label>
          <label class="flex flex-col gap-1.5 text-[13px] font-medium">
            {{ tariff.type === "flat" ? "(all hours use the same rate)" : "Off-Peak Energy Consumption (kWh)" }}
            <input v-if="tariff.type === 'etou'" v-model="offPeakKwh" type="number" min="0" placeholder="e.g., 2300" class="rounded-lg border border-[var(--border-soft-2)] px-3.5 py-2.5 text-sm outline-none focus:border-[var(--accent)]" />
          </label>
          <label class="flex flex-col gap-1.5 text-[13px] font-medium">
            Maximum Demand (kW)
            <input v-model="maxDemand" type="number" min="0" placeholder="e.g., 287" class="rounded-lg border border-[var(--border-soft-2)] px-3.5 py-2.5 text-sm outline-none focus:border-[var(--accent)]" />
          </label>

          <button type="button" class="mt-1 rounded-lg bg-[var(--accent)] py-3 text-sm font-bold text-white hover:opacity-90" @click="calculateBill">
            Calculate Monthly Bill
          </button>

          <div v-if="billResult" class="mt-1 flex flex-col gap-1.5 rounded-lg bg-[var(--accent-soft)] px-4 py-3 text-sm">
            <div class="flex justify-between"><span>Energy cost</span><span class="font-semibold">RM {{ billResult.energyCost.toFixed(2) }}</span></div>
            <div class="flex justify-between"><span>Demand cost</span><span class="font-semibold">RM {{ billResult.demandCost.toFixed(2) }}</span></div>
            <div class="flex justify-between border-t border-[var(--border-soft-2)] pt-1.5 text-base font-bold"><span>Estimated total</span><span class="text-[var(--accent)]">RM {{ billResult.total.toFixed(2) }}</span></div>
          </div>
        </div>
      </div>
    </div>

    <div class="rounded-2xl bg-[var(--surface)] p-6 shadow-sm">
      <div class="mb-4 flex items-center gap-2">
        <span class="text-[var(--accent)]">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" stroke-linecap="round" /></svg>
        </span>
        <h2 class="text-base font-bold">Enhanced Time of Use (ETOU) Time Zones</h2>
      </div>
      <p class="mb-4 text-[12.5px] text-[var(--text-muted)]">
        Applies to Tariff E2/E3. Confirmed durations only (4h Peak / 10h Mid-Peak / 10h Off-Peak on weekdays) -
        the exact official clock boundaries weren't confirmable from available sources, so they're left blank
        here rather than guessed. Check your TNB ETOU agreement or mytnb.com.my for your exact windows.
      </p>
      <div class="grid gap-4 md:grid-cols-2">
        <div class="flex flex-col gap-2 rounded-lg border border-[var(--border-soft)] p-4">
          <span class="text-[13px] font-semibold">Weekdays (Mon&ndash;Fri)</span>
          <div class="flex items-center justify-between rounded-md bg-[var(--green-soft)] px-3 py-2 text-[13px]">
            <span>Off-Peak &mdash; 10 hours</span>
            <span class="rounded-full bg-[var(--green)] px-2 py-0.5 text-[10px] font-bold text-white">Off-Peak</span>
          </div>
          <div class="flex items-center justify-between rounded-md bg-[var(--amber-soft)] px-3 py-2 text-[13px]">
            <span>Mid-Peak &mdash; 10 hours</span>
            <span class="rounded-full bg-[var(--amber)] px-2 py-0.5 text-[10px] font-bold text-white">Mid-Peak</span>
          </div>
          <div class="flex items-center justify-between rounded-md bg-[var(--red-soft)] px-3 py-2 text-[13px]">
            <span>Peak &mdash; 4 hours</span>
            <span class="rounded-full bg-[var(--red)] px-2 py-0.5 text-[10px] font-bold text-white">Peak</span>
          </div>
        </div>
        <div class="flex flex-col gap-2 rounded-lg border border-[var(--border-soft)] p-4">
          <span class="text-[13px] font-semibold">Saturday, Sunday &amp; Public Holidays</span>
          <div class="flex items-center justify-between rounded-md bg-[var(--green-soft)] px-3 py-2 text-[13px]">
            <span>00:00 &ndash; 24:00 &mdash; Off-Peak all day</span>
            <span class="rounded-full bg-[var(--green)] px-2 py-0.5 text-[10px] font-bold text-white">Off-Peak</span>
          </div>
          <span class="mt-1 text-[12px] text-[var(--text-muted)]">Maximum Demand charge is waived on weekends and public holidays.</span>
        </div>
      </div>
    </div>

    <p class="px-2 text-[11px] text-[var(--text-faint)]">
      Rates: TNB RP4 (2025&ndash;2027) schedule, Peninsular Malaysia, sourced 2026-09-11. ICPT surcharge and any
      subsequent tariff revisions are not included - verify current rates at mytnb.com.my before real billing use.
    </p>
  </div>
</template>
