// Assistant page: full-page chat. Replies are rendered as plain text only.

import { $, createElement } from "../core/dom.js";
import { dashboardApi } from "../core/api.js";

const SUGGESTIONS = ["Summary", "Latest alert", "What is SQL injection?", "What should I do?", "Explain event 5"];

export function initAssistantView() {
  const messages = $("#msgs"), input = $("#chatIn");

  function addMessage(text, sender) {
    const bubble = createElement("div", { class: "m " + sender }, text);
    messages.append(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  async function ask(question) {
    addMessage(question, "me");
    const reply = addMessage("Thinking…", "bot wait");
    try {
      const response = await dashboardApi.sendChat(question);
      reply.textContent = response.reply;
      if (response.source === "ai") reply.title = "Answered by the AI model";
    } catch (error) {
      reply.textContent = "I can't reach the backend right now.";
    }
    reply.classList.remove("wait");
    messages.scrollTop = messages.scrollHeight;
  }

  SUGGESTIONS.forEach((text) => $("#chips").append(createElement("button", { type: "button", onclick: () => ask(text) }, text)));
  $("#chatForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (question) { input.value = ""; ask(question); }
  });

  /** Called when the page becomes visible. */
  return function onShow() {
    if (!messages.children.length) addMessage("Hi, I'm the Sentinel assistant. Ask about the alerts, or pick a suggestion below.", "bot");
    input.focus();
  };
}
