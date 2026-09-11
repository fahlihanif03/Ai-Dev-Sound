<script setup>
import { onMounted } from "vue";
import Sidebar from "./components/Sidebar.vue";
import TopBar from "./components/TopBar.vue";
import { useLiveStore } from "./stores/live.js";

const live = useLiveStore();
onMounted(live.connect);
</script>

<template>
  <div class="flex min-h-screen items-start">
    <Sidebar />
    <div class="flex min-w-0 flex-1 flex-col gap-1">
      <TopBar />
      <main>
        <router-view />
      </main>
    </div>
  </div>
</template>
