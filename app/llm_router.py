"""Multi-provider LLM completion (Groq, Hugging Face Inference, Gemini)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("nutrition-raqa.llm")

# Allowlist: provider free-tier style models (adjust via env on Space)
DEFAULT_MODELS: list[dict[str, str]] = [
    {"id": "groq:llama-3.3-70b-versatile", "label": "Groq — Llama 3.3 70B"},
    {"id": "groq:llama-3.1-8b-instant", "label": "Groq — Llama 3.1 8B Instant"},
    {"id": "groq:mixtral-8x7b-32768", "label": "Groq — Mixtral 8x7B"},
    {"id": "hf:mistralai/Mistral-7B-Instruct-v0.2", "label": "HF — Mistral 7B Instruct"},
    {"id": "hf:meta-llama/Llama-3.2-3B-Instruct", "label": "HF — Llama 3.2 3B"},
    {"id": "gemini:gemini-2.0-flash", "label": "Gemini — 2.0 Flash"},
]


@dataclass
class LLMRouter:
    groq_client: Any
    hf_token: str | None
    gemini_key: str | None
    default_llm_id: str

    def list_options(self) -> list[dict[str, str]]:
        opts: list[dict[str, str]] = []
        for m in DEFAULT_MODELS:
            mid = m["id"]
            if mid.startswith("groq:") and self.groq_client is None:
                continue
            if mid.startswith("hf:") and not self.hf_token:
                continue
            if mid.startswith("gemini:") and not self.gemini_key:
                continue
            opts.append(dict(m))
        if not opts:
            return []
        return opts

    def resolve_default(self) -> str:
        opts = self.list_options()
        if not opts:
            return self.default_llm_id
        ids = {o["id"] for o in opts}
        if self.default_llm_id in ids:
            return self.default_llm_id
        return opts[0]["id"]

    def complete(
        self,
        messages: list[dict[str, str]],
        llm_id: str | None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        resolved = llm_id or self.resolve_default()
        allowed = {o["id"] for o in self.list_options()}
        if resolved not in allowed:
            raise ValueError(f"Unknown or unavailable llm_id: {resolved}")

        if resolved.startswith("groq:"):
            model = resolved.split(":", 1)[1]
            msg = self.groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return (msg.choices[0].message.content or "").strip()

        if resolved.startswith("hf:"):
            model_id = resolved.split(":", 1)[1]
            from huggingface_hub import InferenceClient

            client = InferenceClient(token=self.hf_token)
            out = client.chat_completion(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            msg = out.choices[0].message
            return (msg.content or "").strip()

        if resolved.startswith("gemini:"):
            model_name = resolved.split(":", 1)[1]
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel(model_name)
            parts = []
            for m in messages:
                role = m.get("role", "user")
                parts.append(f"{role.upper()}: {m.get('content', '')}")
            prompt = "\n\n".join(parts)
            gen_cfg = {"max_output_tokens": max_tokens, "temperature": temperature}
            resp = model.generate_content(prompt, generation_config=gen_cfg)
            return (resp.text or "").strip()

        raise ValueError(f"Unsupported llm_id: {resolved}")
