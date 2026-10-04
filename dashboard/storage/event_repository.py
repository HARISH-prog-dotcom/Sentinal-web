"""Event log stored in SQLite (repository pattern: the rest of the app never writes SQL).

Every query uses ? placeholders (prepared statements). Never pass passwords or tokens in here.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

MAX_PAGE_SIZE = 500


class EventRepository:
    """Create, read and clear monitoring events."""

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT, ip TEXT, method TEXT, path TEXT,
                category TEXT, severity TEXT, evidence TEXT,
                action TEXT, explanation TEXT)""")

    def add_event(self, ip: str, method: str, path: str, category: str, severity: str,
                  evidence: str, action: str, explanation: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events (time, ip, method, path, category, severity, evidence, action, explanation) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), ip, method, path,
                 category, severity, evidence, action, explanation))

    def list_events(self, severity: Optional[str] = None, category: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Newest events first, optionally filtered by severity and/or category."""
        sql, args = "SELECT * FROM events WHERE 1=1", []
        if severity:
            sql += " AND severity = ?"
            args.append(severity)
        if category:
            sql += " AND category = ?"
            args.append(category)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(max(1, min(limit, MAX_PAGE_SIZE)))
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(sql, args)]

    def get_event(self, event_id: int) -> Optional[dict]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return dict(row) if row else None

    def get_stats(self) -> dict:
        """Totals for the dashboard counters and charts."""
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            by_severity = {row[0]: row[1] for row in connection.execute("SELECT severity, COUNT(*) FROM events GROUP BY severity")}
            by_category = {row[0]: row[1] for row in connection.execute(
                "SELECT category, COUNT(*) FROM events WHERE severity != 'SAFE' GROUP BY category ORDER BY 2 DESC")}
        return {"total": total, "suspicious": total - by_severity.get("SAFE", 0),
                "by_severity": by_severity, "by_category": by_category}

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM events")
