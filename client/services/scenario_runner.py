"""Runs a scenario against SentinelWeb and reports what happened."""
import time

from client.scenarios.models import Scenario
from client.services.sentinel_gateway import SentinelGateway

SEVERITY_RANK = {"SAFE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


class ScenarioRunner:
    def __init__(self, gateway: SentinelGateway):
        self._gateway = gateway

    def run(self, scenario: Scenario) -> dict:
        """Send every request of the scenario, then collect the events SentinelWeb logged for them."""
        last_id_before = self._gateway.latest_event_id()
        statuses = []
        for step in scenario.steps:
            for request in step.expand():
                status, _ = self._gateway.send(request["method"], request["path"], request["query"], request["body_type"], request["body"])
                statuses.append(status)
        events = self._gateway.events_after(last_id_before)
        return {"id": scenario.id, "title": scenario.title, "sends": scenario.describe(), "statuses": statuses,
                "events": events, "verdict": self.compare_with_expectation(scenario.expect, events), "at": time.strftime("%H:%M:%S")}

    @staticmethod
    def compare_with_expectation(expected: str, events: list) -> dict:
        """The most severe logged event versus the scenario's expected severity."""
        if not events:
            return {"expected": expected, "actual": None, "matches": expected == "ANY"}
        actual = max(events, key=lambda event: SEVERITY_RANK.get(event["severity"], 0))["severity"]
        return {"expected": expected, "actual": actual, "matches": expected == "ANY" or expected == actual}
