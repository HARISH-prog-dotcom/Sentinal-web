// Scenario cards, grouped. Built-in and pack scenarios can be run or duplicated; custom ones can also be edited and deleted.

import { $, createElement, severityBadge } from "../core/dom.js";

/**
 * handlers: { onRun(scenario), onDuplicate(scenario), onEdit(scenario), onDelete(scenario) }
 * Returns { render(scenarios), setRunning(id, isRunning) }.
 */
export function createScenarioList(container, handlers) {
  function sourceTag(scenario) {
    if (scenario.source === "custom") return createElement("span", { class: "tag" }, "Custom");
    if (scenario.source.startsWith("pack:")) return createElement("span", { class: "tag", title: scenario.source.slice(5) }, "Pack");
    return null;
  }

  function card(scenario) {
    const actions = [
      createElement("button", { class: "btn small", type: "button", title: "Copy into the editor", onclick: () => handlers.onDuplicate(scenario) }, "Duplicate"),
      scenario.editable && createElement("button", { class: "btn small", type: "button", onclick: () => handlers.onEdit(scenario) }, "Edit"),
      scenario.editable && createElement("button", { class: "btn small danger", type: "button", onclick: () => handlers.onDelete(scenario) }, "Delete"),
      createElement("button", { class: "btn run", type: "button", "data-id": scenario.id, onclick: () => handlers.onRun(scenario) }, "Run"),
    ];
    return createElement("article", { class: "card" },
      createElement("div", { class: "top" }, createElement("h3", null, scenario.title, sourceTag(scenario)), severityBadge(scenario.expect)),
      createElement("div", { class: "sends mono" }, scenario.sends),
      scenario.description && createElement("p", { class: "about" }, scenario.description),
      createElement("span", { class: "expect" }, "Expected: ", createElement("b", null, scenario.expect_text)),
      createElement("div", { class: "foot" }, createElement("span"), createElement("div", { class: "actions" }, actions)));
  }

  function render(scenarios) {
    const groups = new Map();
    scenarios.forEach((scenario) => { if (!groups.has(scenario.group)) groups.set(scenario.group, []); groups.get(scenario.group).push(scenario); });
    container.replaceChildren(...[...groups].map(([name, list]) => createElement("div", { class: "group" },
      createElement("h3", null, name), createElement("div", { class: "cards" }, list.map(card)))));
    if (!scenarios.length) container.append(createElement("p", { class: "empty" }, "No scenarios yet. Create one with New scenario."));
  }

  function setRunning(id, isRunning) {
    const button = $(`.run[data-id="${CSS.escape(id)}"]`, container);
    if (button) button.replaceChildren(...(isRunning ? [createElement("span", { class: "spin", "aria-hidden": "true" }), "Sending"] : ["Run"]));
  }

  return { render, setRunning };
}
