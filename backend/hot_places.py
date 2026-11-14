"""Live 'what is actually popular right now' places for ANY city, using only free sources.

Chain (each step is skipped if it fails or finds nothing):
  1. Gemini with Google Search grounding (needs GEMINI_API_KEY; free tier has a daily limit)
  2. Free web search (DuckDuckGo, no key) -> the AI may only pick places named in those results
Results are cached for everyone by the caller, and each name is later verified on the map.
"""
import asyncio
import json
import logging
import re
from datetime import date
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger("voyanta.hot")

HOT_FOCUS: Dict[str, str] = {
    "trending": "specialty cafes, rooftop and aesthetic spots, gaming/bowling/entertainment zones, live music, dessert and brunch places, thrift and streetwear, nightlife",
    "attractions": "the most popular and most-posted things to see and do: viral photo spots, new openings, immersive experiences, famous landmarks people actually queue for, plus a couple of modern attractions (not just old monuments and museums)",
    "culinary": "the most talked-about restaurants, street food spots, famous local dishes' best outlets and new food openings",
    "bars_pubs": "the best bars, craft breweries, rooftop lounges and nightclubs people are going to right now",
    "secret_spots": "hidden gems and offbeat places that locals love but tourists miss: sunset points, quirky corners, local hangouts",
    "shopping": "the best markets, street shopping, thrift and streetwear stores, malls and concept stores people actually shop at",
    "adventures": "the best adventure activities and outdoor experiences: trekking, water sports, go-karting, ziplines, day trips",
    "wellness": "the best spas, yoga studios, retreats and calming places people recommend",
}
HOT_PILLARS = set(HOT_FOCUS)

_EXCLUDE = "Exclude hotels, schools, colleges, hospitals, banks, and businesses with no public hangout value."


def _prompt_grounded(dest: str, focus: str) -> str:
    return (
        f"Use Google Search. List the 10 best-known places in {dest} right now ({date.today().year}) for: {focus}. "
        f"Prefer places people are talking about recently (reviews, news, social posts, 'best of' lists from this year). {_EXCLUDE} "
        'Return ONLY a JSON array, no prose: [{"name": "exact place name", "area": "neighbourhood", "why": "one inviting sentence on why people love it, no numbers"}]'
    )


def _clean(data: Any) -> List[Dict[str, str]]:
    if isinstance(data, dict):  # models sometimes wrap the list: {"places": [...]}
        data = next((v for v in data.values() if isinstance(v, list)), [])
    if not isinstance(data, list):
        return []
    out = []
    for d in data:
        if isinstance(d, dict) and str(d.get("name", "")).strip():
            out.append({"name": str(d["name"]).strip()[:80], "area": str(d.get("area", "")).strip()[:60],
                        "why": re.sub(r"[0-9₹$€£]", "", str(d.get("why", ""))).strip()[:200]})
    return out[:12]


_model_cache: Dict[str, Any] = {"at": 0.0, "models": []}


def _version_key(name: str):
    return [int(x) for x in re.findall(r"\d+", name)] or [0]


async def gemini_models(client: httpx.AsyncClient, key: str) -> List[str]:
    """Flash models this key can actually use right now (Google retires model names often)."""
    import time
    if _model_cache["models"] and time.time() - _model_cache["at"] < 21600:
        return _model_cache["models"]
    try:
        r = await client.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key, "pageSize": 200}, timeout=8.0)
        if r.status_code == 200:
            names = []
            for m in r.json().get("models", []):
                n = m.get("name", "").replace("models/", "")
                if ("flash" in n and "generateContent" in (m.get("supportedGenerationMethods") or [])
                        and not any(x in n for x in ("lite", "image", "tts", "live", "audio", "thinking", "exp", "embedding"))):
                    names.append(n)
            names = sorted(set(names), key=_version_key, reverse=True)[:3]
            if names:
                _model_cache.update(at=time.time(), models=names)
                return names
    except Exception as e:
        logger.warning(f"Gemini model list failed: {e}")
    return ["gemini-flash-latest"]


async def gemini_hot(client: httpx.AsyncClient, key: str, dest: str, focus: str,
                     extract_json: Callable[[str], Any], trace: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    if not key or client is None:
        return []
    queue = list(await gemini_models(client, key))
    tried: set = set()
    while queue and len(tried) < 4:
        model = queue.pop(0)
        if model in tried:
            continue
        tried.add(model)
        try:
            r = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": _prompt_grounded(dest, focus)}]}], "tools": [{"google_search": {}}]},
                timeout=25.0)
            if r.status_code != 200:
                msg = r.text.replace(key, "***")
                logger.warning(f"Gemini grounded {model} -> {r.status_code}: {msg[:200]}")
                if trace is not None:
                    trace.append({"step": f"gemini:{model}", "status": r.status_code, "detail": re.sub(r"\s+", " ", msg)[:260]})
                if r.status_code == 404:  # Google's error names the replacement model; follow it
                    m = re.search(r"models/([A-Za-z0-9._\-]+)", msg.split("use", 1)[-1] if "use" in msg else "")
                    if m:
                        queue.insert(0, m.group(1).rstrip(".-"))
                continue
            parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            out = _clean(extract_json("".join(p.get("text", "") for p in parts)))
            if trace is not None:
                trace.append({"step": f"gemini:{model}", "status": 200, "found": len(out)})
            if out:
                return out
        except Exception as e:
            logger.warning(f"Gemini grounded {model} error: {e}")
            if trace is not None:
                trace.append({"step": f"gemini:{model}", "error": str(e)[:120]})
    return []


def _ddg_text(query: str, n: int) -> List[Dict[str, Any]]:
    try:
        from ddgs import DDGS  # newer package name
    except Exception:
        from duckduckgo_search import DDGS
    with DDGS() as d:
        return list(d.text(query, max_results=n))


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|nav|footer|header|aside|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<(h[1-4]|li|p|br|div|tr)[^>]*>", "\n", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&#?\w+;", " ", text)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


_BAD_HOSTS = ("youtube.", "facebook.", "instagram.", "twitter.", "x.com", "tiktok.", "pinterest.", "linkedin.", "tripadvisor.", "booking.", "makemytrip.")


async def _fetch_page(client: Optional[httpx.AsyncClient], url: str) -> str:
    try:
        c = client or httpx.AsyncClient()
        r = await c.get(url, timeout=6.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (compatible; VoyantaBot/1.0)"})
        if r.status_code == 200 and "html" in r.headers.get("content-type", "html"):
            return _html_to_text(r.text)[:5000]
    except Exception:
        pass
    return ""


async def ddg_hot(dest: str, focus: str, call_ai: Callable[[str], Awaitable[str]],
                  extract_json: Callable[[str], Any], trace: Optional[List[Dict[str, Any]]] = None,
                  client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, str]]:
    short = focus.split(":")[0][:90]
    year = date.today().year
    queries = [f"best {short} in {dest} {year}", f"{dest} {short} list guide {year}", f"{dest} {short} reddit locals recommend"]
    results: List[Dict[str, Any]] = []
    for q in queries:
        try:
            results += await asyncio.wait_for(asyncio.to_thread(_ddg_text, q, 8), timeout=10.0)
        except Exception as e:
            logger.warning(f"web search failed for '{q}': {e}")
            if trace is not None:
                trace.append({"step": "web_search", "error": str(e)[:120]})
    if not results:
        return []
    seen_u, urls = set(), []
    for r in results:
        u = str(r.get("href") or r.get("url") or "")
        if u.startswith("http") and u not in seen_u and not any(b in u for b in _BAD_HOSTS):
            seen_u.add(u)
            urls.append(u)
    pages = await asyncio.gather(*[_fetch_page(client, u) for u in urls[:4]])
    snippets = "\n".join(f"- {r.get('title', '')}: {r.get('body', '')}" for r in results)[:3500]
    articles = "\n\n".join(f"ARTICLE: {t}" for t in pages if t)[:12000]
    blob = f"{snippets}\n\n{articles}"
    prompt = (
        f"Below are web search results and article text about {focus.split(':')[0]} in {dest}.\n{blob}\n\n"
        f"Using ONLY places that are actually named in this text, list up to 10 specific named places in {dest} that are mentioned most or recommended most "
        f"(not articles, not generic categories). {_EXCLUDE} "
        'Return ONLY a JSON array: [{"name": "exact place name as written", "area": "neighbourhood if stated, else empty", "why": "one inviting sentence, no numbers"}]'
    )
    raw = ""
    try:
        raw = await asyncio.wait_for(call_ai(prompt), timeout=20.0)
        out = _clean(extract_json(raw))
    except Exception as e:
        logger.warning(f"web-search extraction failed: {e}")
        if trace is not None:
            trace.append({"step": "web_search+ai", "error": str(e)[:120]})
        return []
    low = blob.lower()
    grounded = [o for o in out if o["name"].lower() in low]  # drop anything not literally in the text
    if trace is not None:
        trace.append({"step": "web_search+ai", "results": len(results), "pages_read": sum(1 for t in pages if t),
                      "ai_names": len(out), "kept": len(grounded), "ai_reply_chars": len(raw or "")})
    return grounded


async def hot_places(client: httpx.AsyncClient, dest: str, pillar: str, gemini_key: str,
                     call_ai: Callable[[str], Awaitable[str]], extract_json: Callable[[str], Any],
                     focus_override: str = "", trace: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    focus = focus_override or HOT_FOCUS.get(pillar, HOT_FOCUS["trending"])
    out = await gemini_hot(client, gemini_key, dest, focus, extract_json, trace)
    if not out:
        out = await ddg_hot(dest, focus, call_ai, extract_json, trace, client)
    return out
