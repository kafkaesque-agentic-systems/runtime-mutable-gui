"""Token counting.

Purpose: measure prompts and ticket read-manifests with the serving model's own
tokenizer (`POST /v1/messages/count_tokens` on a Strata server), and fall back
to a conservative estimate when no server answers.
Dependencies: urllib only.
Side effects: one HTTP request per count. The API key is read from the
environment or from the local OpenCode config and is never printed or logged.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Code and logs run near two characters per token on this model family
# (Strata's own measurement); prose near four. Three keeps an estimate from
# flattering a manifest that is mostly code.
ESTIMATE_CHARS_PER_TOKEN = 3.0


def estimate(text: str) -> int:
    """Token estimate used when the tokenizer cannot be reached."""
    return int(math.ceil(len(text) / ESTIMATE_CHARS_PER_TOKEN))


def _api_key(settings: Dict[str, Any]) -> Optional[str]:
    key = os.environ.get(str(settings.get("key_env", "")), "")
    if key:
        return key
    path = Path(os.path.expanduser(str(settings.get("opencode_config", ""))))
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # The OpenCode config tolerates trailing commas, so it is not parsed as JSON:
    # find the provider block, then the first apiKey after it.
    start = text.find('"' + str(settings.get("provider", "")) + '"')
    match = re.search(r'"apiKey"\s*:\s*"([^"]+)"', text[start if start >= 0 else 0:])
    return match.group(1) if match else None


class Counter:
    """Counts tokens; remembers after the first failure that the server is away."""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.exact = True
        self.reason = ""
        self._seen: Dict[str, int] = {}   # exact counts by text digest; the estimate needs no memory

    def count(self, text: str) -> Tuple[int, bool]:
        """Return (tokens, exact). `exact` is False for an estimate."""
        if not text:
            return 0, self.exact
        if not self.exact:
            return estimate(text), False
        model = str(self.settings.get("model", ""))
        url = str(self.settings.get("url", "")).rstrip("/") + "/v1/messages/count_tokens"
        key = _api_key(self.settings)
        if not model or not key:
            return self._fall_back("no model name or API key configured", text)
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}]}).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST", headers={
            "content-type": "application/json", "x-api-key": key, "authorization": "Bearer " + key,
        })
        digest = hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()
        if digest in self._seen:
            return self._seen[digest], True
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self._seen[digest] = int(payload["input_tokens"])
            return self._seen[digest], True
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as error:
            return self._fall_back(f"{type(error).__name__}", text)

    def _fall_back(self, reason: str, text: str) -> Tuple[int, bool]:
        self.exact = False
        self.reason = reason
        return estimate(text), False
