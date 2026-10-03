"""SentinelWeb backend. Run: uvicorn main:app --reload
Only requests to /demo/* are monitored. Use it on YOUR OWN demo app only."""
import hmac
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import chatbot
import db
import detection
import ml

# ---- Demo settings (choose and explain your own thresholds) ----
BLOCK_HIGH = os.getenv("SENTINEL_BLOCK", "1") == "1"  # set SENTINEL_BLOCK=0 for flag-only mode
REQ_LIMIT, REQ_WINDOW = 20, 10        # more than 20 requests in 10 s from one IP
LOGIN_LIMIT, LOGIN_WINDOW = 5, 60     # 5 failed logins in 60 s for one account
LOCK_SECONDS = 60

app = FastAPI(title="SentinelWeb")
db.init()

req_hits = detection.SlidingWindow()
login_fails = detection.SlidingWindow()
locked = {}  # key -> time when the rate limit ends

SKIP_KEYS = {"password", "token", "session"}  # never scanned or stored


def is_locked(key):
    return locked.get(key, 0) > time.time()


def collect_inputs(request, body):
    """Gather query/body strings to scan. Returns (list of (field, value), username)."""
    items = list(request.query_params.items())
    username = None
    if body:
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                username = str(data.get("username", "")) or None
                items += [(k, v) for k, v in data.items() if isinstance(v, str)]
        except ValueError:
            pass
    return [(k, v) for k, v in items if k.lower() not in SKIP_KEYS], username


# ---------------- Monitoring middleware ----------------
@app.middleware("http")
async def sentinel(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/demo"):
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    method = request.method
    inputs, username = collect_inputs(request, await request.body())

    def log(category, severity, evidence, action):
        db.add_event(ip, method, path, category, severity, evidence, action, detection.EXPLAIN[category])

    # 1. Already rate-limited? (not logged again, to avoid flooding the log)
    if is_locked(f"ip:{ip}") or (username and is_locked(f"user:{username}")):
        return JSONResponse({"error": "Rate-limited. Try again later."}, status_code=429)

    # 2. Too many requests from one IP?
    count = req_hits.hit(ip, REQ_WINDOW)
    if count > REQ_LIMIT:
        locked[f"ip:{ip}"] = time.time() + LOCK_SECONDS
        log("Suspicious API activity", "MEDIUM",
            f"{count} requests in {REQ_WINDOW}s (demo limit {REQ_LIMIT})", "Rate-limited")
        return JSONResponse({"error": "Rate-limited."}, status_code=429)

    # 3. Suspicious input?
    findings = [f for field, value in inputs for f in detection.scan_text(field, value)]
    if findings:
        f = findings[0]
        block = BLOCK_HIGH and f["severity"] == "HIGH"
        log(f["category"], f["severity"], f["evidence"], "Blocked (demo)" if block else "Flagged")
        if block:
            return JSONResponse({"error": "Blocked by SentinelWeb (demo)."}, status_code=403)

    response = await call_next(request)

    # 4. Failed login tracking (needs the response status)
    if path == "/demo/login" and response.status_code == 401 and username:
        fails = login_fails.hit(username, LOGIN_WINDOW)
        if fails >= LOGIN_LIMIT:
            locked[f"user:{username}"] = time.time() + LOCK_SECONDS
            log("Repeated failed logins", "MEDIUM",
                f"{fails} failed attempts in {LOGIN_WINDOW}s for '{username[:30]}' (demo threshold {LOGIN_LIMIT})",
                "Rate-limited account")
        else:
            log("Failed login", "LOW", f"Failed attempt {fails} of {LOGIN_LIMIT} for '{username[:30]}'", "Allowed")
    elif not findings:
        log("Normal request", "SAFE", "No rule matched", "Allowed")

    return response


# ---------------- Demo app (the thing being protected) ----------------
ITEMS = ["laptop", "keyboard", "monitor", "mouse", "headphones"]
USERS = {"alice": "password123"}  # demo only


class Login(BaseModel):
    username: str
    password: str


@app.get("/demo/search")
def search(q: str = ""):
    # Safe by design: q is never put into a SQL string and is returned as JSON, not HTML.
    return {"query": q, "results": [i for i in ITEMS if q.lower() in i]}


@app.get("/demo/items")
def items():
    return {"items": ITEMS}


@app.post("/demo/login")
def login(body: Login):
    expected = USERS.get(body.username, "")
    if expected and hmac.compare_digest(expected, body.password):
        return {"ok": True}
    return JSONResponse({"ok": False}, status_code=401)


# ---------------- Dashboard API ----------------
@app.get("/api/events")
def events(severity: str = None, category: str = None, limit: int = 100):
    return db.list_events(severity or None, category or None, limit)


@app.get("/api/stats")
def stats():
    return db.stats()


class Chat(BaseModel):
    message: str


@app.post("/api/chat")
def chat(body: Chat):
    """Simple rule-based assistant (see chatbot.py). Not monitored: it lives under /api."""
    text, source = chatbot.reply(body.message[:300])  # source is "rules" or "ai"
    return {"reply": text, "source": source}


@app.get("/api/model")
def model_info():
    """Which detection engines are active, plus the training metrics."""
    return {"ml_loaded": ml.available(), **ml.info()}


@app.post("/api/reset")
def reset():
    """Demo convenience: clears events and rate limits before a fresh run."""
    db.clear()
    req_hits.clear()
    login_fails.clear()
    locked.clear()
    return {"ok": True}


@app.get("/")
def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html")