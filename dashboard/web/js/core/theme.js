// Dark/light theme toggle. The choice is remembered per browser when storage is available.

export function initThemeToggle({ button, label, storageKey }) {
  const root = document.documentElement;

  function applyTheme(theme) {
    root.dataset.theme = theme;
    const next = theme === "light" ? "dark" : "light";
    label.textContent = next === "light" ? "Light theme" : "Dark theme";
    button.setAttribute("aria-label", `Switch to ${next} theme`);
  }

  let savedTheme = null;
  try { savedTheme = localStorage.getItem(storageKey); } catch (error) { /* storage blocked */ }
  applyTheme(savedTheme === "light" ? "light" : "dark");

  button.addEventListener("click", () => {
    const theme = root.dataset.theme === "light" ? "dark" : "light";
    applyTheme(theme);
    try { localStorage.setItem(storageKey, theme); } catch (error) { /* private mode: not remembered */ }
  });
}
