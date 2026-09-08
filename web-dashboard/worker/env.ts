import type { DashboardState } from "./dashboard-do";

export interface Env {
  ASSETS: Fetcher;
  DASHBOARD_STATE: DurableObjectNamespace<DashboardState>;
  INGEST_TOKEN?: string;
}
