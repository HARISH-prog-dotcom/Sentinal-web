// Severity badge: colour is always paired with its text label.

import { createElement } from "../core/dom.js";
import { severityInfo } from "../core/format.js";

export const severityBadge = (severity) => createElement("span", { class: "sev sev-" + severity }, severityInfo(severity).label);
