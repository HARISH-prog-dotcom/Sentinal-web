// Quick input: send one search or login from your own text, as an unsaved scenario.

import { $, $$ } from "../core/dom.js";

/** onSend(scenario, title) sends an unsaved scenario. */
export function initQuickInput(onSend) {
  $("#quickKind").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const kind = button.dataset.kind;
    $$("#quickKind button").forEach((item) => item.setAttribute("aria-pressed", item === button));
    $("#searchForm").hidden = kind !== "search";
    $("#loginForm").hidden = kind !== "login";
    $("#quickHint").hidden = kind !== "search";
  });

  $("#searchForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const query = $("#quickQuery").value;
    if (!query.trim()) return;
    onSend({ title: "Your search", expect: "ANY", steps: [{ method: "GET", path: "/demo/search", query: { q: query } }] }, "Your search");
  });

  $("#loginForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const body = { username: $("#quickUser").value, password: $("#quickPassword").value };
    $("#quickPassword").value = "";
    onSend({ title: "Your login", expect: "ANY", steps: [{ method: "POST", path: "/demo/login", body_type: "json", body }] }, "Your login");
  });

  $("#quickHint").addEventListener("click", (event) => {
    const example = event.target.closest("button");
    if (example) { $("#quickQuery").value = example.textContent; $("#quickQuery").focus(); }
  });
}
