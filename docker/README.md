# Docker files for SentinelWeb

| File | Purpose |
|---|---|
| `Dockerfile` | One image for both products (dashboard and SentinelWeb Lab). Trains the model during the build. |
| `docker-compose.yml` | Runs the dashboard (port 8000) and the Lab (port 8001) together. |
| `../.dockerignore` | Stays in the project root because the build context is the project folder. Keeps `.env` and local data out of the image. |

Quick start:

    cd docker
    docker compose up --build

Then open http://localhost:8000 (dashboard) and http://localhost:8001 (Lab).

**Full instructions** (AI keys, running one product only, volumes, flag-only mode, troubleshooting) are in the
main README: [Run with Docker](../README.md#run-with-docker).
