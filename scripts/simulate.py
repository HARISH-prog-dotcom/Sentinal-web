"""Send harmless TEST requests to your own local SentinelWeb demo app from the terminal.

Run from the project folder:  python scripts/simulate.py [base_url]
For a web UI with the same scenarios (and your own), use SentinelWeb Lab: python client/app.py
Never point this at a site you do not own.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def send_request(base_url: str, method: str, path: str, body=None) -> int:
    """Send one request and return the HTTP status code (errors are results, not failures)."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base_url + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def search_path(text: str) -> str:
    return "/demo/search?q=" + urllib.parse.quote(text)


def main() -> None:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL).rstrip("/")
    print("Reset:", send_request(base_url, "POST", "/api/reset"))

    print("1. Normal request      ->", send_request(base_url, "GET", search_path("laptop")))
    print("2. SQLi test string    ->", send_request(base_url, "GET", search_path("' OR '1'='1")))
    print("3. XSS test string     ->", send_request(base_url, "GET", search_path("<script>alert(1)</script>")))

    # Written so the fixed rules do not match: only the trained model flags these (MEDIUM, flagged, not blocked)
    print("3b. ML-only test       ->", send_request(base_url, "GET", search_path("1 or sleep(5)")))
    print("3c. ML-only test       ->", send_request(base_url, "GET", search_path('admin" or "a"="a')))

    for attempt in range(1, 7):
        status = send_request(base_url, "POST", "/demo/login", {"username": "alice", "password": f"wrong{attempt}"})
        print(f"4. Wrong login #{attempt}      ->", status)

    time.sleep(11)  # let the request-rate window clear before the burst test
    codes = [send_request(base_url, "GET", "/demo/items") for _ in range(25)]
    print("5. Burst of 25 requests -> status codes seen:", sorted(set(codes)))
    print(f"Done. Open {base_url}")


if __name__ == "__main__":
    main()
