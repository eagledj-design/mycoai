"""Proveedores de inferencia configurados por el administrador de MycoAI."""

import os
from dataclasses import dataclass, field
from typing import Literal

import requests

Provider = Literal["lm_studio", "ollama", "openai", "cloud_compatible"]


@dataclass(frozen=True)
class ModelProvider:
    name: str
    base_url: str
    chat_url: str
    api_key: str = field(default="", repr=False)

    def request(self, method: str, url: str, *, payload: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with requests.Session() as session:
            response = session.request(
                method, url, headers=headers, json=payload,
                timeout=(5, 120 if payload is not None else 15), allow_redirects=False,
            )
            if response.status_code != 200:
                raise ValueError(f"El proveedor respondió con HTTP {response.status_code}.")
            return response.json()

    def models(self) -> list[str]:
        data = self.request("GET", f"{self.base_url}/models")["data"]
        return sorted({row["id"] for row in data if isinstance(row.get("id"), str)})


def resolve_provider(name: Provider, client_key: str = "") -> ModelProvider:
    if name == "lm_studio":
        chat = os.getenv("MYCOAI_LM_URL", "http://127.0.0.1:1234/v1/chat/completions")
        return ModelProvider(name, chat.rsplit("/chat/completions", 1)[0], chat)
    if name == "ollama":
        base = os.getenv("MYCOAI_OLLAMA_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        return ModelProvider(name, base, f"{base}/chat/completions")
    if name == "openai":
        base = "https://api.openai.com/v1"
        key = client_key or os.getenv("OPENAI_API_KEY", "")
    else:
        base = os.getenv("MYCOAI_CLOUD_URL", "").rstrip("/")
        key = client_key or os.getenv("MYCOAI_CLOUD_API_KEY", "")
    if not base.startswith("https://") or not key:
        raise ValueError("Configura una URL HTTPS y una clave para el proveedor en nube.")
    return ModelProvider(name, base, f"{base}/chat/completions", key)
