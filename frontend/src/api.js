// Requests go through the Vite dev proxy (see vite.config.js), so the browser
// never makes a cross-origin call and no CORS setup is needed in development.
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

function toQuery(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    // Repeatable params (category, risk_level, ...) arrive as arrays.
    if (Array.isArray(value)) value.forEach((v) => search.append(key, v));
    else search.append(key, value);
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function get(path, params = {}) {
  const response = await fetch(`${BASE}${path}${toQuery(params)}`);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* non-JSON error body; keep the status line */
    }
    throw new Error(detail);
  }
  return response.json();
}

export const fetchDashboard = (params) => get("/hr-dashboard", params);
export const fetchFilterOptions = () => get("/analytics/filters");
export const fetchEmployees = (params) => get("/analytics/employees", params);
