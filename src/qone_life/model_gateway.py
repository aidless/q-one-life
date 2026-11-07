"""最小模型网关客户端：单次 chat completion 调用，失败返回 None。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable

DEFAULT_URL = "http://127.0.0.1:3425/v1/chat/completions"
DEFAULT_MODEL = "group/auto-gpt-6"


def make_model_call(
    *,
    url: str = DEFAULT_URL,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 1200,
    timeout: int = 60,
) -> Callable[[str], str | None]:
    """构造一个只发一次请求的 model_call；任何异常都返回 None。"""

    def call(prompt: str) -> str | None:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            return None
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None
        return content.strip() or None

    return call
