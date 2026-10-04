"""SentinelWeb Lab settings. The target server is fixed at startup; the UI cannot change it."""
import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class LabSettings:
    target_url: str                  # SentinelWeb base URL, e.g. http://127.0.0.1:8000
    dashboard_url: str = ""          # link shown in the UI (differs from target_url inside Docker)
    web_dir: Path = PACKAGE_DIR / "web"
    builtin_scenarios_path: Path = PACKAGE_DIR / "scenarios" / "builtin.json"
    scenario_packs_dir: Path = PACKAGE_DIR / "scenarios" / "packs"
    custom_scenarios_path: Path = PACKAGE_DIR / "scenarios" / "custom.json"
    request_timeout_seconds: int = 10

    @classmethod
    def from_environment(cls, target_url: str = "") -> "LabSettings":
        """Target from the argument, else SENTINEL_TARGET, else the local default."""
        target = target_url or os.getenv("SENTINEL_TARGET", DEFAULT_TARGET)
        target = target.rstrip("/")
        options = {"target_url": target, "dashboard_url": os.getenv("LAB_DASHBOARD_URL", target).rstrip("/")}
        if os.getenv("LAB_CUSTOM_SCENARIOS_PATH"):
            options["custom_scenarios_path"] = Path(os.environ["LAB_CUSTOM_SCENARIOS_PATH"])
        return cls(**options)
