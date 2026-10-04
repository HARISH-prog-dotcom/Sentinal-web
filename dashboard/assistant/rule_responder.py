"""Keyword-based answers from the event log or the FAQ. No API key, no internet needed."""
import re
from typing import Optional

from dashboard.assistant.knowledge import ADVICE_BY_CATEGORY, FAQ_ANSWERS, HELP_TEXT, TOPIC_KEYWORDS
from dashboard.storage import EventRepository


def describe_event(event: dict) -> str:
    """One-paragraph summary of an event for chat replies."""
    return (f"#{event['id']} {event['category']} ({event['severity']}) at {event['time'][11:]} from {event['ip']}. "
            f"Action: {event['action']}. Evidence: {event['evidence']} Why: {event['explanation']}")


class RuleResponder:
    """Answers common questions. Returns None when no rule matches, so the AI can try."""

    def __init__(self, repository: EventRepository):
        self._repository = repository

    def _latest_suspicious_event(self) -> Optional[dict]:
        return next((event for event in self._repository.list_events(limit=100) if event["severity"] != "SAFE"), None)

    def answer(self, message: str) -> Optional[str]:
        text = message.lower().strip()
        words = set(re.findall(r"[a-z]+", text))
        if not text or words & {"hi", "hello", "hey", "help"}:
            return HELP_TEXT

        event_number = re.search(r"event\s*#?\s*(\d+)", text)                 # "explain event 5"
        if event_number:
            event = self._repository.get_event(int(event_number.group(1)))
            return describe_event(event) if event else "I could not find an event with that number."

        if words & {"latest", "last", "recent", "newest"}:
            event = self._latest_suspicious_event()
            return ("Latest suspicious event: " + describe_event(event)) if event else "No suspicious events yet. Everything looks normal."

        if words & {"many", "count", "total", "summary", "status", "overview", "stats"}:
            return self._summary(words)

        for word in re.findall(r"[a-z]+", text):
            if word in TOPIC_KEYWORDS:
                return FAQ_ANSWERS[TOPIC_KEYWORDS[word]]

        if words & {"should", "recommend", "advice", "action", "fix", "prevent", "protect"}:
            return self._advice()
        return None

    def _summary(self, words: set) -> str:
        stats = self._repository.get_stats()
        for token in ("sql", "xss", "login", "api"):
            if token in words:
                count = sum(n for category, n in stats["by_category"].items() if token in category.lower())
                return f"{count} suspicious event(s) match '{token}'."
        by_severity = stats["by_severity"]
        top = ", ".join(f"{name} ({n})" for name, n in list(stats["by_category"].items())[:3]) or "none"
        return (f"{stats['total']} requests monitored, {stats['suspicious']} suspicious. "
                f"High: {by_severity.get('HIGH', 0)}, Medium: {by_severity.get('MEDIUM', 0)}, Low: {by_severity.get('LOW', 0)}. "
                f"Most common: {top}.")

    def _advice(self) -> str:
        event = self._latest_suspicious_event()
        if not event:
            return "Nothing suspicious right now. Keep the monitoring running and review events regularly."
        for keyword, tip in ADVICE_BY_CATEGORY.items():
            if keyword.lower() in event["category"].lower():
                return f"Latest issue: {event['category']}. Suggested next step: {tip}"
        return "Review the latest event's evidence and decide whether the action taken was right."
