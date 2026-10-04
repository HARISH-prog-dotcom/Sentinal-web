"""Application factory: creates every component once and wires them together (dependency injection).

Nothing here is global, so tests or other entry points can call create_app() with their own Settings.
"""
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from dashboard.api.assistant_routes import create_assistant_router
from dashboard.api.dashboard_routes import create_dashboard_router
from dashboard.api.demo_routes import create_demo_router
from dashboard.assistant import AiSettingsStore, ChatAssistant
from dashboard.config import Settings
from dashboard.detection import InputScanner, SqlInjectionDetector, SqlInjectionModel, XssDetector
from dashboard.monitoring import RequestMonitor
from dashboard.storage import EventRepository


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings.from_environment()

    # Core components
    repository = EventRepository(settings.db_path)
    model = SqlInjectionModel(settings.model_path, settings.metrics_path)
    scanner = InputScanner([SqlInjectionDetector(model), XssDetector()])   # add new detectors here
    monitor = RequestMonitor(settings, scanner, repository)
    settings_store = AiSettingsStore(settings.ai_settings_path)
    assistant = ChatAssistant(repository, settings_store)

    app = FastAPI(title="SentinelWeb")
    app.middleware("http")(monitor)
    app.include_router(create_dashboard_router(settings, repository, model, monitor))
    app.include_router(create_assistant_router(assistant, settings_store))
    app.include_router(create_demo_router())

    # Dashboard UI: index.html at "/", CSS/JS/images under /static
    app.mount("/static", StaticFiles(directory=settings.web_dir), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard_page():
        return FileResponse(settings.web_dir / "index.html")

    return app
