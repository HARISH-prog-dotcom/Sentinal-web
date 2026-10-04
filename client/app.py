"""SentinelWeb Lab: safe test traffic for YOUR OWN SentinelWeb server, with a web UI.

Run (with SentinelWeb already running), from the project folder:
    python client/app.py                                   # targets http://127.0.0.1:8000, UI on http://127.0.0.1:8001
    python client/app.py --target http://10.0.0.5:8000     # SentinelWeb on another machine
    python -m client --host 0.0.0.0                         # same thing, open the Lab to other devices

The target is fixed at startup and the UI cannot change it. Never point it at a site you do not own.
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):                       # started as "python client/app.py"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from client.api.routes import create_lab_router  # noqa: E402
from client.config import LabSettings  # noqa: E402
from client.scenarios import ScenarioRegistry  # noqa: E402
from client.services import ScenarioRunner, SentinelGateway  # noqa: E402


def create_app(settings: Optional[LabSettings] = None) -> FastAPI:
    """Application factory: build the components and wire them together."""
    settings = settings or LabSettings.from_environment()
    registry = ScenarioRegistry(settings.builtin_scenarios_path, settings.scenario_packs_dir, settings.custom_scenarios_path)
    gateway = SentinelGateway(settings.target_url, settings.request_timeout_seconds)
    runner = ScenarioRunner(gateway)

    app = FastAPI(title="SentinelWeb Lab")
    app.include_router(create_lab_router(registry, runner, gateway, settings.dashboard_url))
    app.mount("/static", StaticFiles(directory=settings.web_dir), name="static")

    @app.get("/", include_in_schema=False)
    def lab_page():
        return FileResponse(settings.web_dir / "index.html")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="SentinelWeb Lab: safe test traffic for your own SentinelWeb server")
    parser.add_argument("--target", default="", help="SentinelWeb base URL (default: SENTINEL_TARGET or http://127.0.0.1:8000)")
    parser.add_argument("--host", default="127.0.0.1", help="interface for the Lab UI (0.0.0.0 = reachable from other devices)")
    parser.add_argument("--port", type=int, default=8001, help="port for the Lab UI (default %(default)s)")
    args = parser.parse_args()
    settings = LabSettings.from_environment(args.target)
    print(f"SentinelWeb Lab on http://{args.host}:{args.port}  ->  sending test traffic to {settings.target_url}")
    uvicorn.run(create_app(settings), host=args.host, port=args.port, ws="none")   # no websockets needed


if __name__ == "__main__":
    main()
