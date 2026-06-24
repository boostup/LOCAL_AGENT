import os
from typing import Any

import ollama


class OllamaClient:
    def __init__(self, model: str | None = None, host: str | None = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
        self.client = ollama.Client(host=host or os.environ.get("OLLAMA_HOST"))

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        print(f"[OLLAMA REQUEST] model={self.model} prompt={repr(prompt)[:200]}")
        try:
            response: dict[str, Any] = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature},
            )
            content = response.get("message", {}).get("content", "")
            print(f"[OLLAMA RESPONSE] model={self.model} response={repr(content)[:200]}")
            return content
        except Exception as exc:
            error_msg = f"Ollama is unavailable: {exc}"
            print(f"[OLLAMA ERROR] {error_msg}")
            return error_msg


if __name__ == "__main__":
    print(OllamaClient().generate("Reply with one sentence confirming you are ready."))
