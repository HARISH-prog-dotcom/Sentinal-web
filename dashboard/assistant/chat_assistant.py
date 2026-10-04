"""The chat assistant (facade): rule answers first, then the configured AI provider."""
import time
from collections import deque
from typing import Optional, Tuple

from dashboard.assistant.ai_settings import AiSettingsStore
from dashboard.assistant.knowledge import AI_SYSTEM_PROMPT, HELP_TEXT
from dashboard.assistant.llm_providers import PROVIDERS, LlmError
from dashboard.assistant.rule_responder import RuleResponder
from dashboard.storage import EventRepository

SOURCE_RULES, SOURCE_AI = "rules", "ai"


class CallBudget:
    """Protects the free quota: at most max_calls AI answers per rolling minute."""

    def __init__(self, max_calls: int):
        self._max_calls = max_calls
        self._call_times = deque()

    def try_spend(self) -> bool:
        now = time.time()
        while self._call_times and now - self._call_times[0] > 60:
            self._call_times.popleft()
        if len(self._call_times) >= self._max_calls:
            return False
        self._call_times.append(now)
        return True


class ChatAssistant:
    """Single entry point used by the /api/chat route."""

    def __init__(self, repository: EventRepository, settings_store: AiSettingsStore, max_ai_calls_per_minute: int = 10):
        self._repository = repository
        self._settings_store = settings_store
        self._rules = RuleResponder(repository)
        self._budget = CallBudget(max_ai_calls_per_minute)

    def reply(self, message: str) -> Tuple[str, str]:
        """Return (answer, source) where source is 'rules' or 'ai'."""
        answer = self._rules.answer(message)
        if answer is not None:
            return answer, SOURCE_RULES
        ai_answer = self._ask_ai(message)
        if ai_answer:
            return ai_answer, SOURCE_AI
        return "Sorry, I only know simple things about this dashboard. " + HELP_TEXT, SOURCE_RULES

    def _system_prompt(self) -> str:
        stats = self._repository.get_stats()   # only summary numbers are sent - never IPs, evidence text or logs
        return AI_SYSTEM_PROMPT + (f" Dashboard numbers: {stats['total']} requests monitored, {stats['suspicious']} suspicious, "
                                   f"{stats['by_severity'].get('HIGH', 0)} high, {stats['by_severity'].get('MEDIUM', 0)} medium.")

    def _ask_ai(self, question: str) -> Optional[str]:
        config = self._settings_store.resolve()
        if not config.is_configured or not self._budget.try_spend():
            return None
        try:
            return PROVIDERS[config.provider].complete(config.api_key, config.model, self._system_prompt(), question)
        except LlmError as error:
            print(f"[SentinelWeb] AI chat unavailable: {error}")   # never print the key
            return None

    def test_ai_connection(self) -> dict:
        """Send one tiny question with the current settings and report the result (used by the Settings page)."""
        config = self._settings_store.resolve()
        if not config.is_configured:
            return {"ok": False, "message": "No API key is set. Add one here or in .env."}
        try:
            PROVIDERS[config.provider].complete(config.api_key, config.model, "Reply with the single word OK.", "Say OK.")
            return {"ok": True, "message": f"Connected to {PROVIDERS[config.provider].label} with model {config.model}."}
        except LlmError as error:
            return {"ok": False, "message": str(error)}
