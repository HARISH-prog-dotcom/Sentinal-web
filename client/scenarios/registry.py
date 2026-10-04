"""Scenario registry: one place that knows every scenario and where it came from.

Sources, in display order:
    builtin.json        shipped with the Lab (read-only)
    packs/*.json        extra scenario packs: drop a JSON file here to add scenarios (read-only)
    custom.json         scenarios created in the UI or imported (editable; git-ignored)
"""
import json
import os
import re
import threading
from pathlib import Path
from typing import Dict, List

from client.scenarios.models import Scenario, ScenarioError

MAX_CUSTOM_SCENARIOS = 200


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "scenario"


class ScenarioRegistry:
    def __init__(self, builtin_path: Path, packs_dir: Path, custom_path: Path):
        self._builtin_path, self._packs_dir, self._custom_path = Path(builtin_path), Path(packs_dir), Path(custom_path)
        self._lock = threading.Lock()          # routes run in a thread pool; serialise file writes

    # ---------- loading ----------
    @staticmethod
    def _read_json_list(path: Path) -> list:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except ValueError as error:
            print(f"[SentinelWeb Lab] Skipping {path.name}: not valid JSON ({error}).")
            return []
        return data.get("scenarios", []) if isinstance(data, dict) else data if isinstance(data, list) else []

    def _load_file(self, path: Path, source: str) -> List[Scenario]:
        scenarios = []
        for index, raw in enumerate(self._read_json_list(path)):
            try:
                scenario = Scenario.from_dict(raw, source=source)
                scenario.id = scenario.id or f"{path.stem}-{index + 1}"
                scenarios.append(scenario)
            except ScenarioError as error:
                print(f"[SentinelWeb Lab] Skipping scenario {index + 1} in {path.name}: {error}")
        return scenarios

    def list_all(self) -> List[Scenario]:
        """Every valid scenario. Later sources never replace an earlier id."""
        scenarios: Dict[str, Scenario] = {}
        sources = [(self._builtin_path, "builtin")]
        sources += [(pack, f"pack:{pack.name}") for pack in sorted(self._packs_dir.glob("*.json"))]
        sources += [(self._custom_path, "custom")]
        for path, source in sources:
            for scenario in self._load_file(path, source):
                scenarios.setdefault(scenario.id, scenario)
        return list(scenarios.values())

    def get(self, scenario_id: str) -> Scenario:
        for scenario in self.list_all():
            if scenario.id == scenario_id:
                return scenario
        raise KeyError(scenario_id)

    # ---------- custom scenarios ----------
    def _read_custom(self) -> List[dict]:
        return [item for item in self._read_json_list(self._custom_path) if isinstance(item, dict)]

    def _write_custom(self, items: List[dict]) -> None:
        """Atomic write so a crash never leaves a half-written file."""
        self._custom_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._custom_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps({"scenarios": items}, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp_path, self._custom_path)

    def _unique_id(self, title: str) -> str:
        taken = {scenario.id for scenario in self.list_all()}
        base = "custom-" + _slugify(title)
        candidate, counter = base, 2
        while candidate in taken:
            candidate, counter = f"{base}-{counter}", counter + 1
        return candidate

    def create(self, data: dict) -> Scenario:
        with self._lock:
            items = self._read_custom()
            if len(items) >= MAX_CUSTOM_SCENARIOS:
                raise ScenarioError(f"You can keep at most {MAX_CUSTOM_SCENARIOS} custom scenarios.")
            scenario = Scenario.from_dict(data, source="custom")
            scenario.id = self._unique_id(scenario.title)
            self._write_custom(items + [scenario.to_dict()])
            return scenario

    def update(self, scenario_id: str, data: dict) -> Scenario:
        with self._lock:
            items = self._read_custom()
            index = next((i for i, item in enumerate(items) if item.get("id") == scenario_id), None)
            if index is None:
                raise KeyError(scenario_id)        # built-in and pack scenarios cannot be edited
            scenario = Scenario.from_dict(data, source="custom", scenario_id=scenario_id)
            items[index] = scenario.to_dict()
            self._write_custom(items)
            return scenario

    def delete(self, scenario_id: str) -> None:
        with self._lock:
            items = self._read_custom()
            remaining = [item for item in items if item.get("id") != scenario_id]
            if len(remaining) == len(items):
                raise KeyError(scenario_id)
            self._write_custom(remaining)

    def import_scenarios(self, raw_items: list) -> dict:
        """Add every valid scenario from an imported list; report the ones that were skipped."""
        if not isinstance(raw_items, list):
            raise ScenarioError("Import a JSON list of scenarios, or an object with a 'scenarios' list.")
        added, skipped = [], []
        for index, raw in enumerate(raw_items[:MAX_CUSTOM_SCENARIOS]):
            try:
                added.append(self.create(raw).id)
            except ScenarioError as error:
                title = raw.get("title") if isinstance(raw, dict) else None
                skipped.append({"item": title or f"#{index + 1}", "reason": str(error)})
        return {"added": added, "skipped": skipped}

    def export_custom(self) -> dict:
        return {"scenarios": self._read_custom()}
