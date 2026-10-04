// Overview page: threat level, KPI tiles, activity chart, latest alerts, breakdowns and top sources.

import { $, createElement } from "../core/dom.js";
import { actionGroup, eventClock, eventTimestamp, formatNumber, isEnforcement, severityInfo } from "../core/format.js";
import { renderActivityChart } from "../components/activity-chart.js";
import { severityBadge } from "../components/badges.js";

const FIVE_MINUTES = 300000, TWO_MINUTES = 120000;

/** Threat level from the last 2 minutes: any HIGH = High alert, any MEDIUM = Elevated. */
function threatLevel(events, now) {
  const recent = events.filter((event) => now - eventTimestamp(event) < TWO_MINUTES);
  if (recent.some((event) => event.severity === "HIGH")) return ["High alert", "var(--high)", "High-severity activity in the last 2 minutes."];
  if (recent.some((event) => event.severity === "MEDIUM")) return ["Elevated", "var(--medium)", "Medium-severity activity in the last 2 minutes."];
  if (events.length) return ["Calm", "var(--safe)", "No suspicious activity in the last 2 minutes."];
  return ["Idle", "var(--ink-2)", "No traffic recorded yet."];
}

function setKpi(id, value, addedRecently) {
  $(`#${id}`).textContent = formatNumber(value);
  const subtitle = $(`#${id}Sub`);
  subtitle.textContent = addedRecently ? `+${formatNumber(addedRecently)} in last 5 min` : "None in last 5 min";
  subtitle.classList.toggle("up", addedRecently > 0);
}

function renderBarList(container, entries, scaleTotal) {
  container.replaceChildren(...entries.map(([name, count]) => createElement("div", { class: "bar-row" },
    createElement("span", null, name), createElement("span", { class: "num" }, formatNumber(count)),
    createElement("div", { class: "track", "aria-hidden": "true" }, createElement("i", { style: `width:${scaleTotal ? count / scaleTotal * 100 : 0}%` })))));
}

function renderLatestAlerts(events, openEvent) {
  const list = $("#latest"), alerts = events.filter((event) => event.severity !== "SAFE").slice(0, 5);
  list.replaceChildren(...alerts.map((event) => createElement("li", null,
    createElement("button", { type: "button", onclick: () => openEvent(event.id) }, severityBadge(event.severity),
      createElement("span", { class: "a-main" }, createElement("b", null, event.category), createElement("span", null, `${event.action} · ${event.ip}`)),
      createElement("time", null, eventClock(event))))));
  if (!alerts.length) list.append(createElement("li", { class: "empty" }, "No alerts yet."));
}

function renderTopSources(events) {
  const sources = new Map();
  for (const event of events) {
    const source = sources.get(event.ip) || { ip: event.ip, requests: 0, suspicious: 0, lastSeen: -Infinity, lastTime: event.time, worst: "SAFE" };
    source.requests++;
    if (event.severity !== "SAFE") source.suspicious++;
    if (eventTimestamp(event) > source.lastSeen) { source.lastSeen = eventTimestamp(event); source.lastTime = event.time; }
    if (severityInfo(event.severity).rank > severityInfo(source.worst).rank) source.worst = event.severity;
    sources.set(event.ip, source);
  }
  const rows = [...sources.values()].sort((a, b) => b.suspicious - a.suspicious || b.requests - a.requests).slice(0, 8);
  $("#sources").replaceChildren(...rows.map((source) => createElement("tr", { class: source.worst },
    createElement("td", { class: "mono" }, source.ip), createElement("td", { class: "r num" }, formatNumber(source.requests)),
    createElement("td", { class: "r num" }, formatNumber(source.suspicious)), createElement("td", null, severityBadge(source.worst)),
    createElement("td", { class: "mono" }, source.lastTime.replace("T", " ")))));
  if (!rows.length) $("#sources").append(createElement("tr", null, createElement("td", { colspan: 5, class: "empty" }, "No traffic yet.")));
}

export function renderActivity(events) {
  renderActivityChart($("#chart"), $("#tip"), events);
}

/** Render the whole Overview page from the shared state. */
export function renderOverview({ events, stats }, openEvent) {
  if (!stats) return;
  const now = Date.now(), recent = events.filter((event) => now - eventTimestamp(event) < FIVE_MINUTES);
  setKpi("kTotal", stats.total, recent.length);
  setKpi("kSusp", stats.suspicious, recent.filter((event) => event.severity !== "SAFE").length);
  setKpi("kHigh", stats.by_severity.HIGH || 0, recent.filter((event) => event.severity === "HIGH").length);
  setKpi("kMed", stats.by_severity.MEDIUM || 0, recent.filter((event) => event.severity === "MEDIUM").length);
  setKpi("kAct", events.filter(isEnforcement).length, recent.filter(isEnforcement).length);

  const [label, color, description] = threatLevel(events, now);
  $("#level").textContent = label; $("#level").style.setProperty("--c", color); $("#levelText").textContent = description;

  const recentSuspicious = recent.filter((event) => event.severity !== "SAFE").length, navCount = $("#navCount");
  navCount.hidden = !recentSuspicious; navCount.textContent = recentSuspicious;
  navCount.classList.toggle("hot", recent.some((event) => event.severity === "HIGH"));
  navCount.setAttribute("aria-label", `${recentSuspicious} suspicious events in the last 5 minutes`);

  renderActivity(events);
  renderLatestAlerts(events, openEvent);
  const categories = Object.entries(stats.by_category);
  renderBarList($("#types"), categories, Math.max(1, ...categories.map((entry) => entry[1])));
  if (!categories.length) $("#types").append(createElement("p", { class: "empty" }, "Nothing suspicious yet."));
  const actionCounts = { Blocked: 0, Flagged: 0, "Rate-limited": 0, Allowed: 0 };
  events.forEach((event) => actionCounts[actionGroup(event.action)]++);
  renderBarList($("#actions"), Object.entries(actionCounts).map(([name, count]) =>
    [`${name} · ${events.length ? Math.round(count / events.length * 100) : 0}%`, count]), events.length);
  renderTopSources(events);
}
