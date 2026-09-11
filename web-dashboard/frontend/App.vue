<script setup>
import { onMounted } from "vue";
import TopNav from "./components/TopNav.vue";
import { useLiveStore } from "./stores/live.js";

const live = useLiveStore();
onMounted(live.connect);
</script>

<template>
  <TopNav />
  <main>
    <router-view />
  </main>
</template>
