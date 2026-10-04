// Event details drawer: evidence, explanation and (for model detections) the ML score bar.

import { $, createElement, prefersReducedMotion } from "../core/dom.js";
import { severityBadge } from "./badges.js";

const DEFAULT_THRESHOLD = 0.7;

/**
 * store: shared store (uses state.events, state.model, state.selectedEventId).
 * Returns { open(eventId), close() }.
 */
export function createEventDrawer(store) {
  const drawer = $("#drawer"), scrim = $("#scrim");
  let focusBeforeOpen = null;

  function copyButton(text) {
    const button = createElement("button", { class: "btn icon", type: "button", "aria-label": "Copy evidence" }, "⧉");
    button.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(text); button.textContent = "✓"; button.setAttribute("aria-label", "Copied"); }
      catch (error) { button.textContent = "!"; button.setAttribute("aria-label", "Copy failed"); }
      setTimeout(() => { button.textContent = "⧉"; button.setAttribute("aria-label", "Copy evidence"); }, 1500);
    });
    return button;
  }

  function modelScoreSection(evidence) {
    const match = /ML score (\d(?:\.\d+)?)/.exec(evidence);
    if (!match) return null;
    const score = Math.min(1, Number(match[1])), threshold = store.state.model?.threshold ?? DEFAULT_THRESHOLD, isAbove = score >= threshold;
    const meter = createElement("div", { class: "meter", role: "meter", "aria-valuemin": "0", "aria-valuemax": "1", "aria-valuenow": String(score), "aria-label": "ML score" },
      createElement("i", { style: `width:${score * 100}%;--c:${isAbove ? "var(--medium)" : "var(--low)"}` }),
      createElement("span", { class: "th", style: `left:${threshold * 100}%` }, createElement("span", null, `threshold ${threshold.toFixed(2)}`)));
    return createElement("section", null, createElement("h3", null, "Model score"),
      createElement("div", { class: "score-row" }, createElement("b", null, score.toFixed(2)),
        createElement("span", { class: "muted" }, isAbove ? "Above threshold" : "Below threshold")),
      meter, createElement("p", { class: "caption" }, "Model similarity score, not a probability of attack."));
  }

  function renderContent(event) {
    drawer.replaceChildren(...[
      createElement("div", { class: "d-head" }, createElement("h2", { id: "dTitle" }, event.category),
        createElement("button", { class: "btn icon d-close", type: "button", "aria-label": "Close details", onclick: close }, "✕")),
      createElement("div", { class: "d-meta" }, severityBadge(event.severity), createElement("span", { class: "muted" }, `Event #${event.id}`)),
      createElement("dl", null,
        createElement("dt", null, "Time"), createElement("dd", { class: "mono" }, event.time.replace("T", " ")),
        createElement("dt", null, "Action taken"), createElement("dd", null, event.action),
        createElement("dt", null, "Request"), createElement("dd", { class: "mono" }, `${event.method} ${event.path}`),
        createElement("dt", null, "Source IP"), createElement("dd", { class: "mono" }, event.ip)),
      createElement("section", null, createElement("h3", null, "Evidence"), createElement("div", { class: "code" }, createElement("pre", null, event.evidence), copyButton(event.evidence))),
      createElement("section", null, createElement("h3", null, "Why it matters"), createElement("p", null, event.explanation)),
      modelScoreSection(event.evidence)].filter(Boolean));
  }

  function open(eventId) {
    const event = store.state.events.find((item) => item.id === eventId);
    if (!event) return;
    if (!store.state.selectedEventId) focusBeforeOpen = document.activeElement;
    renderContent(event);
    store.update({ selectedEventId: eventId });
    drawer.hidden = false; scrim.hidden = false;
    requestAnimationFrame(() => { drawer.classList.add("open"); scrim.classList.add("open"); $(".d-close", drawer).focus(); });
  }

  function close() {
    if (!store.state.selectedEventId) return;
    store.update({ selectedEventId: null });
    drawer.classList.remove("open"); scrim.classList.remove("open");
    setTimeout(() => { if (!store.state.selectedEventId) { drawer.hidden = true; scrim.hidden = true; } }, prefersReducedMotion ? 0 : 160);
    focusBeforeOpen?.focus?.();
  }

  scrim.addEventListener("click", close);
  // Keep keyboard focus inside the open drawer.
  drawer.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const buttons = [...drawer.querySelectorAll("button")];
    if (!buttons.length) return;
    if (event.shiftKey && document.activeElement === buttons[0]) { event.preventDefault(); buttons[buttons.length - 1].focus(); }
    else if (!event.shiftKey && document.activeElement === buttons[buttons.length - 1]) { event.preventDefault(); buttons[0].focus(); }
  });
  return { open, close, isOpen: () => Boolean(store.state.selectedEventId) };
}
