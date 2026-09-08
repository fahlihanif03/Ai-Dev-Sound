<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  active: { type: Boolean, default: false },
  message: { type: String, default: "" },
  updatedAt: { type: [Number, String], default: 0 },
});

const dismissed = ref(false);

/* Per the design PRD: dismissible, but reappears if the condition is still
 * active on the next update - so a dismissal only lasts until new data
 * arrives, not for the whole duration of the anomaly. */
watch(
  () => props.updatedAt,
  () => {
    if (props.active) dismissed.value = false;
  }
);
</script>

<template>
  <Transition name="fade">
    <div v-if="active && !dismissed" class="alert-strip" role="alert">
      <span class="alert-dot"></span>
      <span class="alert-text">{{ message }}</span>
      <button class="dismiss" aria-label="Dismiss" @click="dismissed = true">&times;</button>
    </div>
  </Transition>
</template>

<style scoped>
.alert-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  border-radius: var(--radius-md);
  background: var(--amber-soft);
  color: var(--amber);
  font-size: 13px;
  font-weight: 500;
}

.alert-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.alert-text {
  flex: 1;
}

.dismiss {
  border: none;
  background: transparent;
  color: currentColor;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 4px;
  opacity: 0.7;
}

.dismiss:hover {
  opacity: 1;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
