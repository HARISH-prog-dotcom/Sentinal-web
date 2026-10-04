// Dark/light theme toggle, remembered per browser when storage is available.

export function initThemeToggle(button, storageKey) {
  const root = document.documentElement;
  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    button.textContent = theme === "light" ? "Dark" : "Light";
    button.setAttribute("aria-label", `Switch to ${theme === "light" ? "dark" : "light"} theme`);
  };
  let saved = null;
  try { saved = localStorage.getItem(storageKey); } catch (error) { /* storage blocked */ }
  applyTheme(saved === "light" ? "light" : "dark");
  button.addEventListener("click", () => {
    const theme = root.dataset.theme === "light" ? "dark" : "light";
    applyTheme(theme);
    try { localStorage.setItem(storageKey, theme); } catch (error) { /* not remembered */ }
  });
}
