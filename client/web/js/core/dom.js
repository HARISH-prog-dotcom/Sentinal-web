// DOM helpers. Results contain attack strings from SentinelWeb's log, so everything is
// rendered with textContent (via createElement), never innerHTML.

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

/** Create an element. Strings in `children` become text nodes. */
export function createElement(tag, props, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === "class") element.className = value;
    else if (key.startsWith("on")) element.addEventListener(key.slice(2), value);
    else element.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) if (child != null && child !== false) element.append(child);
  return element;
}

export const SEVERITY = { HIGH: ["High", 3], MEDIUM: ["Medium", 2], LOW: ["Low", 1], SAFE: ["Normal", 0], ANY: ["Any", -1] };
export const severityBadge = (severity) => createElement("span", { class: "sev sev-" + severity }, (SEVERITY[severity] || [severity])[0]);
export const severityRank = (severity) => (SEVERITY[severity] || ["", 0])[1];
