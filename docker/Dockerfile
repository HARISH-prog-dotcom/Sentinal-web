# SentinelWeb: one image for both products.
#   Dashboard (default command):  uvicorn main:app on port 8000
#   SentinelWeb Lab:              python -m client --host 0.0.0.0 --port 8001 --target http://<dashboard>:8000
#
# Build from the PROJECT folder (the build context must be the project root):
#     docker build -f docker/Dockerfile -t sentinelweb .
# See docker-compose.yml in this folder to run both products together.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SENTINEL_DB_PATH=/app/var/sentinel.db \
    SENTINEL_AI_SETTINGS_PATH=/app/var/ai_settings.json \
    LAB_CUSTOM_SCENARIOS_PATH=/app/var/custom-scenarios.json

WORKDIR /app

# Dependencies first, so code changes do not reinstall them.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train the model inside the image so it always matches this image's scikit-learn version.
RUN python scripts/train_model.py

# Run as an unprivileged user; runtime data (events, saved AI settings, custom scenarios) lives in /app/var.
RUN useradd --create-home --uid 10001 sentinel && mkdir -p /app/var && chown -R sentinel:sentinel /app/var
USER sentinel
VOLUME ["/app/var"]

EXPOSE 8000 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "none"]
