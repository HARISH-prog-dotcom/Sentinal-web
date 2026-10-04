"""The demo app that SentinelWeb protects. Every route here is monitored by RequestMonitor.

Besides the fixed routes, a catch-all route accepts any method on any /demo/... path, so custom
scenarios from SentinelWeb Lab always get a real response instead of a 404.
Safe by design: user input is never put into SQL and is returned as JSON, never as HTML.
"""
import hmac
import json
from collections import deque
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

DEMO_ITEMS = ["laptop", "keyboard", "monitor", "mouse", "headphones"]
DEMO_USERS = {"alice": "password123"}   # demo only
MAX_STORED_COMMENTS = 20

# Published through /api/demo/endpoints so clients (SentinelWeb Lab) know what they can call.
DEMO_ENDPOINTS = [
    {"method": "GET", "path": "/demo/search", "input": "query parameter q", "description": "Product search"},
    {"method": "GET", "path": "/demo/items", "input": "none", "description": "List products"},
    {"method": "POST", "path": "/demo/login", "input": "JSON or form: username, password",
     "description": "Login (alice / password123). Failed logins are counted."},
    {"method": "GET", "path": "/demo/comments", "input": "none", "description": "Read the latest comments"},
    {"method": "POST", "path": "/demo/comments", "input": "JSON or form: author, text", "description": "Post a comment"},
    {"method": "ANY", "path": "/demo/<anything>", "input": "query, JSON, form or text body",
     "description": "Generic endpoint for custom scenarios: echoes what it received"},
]


async def read_body_fields(request: Request) -> dict:
    """Body as a flat dict from JSON or form data (empty dict for anything else)."""
    raw = (await request.body()).decode("utf-8", errors="replace")
    if not raw:
        return {}
    if "application/x-www-form-urlencoded" in request.headers.get("content-type", ""):
        return dict(parse_qsl(raw))
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def create_demo_router() -> APIRouter:
    router = APIRouter(prefix="/demo", tags=["demo app"])
    comments = deque(maxlen=MAX_STORED_COMMENTS)

    @router.get("/search")
    def search_items(q: str = ""):
        return {"query": q, "results": [item for item in DEMO_ITEMS if q.lower() in item]}

    @router.get("/items")
    def list_items():
        return {"items": DEMO_ITEMS}

    @router.post("/login")
    async def login(request: Request):
        body = await read_body_fields(request)
        username, password = str(body.get("username", "")), str(body.get("password", ""))
        expected = DEMO_USERS.get(username, "")
        if expected and hmac.compare_digest(expected, password):   # constant-time comparison
            return {"ok": True}
        return JSONResponse({"ok": False}, status_code=401)

    @router.get("/comments")
    def list_comments():
        return {"comments": list(comments)}

    @router.post("/comments")
    async def add_comment(request: Request):
        body = await read_body_fields(request)
        comment = {"author": str(body.get("author", "guest"))[:40], "text": str(body.get("text", ""))[:500]}
        comments.appendleft(comment)
        return {"ok": True, "comment": comment}

    @router.api_route("/{subpath:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def generic_endpoint(subpath: str, request: Request):
        """Catch-all for custom scenarios. Registered last, so the routes above take priority."""
        return {"path": "/demo/" + subpath, "method": request.method,
                "received_query": dict(request.query_params), "note": "Generic demo endpoint"}

    return router
