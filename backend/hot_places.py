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
    if not isinstance(data, list):
        return []
    out = []
    for d in data:
        if isinstance(d, dict) and str(d.get("name", "")).strip():
            out.append({"name": str(d["name"]).strip()[:80], "area": str(d.get("area", "")).strip()[:60],
                        "why": re.sub(r"[0-9₹$€£]", "", str(d.get("why", ""))).strip()[:200]})
    return out[:12]


async def gemini_hot(client: httpx.AsyncClient, key: str, dest: str, focus: str,
                     extract_json: Callable[[str], Any], trace: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    if not key or client is None:
        return []
    for model in ("gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"):
        try:
            r = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": _prompt_grounded(dest, focus)}]}], "tools": [{"google_search": {}}]},
                timeout=20.0)
            if r.status_code != 200:
                msg = r.text[:160].replace(key, "***")
                logger.warning(f"Gemini grounded {model} -> {r.status_code}: {msg}")
                if trace is not None:
                    trace.append({"step": f"gemini:{model}", "status": r.status_code, "detail": msg})
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


async def ddg_hot(dest: str, focus: str, call_ai: Callable[[str], Awaitable[str]],
                  extract_json: Callable[[str], Any], trace: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    short = focus.split(":")[0][:90]
    queries = [f"best {short} in {dest} {date.today().year}", f"{dest} trending {short} reddit locals recommend"]
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
    blob = "\n".join(f"- {r.get('title', '')}: {r.get('body', '')}" for r in results)[:9000]
    prompt = (
        f"Below are web search results about {focus.split(':')[0]} in {dest}.\n{blob}\n\n"
        f"Using ONLY places that are actually named in these results, list up to 10 specific named places in {dest} (not articles, not generic categories). {_EXCLUDE} "
        'Return ONLY a JSON array: [{"name": "exact place name as written", "area": "neighbourhood if stated, else empty", "why": "one inviting sentence, no numbers"}]'
    )
    try:
        out = _clean(extract_json(await asyncio.wait_for(call_ai(prompt), timeout=15.0)))
    except Exception as e:
        logger.warning(f"web-search extraction failed: {e}")
        return []
    low = blob.lower()
    grounded = [o for o in out if o["name"].lower() in low]  # drop anything not literally in the results
    if trace is not None:
        trace.append({"step": "web_search+ai", "results": len(results), "found": len(grounded)})
    return grounded


async def hot_places(client: httpx.AsyncClient, dest: str, pillar: str, gemini_key: str,
                     call_ai: Callable[[str], Awaitable[str]], extract_json: Callable[[str], Any],
                     focus_override: str = "", trace: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    focus = focus_override or HOT_FOCUS.get(pillar, HOT_FOCUS["trending"])
    out = await gemini_hot(client, gemini_key, dest, focus, extract_json, trace)
    if not out:
        out = await ddg_hot(dest, focus, call_ai, extract_json, trace)
    return out
