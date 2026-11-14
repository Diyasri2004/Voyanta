"""Shared cache so every visitor reuses the same expensive answers.

Uses Upstash Redis (free tier, REST API) when UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN are set,
so cached answers survive Render restarts and are shared across instances. Without them it falls back to an
in-process cache, so nothing breaks. Every failure is swallowed: a cache problem must never break a request.
"""
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger("voyanta.cache")

_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
_local: Dict[str, Tuple[float, str]] = {}
_LOCAL_MAX = 600
_client: Optional[httpx.AsyncClient] = None


def backend_name() -> str:
    return "upstash" if (_URL and _TOKEN) else "memory"


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=3.0)
    return _client


async def _cmd(*args: Any) -> Any:
    r = await _http().post(_URL, headers={"Authorization": f"Bearer {_TOKEN}"}, json=list(args))
    r.raise_for_status()
    return r.json().get("result")


async def cache_get(key: str) -> Optional[Any]:
    key = f"voyanta:{key}"
    now = time.time()
    hit = _local.get(key)
    if hit and hit[0] > now:
        try:
            return json.loads(hit[1])
        except Exception:
            return None
    if _URL and _TOKEN:
        try:
            raw = await _cmd("GET", key)
            if raw:
                _local[key] = (now + 60, raw)  # short local copy to spare Redis reads
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"cache get failed: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: int = 43200) -> None:
    key = f"voyanta:{key}"
    try:
        raw = json.dumps(value, default=str)
    except Exception:
        return
    if len(_local) >= _LOCAL_MAX:
        for k in sorted(_local, key=lambda k: _local[k][0])[: _LOCAL_MAX // 4]:
            _local.pop(k, None)
    _local[key] = (time.time() + (ttl if not (_URL and _TOKEN) else 60), raw)
    if _URL and _TOKEN:
        try:
            await _cmd("SET", key, raw, "EX", int(ttl))
        except Exception as e:
            logger.warning(f"cache set failed: {e}")
