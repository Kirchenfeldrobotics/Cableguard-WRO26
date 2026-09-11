const seg = encodeURIComponent;

/** Every app URL is built here so links never drift from the folder structure. */
export const routes = {
  dashboard: "/",
  live: "/live",
  ropes: "/ropes",
  settings: "/settings",
  rope: (ropeId: string) => `/ropes/${seg(ropeId)}`,
  run: (ropeId: string, runId: string) => `/ropes/${seg(ropeId)}/runs/${seg(runId)}`,
  defect: (ropeId: string, runId: string, defectId: string) =>
    `/ropes/${seg(ropeId)}/runs/${seg(runId)}/defects/${seg(defectId)}`,
  compare: (ropeId?: string) => (ropeId ? `/compare?rope=${seg(ropeId)}` : "/compare"),
};
