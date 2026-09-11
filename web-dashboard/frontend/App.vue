<script setup>
import { onMounted } from "vue";
import TopNav from "./components/TopNav.vue";
import { connectLiveState } from "./lib/live-state.js";

onMounted(connectLiveState);
</script>

<template>
  <TopNav />
  <main>
    <router-view />
  </main>
</template>
