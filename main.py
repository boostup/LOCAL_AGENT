import os
from typing import Any

import ollama


class OllamaClient:
    def __init__(self, model: str | None = None, host: str | None = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
        self.client = ollama.Client(host=host or os.environ.get("OLLAMA_HOST"))

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        try:
            response: dict[str, Any] = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature},
            )
            return response.get("message", {}).get("content", "")
        except Exception as exc:
            return f"Ollama is unavailable: {exc}"


if __name__ == "__main__":
    print(OllamaClient().generate("Reply with one sentence confirming you are ready."))
