"""SQLite storage. Every query uses ? placeholders (prepared statements)."""
import sqlite3
from datetime import datetime

DB_PATH = "sentinel.db"


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT, ip TEXT, method TEXT, path TEXT,
            category TEXT, severity TEXT, evidence TEXT,
            action TEXT, explanation TEXT)""")


def add_event(ip, method, path, category, severity, evidence, action, explanation):
    # Never pass passwords or tokens in here.
    with conn() as c:
        c.execute(
            "INSERT INTO events (time, ip, method, path, category, severity, evidence, action, explanation) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), ip, method, path,
             category, severity, evidence, action, explanation))


def list_events(severity=None, category=None, limit=100):
    sql, args = "SELECT * FROM events WHERE 1=1", []
    if severity:
        sql += " AND severity = ?"
        args.append(severity)
    if category:
        sql += " AND category = ?"
        args.append(category)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(min(limit, 500))
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args)]


def stats():
    with conn() as c:
        total = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        by_sev = {r[0]: r[1] for r in c.execute("SELECT severity, COUNT(*) FROM events GROUP BY severity")}
        by_cat = {r[0]: r[1] for r in c.execute(
            "SELECT category, COUNT(*) FROM events WHERE severity != 'SAFE' GROUP BY category ORDER BY 2 DESC")}
    suspicious = total - by_sev.get("SAFE", 0)
    return {"total": total, "suspicious": suspicious, "by_severity": by_sev, "by_category": by_cat}


def clear():
    with conn() as c:
        c.execute("DELETE FROM events")
