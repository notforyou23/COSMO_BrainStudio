from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple
import json as _json
import os
import random
import time
import urllib.request
import urllib.error


Message = Dict[str, str]


class LLMBackend(Protocol):
    def complete(self, messages: Sequence[Message], **kwargs: Any) -> Dict[str, Any]: ...
    def generate(self, prompt: str, system: str = "You are a helpful assistant.", **kwargs: Any) -> Dict[str, Any]: ...
    def verify(self, prompt: str, system: str = "You are a careful verifier.", **kwargs: Any) -> Dict[str, Any]: ...


def _sleep_backoff(attempt: int, base: float = 0.5, cap: float = 8.0) -> None:
    time.sleep(min(cap, base * (2 ** max(0, attempt - 1))))


def _extract_text(resp: Dict[str, Any]) -> str:
    try:
        return resp["choices"][0]["message"]["content"]
    except Exception:
        try:
            return resp["choices"][0]["text"]
        except Exception:
            return ""


@dataclass
class OpenAIHTTPBackend:
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    timeout_s: float = 30.0
    max_retries: int = 3
    user_agent: str = "verifier-benchmark/0.1"
    seed: Optional[int] = 0

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY")

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        data = _json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        last_err: Optional[BaseException] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                    body = r.read().decode("utf-8")
                    return _json.loads(body) if body else {}
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                last_err = e
                if attempt >= self.max_retries:
                    break
                _sleep_backoff(attempt)
        raise RuntimeError(f"OpenAIHTTPBackend request failed after {self.max_retries} retries: {last_err}")
    def complete(
        self,
        messages: Sequence[Message],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        seed: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": list(messages),
            "temperature": float(temperature),
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if top_p is not None:
            payload["top_p"] = float(top_p)
        s = self.seed if seed is None else seed
        if s is not None:
            payload["seed"] = int(s)
        if response_format is not None:
            payload["response_format"] = response_format
        if extra:
            payload.update(extra)
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        raw = self._post_json("/chat/completions", payload)
        return {
            "text": _extract_text(raw),
            "raw": raw,
            "model": payload["model"],
            "usage": raw.get("usage", {}),
        }

    def generate(self, prompt: str, system: str = "You are a helpful assistant.", **kwargs: Any) -> Dict[str, Any]:
        msgs: List[Message] = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        return self.complete(msgs, **kwargs)

    def verify(self, prompt: str, system: str = "You are a careful verifier.", **kwargs: Any) -> Dict[str, Any]:
        msgs: List[Message] = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        return self.complete(msgs, **kwargs)


@dataclass
class LocalStubBackend:
    seed: int = 0
    mode: str = "echo"  # echo | canned | rng
    canned: Tuple[str, ...] = ("OK", "FAIL", "UNCERTAIN")

    def _rng(self) -> random.Random:
        return random.Random(self.seed)

    def complete(self, messages: Sequence[Message], **kwargs: Any) -> Dict[str, Any]:
        text = ""
        if self.mode == "echo":
            text = messages[-1].get("content", "") if messages else ""
        elif self.mode == "canned":
            text = self.canned[0]
        elif self.mode == "rng":
            r = self._rng()
            text = r.choice(self.canned)
        else:
            text = messages[-1].get("content", "") if messages else ""
        return {"text": text, "raw": {"choices": [{"message": {"content": text}}]}, "model": "local-stub", "usage": {}}

    def generate(self, prompt: str, system: str = "You are a helpful assistant.", **kwargs: Any) -> Dict[str, Any]:
        return self.complete([{"role": "system", "content": system}, {"role": "user", "content": prompt}], **kwargs)

    def verify(self, prompt: str, system: str = "You are a careful verifier.", **kwargs: Any) -> Dict[str, Any]:
        return self.complete([{"role": "system", "content": system}, {"role": "user", "content": prompt}], **kwargs)


def make_backend(kind: str = "openai_http", **kwargs: Any) -> LLMBackend:
    k = (kind or "").lower().strip()
    if k in {"openai", "openai_http", "http"}:
        return OpenAIHTTPBackend(**kwargs)
    if k in {"local", "stub", "local_stub"}:
        return LocalStubBackend(**kwargs)
    raise ValueError(f"Unknown backend kind: {kind}")
