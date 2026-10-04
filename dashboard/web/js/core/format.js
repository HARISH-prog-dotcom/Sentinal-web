// Formatting and event helpers shared by all views.

export const SEVERITY = {
  HIGH: { label: "High", rank: 3 },
  MEDIUM: { label: "Medium", rank: 2 },
  LOW: { label: "Low", rank: 1 },
  SAFE: { label: "Normal", rank: 0 },
};

export const severityInfo = (severity) => SEVERITY[severity] || { label: severity, rank: 0 };
export const eventTimestamp = (event) => new Date(event.time).getTime();
export const eventClock = (event) => event.time.slice(11, 19);
export const formatNumber = (n) => Number(n).toLocaleString();
export const formatPercent = (fraction) => (fraction * 100).toFixed(1) + "%";

/** Group the detailed action text into Blocked / Flagged / Rate-limited / Allowed. */
export function actionGroup(action) {
  if (/^Blocked/.test(action)) return "Blocked";
  if (/^Flagged/.test(action)) return "Flagged";
  if (/^Rate-limited/.test(action)) return "Rate-limited";
  return "Allowed";
}

export const isEnforcement = (event) => ["Blocked", "Rate-limited"].includes(actionGroup(event.action));
