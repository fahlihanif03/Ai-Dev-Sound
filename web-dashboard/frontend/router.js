import { createRouter, createWebHistory } from "vue-router";
import EnergyMonitoring from "./pages/EnergyMonitoring.vue";
import PredictiveMaintenance from "./pages/PredictiveMaintenance.vue";
import TariffStructure from "./pages/TariffStructure.vue";
import CarbonSustainability from "./pages/CarbonSustainability.vue";
import EnergyAnalytics from "./pages/EnergyAnalytics.vue";

/* Energy Monitoring is the main/default page per the design PRD (section 3/4). */
const routes = [
  { path: "/", name: "energy", component: EnergyMonitoring },
  { path: "/predictive-maintenance", name: "predictive-maintenance", component: PredictiveMaintenance },
  { path: "/tariff", name: "tariff", component: TariffStructure },
  { path: "/carbon", name: "carbon", component: CarbonSustainability },
  { path: "/analytics", name: "analytics", component: EnergyAnalytics },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
