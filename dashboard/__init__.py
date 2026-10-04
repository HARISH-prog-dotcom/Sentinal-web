"""SentinelWeb dashboard: monitors requests to a demo app, detects attacks and explains them.

Package layout:
    config.py     settings and thresholds in one place (+ the .env loader)
    app.py        create_app(): builds every component and wires them together
    detection/    attack rules, the ML model and the detectors that combine them
    monitoring/   the request pipeline (middleware), input extraction and rate limiting
    storage/      the event log (repository over SQLite)
    assistant/    the chatbot: rule answers, AI providers and AI key settings
    api/          HTTP routes for the dashboard, the assistant and the demo app
    web/          the dashboard UI (HTML, CSS, JavaScript, logo)
"""
