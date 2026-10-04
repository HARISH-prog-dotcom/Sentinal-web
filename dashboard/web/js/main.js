// Dashboard entry point: creates the shared store, wires every page and runs the polling loop.

import { $ } from "./core/dom.js";
import { dashboardApi } from "./core/api.js";
import { eventTimestamp, severityInfo } from "./core/format.js";
import { initRouter } from "./core/router.js";
import { createStore } from "./core/store.js";
import { initThemeToggle } from "./core/theme.js";
import { createEventDrawer } from "./components/event-drawer.js";
import { initAssistantView } from "./views/assistant-view.js";
import { renderDetection } from "./views/detection-view.js";
import { initEventsView } from "./views/events-view.js";
import { renderActivity, renderOverview } from "./views/overview-view.js";
import { initSettingsView } from "./views/settings-view.js";

const POLL_INTERVAL_MS = 3000;

const store = createStore({
  events: [], stats: null, model: null, paused: false, selectedEventId: null,
  filters: { severity: "", category: "", query: "", range: "all" },
  sort: { key: "time", direction: -1 },
});
const seenEventIds = new Set();
let isFirstLoad = true;

/* ---------- live status in the sidebar ---------- */
function showStatus(mode) {
  const status = $("#status");
  status.classList.toggle("off", mode === "offline");
  status.classList.toggle("paused", store.state.paused && mode !== "offline");
  $("#statusText").textContent = mode === "offline" ? "Backend unreachable" : store.state.paused ? "Updates paused" : "Monitoring live";
  if (mode === "live") $("#updated").textContent = "Updated " + new Date().toLocaleTimeString();
}

/** Tell screen readers about new alerts. */
function announceNewAlerts(newEvents) {
  const alerts = newEvents.filter((event) => event.severity !== "SAFE");
  if (!alerts.length) return;
  const worst = alerts.reduce((a, b) => (severityInfo(b.severity).rank > severityInfo(a.severity).rank ? b : a));
  $("#announcer").textContent = `${alerts.length} new alert${alerts.length > 1 ? "s" : ""}. Most severe: ${severityInfo(worst.severity).label}, ${worst.category} from ${worst.ip}.`;
}

/* ---------- pages ---------- */
const drawer = createEventDrawer(store);
const eventsView = initEventsView(store, {
  openEvent: drawer.open,
  closeEvent: drawer.close,
  setPaused: (paused) => { store.update({ paused }); showStatus("live"); if (!paused) loadData(true); },
  resetDemo: async () => {
    try { await dashboardApi.resetDemo(); } catch (error) { showStatus("offline"); return; }
    seenEventIds.clear(); isFirstLoad = true;
    loadData(true);
  },
});
const showAssistant = initAssistantView();
const settingsView = initSettingsView();

/* ---------- polling ---------- */
async function loadModel() {
  try { store.update({ model: await dashboardApi.fetchModel() }); renderDetection(store.state.model); }
  catch (error) { /* retried after the next successful load */ }
}

async function loadData(force = false) {
  if (!force && (store.state.paused || document.hidden)) return;
  try {
    const [events, stats] = await Promise.all([dashboardApi.fetchEvents(), dashboardApi.fetchStats()]);
    const newEvents = isFirstLoad ? [] : events.filter((event) => !seenEventIds.has(event.id));
    store.update({ events, stats });
    showStatus("live");
    if (!store.state.model) loadModel();
    renderOverview(store.state, drawer.open);
    eventsView.render(new Set(newEvents.map((event) => event.id)));
    announceNewAlerts(newEvents);
    events.forEach((event) => seenEventIds.add(event.id));
    isFirstLoad = false;
  } catch (error) {
    showStatus("offline");
  }
}

/* ---------- start ---------- */
initThemeToggle({ button: $("#themeBtn"), label: $("#themeLabel"), storageKey: "sentinel-theme" });
initRouter({
  overview: { title: "Overview", subtitle: "Live summary of monitored traffic", onShow: () => renderActivity(store.state.events) },
  events: { title: "Events", subtitle: "Every monitored request, newest first" },
  detection: { title: "Detection", subtitle: "How SentinelWeb decides what is suspicious" },
  assistant: { title: "Assistant", subtitle: "Ask about alerts and security concepts", onShow: showAssistant },
  settings: { title: "Settings", subtitle: "AI assistant provider, model and API key", onShow: settingsView.onShow },
});
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && drawer.isOpen()) drawer.close(); });
let resizeTimer;
addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => renderActivity(store.state.events), 100); });
document.addEventListener("visibilitychange", () => { if (!document.hidden) loadData(); });

loadModel();
loadData(true);
setInterval(loadData, POLL_INTERVAL_MS);
// Keep the "5 min ago" chart moving even when no new events arrive.
setInterval(() => { if (store.state.events.some((event) => Date.now() - eventTimestamp(event) < 330000)) renderActivity(store.state.events); }, 15000);
