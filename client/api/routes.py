"""Lab API: scenarios (list, create, edit, delete, import, export), running them, and target status."""
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Body, HTTPException

from client.scenarios import Scenario, ScenarioError, ScenarioRegistry
from client.services import ScenarioRunner, SentinelGateway, SentinelUnreachable

# Shown in the editor when SentinelWeb is too old to describe its demo app.
FALLBACK_ENDPOINTS = [
    {"method": "GET", "path": "/demo/search", "input": "query parameter q"},
    {"method": "GET", "path": "/demo/items", "input": "none"},
    {"method": "POST", "path": "/demo/login", "input": "JSON: username, password"},
]


def create_lab_router(registry: ScenarioRegistry, runner: ScenarioRunner, gateway: SentinelGateway, dashboard_url: str = "") -> APIRouter:
    router = APIRouter(prefix="/api")

    def run_safely(scenario: Scenario) -> dict:
        try:
            return runner.run(scenario)
        except SentinelUnreachable as error:
            raise HTTPException(502, str(error))

    # ---------- target ----------
    @router.get("/target")
    def get_target_status():
        try:
            model = gateway.model_info()
            online, ml_loaded = bool(model), model.get("ml_loaded")
        except SentinelUnreachable:
            online, ml_loaded = False, None
        return {"target": gateway.base_url, "dashboard_url": dashboard_url or gateway.base_url, "online": online, "ml_loaded": ml_loaded}

    @router.get("/demo-endpoints")
    def get_demo_endpoints():
        """Endpoints the demo app offers, for the scenario editor's suggestions."""
        try:
            described = gateway.demo_endpoints()
        except SentinelUnreachable:
            described = {}
        return described or {"endpoints": FALLBACK_ENDPOINTS}

    @router.post("/reset")
    def reset_target():
        try:
            return {"ok": gateway.reset()}
        except SentinelUnreachable as error:
            raise HTTPException(502, str(error))

    # ---------- scenarios ----------
    @router.get("/scenarios")
    def list_scenarios():
        return [scenario.to_public_dict() for scenario in registry.list_all()]

    @router.post("/scenarios", status_code=201)
    def create_scenario(data: Dict[str, Any] = Body(...)):
        try:
            return registry.create(data).to_public_dict()
        except ScenarioError as error:
            raise HTTPException(400, str(error))

    @router.put("/scenarios/{scenario_id}")
    def update_scenario(scenario_id: str, data: Dict[str, Any] = Body(...)):
        try:
            return registry.update(scenario_id, data).to_public_dict()
        except KeyError:
            raise HTTPException(404, "Only custom scenarios can be edited. Duplicate this one to change it.")
        except ScenarioError as error:
            raise HTTPException(400, str(error))

    @router.delete("/scenarios/{scenario_id}")
    def delete_scenario(scenario_id: str):
        try:
            registry.delete(scenario_id)
        except KeyError:
            raise HTTPException(404, "Only custom scenarios can be deleted.")
        return {"ok": True}

    @router.post("/scenarios/import")
    def import_scenarios(data: Union[List[Any], Dict[str, Any]] = Body(...)):
        items = data.get("scenarios") if isinstance(data, dict) else data
        try:
            return registry.import_scenarios(items)
        except ScenarioError as error:
            raise HTTPException(400, str(error))

    @router.get("/scenarios/export")
    def export_scenarios():
        return registry.export_custom()

    # ---------- running ----------
    @router.post("/run/{scenario_id}")
    def run_saved_scenario(scenario_id: str):
        try:
            scenario = registry.get(scenario_id)
        except KeyError:
            raise HTTPException(404, "Unknown scenario")
        return run_safely(scenario)

    @router.post("/run")
    def run_unsaved_scenario(data: Dict[str, Any] = Body(...)):
        """Run a scenario straight from the editor or the quick-input box without saving it."""
        try:
            scenario = Scenario.from_dict(data, source="adhoc", scenario_id="adhoc")
        except ScenarioError as error:
            raise HTTPException(400, str(error))
        return run_safely(scenario)

    return router
