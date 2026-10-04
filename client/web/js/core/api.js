// The only module that talks to the Lab server.

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

const sendJson = (method, url, body) =>
  requestJson(url, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });

export const labApi = {
  getTarget: () => requestJson("/api/target"),
  getDemoEndpoints: () => requestJson("/api/demo-endpoints"),
  listScenarios: () => requestJson("/api/scenarios"),
  createScenario: (scenario) => sendJson("POST", "/api/scenarios", scenario),
  updateScenario: (id, scenario) => sendJson("PUT", `/api/scenarios/${encodeURIComponent(id)}`, scenario),
  deleteScenario: (id) => sendJson("DELETE", `/api/scenarios/${encodeURIComponent(id)}`),
  importScenarios: (data) => sendJson("POST", "/api/scenarios/import", data),
  exportScenarios: () => requestJson("/api/scenarios/export"),
  runScenario: (id) => sendJson("POST", `/api/run/${encodeURIComponent(id)}`),
  runUnsaved: (scenario) => sendJson("POST", "/api/run", scenario),
  resetTarget: () => sendJson("POST", "/api/reset"),
};
