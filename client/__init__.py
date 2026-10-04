"""SentinelWeb Lab: a separate web UI that sends safe test traffic to YOUR OWN SentinelWeb server.

Package layout:
    config.py     Lab settings (target server, host, port, file locations)
    app.py        create_app() and the command-line entry point
    scenarios/    scenario model, validation and the registry (built-in, packs, custom)
    services/     gateway to SentinelWeb and the scenario runner
    api/          HTTP routes used by the Lab UI
    web/          the Lab UI (HTML, CSS, JavaScript, logo)
"""
