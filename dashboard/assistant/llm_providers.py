"""AI providers (strategy pattern). Each provider knows how to build its request and read its reply.

To add a provider, write one LlmProvider subclass and register it in PROVIDERS.
Only summary numbers are ever sent, never IPs, evidence text or logs.
"""
import json
import urllib.error
import urllib.request
from typing import Tuple


class LlmError(Exception):
    """An AI call failed. status_code is the HTTP status when there was one (e.g. 404 = model retired)."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class LlmProvider:
    """Base class: subclasses fill in the request format and the reply parsing."""

    name = ""
    default_model = ""
    label = ""

    def build_request(self, api_key: str, model: str, system_prompt: str, question: str) -> Tuple[str, dict, dict]:
        """Return (url, headers, json_body)."""
        raise NotImplementedError

    def extract_text(self, reply: dict) -> str:
        raise NotImplementedError

    def complete(self, api_key: str, model: str, system_prompt: str, question: str, timeout: int = 10) -> str:
        """Send one question and return the answer text. Raises LlmError on any problem."""
        url, headers, body = self.build_request(api_key, model, system_prompt, question)
        headers = {"Content-Type": "application/json", "User-Agent": "SentinelWeb/1.0", **headers}
        request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = self.extract_text(json.load(response)).strip()
        except urllib.error.HTTPError as error:
            raise LlmError(_http_error_message(error), error.code) from None
        except (urllib.error.URLError, OSError) as error:
            raise LlmError(f"Could not reach the AI service ({type(error).__name__}).") from None
        except (KeyError, IndexError, TypeError, ValueError):
            raise LlmError("The AI service sent an unexpected reply.") from None
        if not text:
            raise LlmError("The AI service returned an empty answer.")
        return text[:1200]


def _http_error_message(error: urllib.error.HTTPError) -> str:
    """Short, key-free explanation of an HTTP error from a provider."""
    hints = {400: "the request was rejected (check the model name)", 401: "the API key is not valid",
             403: "the API key is not allowed to use this model", 404: "the model was not found or has been retired",
             429: "the free quota is used up for now"}
    return f"HTTP {error.code}: {hints.get(error.code, 'the AI service returned an error')}."


class GeminiProvider(LlmProvider):
    name, label, default_model = "gemini", "Google Gemini (AI Studio)", "gemini-3.5-flash-lite"

    def build_request(self, api_key, model, system_prompt, question):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        body = {"system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": question}]}],
                "generationConfig": {"maxOutputTokens": 300}}
        return url, {"x-goog-api-key": api_key}, body

    def extract_text(self, reply):
        return reply["candidates"][0]["content"]["parts"][0]["text"]


class GroqProvider(LlmProvider):
    name, label, default_model = "groq", "Groq", "llama-3.3-70b-versatile"

    def build_request(self, api_key, model, system_prompt, question):
        body = {"model": model, "max_tokens": 300,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]}
        return "https://api.groq.com/openai/v1/chat/completions", {"Authorization": "Bearer " + api_key}, body

    def extract_text(self, reply):
        return reply["choices"][0]["message"]["content"]


PROVIDERS = {provider.name: provider for provider in (GeminiProvider(), GroqProvider())}
DEFAULT_PROVIDER = "gemini"
