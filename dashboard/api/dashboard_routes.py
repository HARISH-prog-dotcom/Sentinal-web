"""Read-only data for the dashboard UI, plus reset and the demo-app description."""
from typing import Optional

from fastapi import APIRouter

from dashboard.api.demo_routes import DEMO_ENDPOINTS
from dashboard.config import Settings
from dashboard.detection import SqlInjectionModel
from dashboard.monitoring import RequestMonitor
from dashboard.storage import EventRepository


def create_dashboard_router(settings: Settings, repository: EventRepository, model: SqlInjectionModel,
                            monitor: RequestMonitor) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["dashboard"])

    @router.get("/events")
    def list_events(severity: Optional[str] = None, category: Optional[str] = None, limit: int = 100):
        return repository.list_events(severity or None, category or None, limit)

    @router.get("/stats")
    def get_stats():
        return repository.get_stats()

    @router.get("/model")
    def get_model_info():
        """Which detection engines are active, plus the training metrics."""
        return {"ml_loaded": model.is_available, **model.training_metrics()}

    @router.get("/demo/endpoints")
    def describe_demo_app():
        """What the protected demo app offers and what SentinelWeb scans (used by SentinelWeb Lab)."""
        return {
            "endpoints": DEMO_ENDPOINTS,
            "scanned_inputs": ["query parameters", "JSON body (nested)", "form body", "text body", "URL path with unusual characters"],
            "never_scanned_fields": sorted(settings.skip_fields),
            "limits": {"requests_per_ip": f"{settings.request_limit} per {settings.request_window_seconds}s",
                       "failed_logins_per_account": f"{settings.login_limit} per {settings.login_window_seconds}s",
                       "lock_seconds": settings.lock_seconds},
            "blocking_enabled": settings.block_high_severity,
        }

    @router.post("/reset")
    def reset_demo():
        """Demo convenience: clears events and rate limits before a fresh run."""
        repository.clear()
        monitor.reset()
        return {"ok": True}

    return router
