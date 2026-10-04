// The only module that talks to the backend. Paths are relative, so the UI works on any host or IP.

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

const sendJson = (method, url, body) =>
  requestJson(url, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });

export const dashboardApi = {
  fetchEvents: (limit = 500) => requestJson(`/api/events?limit=${limit}`),
  fetchStats: () => requestJson("/api/stats"),
  fetchModel: () => requestJson("/api/model"),
  resetDemo: () => sendJson("POST", "/api/reset"),
  sendChat: (message) => sendJson("POST", "/api/chat", { message }),
  getAiSettings: () => requestJson("/api/settings/ai"),
  saveAiSettings: (settings) => sendJson("PUT", "/api/settings/ai", settings),
  clearAiSettings: () => sendJson("DELETE", "/api/settings/ai"),
  testAiSettings: () => sendJson("POST", "/api/settings/ai/test"),
};
