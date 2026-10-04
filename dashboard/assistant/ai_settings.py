"""AI assistant settings from two sources: the dashboard's Settings page and .env / environment variables.

Precedence for each setting: saved in the dashboard  >  .env or environment  >  built-in default.
Saved settings live in data/ai_settings.json (git-ignored, readable only by the owner).
The API key is never returned to the browser, only whether one is set and its last 4 characters.
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dashboard.assistant.llm_providers import DEFAULT_PROVIDER, PROVIDERS

MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._:\-/]{1,80}$")
SOURCE_DASHBOARD, SOURCE_ENV, SOURCE_DEFAULT, SOURCE_NONE = "dashboard", "env", "default", "none"


class SettingsError(ValueError):
    """Invalid value sent to the settings API."""


@dataclass(frozen=True)
class AiConfig:
    """The settings actually in use, plus where each one came from."""

    provider: str
    model: str
    api_key: str
    provider_source: str
    model_source: str
    key_source: str

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


class AiSettingsStore:
    """Reads, merges and saves AI settings."""

    def __init__(self, path: Path):
        self._path = Path(path)

    # ---------- reading ----------
    def _read_saved(self) -> dict:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def resolve(self) -> AiConfig:
        """Merge saved settings, environment and defaults into the configuration to use now."""
        saved = self._read_saved()
        env_provider = os.getenv("LLM_PROVIDER", "").lower()

        if saved.get("provider") in PROVIDERS:
            provider, provider_source = saved["provider"], SOURCE_DASHBOARD
        elif env_provider in PROVIDERS:
            provider, provider_source = env_provider, SOURCE_ENV
        else:
            provider, provider_source = DEFAULT_PROVIDER, SOURCE_DEFAULT

        provider_changed_in_dashboard = provider_source == SOURCE_DASHBOARD and provider != (env_provider or DEFAULT_PROVIDER)
        if saved.get("model"):
            model, model_source = saved["model"], SOURCE_DASHBOARD
        elif os.getenv("LLM_MODEL") and not provider_changed_in_dashboard:
            model, model_source = os.environ["LLM_MODEL"], SOURCE_ENV
        else:
            model, model_source = PROVIDERS[provider].default_model, SOURCE_DEFAULT

        if saved.get("api_key"):
            api_key, key_source = saved["api_key"], SOURCE_DASHBOARD
        elif os.getenv("LLM_API_KEY"):
            api_key, key_source = os.environ["LLM_API_KEY"], SOURCE_ENV
        else:
            api_key, key_source = "", SOURCE_NONE
        return AiConfig(provider, model, api_key, provider_source, model_source, key_source)

    def public_view(self) -> dict:
        """What the Settings page may see: never the key itself."""
        config = self.resolve()
        return {
            "provider": config.provider, "model": config.model,
            "key_configured": config.is_configured,
            "key_hint": ("…" + config.api_key[-4:]) if len(config.api_key) >= 8 else ("set" if config.api_key else ""),
            "sources": {"provider": config.provider_source, "model": config.model_source, "api_key": config.key_source},
            "has_saved_settings": bool(self._read_saved()),
            "providers": [{"name": p.name, "label": p.label, "default_model": p.default_model} for p in PROVIDERS.values()],
        }

    # ---------- writing ----------
    def save(self, provider: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
        """Save settings from the dashboard. None = keep the current saved value; "" = remove it (fall back to .env)."""
        saved = self._read_saved()
        if provider is not None:
            provider = provider.strip().lower()
            if provider and provider not in PROVIDERS:
                raise SettingsError(f"Unknown provider. Choose one of: {', '.join(PROVIDERS)}.")
            self._set_or_remove(saved, "provider", provider)
        if model is not None:
            model = model.strip()
            if model and not MODEL_NAME_PATTERN.match(model):
                raise SettingsError("Model names may only contain letters, digits and . _ : - /")
            self._set_or_remove(saved, "model", model)
        if api_key is not None:
            api_key = api_key.strip()
            if api_key and (len(api_key) > 300 or re.search(r"\s", api_key)):
                raise SettingsError("That does not look like an API key (no spaces, at most 300 characters).")
            self._set_or_remove(saved, "api_key", api_key)
        self._write(saved)

    def clear(self) -> None:
        """Delete everything saved from the dashboard; .env / environment values apply again."""
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass

    @staticmethod
    def _set_or_remove(saved: dict, key: str, value: str) -> None:
        if value:
            saved[key] = value
        else:
            saved.pop(key, None)

    def _write(self, data: dict) -> None:
        """Atomic write with owner-only permissions."""
        if not data:
            self.clear()
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass  # e.g. some Windows file systems
        os.replace(temp_path, self._path)
