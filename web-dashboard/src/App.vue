<script setup>
import { onMounted } from "vue";
import AppHeader from "./components/AppHeader.vue";
import { connectLiveState } from "./lib/live-state.js";

onMounted(connectLiveState);
</script>

<template>
  <AppHeader />
  <main>
    <router-view />
  </main>
</template>
