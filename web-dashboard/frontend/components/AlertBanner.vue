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
    <div
      v-if="active && !dismissed"
      class="flex items-center gap-2.5 rounded-[var(--radius-md)] bg-[var(--amber-soft)] px-4.5 py-3 text-[13px] font-medium text-[var(--amber)]"
      role="alert"
    >
      <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-current"></span>
      <span class="flex-1">{{ message }}</span>
      <button
        class="cursor-pointer border-none bg-transparent px-1 py-0.5 text-base leading-none text-current opacity-70 hover:opacity-100"
        aria-label="Dismiss"
        @click="dismissed = true"
      >&times;</button>
    </div>
  </Transition>
</template>

<style scoped>
/* Vue's <Transition name="fade"> needs actual named CSS classes to hook
 * into - not expressible as inline utility classes on the elements
 * themselves, so this is the one bit that has to stay real CSS. */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
