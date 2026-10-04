// Scenario editor dialog: build a scenario from form fields, then save it or run it without saving.

import { $, $$, createElement } from "../core/dom.js";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const BODY_TYPES = [["none", "No body"], ["json", "JSON body"], ["form", "Form body"], ["text", "Text body"]];
const DEFAULT_STEP = { method: "GET", path: "/demo/search", query: { q: "" }, body_type: "none", body: null, repeat: 1 };

function select(options, value, className) {
  const element = createElement("select", { class: className }, options.map(([optionValue, label]) => createElement("option", { value: optionValue }, label)));
  element.value = value;
  return element;
}

/** Rows of name/value inputs (used for query parameters and form bodies). */
function pairEditor(pairs, label) {
  const container = createElement("div", { class: "pairs" });
  const addRow = (name = "", value = "") => {
    const row = createElement("div", { class: "pair" },
      createElement("input", { type: "text", class: "pair-name", placeholder: "name", value: name, "aria-label": `${label} name` }),
      createElement("input", { type: "text", class: "pair-value", placeholder: "value", value: String(value), "aria-label": `${label} value` }),
      createElement("button", { class: "btn small", type: "button", "aria-label": `Remove ${label} row`, onclick: () => row.remove() }, "✕"));
    container.insertBefore(row, container.lastElementChild);
  };
  container.append(createElement("div", null, createElement("button", { class: "btn small", type: "button", onclick: () => addRow() }, `+ ${label}`)));
  const entries = Object.entries(pairs || {});
  (entries.length ? entries : [["", ""]]).forEach(([name, value]) => addRow(name, value));
  container.readPairs = () => Object.fromEntries($$(".pair", container)
    .map((row) => [$(".pair-name", row).value.trim(), $(".pair-value", row).value]).filter(([name]) => name));
  return container;
}

function stepElement(step, index, onRemove) {
  const methodSelect = select(METHODS.map((m) => [m, m]), step.method, "st-method");
  const pathInput = createElement("input", { type: "text", class: "st-path", list: "pathOptions", value: step.path, "aria-label": "Path", spellcheck: "false" });
  const bodySelect = select(BODY_TYPES, step.body_type || "none", "st-body-type");
  const repeatInput = createElement("input", { type: "number", class: "st-repeat", min: "1", max: "50", value: String(step.repeat || 1), "aria-label": "Repeat" });
  const queryEditor = pairEditor(step.query, "query parameter");
  const formEditor = pairEditor(step.body_type === "form" ? step.body : {}, "form field");
  const bodyText = createElement("textarea", { class: "st-body-text", spellcheck: "false", "aria-label": "Body" });
  bodyText.value = step.body_type === "json" ? JSON.stringify(step.body ?? {}, null, 2) : step.body_type === "text" ? String(step.body ?? "") : "";

  const bodyArea = createElement("div", { class: "field" });
  const showBodyInput = () => {
    const type = bodySelect.value;
    bodyArea.replaceChildren(...(type === "form" ? [createElement("span", { class: "label" }, "Form fields"), formEditor]
      : type === "json" || type === "text" ? [createElement("span", { class: "label" }, type === "json" ? "JSON body" : "Text body"), bodyText] : []));
    if (type === "json" && !bodyText.value.trim()) bodyText.value = "{\n  \"text\": \"\"\n}";
  };
  bodySelect.addEventListener("change", showBodyInput);
  showBodyInput();

  const element = createElement("div", { class: "step" },
    createElement("div", { class: "step-head" }, createElement("b", null, `Step ${index + 1}`),
      createElement("button", { class: "btn small danger", type: "button", onclick: onRemove }, "Remove")),
    createElement("div", { class: "step-grid" },
      createElement("div", { class: "field" }, createElement("span", { class: "label" }, "Method"), methodSelect),
      createElement("div", { class: "field" }, createElement("span", { class: "label" }, "Path"), pathInput),
      createElement("div", { class: "field" }, createElement("span", { class: "label" }, "Body"), bodySelect),
      createElement("div", { class: "field" }, createElement("span", { class: "label" }, "Repeat"), repeatInput)),
    createElement("div", { class: "field" }, createElement("span", { class: "label" }, "Query parameters"), queryEditor),
    bodyArea);

  /** Read this step back into the scenario JSON format. */
  element.readStep = () => {
    const bodyType = bodySelect.value;
    const body = bodyType === "form" ? formEditor.readPairs() : bodyType === "json" || bodyType === "text" ? bodyText.value : null;
    return { method: methodSelect.value, path: pathInput.value.trim(), query: queryEditor.readPairs(), body_type: bodyType, body, repeat: Number(repeatInput.value) || 1 };
  };
  return element;
}

/**
 * handlers: { onSave(scenario, existingId) -> Promise, onRunUnsaved(scenario) -> Promise }
 * Returns { open(scenario?, mode), setKnownGroups(names), setKnownPaths(paths) }.
 */
export function createScenarioEditor(handlers) {
  const dialog = $("#editor"), stepsContainer = $("#edSteps"), errorText = $("#editorError");
  let editingId = null;

  function renumberSteps() {
    $$(".step", stepsContainer).forEach((step, index) => { $(".step-head b", step).textContent = `Step ${index + 1}`; });
  }

  function addStep(step = DEFAULT_STEP) {
    const element = stepElement(step, stepsContainer.children.length, () => { element.remove(); renumberSteps(); });
    stepsContainer.append(element);
  }

  function readScenario() {
    return {
      title: $("#edTitle").value.trim(), group: $("#edGroup").value.trim(), description: $("#edDescription").value.trim(),
      expect: $("#edExpect").value, expect_text: $("#edExpectText").value.trim(),
      steps: $$(".step", stepsContainer).map((step) => step.readStep()),
    };
  }

  /** mode: "new" | "edit" | "duplicate" */
  function open(scenario = null, mode = "new") {
    editingId = mode === "edit" ? scenario.id : null;
    $("#editorTitle").textContent = mode === "edit" ? "Edit scenario" : mode === "duplicate" ? "New scenario (copy)" : "New scenario";
    $("#edTitle").value = scenario ? (mode === "duplicate" ? `${scenario.title} (copy)` : scenario.title) : "";
    $("#edGroup").value = scenario && mode !== "duplicate" ? scenario.group : scenario ? "Custom scenarios" : "";
    $("#edDescription").value = scenario?.description || "";
    $("#edExpect").value = scenario?.expect || "HIGH";
    $("#edExpectText").value = scenario && mode === "edit" ? (scenario.expect_text || "") : "";
    stepsContainer.replaceChildren();
    (scenario?.steps?.length ? scenario.steps : [DEFAULT_STEP]).forEach((step) => addStep(step));
    errorText.textContent = "";
    dialog.showModal();
    $("#edTitle").focus();
  }

  async function submit(action) {
    errorText.textContent = "";
    try {
      await action(readScenario());
      dialog.close();
    } catch (error) {
      errorText.textContent = error.message;
    }
  }

  $("#addStepBtn").addEventListener("click", () => addStep({ ...DEFAULT_STEP, query: {} }));
  $("#editorClose").addEventListener("click", () => dialog.close());
  $("#editorForm").addEventListener("submit", (event) => { event.preventDefault(); submit((scenario) => handlers.onSave(scenario, editingId)); });
  $("#editorRun").addEventListener("click", () => submit((scenario) => handlers.onRunUnsaved({ ...scenario, title: scenario.title || "Unsaved scenario" })));

  return {
    open,
    setKnownGroups: (names) => $("#groupOptions").replaceChildren(...names.map((name) => createElement("option", { value: name }))),
    setKnownPaths: (paths) => $("#pathOptions").replaceChildren(...paths.map((path) => createElement("option", { value: path }))),
  };
}
