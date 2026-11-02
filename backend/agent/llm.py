from __future__ import annotations

import json
import re
from typing import Any

import httpx

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT
from utils.logger import get_logger

logger = get_logger("llm")


class LLMClient:
    @property
    def configured(self) -> bool:
        return bool(LLM_API_KEY)

    @property
    def model(self) -> str:
        return LLM_MODEL

    @property
    def base_url(self) -> str:
        return LLM_BASE_URL

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> str | None:
        if not self.configured:
            return None
        payload: dict[str, Any] = {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=LLM_TIMEOUT) as client:
                response = client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("LLM 调用失败，回退到规则引擎：%s", exc)
            return None

    def chat_json(self, system: str, user: str) -> dict[str, Any] | None:
        content = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            json_mode=True,
        )
        if not content:
            return None
        return parse_json(content)

    def chat_text(self, system: str, user: str) -> str | None:
        return self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
        )


def parse_json(content: str) -> dict[str, Any] | None:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
    return None


llm_client = LLMClient()
