// DOM helpers. Every value from the API is shown with textContent, never innerHTML:
// logged input may contain attack strings and the dashboard must not run them.

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

/** Create an element. Strings in `children` become text nodes (safe for attack strings). */
export function createElement(tag, props, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === "class") element.className = value;
    else if (key === "style") element.style.cssText = value;
    else if (key.startsWith("on")) element.addEventListener(key.slice(2), value);
    else element.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) if (child != null && child !== false) element.append(child);
  return element;
}

/** Create an SVG element with attributes. */
export function createSvgElement(tag, attributes) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const name in attributes) element.setAttribute(name, attributes[name]);
  return element;
}

export const prefersReducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
