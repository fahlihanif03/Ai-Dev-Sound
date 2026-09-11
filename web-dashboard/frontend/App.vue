<script setup>
import { onMounted } from "vue";
import Sidebar from "./components/Sidebar.vue";
import TopBar from "./components/TopBar.vue";
import { connectLiveState } from "./lib/live-state.js";

onMounted(connectLiveState);
</script>

<template>
  <div class="shell">
    <Sidebar />
    <div class="main">
      <TopBar />
      <main>
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  align-items: flex-start;
  min-height: 100vh;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

@media (max-width: 860px) {
  .shell {
    flex-direction: column;
  }
}
</style>
