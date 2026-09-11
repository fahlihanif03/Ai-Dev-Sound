<script setup>
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
</script>

<template>
  <button
    type="button"
    class="power-toggle"
    :class="[{ on: modelValue, disabled }, size]"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    @click="toggle"
  >
    <span class="track">
      <span class="knob"></span>
    </span>
    <span class="label">{{ modelValue ? onLabel : offLabel }}</span>
  </button>
</template>

<style scoped>
.power-toggle {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
}

.power-toggle.disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.track {
  width: 38px;
  height: 21px;
  border-radius: var(--radius-pill);
  /* var(--border-soft-2), not a hardcoded white rgba - the old hardcoded
   * value assumed a dark surface behind it (barely visible, which was the
   * point against near-black cards) and nearly disappeared once light-
   * themed pages (e.g. Energy Monitoring) put this on a white card. */
  background: var(--border-soft-2);
  position: relative;
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.power-toggle.sm .track {
  width: 30px;
  height: 17px;
}

.power-toggle.on .track {
  background: var(--accent-grad);
}

.knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
  transition: transform 0.2s ease;
}

.power-toggle.sm .knob {
  width: 13px;
  height: 13px;
}

.power-toggle.on .knob {
  transform: translateX(17px);
}

.power-toggle.sm.on .knob {
  transform: translateX(13px);
}

.label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}

.power-toggle.sm .label {
  font-size: 11.5px;
}

.power-toggle.on .label {
  color: var(--text);
}
</style>
