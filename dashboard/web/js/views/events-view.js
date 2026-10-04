// Events page: filters, sortable table, CSV export, pause, and "Clear all events".

import { $, $$, createElement, prefersReducedMotion } from "../core/dom.js";
import { eventClock, eventTimestamp, formatNumber, severityInfo } from "../core/format.js";
import { severityBadge } from "../components/badges.js";

const RANGE_LIMITS = { "5m": 300000, "1h": 3600000 };
const CSV_COLUMNS = ["time", "severity", "category", "action", "method", "path", "ip", "evidence", "explanation"];

/** Events after filters and sorting. */
function filterAndSort(events, filters, sort) {
  const now = Date.now(), maxAge = RANGE_LIMITS[filters.range] || Infinity, query = filters.query.toLowerCase();
  const matches = events.filter((event) => (!filters.severity || event.severity === filters.severity)
    && (!filters.category || event.category === filters.category) && now - eventTimestamp(event) <= maxAge
    && (!query || `${event.evidence} ${event.ip} ${event.path} ${event.category}`.toLowerCase().includes(query)));
  const sortValue = (event) => sort.key === "time" ? event.id : sort.key === "severity" ? severityInfo(event.severity).rank : String(event[sort.key]);
  return matches.sort((a, b) => {
    const x = sortValue(a), y = sortValue(b);
    return (typeof x === "number" ? x - y : x.localeCompare(y)) * sort.direction || b.id - a.id;
  });
}

function downloadCsv(events) {
  // Prefix formula-like cells so spreadsheet apps don't evaluate logged attack strings.
  const csvCell = (value) => {
    let text = String(value ?? "");
    if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  };
  const csv = [CSV_COLUMNS.join(","), ...events.map((event) => CSV_COLUMNS.map((column) => csvCell(event[column])).join(","))].join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const link = createElement("a", { href: url, download: `sentinelweb-events-${new Date().toISOString().slice(0, 19).replace(/:/g, "")}.csv` });
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Wire up the Events page. Returns render(freshIds) for the polling loop.
 * actions: { openEvent(id), closeEvent(), resetDemo(), setPaused(bool) }
 */
export function initEventsView(store, actions) {
  const { state } = store;
  const categorySelect = $("#fCat"), menu = $("#moreMenu"), moreButton = $("#moreBtn");

  function syncCategoryOptions() {
    const names = new Set([...Object.keys(state.stats?.by_category || {}), ...state.events.map((event) => event.category), "Normal request"]);
    [...names].sort().forEach((name) => {
      if (![...categorySelect.options].some((option) => option.value === name)) categorySelect.append(createElement("option", { value: name }, name));
    });
  }

  function render(freshIds = new Set()) {
    syncCategoryOptions();
    const visible = filterAndSort(state.events, state.filters, state.sort), body = $("#rows");
    body.replaceChildren(...visible.map((event) => {
      const isFresh = freshIds.has(event.id) && !prefersReducedMotion;
      const row = createElement("tr", { class: `${event.severity} click${event.id === state.selectedEventId ? " sel" : ""}${isFresh ? " fresh" : ""}`, tabindex: "0",
        "aria-label": `${severityInfo(event.severity).label}, ${event.category}, ${eventClock(event)}. Open details` },
        createElement("td", { class: "mono" }, eventClock(event)), createElement("td", null, severityBadge(event.severity)),
        createElement("td", null, event.category), createElement("td", null, event.action),
        createElement("td", { class: "mono" }, `${event.method} ${event.path}`), createElement("td", { class: "mono" }, event.ip),
        createElement("td", { class: "mono ev", title: event.evidence }, event.evidence));
      row.addEventListener("click", () => actions.openEvent(event.id));
      row.addEventListener("keydown", (key) => { if (key.key === "Enter" || key.key === " ") { key.preventDefault(); actions.openEvent(event.id); } });
      return row;
    }));
    if (!visible.length) body.append(createElement("tr", null, createElement("td", { colspan: 7, class: "empty" },
      state.events.length ? "No events match these filters."
        : ["No events yet. Send test traffic with SentinelWeb Lab (", createElement("code", null, "python client/app.py"), ") or ",
           createElement("code", null, "python scripts/simulate.py"), "."])));
    $("#rowcount").textContent = `Showing ${formatNumber(visible.length)} of ${formatNumber(state.events.length)} events` + (state.paused ? " · live updates paused" : "");
    $$("#evHead th[data-key]").forEach((header) => {
      const isSorted = header.dataset.key === state.sort.key;
      if (isSorted) header.setAttribute("aria-sort", state.sort.direction < 0 ? "descending" : "ascending"); else header.removeAttribute("aria-sort");
      $(".arrow", header).textContent = isSorted ? (state.sort.direction < 0 ? "↓" : "↑") : "↕";
    });
  }

  const setFilter = (changes) => { store.update({ filters: { ...state.filters, ...changes } }); render(); };
  $("#seg").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    $$("#seg button").forEach((item) => item.setAttribute("aria-pressed", item === button));
    setFilter({ severity: button.dataset.sev });
  });
  categorySelect.addEventListener("change", (event) => setFilter({ category: event.target.value }));
  $("#fRange").addEventListener("change", (event) => setFilter({ range: event.target.value }));
  $("#fQ").addEventListener("input", (event) => setFilter({ query: event.target.value.trim() }));
  $("#evHead").addEventListener("click", (event) => {
    const header = event.target.closest("th[data-key]");
    if (!header) return;
    const key = header.dataset.key, defaultDirection = key === "time" || key === "severity" ? -1 : 1;
    store.update({ sort: { key, direction: state.sort.key === key ? -state.sort.direction : defaultDirection } });
    render();
  });
  $("#pauseBtn").addEventListener("click", () => {
    const paused = !state.paused;
    $("#pauseBtn").setAttribute("aria-pressed", paused);
    $("#pauseBtn").textContent = paused ? "Resume" : "Pause";
    actions.setPaused(paused);
    render();
  });
  $("#csvBtn").addEventListener("click", () => downloadCsv(filterAndSort(state.events, state.filters, state.sort)));

  // "More" menu and the confirmation dialog for clearing events
  const setMenuOpen = (open) => { menu.hidden = !open; moreButton.setAttribute("aria-expanded", open); if (open) $("button", menu).focus(); };
  moreButton.addEventListener("click", () => setMenuOpen(menu.hidden));
  document.addEventListener("click", (event) => { if (!menu.hidden && !event.target.closest(".menu-wrap")) setMenuOpen(false); });
  $("#clearBtn").addEventListener("click", () => { setMenuOpen(false); $("#confirm").showModal(); });
  $("#cCancel").addEventListener("click", () => $("#confirm").close());
  $("#cOk").addEventListener("click", async () => {
    $("#confirm").close();
    actions.closeEvent();
    categorySelect.replaceChildren(createElement("option", { value: "" }, "All event types"));
    store.update({ filters: { ...state.filters, category: "" } });
    await actions.resetDemo();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !menu.hidden) { setMenuOpen(false); moreButton.focus(); }
  });

  // Re-render when the selected event changes (row highlight)
  store.subscribe((_, changedKeys) => { if (changedKeys.includes("selectedEventId")) render(); });
  return { render };
}
