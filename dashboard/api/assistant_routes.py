"""Chat and AI-settings routes. These live under /api, so they are not monitored."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dashboard.assistant import AiSettingsStore, ChatAssistant
from dashboard.assistant.ai_settings import SettingsError


class ChatRequest(BaseModel):
    message: str


class AiSettingsUpdate(BaseModel):
    """Omit a field (null) to keep it; send "" to remove the saved value and fall back to .env."""

    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


def create_assistant_router(assistant: ChatAssistant, settings_store: AiSettingsStore) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["assistant"])

    @router.post("/chat")
    def chat(body: ChatRequest):
        text, source = assistant.reply(body.message[:300])
        return {"reply": text, "source": source}

    @router.get("/settings/ai")
    def get_ai_settings():
        return settings_store.public_view()

    @router.put("/settings/ai")
    def update_ai_settings(body: AiSettingsUpdate):
        try:
            settings_store.save(provider=body.provider, model=body.model, api_key=body.api_key)
        except SettingsError as error:
            raise HTTPException(400, str(error))
        return settings_store.public_view()

    @router.delete("/settings/ai")
    def clear_ai_settings():
        """Forget everything saved from the dashboard; .env / environment values apply again."""
        settings_store.clear()
        return settings_store.public_view()

    @router.post("/settings/ai/test")
    def test_ai_settings():
        return assistant.test_ai_connection()

    return router
