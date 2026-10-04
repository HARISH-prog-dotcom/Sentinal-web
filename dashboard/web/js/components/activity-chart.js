// Stacked bar chart: events per 15-second bucket over the last 5 minutes, drawn as inline SVG.

import { createElement, createSvgElement } from "../core/dom.js";
import { SEVERITY, eventTimestamp } from "../core/format.js";

const BUCKET_COUNT = 20;
const BUCKET_MS = 15000;
const STACK_ORDER = ["SAFE", "LOW", "MEDIUM", "HIGH"];   // bottom to top

function countEventsPerBucket(events, now) {
  const buckets = Array.from({ length: BUCKET_COUNT }, () => ({ SAFE: 0, LOW: 0, MEDIUM: 0, HIGH: 0 }));
  for (const event of events) {
    const index = BUCKET_COUNT - 1 - Math.floor((now - eventTimestamp(event)) / BUCKET_MS);
    if (index >= 0 && index < BUCKET_COUNT && event.severity in buckets[index]) buckets[index][event.severity]++;
  }
  return buckets;
}

function axisLabel(x, y, text, anchor = "start") {
  const label = createSvgElement("text", { x, y, "text-anchor": anchor, class: "axis" });
  label.textContent = text;
  return label;
}

function showTooltip(tooltip, container, bucket, index, centerX, now) {
  const end = new Date(now - (BUCKET_COUNT - 1 - index) * BUCKET_MS), start = new Date(end - BUCKET_MS);
  const time = (date) => date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  tooltip.replaceChildren(createElement("div", { class: "t-head" }, `${time(start)} – ${time(end)}`),
    ...["HIGH", "MEDIUM", "LOW", "SAFE"].map((key) => createElement("div", null, createElement("span", null, SEVERITY[key].label),
      createElement("b", { class: "num" }, String(bucket[key])))));
  tooltip.hidden = false;
  const width = tooltip.offsetWidth;
  tooltip.style.left = Math.min(Math.max(0, centerX - width / 2), container.clientWidth - width) + "px";
  tooltip.style.top = "0px";
}

/** Draw the chart into `container` (which also holds the `tooltip` element). */
export function renderActivityChart(container, tooltip, events) {
  const width = container.clientWidth, height = container.clientHeight;
  if (!width) return;                                     // view hidden; drawn again when shown
  container.querySelector("svg")?.remove();

  const now = Date.now();
  const buckets = countEventsPerBucket(events, now);
  const bucketTotal = (bucket) => STACK_ORDER.reduce((sum, key) => sum + bucket[key], 0);
  const step = Math.ceil(Math.max(4, ...buckets.map(bucketTotal)) / 4), maxValue = step * 4;
  const left = 32, right = 4, top = 8, bottom = 22;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const slotWidth = plotWidth / BUCKET_COUNT, barWidth = Math.max(4, slotWidth * 0.6);

  const svg = createSvgElement("svg", { viewBox: `0 0 ${width} ${height}`, role: "img",
    "aria-label": `Events per 15 seconds over the last 5 minutes, ${buckets.reduce((n, b) => n + bucketTotal(b), 0)} in total` });
  for (let gridIndex = 0; gridIndex <= 4; gridIndex++) {
    const y = top + plotHeight - plotHeight * gridIndex / 4;
    svg.append(createSvgElement("line", { x1: left, x2: width - right, y1: y, y2: y, class: "grid-line" }), axisLabel(left - 8, y + 4, step * gridIndex, "end"));
  }
  buckets.forEach((bucket, index) => {
    const x = left + index * slotWidth + (slotWidth - barWidth) / 2;
    const hoverArea = createSvgElement("rect", { x: left + index * slotWidth, y: top, width: slotWidth, height: plotHeight, class: "hit" });
    hoverArea.addEventListener("mouseenter", () => showTooltip(tooltip, container, bucket, index, x + barWidth / 2, now));
    hoverArea.addEventListener("mouseleave", () => { tooltip.hidden = true; });
    svg.append(hoverArea);
    let y = top + plotHeight;
    for (const key of STACK_ORDER) {
      if (!bucket[key]) continue;
      const barHeight = bucket[key] / maxValue * plotHeight;
      y -= barHeight;
      const bar = createSvgElement("rect", { x, y, width: barWidth, height: Math.max(1, barHeight - 1), rx: 2, class: "b-" + key });
      bar.style.pointerEvents = "none";
      svg.append(bar);
    }
  });
  svg.append(axisLabel(left, height - 4, "5 min ago"), axisLabel(width - right, height - 4, "now", "end"));
  container.prepend(svg);
}
