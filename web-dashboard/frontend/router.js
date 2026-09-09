import { createRouter, createWebHistory } from "vue-router";
import EnergyMonitoring from "./pages/EnergyMonitoring.vue";
import PredictiveMaintenance from "./pages/PredictiveMaintenance.vue";

/* Energy Monitoring is the main/default page per the design PRD (section 3/4). */
const routes = [
  { path: "/", name: "energy", component: EnergyMonitoring },
  { path: "/predictive-maintenance", name: "predictive-maintenance", component: PredictiveMaintenance },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
