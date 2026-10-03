"""Sends harmless TEST requests to your own local demo app. Run: python simulate.py
Never point this at a site you do not own."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"


def send(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def q(text):
    return "/demo/search?q=" + urllib.parse.quote(text)


print("Reset:", send("POST", "/api/reset"))

print("1. Normal request      ->", send("GET", q("laptop")))
print("2. SQLi test string    ->", send("GET", q("' OR '1'='1")))
print("3. XSS test string     ->", send("GET", q("<script>alert(1)</script>")))

# Payloads written in a way the fixed rules do not match - only the trained model flags these (MEDIUM, flagged, not blocked)
print("3b. ML-only test       ->", send("GET", q("1 or sleep(5)")))
print("3c. ML-only test       ->", send("GET", q('admin" or "a"="a')))

for i in range(1, 7):
    print(f"4. Wrong login #{i}      ->", send("POST", "/demo/login", {"username": "alice", "password": f"wrong{i}"}))

time.sleep(11)  # let the request-rate window clear before the burst test
codes = [send("GET", "/demo/items") for _ in range(25)]
print("5. Burst of 25 requests -> status codes seen:", sorted(set(codes)))
print("Done. Open http://127.0.0.1:8000")
