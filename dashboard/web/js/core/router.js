// Hash router: #overview, #events, #detection, #assistant, #settings.

import { $, $$ } from "./dom.js";

/**
 * views: { name: { title, subtitle, onShow?() } }. The first view is the default.
 * Returns the name of the view currently shown.
 */
export function initRouter(views) {
  const names = Object.keys(views);
  let current = names[0];

  function showView() {
    const requested = location.hash.slice(1);
    current = names.includes(requested) ? requested : names[0];
    names.forEach((name) => { $(`#view-${name}`).hidden = name !== current; });
    $$("nav a").forEach((link) => (link.dataset.view === current ? link.setAttribute("aria-current", "page") : link.removeAttribute("aria-current")));
    const { title, subtitle, onShow } = views[current];
    $("#pageTitle").textContent = title;
    $("#pageSub").textContent = subtitle;
    document.title = `${title} · SentinelWeb`;
    onShow?.();
  }

  addEventListener("hashchange", showView);
  showView();
  return { currentView: () => current };
}
