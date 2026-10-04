// Results feed: one card per run with HTTP statuses and SentinelWeb's verdict for those exact requests.

import { $, createElement, severityBadge, severityRank } from "../core/dom.js";

const STATUS_TEXT = { 200: "OK", 401: "Login failed", 403: "Blocked", 429: "Rate-limited" };
const statusClass = (code) => code === 403 ? "s403" : code === 429 ? "s429" : code >= 200 && code < 300 ? "s2" : "s4";
const EMPTY_TEXT = "Run a scenario to see what SentinelWeb does with it.";

function statusChips(statuses) {
  const counts = new Map();
  statuses.forEach((code) => counts.set(code, (counts.get(code) || 0) + 1));
  return [...counts].map(([code, count]) => createElement("span", { class: "chip " + statusClass(code) },
    `${count > 1 ? count + "× " : ""}${code} ${STATUS_TEXT[code] || ""}`.trim()));
}

function verdictSection(result) {
  const events = result.events || [], section = createElement("div", { class: "verdict" });
  const top = events.reduce((worst, event) => (!worst || severityRank(event.severity) >= severityRank(worst.severity) ? event : worst), null);
  if (!top) {
    section.append(createElement("p", { class: "note" }, "SentinelWeb did not log a new event for this."));
  } else {
    const line = createElement("div", { class: "line" }, severityBadge(top.severity), createElement("b", null, top.category), createElement("span", { class: "muted" }, "· " + top.action));
    const verdict = result.verdict;
    if (verdict && verdict.expected !== "ANY") {
      line.append(verdict.matches ? createElement("span", { class: "check ok" }, "✓ As expected")
                                  : createElement("span", { class: "check diff" }, `Expected ${verdict.expected.toLowerCase()}`));
    }
    section.append(line, createElement("pre", null, top.evidence), createElement("p", { class: "why" }, top.explanation));
    const others = events.filter((event) => event !== top), flagged = others.filter((event) => event.severity !== "SAFE");
    const normalCount = others.length - flagged.length;
    if (flagged.length) {
      const shown = flagged.slice(-6);
      section.append(createElement("p", { class: "note" }, "Also logged:"),
        createElement("ul", { class: "more" }, shown.map((event) => createElement("li", null, severityBadge(event.severity), createElement("span", null, `${event.category} · ${event.action}`)))));
      if (flagged.length > shown.length) section.append(createElement("p", { class: "note" }, `…and ${flagged.length - shown.length} more, see the dashboard.`));
    }
    if (normalCount) section.append(createElement("p", { class: "note" }, `Plus ${normalCount} normal request${normalCount > 1 ? "s" : ""} logged as Normal.`));
  }
  if ((result.statuses || []).includes(429)) {
    section.append(createElement("p", { class: "note" },
      "429 means this client or account is temporarily locked (60 s). Locked requests are rejected without being logged again. Use Reset SentinelWeb to lift the lock."));
  }
  return section;
}

export function createResultsFeed(list) {
  const removeEmptyState = () => $("#empty", list)?.remove();
  const timeNow = () => new Date().toLocaleTimeString();

  return {
    addResult(title, result) {
      removeEmptyState();
      list.prepend(createElement("li", { class: "res" },
        createElement("div", { class: "head" }, createElement("h3", null, title), createElement("time", null, result.at || timeNow())),
        createElement("div", { class: "req mono" }, result.sends || ""),
        createElement("div", { class: "chips" }, statusChips(result.statuses || [])),
        verdictSection(result)));
    },
    addNote(title, text) {
      removeEmptyState();
      list.prepend(createElement("li", { class: "res" }, createElement("div", { class: "head" }, createElement("h3", null, title), createElement("time", null, timeNow())),
        createElement("p", { class: "note", style: "margin-top:6px" }, text)));
    },
    addError(title, message) {
      removeEmptyState();
      list.prepend(createElement("li", { class: "res" }, createElement("div", { class: "head" }, createElement("h3", null, title), createElement("time", null, timeNow())),
        createElement("p", { class: "err", style: "margin-top:6px" }, message)));
    },
    clear() { list.replaceChildren(createElement("li", { class: "empty", id: "empty" }, EMPTY_TEXT)); },
  };
}
