<script setup>
import { computed } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: true },
  onLabel: { type: String, default: "On" },
  offLabel: { type: String, default: "Off" },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: "md" }, // "md" | "sm"
});
const emit = defineEmits(["update:modelValue"]);

function toggle() {
  if (props.disabled) return;
  emit("update:modelValue", !props.modelValue);
}

// Sizing varies enough between "sm"/"md" (track, knob, translate distance,
// label size) that computing full class strings here reads more clearly
// than several parallel `:class="{ sm: ... }"` bindings across 3 elements.
const trackClasses = computed(() => [
  props.size === "sm" ? "h-[17px] w-[30px]" : "h-[21px] w-[38px]",
  props.modelValue ? "bg-[image:var(--accent-grad)]" : "bg-[var(--border-soft-2)]",
]);
const knobClasses = computed(() => [
  props.size === "sm" ? "h-[13px] w-[13px]" : "h-[17px] w-[17px]",
  props.modelValue ? (props.size === "sm" ? "translate-x-[13px]" : "translate-x-[17px]") : "translate-x-0",
]);
const labelClasses = computed(() => [
  props.size === "sm" ? "text-[11.5px]" : "text-[12.5px]",
  props.modelValue ? "text-[var(--text)]" : "text-[var(--text-muted)]",
]);
</script>

<template>
  <button
    type="button"
    class="inline-flex cursor-pointer items-center gap-2.5 border-none bg-transparent p-0"
    :class="{ 'cursor-not-allowed opacity-45': disabled }"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    @click="toggle"
  >
    <span class="relative shrink-0 rounded-[var(--radius-pill)] transition-colors duration-200" :class="trackClasses">
      <span
        class="absolute top-0.5 left-0.5 rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.35)] transition-transform duration-200"
        :class="knobClasses"
      ></span>
    </span>
    <span class="font-semibold whitespace-nowrap" :class="labelClasses">{{ modelValue ? onLabel : offLabel }}</span>
  </button>
</template>
