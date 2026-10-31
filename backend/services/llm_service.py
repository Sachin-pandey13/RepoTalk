"""
backend/services/llm_service.py
LLM abstraction: tries Ollama first, falls back to Groq API.
"""
import json
import requests
from typing import Generator

from backend.core.config import settings


# ─── Non-streaming (original API preserved) ──────────────────────────────────

def ask_mistral(prompt: str) -> str:
    """Blocking call — tries Ollama then Groq."""
    result = _try_ollama(prompt)
    if result:
        return result
    result = _try_groq(prompt)
    if result:
        return result
    return "Error: No LLM backend available. Start Ollama or set GROQ_API_KEY."


def _try_ollama(prompt: str) -> str | None:
    try:
        resp = requests.post(
            settings.OLLAMA_URL,
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=90,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "")
        return None
    except Exception:
        return None


def _try_groq(prompt: str) -> str | None:
    if not settings.GROQ_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return None
    except Exception:
        return None


# ─── Streaming (SSE) ──────────────────────────────────────────────────────────

def stream_mistral(prompt: str) -> Generator[str, None, None]:
    """
    Yields text chunks for SSE streaming.
    Falls back to Groq streaming when Ollama is unavailable.
    """
    # Try Ollama streaming
    try:
        with requests.post(
            settings.OLLAMA_URL,
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": True},
            stream=True,
            timeout=120,
        ) as resp:
            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk
                            if data.get("done"):
                                return
                        except json.JSONDecodeError:
                            continue
                return
    except Exception:
        pass

    # Groq streaming fallback
    if settings.GROQ_API_KEY:
        try:
            with requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    "max_tokens": 2048,
                },
                stream=True,
                timeout=90,
            ) as resp:
                for line in resp.iter_lines():
                    line = line.decode("utf-8") if isinstance(line, bytes) else line
                    if line.startswith("data: "):
                        payload = line[6:]
                        if payload == "[DONE]":
                            return
                        try:
                            data = json.loads(payload)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue
        except Exception:
            pass

    yield "Error: No LLM backend available."