// SentinelWeb Lab entry point: loads scenarios, wires the views and runs the full demo.

import { $ } from "./core/dom.js";
import { labApi } from "./core/api.js";
import { initThemeToggle } from "./core/theme.js";
import { initQuickInput } from "./views/quick-input.js";
import { createResultsFeed } from "./views/results-feed.js";
import { createScenarioEditor } from "./views/scenario-editor.js";
import { createScenarioList } from "./views/scenario-list.js";

// Same sequence as scripts/simulate.py. The wait lets the request-rate window clear before the flood.
const FULL_DEMO_STEPS = ["normal-search", "normal-items", "sqli-rule", "xss-rule", "ml-sleep", "ml-quote", "brute-force", { waitSeconds: 11 }, "flood"];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let scenarios = [];
let isBusy = false;
const feed = createResultsFeed($("#feed"));

/* ---------- busy state: one run at a time ---------- */
function setBusy(busy) {
  isBusy = busy;
  document.querySelectorAll(".run, #demoBtn, #resetBtn, #searchForm button, #loginForm button, #editorRun, #editorSave").forEach((button) => { button.disabled = busy; });
}

async function runExclusive(task) {
  if (isBusy) return;
  setBusy(true);
  try { await task(); } finally { setBusy(false); }
}

/* ---------- scenarios ---------- */
async function runScenario(scenario) {
  list.setRunning(scenario.id, true);
  try { feed.addResult(scenario.title, await labApi.runScenario(scenario.id)); }
  catch (error) { feed.addError(scenario.title, error.message); }
  finally { list.setRunning(scenario.id, false); }
}

async function loadScenarios() {
  try {
    scenarios = await labApi.listScenarios();
    list.render(scenarios);
    editor.setKnownGroups([...new Set(scenarios.map((scenario) => scenario.group))]);
    const custom = scenarios.filter((scenario) => scenario.source === "custom").length;
    $("#scenarioCount").textContent = `${scenarios.length} scenarios · ${custom} custom`;
  } catch (error) {
    $("#groups").replaceChildren(document.createTextNode(error.message));
  }
}

const list = createScenarioList($("#groups"), {
  onRun: (scenario) => runExclusive(() => runScenario(scenario)),
  onDuplicate: (scenario) => editor.open(scenario, "duplicate"),
  onEdit: (scenario) => editor.open(scenario, "edit"),
  onDelete: async (scenario) => {
    if (!confirm(`Delete the custom scenario "${scenario.title}"?`)) return;
    try { await labApi.deleteScenario(scenario.id); await loadScenarios(); }
    catch (error) { feed.addError("Delete scenario", error.message); }
  },
});

const editor = createScenarioEditor({
  onSave: async (scenario, existingId) => {
    const saved = existingId ? await labApi.updateScenario(existingId, scenario) : await labApi.createScenario(scenario);
    await loadScenarios();
    feed.addNote(existingId ? "Scenario updated" : "Scenario saved", `"${saved.title}" is in the ${saved.group} group. Press Run to send it.`);
  },
  onRunUnsaved: async (scenario) => {
    setBusy(true);
    try { feed.addResult(scenario.title, await labApi.runUnsaved(scenario)); } finally { setBusy(false); }
  },
});

/* ---------- import / export ---------- */
$("#importBtn").addEventListener("click", () => $("#importFile").click());
$("#importFile").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  try {
    const result = await labApi.importScenarios(JSON.parse(await file.text()));
    await loadScenarios();
    const skipped = result.skipped.map((item) => `${item.item}: ${item.reason}`).join(" ");
    feed.addNote("Import", `${result.added.length} scenario(s) added.${result.skipped.length ? ` Skipped ${result.skipped.length}. ${skipped}` : ""}`);
  } catch (error) { feed.addError("Import", error instanceof SyntaxError ? "That file is not valid JSON." : error.message); }
});
$("#exportBtn").addEventListener("click", async () => {
  try {
    const data = await labApi.exportScenarios();
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = Object.assign(document.createElement("a"), { href: url, download: "sentinelweb-lab-scenarios.json" });
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    if (!data.scenarios.length) feed.addNote("Export", "You have no custom scenarios yet, so the file is empty.");
  } catch (error) { feed.addError("Export", error.message); }
});

/* ---------- full demo ---------- */
async function runFullDemo() {
  const progress = $("#progress");
  progress.classList.add("show");
  const showStep = (index, text) => {
    $("#progressText").textContent = `Step ${index} of ${FULL_DEMO_STEPS.length}: ${text}`;
    $("#progressBar").style.width = (index - 1) / FULL_DEMO_STEPS.length * 100 + "%";
  };
  try {
    await labApi.resetTarget();
    feed.addNote("Reset", "Events cleared and rate limits lifted.");
    for (let index = 0; index < FULL_DEMO_STEPS.length; index++) {
      const step = FULL_DEMO_STEPS[index];
      if (step.waitSeconds) {
        for (let left = step.waitSeconds; left > 0; left--) { showStep(index + 1, `waiting ${left} s so the request-rate window clears before the flood test`); await sleep(1000); }
        continue;
      }
      const scenario = scenarios.find((item) => item.id === step);
      if (!scenario) continue;                        // a built-in scenario was removed from builtin.json
      showStep(index + 1, scenario.title);
      await runScenario(scenario);
      await sleep(400);
    }
    $("#progressText").textContent = "Full demo finished. Open the dashboard to see every alert.";
    $("#progressBar").style.width = "100%";
  } catch (error) {
    feed.addError("Full demo", error.message);
  } finally {
    setTimeout(() => progress.classList.remove("show"), 6000);
  }
}

/* ---------- target status and header actions ---------- */
async function refreshTargetStatus() {
  try {
    const target = await labApi.getTarget();
    $("#target").className = "target " + (target.online ? "on" : "off");
    $("#targetText").textContent = target.online
      ? `Connected to ${target.target}` + (target.ml_loaded ? " · Rules + ML" : target.ml_loaded === false ? " · Rules only" : "")
      : `SentinelWeb not reachable at ${target.target}`;
    $("#dashLink").href = (target.dashboard_url || target.target) + "/";
  } catch (error) {
    $("#target").className = "target off";
    $("#targetText").textContent = "Lab server not reachable";
  }
}

$("#newScenarioBtn").addEventListener("click", () => editor.open());
$("#demoBtn").addEventListener("click", () => runExclusive(runFullDemo));
$("#resetBtn").addEventListener("click", () => runExclusive(async () => {
  try { await labApi.resetTarget(); feed.addNote("Reset SentinelWeb", "Events cleared and rate limits lifted."); }
  catch (error) { feed.addError("Reset SentinelWeb", error.message); }
}));
$("#clearBtn").addEventListener("click", () => feed.clear());
initQuickInput((scenario, title) => runExclusive(async () => {
  try { feed.addResult(title, await labApi.runUnsaved(scenario)); } catch (error) { feed.addError(title, error.message); }
}));
initThemeToggle($("#themeBtn"), "sentinel-lab-theme");

refreshTargetStatus();
setInterval(refreshTargetStatus, 10000);
loadScenarios();
labApi.getDemoEndpoints()
  .then((info) => editor.setKnownPaths([...new Set(info.endpoints.map((endpoint) => endpoint.path.replace("<anything>", "my-endpoint")))]))
  .catch(() => {});
