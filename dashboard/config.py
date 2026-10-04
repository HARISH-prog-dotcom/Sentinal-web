"""All dashboard settings in one place.

Defaults live here; environment variables (or the .env file) can override them.
Choose and explain your own thresholds: the values below are demo settings.
"""
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Read KEY=value lines from .env into the environment (no extra library).

    Real environment variables always win, so Docker or the shell can override the file.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return  # no .env file: everything still works with defaults
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True)
class Settings:
    """Immutable dashboard configuration, created once at startup."""

    db_path: Path
    ai_settings_path: Path
    model_path: Path
    metrics_path: Path
    web_dir: Path
    block_high_severity: bool          # False = flag-only mode (SENTINEL_BLOCK=0)

    # Request-rate limit: more than REQUEST_LIMIT requests in REQUEST_WINDOW seconds from one IP
    request_limit: int = 20
    request_window_seconds: int = 10
    # Brute force: LOGIN_LIMIT failed logins in LOGIN_WINDOW seconds for one account
    login_limit: int = 5
    login_window_seconds: int = 60
    lock_seconds: int = 60

    # Field names that are never scanned or stored (secrets)
    skip_fields: frozenset = frozenset({"password", "token", "session"})

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings from defaults + environment variables (after loading .env)."""
        load_dotenv()
        data_dir = PROJECT_ROOT / "data"
        return cls(
            db_path=Path(os.getenv("SENTINEL_DB_PATH", data_dir / "sentinel.db")),
            ai_settings_path=Path(os.getenv("SENTINEL_AI_SETTINGS_PATH", data_dir / "ai_settings.json")),
            model_path=PROJECT_ROOT / "models" / "sqli_model.joblib",
            metrics_path=PROJECT_ROOT / "models" / "metrics.json",
            web_dir=PACKAGE_DIR / "web",
            block_high_severity=os.getenv("SENTINEL_BLOCK", "1") == "1",
        )
