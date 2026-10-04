"""SentinelWeb entry point.

Run:  uvicorn main:app --reload
Only requests to /demo/* are monitored. Use it on YOUR OWN demo app only.
The application itself lives in the dashboard/ package (see dashboard/app.py).
"""
from dashboard.app import create_app

app = create_app()
