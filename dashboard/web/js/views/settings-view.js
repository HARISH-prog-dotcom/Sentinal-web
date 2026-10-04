// Settings page: add or change the AI assistant's provider, model and API key.
// The key is sent to the server once and never shown again; .env keeps working as before.

import { $, createElement } from "../core/dom.js";
import { dashboardApi } from "../core/api.js";

const SOURCE_LABELS = { dashboard: "saved here", env: "from .env", default: "default", none: "not set" };

export function initSettingsView() {
  const form = $("#aiForm"), providerSelect = $("#aiProvider"), modelInput = $("#aiModel"), keyInput = $("#aiKey");
  const message = $("#aiMessage");
  let current = null;

  function showMessage(text, kind = "") {
    message.textContent = text;
    message.className = "form-message " + kind;
  }

  function setSource(selector, source) {
    const chip = $(selector);
    chip.textContent = SOURCE_LABELS[source] || source;
    chip.className = "source " + (source === "dashboard" ? "dashboard" : "");
  }

  function render(settings) {
    current = settings;
    if (!providerSelect.options.length) {
      settings.providers.forEach((provider) => providerSelect.append(createElement("option", { value: provider.name }, provider.label)));
    }
    providerSelect.value = settings.provider;
    modelInput.value = settings.sources.model === "dashboard" ? settings.model : "";
    modelInput.placeholder = settings.model;
    keyInput.value = "";
    setSource("#srcProvider", settings.sources.provider);
    setSource("#srcModel", settings.sources.model);
    setSource("#srcKey", settings.sources.api_key);

    const badge = $("#aiStatusBadge");
    if (settings.key_configured) {
      badge.textContent = "AI on";
      badge.style.setProperty("--c", "var(--safe)");
      $("#aiStatusText").textContent = `Key ${settings.key_hint} (${SOURCE_LABELS[settings.sources.api_key]}) · ${settings.provider} · ${settings.model}`;
    } else {
      badge.textContent = "AI off";
      badge.style.setProperty("--c", "var(--ink-2)");
      $("#aiStatusText").textContent = "No API key: the assistant answers from its built-in rules only.";
    }
    $("#navAiState").hidden = settings.key_configured;
    $("#aiClear").hidden = !settings.has_saved_settings;
  }

  async function refresh() {
    try { render(await dashboardApi.getAiSettings()); }
    catch (error) { showMessage("Could not load the settings: " + error.message, "error"); }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const changes = { provider: providerSelect.value, model: modelInput.value.trim() };
    if (keyInput.value.trim()) changes.api_key = keyInput.value.trim();     // empty = keep the current key
    try {
      render(await dashboardApi.saveAiSettings(changes));
      showMessage("Saved. Use Test connection to check the key.", "ok");
    } catch (error) { showMessage(error.message, "error"); }
  });

  $("#aiTest").addEventListener("click", async () => {
    showMessage("Testing…");
    try {
      const result = await dashboardApi.testAiSettings();
      showMessage(result.message, result.ok ? "ok" : "error");
    } catch (error) { showMessage(error.message, "error"); }
  });

  $("#aiClear").addEventListener("click", async () => {
    try {
      render(await dashboardApi.clearAiSettings());
      showMessage("Saved settings removed. Values from .env (if any) apply again.", "ok");
    } catch (error) { showMessage(error.message, "error"); }
  });

  $("#aiKeyToggle").addEventListener("click", (event) => {
    const isHidden = keyInput.type === "password";
    keyInput.type = isHidden ? "text" : "password";
    event.currentTarget.textContent = isHidden ? "Hide" : "Show";
    event.currentTarget.setAttribute("aria-pressed", isHidden);
  });

  // Changing the provider suggests that provider's default model.
  providerSelect.addEventListener("change", () => {
    const provider = current?.providers.find((item) => item.name === providerSelect.value);
    if (provider) modelInput.placeholder = provider.default_model;
  });

  refresh();
  return { onShow: refresh };
}
