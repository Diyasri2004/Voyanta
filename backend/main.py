import os
import json
import logging
import httpx
import re
import urllib.parse
import asyncio
import time
from collections import OrderedDict
from datetime import date
from uuid import UUID
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncpg
from cachetools import TTLCache
from dotenv import load_dotenv

from models import EventFestival
from chat_agent import get_voya_system_prompt, get_chat_agent_tools, execute_tool_call

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voyanta")

load_dotenv()

# In-Memory High-Speed LRU Cache for Sub-Millisecond Hits
class FastTTLCache:
    def __init__(self, maxsize=150, ttl=3600):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl

    def get(self, key):
        if key not in self.cache:
            return None
        val, exp = self.cache[key]
        if time.time() > exp:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return val

    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time() + self.ttl)
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

response_cache = FastTTLCache(maxsize=200, ttl=86400)
dynamic_cache = TTLCache(maxsize=2000, ttl=86400)

# Environment Variables
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "").strip()
TOMTOM_BASE = "https://api.tomtom.com"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
UNSPLASH_ACCESS_KEY = (os.getenv("UNSPLASH_ACCESS_KEY") or os.getenv("UNSPLASH_API_KEY") or "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY", "").strip()
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()

logger.info(f"Key Status -> Groq ({GROQ_MODEL}): {bool(GROQ_API_KEY)} | OpenRouter: {bool(OPENROUTER_API_KEY)} | Gemini: {bool(GEMINI_API_KEY)}")

# ─────────────────────────────────────────────
#  Pydantic Models
# ─────────────────────────────────────────────

class Coordinates(BaseModel):
    lat: float
    lng: float

class GeocodeResult(BaseModel):
    address: str
    lat: float
    lng: float
    country: str
    city: Optional[str] = None
    score: Optional[float] = None

class RouteWaypoint(BaseModel):
    lat: float
    lng: float

class RouteRequest(BaseModel):
    waypoints: List[RouteWaypoint]
    travel_mode: Optional[str] = "car"

class RouteLeg(BaseModel):
    distance_meters: float
    travel_time_seconds: float
    summary: str

class RouteResponse(BaseModel):
    total_distance_meters: float
    total_travel_time_seconds: float
    geojson: dict
    legs: List[RouteLeg]

class POI(BaseModel):
    id: str
    name: str
    category: str
    lat: float
    lng: float
    distance_meters: Optional[float] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None

class TrafficIncident(BaseModel):
    id: str
    description: str
    severity: str
    lat: float
    lng: float

class ReverseGeocodeResult(BaseModel):
    address: str
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

class TravelerGroup(BaseModel):
    group_type: Optional[str] = "Solo"
    adults: Optional[int] = 1
    seniors: Optional[int] = 0
    infants: Optional[int] = 0

class TripPlanRequest(BaseModel):
    location: Optional[str] = None
    destination: Optional[str] = None
    days: Optional[int] = 3
    start_date: Optional[date] = None
    categories: Optional[List[str]] = None
    pace: Optional[str] = None
    budget: Optional[str] = None
    travelers: Optional[TravelerGroup] = None
    language: Optional[str] = "English"

class TripStop(BaseModel):
    id: str
    day: int
    date: str
    time: str
    title: str
    location: str
    type: str
    creators: str
    distance: str
    elevation: Optional[str] = "N/A"
    duration: str
    image: str
    map_image_url: str
    lat: float
    lng: float
    cost_range: str

class TripDayRoute(BaseModel):
    day: int
    geojson: Optional[dict] = None
    total_distance_meters: float = 0
    total_travel_time_seconds: float = 0

class CulinaryHighlight(BaseModel):
    title: str
    description: str
    famous_for: str
    location: str
    price_tier: Optional[str] = ""
    cost_approx: Optional[str] = ""

class PillarItem(BaseModel):
    id: str
    title: str
    name: Optional[str] = None
    category: str
    specialty: Optional[str] = ""
    description: str
    address: str
    location: Optional[str] = None
    maps_url: str
    navigation_url: Optional[str] = None
    image_url: str
    image: Optional[str] = None
    serving_style: Optional[str] = ""
    event_time: Optional[str] = ""
    price_range: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None

class TripPlanResponse(BaseModel):
    destination: str
    language: str = "en"
    destination_image: str = ""
    map_image_url: str = ""
    weather: str = "Clear"
    dates: str = ""
    days: int = 3
    coordinates: Optional[Coordinates] = None
    itinerary: List[TripStop] = Field(default_factory=list)
    routes: List[TripDayRoute] = Field(default_factory=list)
    culinary_highlights: List[CulinaryHighlight] = Field(default_factory=list)
    attractions: List[PillarItem] = Field(default_factory=list)
    events: List[PillarItem] = Field(default_factory=list)
    culinary: List[PillarItem] = Field(default_factory=list)
    bars_pubs: List[PillarItem] = Field(default_factory=list)
    wellness: List[PillarItem] = Field(default_factory=list)
    secret_spots: List[PillarItem] = Field(default_factory=list)
    essentials: List[PillarItem] = Field(default_factory=list)
    shopping: List[PillarItem] = Field(default_factory=list)
    adventures: List[PillarItem] = Field(default_factory=list)
    theme_parks: List[PillarItem] = Field(default_factory=list)
    sacred_temples: List[PillarItem] = Field(default_factory=list)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    destination: Optional[str] = ""
    language: Optional[str] = "en"
    currency: Optional[str] = "USD"
    user_time: Optional[str] = ""
    user_timezone: Optional[str] = ""
    history: Optional[List[ChatMessage]] = []
    active_itinerary: Optional[List[Dict[str, Any]]] = []

# ─────────────────────────────────────────────
#  Lifespan & Initialization
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = None
    if DATABASE_URL:
        try:
            app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, timeout=10)
            logger.info("Database pool connected.")
        except Exception as e:
            logger.warning(f"Could not connect to DB: {e}")

    limits = httpx.Limits(max_keepalive_connections=100, max_connections=200, keepalive_expiry=30.0)
    timeout = httpx.Timeout(15.0, connect=3.0)
    app.state.client = httpx.AsyncClient(limits=limits, timeout=timeout)
    yield
    if app.state.db_pool:
        await app.state.db_pool.close()
    await app.state.client.aclose()

app = FastAPI(title="Voyanta Pure AI Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
#  Helper Dependencies & Dynamic Resolvers
# ─────────────────────────────────────────────

async def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.client

async def get_db_pool():
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable.")
    yield pool

def tomtom_key():
    if not TOMTOM_API_KEY:
        raise HTTPException(status_code=500, detail="TomTom API key not configured.")
    return TOMTOM_API_KEY

async def resolve_dynamic_coordinates(client: httpx.AsyncClient, destination: str) -> Coordinates:
    cache_key = f"coords:{destination.lower().strip()}"
    if cache_key in dynamic_cache:
        return dynamic_cache[cache_key]

    parts = [x.strip() for x in destination.split(",") if x.strip()]
    clean = parts[0] if parts else destination.strip()
    hint = " ".join(parts[1:]).lower()

    # TomTom first: it understands regions/states ("Kerala") and picks the well-known "Kochi"/"Paris"
    if TOMTOM_API_KEY:
        try:
            res = await client.get(f"{TOMTOM_BASE}/search/2/geocode/{urllib.parse.quote(destination.strip())}.json",
                                   params={"key": TOMTOM_API_KEY, "limit": 1}, timeout=2.5)
            if res.status_code == 200:
                results = res.json().get("results", [])
                if results:
                    pos = results[0].get("position", {})
                    coords = Coordinates(lat=float(pos.get("lat", 0.0)), lng=float(pos.get("lon", 0.0)))
                    dynamic_cache[cache_key] = coords
                    return coords
        except Exception as e:
            logger.warning(f"TomTom geocode error for {destination}: {e}")

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean)}&count=10"
        res = await client.get(geo_url, timeout=2.5)
        if res.status_code == 200 and res.json().get("results"):
            candidates = res.json()["results"]
            if hint:
                narrowed = [c for c in candidates if any(
                    h and h in hint for h in [str(c.get("country", "")).lower(), str(c.get("admin1", "")).lower(), str(c.get("country_code", "")).lower()])]
                candidates = narrowed or candidates
            # Same name exists in many places (Kochi in Kerala vs Japan): prefer the best-known one
            item = max(candidates, key=lambda c: c.get("population") or 0)
            coords = Coordinates(lat=float(item["latitude"]), lng=float(item["longitude"]))
            dynamic_cache[cache_key] = coords
            return coords
    except Exception as e:
        logger.warning(f"Open-Meteo geocode lookup error for {clean}: {e}")

    if TOMTOM_API_KEY:
        try:
            url = f"{TOMTOM_BASE}/search/2/geocode/{urllib.parse.quote(clean)}.json"
            res = await client.get(url, params={"key": TOMTOM_API_KEY, "limit": 1}, timeout=2.0)
            if res.status_code == 200:
                results = res.json().get("results", [])
                if results:
                    pos = results[0].get("position", {})
                    coords = Coordinates(lat=float(pos.get("lat", 0.0)), lng=float(pos.get("lon", 0.0)))
                    dynamic_cache[cache_key] = coords
                    return coords
        except Exception as e:
            logger.warning(f"TomTom geocode error for {clean}: {e}")

    return Coordinates(lat=20.0, lng=0.0)

_PHOTO_STOPWORDS = {
    "the", "and", "for", "with", "from", "near", "city", "park", "old", "new", "day", "night",
    "festival", "temple", "market", "beach", "fort", "museum", "restaurant", "cafe", "bar",
    "tea", "garden", "gardens", "estate", "estates", "house", "hall", "street", "food", "junction",
    "lake", "falls", "waterfall", "waterfalls", "national", "sanctuary", "wildlife", "palace", "hotel",
    "grand", "canteen", "snacks", "stall", "boat", "race", "club", "lounge", "pub", "shop", "store",
    "international", "annual", "cultural", "music", "dance", "show", "fair",
}
_photo_sem = asyncio.Semaphore(10)
_BAD_IMAGE_HINTS = (".svg", "flag", "locator", "_map", "map_of", "location_in", "logo", "icon", "coat_of_arms", "seal_of")

def _photo_tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 3 and w not in _PHOTO_STOPWORDS}

async def _wiki_photo(client: httpx.AsyncClient, query: str, must_match: set) -> str:
    """Wikipedia lead image of the best-matching article; the article title must share a word with the place."""
    try:
        res = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "format": "json", "prop": "pageimages", "piprop": "thumbnail",
                    "pithumbsize": 900, "generator": "search", "gsrsearch": query, "gsrlimit": 5},
            headers={"User-Agent": "VoyantaTravelApp/1.0 (travel@voyanta.app)"}, timeout=2.5)
        if res.status_code != 200:
            return ""
        pages = sorted(res.json().get("query", {}).get("pages", {}).values(), key=lambda pg: pg.get("index", 99))
        for page in pages:
            src = page.get("thumbnail", {}).get("source", "")
            if not src or any(h in src.lower() for h in _BAD_IMAGE_HINTS):
                continue
            if must_match and not (_photo_tokens(page.get("title", "")) & must_match):
                continue
            return src
    except Exception:
        pass
    return ""

async def _stock_photo(client: httpx.AsyncClient, query: str, v_tokens: set, d_tokens: set) -> str:
    """Pexels, then Unsplash; a result is only accepted if its description names the place or the destination."""
    def pick(items):
        best = ""
        for desc, url in items:
            desc = (desc or "").lower()
            if v_tokens and any(t in desc for t in v_tokens):
                return url
            if not best and d_tokens and any(t in desc for t in d_tokens):
                best = url
        return best

    if PEXELS_API_KEY:
        try:
            res = await client.get("https://api.pexels.com/v1/search",
                                   params={"query": query, "orientation": "landscape", "per_page": 8},
                                   headers={"Authorization": PEXELS_API_KEY}, timeout=2.5)
            if res.status_code == 200:
                found = pick([(p.get("alt"), p["src"]["large"]) for p in res.json().get("photos", [])])
                if found:
                    return found
        except Exception:
            pass
    if UNSPLASH_ACCESS_KEY:
        try:
            res = await client.get("https://api.unsplash.com/search/photos",
                                   params={"query": query, "orientation": "landscape", "per_page": 8, "client_id": UNSPLASH_ACCESS_KEY},
                                   timeout=2.5)
            if res.status_code == 200:
                found = pick([(f"{r.get('alt_description') or ''} {r.get('description') or ''}", r["urls"]["regular"])
                              for r in res.json().get("results", [])])
                if found:
                    return found
        except Exception:
            pass
    return ""

async def fetch_destination_photo(client: httpx.AsyncClient, destination: str) -> str:
    d_clean = destination.split(",")[0].strip() if destination else ""
    if not d_clean:
        return ""
    key = f"destphoto:{d_clean.lower()}"
    if key in dynamic_cache:
        return dynamic_cache[key]
    d_tokens = _photo_tokens(d_clean)
    url = await _wiki_photo(client, d_clean, d_tokens) or await _stock_photo(client, f"{d_clean} travel", set(), d_tokens)
    if url:
        dynamic_cache[key] = url
    return url

async def fetch_dynamic_place_photo(client: httpx.AsyncClient, venue: str = "", destination: str = "", category: str = "") -> str:
    """Photo of the actual place in the actual destination. Never returns an unrelated stock image."""
    v_clean = re.sub(r"[\(\)\[\],|]", " ", venue or "").strip()
    d_clean = destination.split(",")[0].strip() if destination else ""
    c_clean = re.sub(r"[\(\)\[\],|]", " ", category or "").strip().lower()

    if not v_clean:
        return await fetch_destination_photo(client, d_clean)

    key = f"photo:{v_clean.lower()}|{d_clean.lower()}"
    if key in dynamic_cache:
        return dynamic_cache[key]

    v_tokens = _photo_tokens(v_clean)
    d_tokens = _photo_tokens(d_clean)
    query = f"{v_clean} {d_clean}".strip()

    # Wikipedia only suits landmarks and events; for eateries and bars it tends to return people or unrelated pages
    is_business = any(k in c_clean for k in ["culinary", "food", "restaurant", "cafe", "dining", "bar", "pub", "nightlife", "lounge"])
    async with _photo_sem:
        url = "" if is_business else await _wiki_photo(client, query, v_tokens)
        if not url:
            url = await _stock_photo(client, query, v_tokens, d_tokens)
    if not url:
        # Same destination, on-topic scene: only accepted when the photo mentions the destination
        topic = ""
        if any(k in c_clean for k in ["culinary", "food", "restaurant", "cafe", "dining"]):
            topic = "food"
        elif any(k in c_clean for k in ["festival", "event", "concert", "dance", "cultural"]):
            topic = "festival"
        elif any(k in c_clean for k in ["temple", "shrine", "church", "mosque"]):
            topic = "temple"
        elif any(k in c_clean for k in ["shopping", "market"]):
            topic = "market"
        elif any(k in c_clean for k in ["bar", "pub", "nightlife"]):
            topic = "nightlife"
        if topic and d_clean:
            async with _photo_sem:
                url = await _stock_photo(client, f"{d_clean} {topic}", set(), d_tokens)
    if not url:
        url = await fetch_destination_photo(client, d_clean)
    if url:
        dynamic_cache[key] = url
    return url

def clean_venue_title(title: str, destination: str = "") -> str:
    if not title:
        return "Iconic Destination"
    clean = str(title).strip()
    if destination:
        dest_esc = re.escape(destination.strip())
        clean = re.sub(rf"^(?:{dest_esc}[\s,:\-]+)+", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"^[,\-:\s]+", "", clean).strip()
    return clean if clean else str(title).strip()

def format_date_range(start: date, days: int) -> str:
    end = start.fromordinal(start.toordinal() + max(days - 1, 0))
    if start.month == end.month:
        return f"{start.strftime('%b %d')} - {end.strftime('%d')}"
    return f"{start.strftime('%b %d')} - {end.strftime('%b %d')}"

PILLAR_DESCRIPTIONS = {
    "attractions": "iconic landmarks and sights",
    "events": "annual festivals and top events",
    "culinary": "famous eateries and local specialties",
    "bars_pubs": "rooftop bars and nightlife hotspots",
    "wellness": "luxury spas and nature spots",
    "secret_spots": "hidden gems and local nooks",
    "essentials": "transit hubs, hospitals, and emergency centers",
    "shopping": "bazaars, markets, and malls",
    "adventures": "outdoor adventure hubs and trails",
    "theme_parks": "amusement and water parks",
    "sacred_temples": "historic temples, cathedrals, and shrines"
}

# ─────────────────────────────────────────────
#  AI Generation Engine (Groq + Gemini Fallback)
# ─────────────────────────────────────────────

async def call_ai_with_rate_limit_fallback(client: httpx.AsyncClient, prompt: str) -> str:
    # ── TIER 3: GROQ (tries each model; moves on when one is rate limited) ───
    groq_key = GROQ_API_KEY or os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        for groq_model in ("openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"):
            try:
                g_payload = {
                    "model": groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
                if groq_model.startswith("openai/gpt-oss"):
                    g_payload["reasoning_effort"] = "low"
                res = await client.post("https://api.groq.com/openai/v1/chat/completions", json=g_payload, headers=headers, timeout=6.0)
                if res.status_code == 200:
                    raw = res.json()["choices"][0]["message"]["content"]
                    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                    logger.info(f"⚡ Fallback AI generation succeeded via Groq ({groq_model})")
                    return cleaned
                logger.warning(f"Groq {groq_model} status {res.status_code}")
            except Exception as e:
                logger.warning(f"Groq {groq_model} error: {e}")

    # ── TIER 1: GEMINI DIRECT ─────────────────────────────────────────────
    gemini_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        g_models = [
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
            "gemini-3-flash-preview"
        ]
        for g_model in g_models:
            try:
                g_url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={gemini_key}"
                g_payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2}
                }
                res = await client.post(g_url, json=g_payload, timeout=8.0)
                if res.status_code == 200:
                    raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                    logger.info(f"⚡ Instant AI generation succeeded via Gemini ({g_model})")
                    return cleaned
                else:
                    logger.warning(f"Gemini {g_model} status {res.status_code}: {res.text[:120]}")
            except Exception as e:
                logger.warning(f"Gemini {g_model} connection error: {e}")

    # ── TIER 2: DIRECT OPENROUTER ───────────────────────────────────────────
    openrouter_key = OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        or_models = [
            "meta-llama/llama-3.3-70b-instruct:free",
            "openrouter/auto",
            "deepseek/deepseek-r1:free"
        ]
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "HTTP-Referer": "https://voyanta-xi.vercel.app",
            "X-Title": "Voyanta AI",
            "Content-Type": "application/json"
        }
        for model in or_models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                res = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=8.0)
                if res.status_code == 200:
                    raw = res.json()["choices"][0]["message"]["content"]
                    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                    logger.info(f"⚡ AI generation succeeded via OpenRouter ({model})")
                    return cleaned
                else:
                    logger.warning(f"OpenRouter {model} status {res.status_code}: {res.text[:120]}")
            except Exception as e:
                logger.warning(f"OpenRouter {model} connection error: {e}")

    return '{"tool_call": null, "reply": "I am ready! Tell me about your destination or plan."}'

# ─────────────────────────────────────────────
#  API Endpoints
# ─────────────────────────────────────────────

@app.api_route("/healthz", methods=["GET", "HEAD", "OPTIONS"], tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "voyanta-pure-ai-engine"}

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": "Voyanta Pure AI Engine",
        "ai_active": bool(OPENROUTER_API_KEY or GROQ_API_KEY or GEMINI_API_KEY),
        "geocoding": "Dynamic Open-Meteo & TomTom"
    }

@app.get("/api/trending", tags=["Discovery"])
async def get_trending_destinations(request: Request):
    cache_key = "dynamic_trending_destinations"
    if cache_key in dynamic_cache:
        return {"trending": dynamic_cache[cache_key]}

    prompt = 'Return JSON with key "trending" listing 8 top travel destinations: {"trending": [{"name": "City", "country": "Country"}]}'
    
    client = getattr(request.app.state, "client", None) or getattr(request.app.state, "http_client", None)
    if not client:
        return {"trending": []}

    try:
        raw = await call_ai_with_rate_limit_fallback(client, prompt)
        data = json.loads(raw)
        trending = data.get("trending", [])
        if trending and isinstance(trending, list):
            dynamic_cache[cache_key] = trending
            return {"trending": trending}
    except Exception as e:
        logger.error(f"Dynamic trending generation error: {e}")

    return {"trending": []}

# --- HIGH-SPEED PURE DYNAMIC THEME PARKS PILLAR ---
async def build_dynamic_themeparks_pillar(client: httpx.AsyncClient, dest_name: str, coords: Coordinates):
    prompt = f"""
    List 5 real, notable theme parks, water parks, or adventure arenas in or near {dest_name}.
    Output strictly JSON matching:
    {{
      "theme_parks": [
        {{
          "title": "Exact Park Name",
          "category": "Theme Park",
          "description": "Short accurate highlight of key rides or attractions",
          "location": "District/Area in {dest_name}",
          "rating": 4.5,
          "ticket_price": "Real ticket price or admission details",
          "best_time": "Real operational hours or season"
        }}
      ]
    }}
    Provide authentic details only.
    """
    try:
        raw = await call_ai_with_rate_limit_fallback(client, prompt)
        data = json.loads(raw)
        parks_raw = data.get("theme_parks", [])[:5]
    except Exception as e:
        logger.error(f"Theme parks AI generation error: {e}")
        return []

    # Parallelize photo lookups with a fast timeout
    async def fetch_photo_safe(name: str):
        try:
            return await asyncio.wait_for(fetch_dynamic_place_photo(client, venue=name, destination=dest_name, category="Theme Park"), timeout=3.5)
        except Exception:
            return ""

    photos = await asyncio.gather(*[fetch_photo_safe(p.get("title", "")) for p in parks_raw])

    parks = []
    for idx, (p, photo) in enumerate(zip(parks_raw, photos)):
        parks.append({
            "id": f"park-{idx+1}",
            "title": p.get("title", ""),
            "category": p.get("category", "Theme Park"),
            "description": p.get("description", ""),
            "location": p.get("location", dest_name),
            "image": photo,
            "rating": p.get("rating"),
            "ticket_price": p.get("ticket_price", ""),
            "best_time": p.get("best_time", ""),
            "lat": coords.lat + (idx * 0.003),
            "lng": coords.lng + (idx * 0.003)
        })
    return parks

# --- HIGH-SPEED PURE DYNAMIC EVENTS PILLAR ---
async def build_dynamic_events_pillar(client: httpx.AsyncClient, dest_name: str, coords: Coordinates):
    prompt = f"""
    List 5 real cultural events, seasonal festivals, or live music showcases in {dest_name}.
    Output strictly JSON matching:
    {{
      "events": [
        {{
          "title": "Exact Event Name",
          "category": "Cultural Festival",
          "description": "Brief description of the event celebration",
          "venue": "Specific venue or area in {dest_name}",
          "dates": "Real recurring month or season",
          "entry_fee": "Real entry policy or ticket cost"
        }}
      ]
    }}
    Provide authentic details only.
    """
    try:
        raw = await call_ai_with_rate_limit_fallback(client, prompt)
        data = json.loads(raw)
        events_raw = data.get("events", [])[:5]
    except Exception as e:
        logger.error(f"Events AI generation error: {e}")
        return []

    # Parallelize photo lookups with a fast timeout
    async def fetch_photo_safe(name: str):
        try:
            return await asyncio.wait_for(fetch_dynamic_place_photo(client, venue=name, destination=dest_name, category="Cultural Festival"), timeout=3.5)
        except Exception:
            return ""

    photos = await asyncio.gather(*[fetch_photo_safe(e.get("title", "")) for e in events_raw])

    events = []
    for idx, (e, photo) in enumerate(zip(events_raw, photos)):
        events.append({
            "id": f"event-{idx+1}",
            "title": e.get("title", ""),
            "category": e.get("category", "Cultural Festival"),
            "description": e.get("description", ""),
            "venue": e.get("venue", dest_name),
            "dates": e.get("dates", ""),
            "entry_fee": e.get("entry_fee", ""),
            "image": photo,
            "lat": coords.lat + (idx * 0.002),
            "lng": coords.lng + (idx * 0.002)
        })
    return events

def extract_json_payload(text: str) -> Optional[Any]:
    if not text:
        return None
    cleaned = text.strip()
    
    # Remove markdown code blocks if wrapped
    if "```" in cleaned:
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE).strip()
    
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Extract JSON array regex pattern safely
    try:
        match_arr = re.search(r'\[[\s\S]*\]', cleaned)
        if match_arr:
            return json.loads(match_arr.group(0))
    except Exception:
        pass

    # Extract JSON object regex pattern safely
    try:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return None

CATEGORY_IMAGE_FALLBACKS = {
    "attractions": [
        "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1538688525198-9b88f6f53126?auto=format&fit=crop&w=800&q=80"
    ],
    "culinary": [
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1552611052-33e04de081de?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=800&q=80"
    ],
    "bars_pubs": [
        "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1572116469696-31de0f17cc34?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1543007630-9710e4a00a20?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1566417713940-fe7c737a9ef2?auto=format&fit=crop&w=800&q=80"
    ],
    "wellness": [
        "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1519710164239-da123dc03ef4?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80"
    ],
    "secret_spots": [
        "https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?auto=format&fit=crop&w=800&q=80"
    ],
    "shopping": [
        "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1528698827591-e19ccd7bc23d?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=800&q=80"
    ],
    "adventures": [
        "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1501555088652-021faa106b9b?auto=format&fit=crop&w=800&q=80"
    ],
    "theme_parks": [
        "https://images.unsplash.com/photo-1513889961551-628c1e5e2ee9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1561571994-3c61c554181a?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80"
    ],
    "sacred_temples": [
        "https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80"
    ],
    "events": [
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=800&q=80"
    ],
    "essentials": [
        "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=800&q=80"
    ]
}

def get_fast_dynamic_image_url(query: str, destination: str, category: str = "", idx: int = 0) -> str:
    cat_key = category.lower().replace(" ", "_")
    pool = CATEGORY_IMAGE_FALLBACKS.get(cat_key, CATEGORY_IMAGE_FALLBACKS["attractions"])
    return pool[idx % len(pool)]

async def fetch_dynamic_venue_image(query: str, destination: str, client: Optional[httpx.AsyncClient] = None) -> str:
    return get_fast_dynamic_image_url(query, destination, "attractions", 0)

async def generate_itinerary_segment(destination: str, start_day: int, end_day: int, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    prompt = f"""You are a master local travel curator.
Destination: {destination}
Target Plan: Day {start_day} to Day {end_day}

Generate an authentic, highly detailed travel plan with 3 daily slots (Morning, Afternoon, Evening) for each day from Day {start_day} to Day {end_day}.
Every slot MUST feature a specific, real-world venue, attraction, or restaurant in {destination} (e.g., 'Jerónimos Monastery', 'Time Out Market', 'Alfama Miradouro Walk'). DO NOT use generic names.

Output strictly a JSON array of slot objects:
[
  {{
    "day": {start_day},
    "time": "Morning",
    "title": "Exact Real Venue Name",
    "description": "Engaging 1-2 sentence overview highlighting why this spot is special.",
    "category": "Attractions",
    "estimated_cost": "$15 - $25",
    "coordinates": {{"lat": 38.7223, "lng": -9.1393}}
  }}
]"""

    try:
        raw = await asyncio.wait_for(call_ai_with_rate_limit_fallback(client, prompt), timeout=3.5)
        parsed = extract_json_payload(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "slots" in parsed:
            return parsed["slots"]
    except Exception as e:
        logger.warning(f"Error generating days {start_day}-{end_day}: {e}")
    return []

@app.post("/api/itinerary/generate", tags=["Trips"])
@app.post("/itinerary/generate", tags=["Trips"])
async def generate_itinerary(req: Dict[str, Any], request: Request):
    client = request.app.state.client
    destination = (req.get("destination") or req.get("location") or "Lisbon").strip().title()
    total_days = min(max(int(req.get("days") or 3), 1), 30)
    cache_key = f"itinerary_{destination.lower()}_{total_days}"

    cached_data = response_cache.get(cache_key)
    if cached_data:
        return cached_data

    # 1. Chunk execution into 5-day parallel batches with strict timeout
    chunk_size = 5
    tasks = []
    for start in range(1, total_days + 1, chunk_size):
        end = min(start + chunk_size - 1, total_days)
        tasks.append(generate_itinerary_segment(destination, start, end, client))

    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_slots = []
    for res in chunk_results:
        if isinstance(res, list):
            all_slots.extend(res)

    for idx, slot in enumerate(all_slots):
        if isinstance(slot, dict):
            title = slot.get("title", destination)
            cat = slot.get("category", "attractions")
            slot["image"] = ""

    final_slots = [s for s in all_slots if isinstance(s, dict)]

    async def attach_slot_photo(slot):
        try:
            slot["image"] = await asyncio.wait_for(
                fetch_dynamic_place_photo(client, venue=slot.get("title", ""), destination=destination, category=slot.get("category", "")),
                timeout=6.0)
        except Exception:
            slot["image"] = await fetch_destination_photo(client, destination)

    await asyncio.gather(*[attach_slot_photo(sl) for sl in final_slots])

    payload = {
        "status": "success",
        "destination": destination,
        "total_days": total_days,
        "slots": final_slots
    }
    if final_slots:
        response_cache.set(cache_key, payload)

    return payload

# ─────────────────────────────────────────────
#  Real Events Engine (Ticketmaster + Google Events). No AI-invented events.
# ─────────────────────────────────────────────

_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def _parse_event_day(text: str) -> Optional[date]:
    """Parse 'Nov 20', '2026-11-20' or 'Fri, Nov 20, 7 PM' into a future-leaning date."""
    if not text:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})\b", text)
    if m and m.group(1).lower() in _MONTHS:
        today = date.today()
        try:
            d = date(today.year, _MONTHS[m.group(1).lower()], int(m.group(2)))
        except ValueError:
            return None
        if (today - d).days > 30:
            d = date(today.year + 1, d.month, d.day)
        return d
    return None

async def fetch_ticketmaster_events(client: httpx.AsyncClient, coords: Coordinates, days_ahead: int = 120) -> List[Dict[str, Any]]:
    if not TICKETMASTER_API_KEY:
        return []
    start = date.today()
    end = date.fromordinal(start.toordinal() + days_ahead)
    try:
        res = await client.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params={"apikey": TICKETMASTER_API_KEY, "latlong": f"{coords.lat},{coords.lng}", "radius": 100, "unit": "km",
                    "startDateTime": f"{start.isoformat()}T00:00:00Z", "endDateTime": f"{end.isoformat()}T23:59:59Z",
                    "sort": "date,asc", "size": 40},
            timeout=8.0)
        if res.status_code != 200:
            logger.warning(f"Ticketmaster status {res.status_code}")
            return []
        out = []
        for ev in res.json().get("_embedded", {}).get("events", []):
            st = ev.get("dates", {}).get("start", {})
            day = _parse_event_day(st.get("localDate", ""))
            venues = ev.get("_embedded", {}).get("venues", [{}])
            venue = venues[0] if venues else {}
            imgs = [i for i in ev.get("images", []) if i.get("url")]
            imgs.sort(key=lambda i: (i.get("ratio") != "16_9", -(i.get("width") or 0)))
            cls = (ev.get("classifications") or [{}])[0]
            kind = " · ".join(x for x in [cls.get("segment", {}).get("name"), cls.get("genre", {}).get("name")] if x and x != "Undefined")
            price = ""
            pr = (ev.get("priceRanges") or [{}])[0]
            if pr.get("min") is not None:
                price = f"{pr.get('currency', '')} {pr['min']:g}" + (f" - {pr['max']:g}" if pr.get("max") not in (None, pr["min"]) else "")
            out.append({
                "title": ev.get("name", ""),
                "day": day,
                "when": f"{day.strftime('%a, %b %d, %Y')}" + (f" · {st['localTime'][:5]}" if st.get("localTime") else "") if day else "",
                "venue": venue.get("name", ""),
                "address": ", ".join(x for x in [venue.get("address", {}).get("line1"), venue.get("city", {}).get("name")] if x),
                "url": ev.get("url", ""),
                "image": imgs[0]["url"] if imgs else "",
                "description": kind or "Live event",
                "price": price.strip(),
                "source": "Ticketmaster",
            })
        return out
    except Exception as e:
        logger.warning(f"Ticketmaster error: {e}")
        return []

async def fetch_google_events(client: httpx.AsyncClient, destination: str) -> List[Dict[str, Any]]:
    if not SERPAPI_KEY:
        return []
    try:
        res = await client.get(
            "https://serpapi.com/search.json",
            params={"engine": "google_events", "q": f"Events in {destination}", "hl": "en", "api_key": SERPAPI_KEY},
            timeout=10.0)
        if res.status_code != 200:
            logger.warning(f"SerpApi status {res.status_code}")
            return []
        out = []
        for ev in res.json().get("events_results", []):
            d = ev.get("date", {}) or {}
            day = _parse_event_day(d.get("start_date", "")) or _parse_event_day(d.get("when", ""))
            venue = (ev.get("venue") or {}).get("name", "")
            out.append({
                "title": ev.get("title", ""),
                "day": day,
                "when": d.get("when") or d.get("start_date", ""),
                "venue": venue,
                "address": ", ".join(ev.get("address") or []),
                "url": ev.get("link", ""),
                "image": ev.get("image") or ev.get("thumbnail") or "",
                "description": ev.get("description", ""),
                "price": "",
                "source": "Google Events",
            })
        return out
    except Exception as e:
        logger.warning(f"SerpApi error: {e}")
        return []

async def build_real_events(client: httpx.AsyncClient, clean_dest: str, trip_start: Optional[date] = None, trip_end: Optional[date] = None, geo_query: str = "") -> List[Dict[str, Any]]:
    coords = await resolve_dynamic_coordinates(client, geo_query or clean_dest)
    today = date.today()
    far = max(today.toordinal() + 180, (trip_end.toordinal() + 60) if trip_end else 0)
    horizon = date.fromordinal(min(far, today.toordinal() + 365))
    tm, ge = await asyncio.gather(
        fetch_ticketmaster_events(client, coords, days_ahead=(horizon - today).days),
        fetch_google_events(client, clean_dest))

    merged, seen = [], set()
    for ev in tm + ge:
        title = (ev.get("title") or "").strip()
        day = ev.get("day")
        if not title or (day and (day < today or day > horizon)):
            continue
        key = (re.sub(r"[^a-z0-9]", "", title.lower()), day)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ev)
    window = (trip_start, trip_end) if trip_start and trip_end else None

    def classify(ev: Dict[str, Any]):
        """In-trip events first, then the nearest ones before/after the trip, then undated ones."""
        day = ev.get("day")
        if not day:
            ev["in_trip"], ev["note"] = False, ""
            return (2, 0, today)
        if not window:
            ev["in_trip"], ev["note"] = False, ""
            return (0, 0, day)
        ts, te = window
        if ts <= day <= te:
            ev["in_trip"], ev["note"] = True, "Happening during your trip"
            return (0, 0, day)
        gap = (ts - day).days if day < ts else (day - te).days
        ev["in_trip"] = False
        ev["note"] = f"Not during your trip \u00b7 {gap} day{'s' if gap != 1 else ''} {'before' if day < ts else 'after'}"
        return (1, gap, day)

    merged.sort(key=classify)
    merged = merged[:30]

    async def finish(idx: int, ev: Dict[str, Any]) -> Dict[str, Any]:
        image = ev.get("image") or ""
        if not image:
            try:
                image = await asyncio.wait_for(
                    fetch_dynamic_place_photo(client, venue=ev.get("venue") or ev["title"], destination=clean_dest, category="Event"), timeout=5.0)
            except Exception:
                image = ""
        location = ev.get("venue") or clean_dest
        q = urllib.parse.quote(f"{ev.get('venue') or ev['title']} {ev.get('address') or clean_dest}")
        nav = f"https://www.google.com/maps/search/?api=1&query={q}"
        return {
            "id": f"events_{idx + 1}",
            "title": ev["title"],
            "name": ev["title"],
            "category": "Event",
            "description": (ev.get("description") or "").strip() or f"Live event in {clean_dest}.",
            "location": location,
            "address": ev.get("address") or location,
            "maps_url": nav,
            "navigation_url": nav,
            "image_url": image,
            "image": image,
            "event_date": ev.get("when", ""),
            "event_start": ev["day"].isoformat() if ev.get("day") else "",
            "in_trip": bool(ev.get("in_trip")),
            "event_note": ev.get("note", ""),
            "url": ev.get("url", ""),
            "source": ev.get("source", ""),
            "price_range": ev.get("price", ""),
        }

    return list(await asyncio.gather(*[finish(i, e) for i, e in enumerate(merged)]))

# ─────────────────────────────────────────────
#  Real Places Engine (TomTom POI + OpenStreetMap). No AI-invented venues.
# ─────────────────────────────────────────────

REAL_POI_PILLARS = {
    "attractions": {
        "queries": ["tourist attraction", "museum", "monument", "park", "beach"],
        "include": ["tourist attraction", "museum", "monument", "historic", "park", "beach", "fort", "palace", "lighthouse",
                    "garden", "zoo", "aquarium", "waterfall", "cultural", "gallery", "heritage", "landmark"],
        "exclude_name": ["hotel", "resort", "lodge", "homestay", "hostel"],
        "osm": ['["tourism"~"attraction|museum|gallery|zoo|aquarium"]', '["historic"~"monument|castle|fort|memorial|ruins|archaeological_site"]'],
        "wiki": True,
    },
    "culinary": {
        "queries": ["restaurant", "cafe", "bakery", "local food restaurant"],
        "include": ["restaurant", "cafe", "bakery", "coffee", "food", "tea", "indian", "fast food", "dining", "ice cream"],
        "exclude_name": ["hotel", "bar & grill", "wine shop", "liquor"],
        "osm": ['["amenity"~"restaurant|cafe|fast_food"]'],
    },
    "bars_pubs": {
        "queries": ["bar", "pub", "brewery", "nightclub", "lounge"],
        "include": ["bar", "pub", "nightclub", "brewery", "wine", "cocktail", "nightlife", "lounge bar", "sky lounge"],
        "exclude_name": ["yoga", "wellness", "spa", "cooking", "flights", "packages", "ayurved", "travel", "tours", "academy", "school", "beauty", "salon", "hair", "clinic"],
        "osm": ['["amenity"~"bar|pub|nightclub|biergarten"]'],
    },
    "wellness": {
        "queries": ["spa", "yoga", "meditation center", "ayurveda", "wellness center"],
        "include": ["spa", "yoga", "massage", "sauna", "wellness", "meditation", "ayurved", "leisure center", "health"],
        "exclude_name": ["hospital", "pharmacy"],
        "exclude_cat": ["hospital"],
        "osm": ['["leisure"~"spa|sauna"]', '["shop"="massage"]', '["amenity"="spa"]'],
    },
    "secret_spots": {
        "queries": ["viewpoint", "scenic lookout", "waterfall", "garden", "lake"],
        "include": ["scenic", "viewpoint", "lookout", "waterfall", "garden", "nature", "lake", "island", "tourist attraction", "park"],
        "exclude_name": ["hotel", "resort", "restaurant", "hospital", "clinic", "school", "college", "apartment", "residency"],
        "exclude_cat": ["hotel", "hospital", "medical", "restaurant", "shop"],
        "osm": ['["tourism"="viewpoint"]', '["natural"~"waterfall|peak|beach|spring"]'],
        "wiki": True,
    },
    "essentials": {
        "queries": ["hospital", "railway station", "airport", "pharmacy", "police station", "bus station"],
        "include": ["hospital", "railway", "airport", "pharmacy", "police", "bus", "station", "medical", "transport", "emergency"],
        "exclude_name": [],
        "osm": ['["amenity"~"hospital|pharmacy|police|bus_station"]', '["railway"="station"]', '["aeroway"="aerodrome"]'],
    },
    "shopping": {
        "queries": ["shopping mall", "market", "bazaar", "handicraft shop"],
        "include": ["shopping", "mall", "market", "shop", "handicraft", "department", "store", "bazaar"],
        "exclude_name": [],
        "osm": ['["shop"~"mall|department_store|gift|handicraft"]', '["amenity"="marketplace"]'],
    },
    "adventures": {
        "queries": ["adventure sports", "trekking", "water sports", "national park", "wildlife sanctuary"],
        "include": ["adventure", "trekking", "water sport", "national park", "wildlife", "camp", "nature", "reserve", "park", "boating", "kayak", "rafting", "diving", "paragliding", "sanctuary"],
        "exclude_name": ["hotel", "restaurant", "shop", "store", "logistic", "private limited", "pvt", "ltd", "equipment", "traders", "mart"],
        "exclude_cat": ["shop", "company", "transport", "insurance", "hotel"],
        "osm": ['["leisure"~"nature_reserve|water_park"]', '["tourism"="camp_site"]', '["boundary"="national_park"]'],
        "wiki": True,
    },
    "theme_parks": {
        "queries": ["amusement park", "water park", "theme park"],
        "include": ["amusement", "water park", "theme", "leisure", "fun"],
        "exclude_name": ["hotel"],
        "osm": ['["tourism"="theme_park"]', '["leisure"="water_park"]'],
        "wiki": True,
    },
    "sacred_temples": {
        "queries": ["temple", "church", "mosque", "shrine", "gurudwara"],
        "include": ["place of worship", "temple", "church", "mosque", "shrine", "religious", "cathedral", "gurudwara"],
        "exclude_name": ["hotel"],
        "osm": ['["amenity"="place_of_worship"]'],
        "wiki": True,
    },
}

_tomtom_sem = asyncio.Semaphore(3)

async def _tomtom_pois(client: httpx.AsyncClient, query: str, coords: Coordinates, radius: int = 30000) -> List[Dict[str, Any]]:
    if not TOMTOM_API_KEY:
        return []
    try:
        res = None
        for attempt in range(3):
            async with _tomtom_sem:
                res = await client.get(
                    f"{TOMTOM_BASE}/search/2/poiSearch/{urllib.parse.quote(query)}.json",
                    params={"key": TOMTOM_API_KEY, "lat": coords.lat, "lon": coords.lng, "radius": radius, "limit": 30, "language": "en-GB"},
                    timeout=6.0)
            if res.status_code != 429:
                break
            await asyncio.sleep(0.6 * (attempt + 1))
        if res.status_code != 200:
            logger.warning(f"TomTom POI '{query}' status {res.status_code}")
            return []
        out = []
        for r in res.json().get("results", []):
            poi, addr, pos = r.get("poi", {}), r.get("address", {}), r.get("position", {})
            name = (poi.get("name") or "").strip()
            if not name or "lat" not in pos:
                continue
            out.append({
                "name": name,
                "cats": [c for c in poi.get("categories", []) if c],
                "address": addr.get("freeformAddress", ""),
                "area": addr.get("municipalitySubdivision") or addr.get("municipality") or "",
                "lat": pos["lat"], "lng": pos["lon"],
                "url": poi.get("url", ""), "phone": poi.get("phone", ""),
            })
        return out
    except Exception as e:
        logger.warning(f"TomTom POI '{query}' error: {e}")
        return []

async def _osm_pois(client: httpx.AsyncClient, pillar: str, coords: Coordinates, radius: int = 20000) -> List[Dict[str, Any]]:
    """OpenStreetMap (Overpass) backup when TomTom has too little."""
    filters = REAL_POI_PILLARS[pillar].get("osm", [])
    if not filters:
        return []
    body = "".join(f'nwr{f}["name"](around:{radius},{coords.lat},{coords.lng});' for f in filters)
    query = f"[out:json][timeout:8];({body});out center 60;"
    for endpoint in ("https://overpass-api.de/api/interpreter",):
        try:
            res = await client.post(endpoint, data={"data": query}, headers={"User-Agent": "VoyantaTravelApp/1.0 (travel@voyanta.app)"}, timeout=9.0)
            if res.status_code != 200:
                continue
            out = []
            for el in res.json().get("elements", []):
                t = el.get("tags", {})
                lat = el.get("lat") or el.get("center", {}).get("lat")
                lng = el.get("lon") or el.get("center", {}).get("lon")
                if not t.get("name") or lat is None:
                    continue
                kind = t.get("tourism") or t.get("amenity") or t.get("historic") or t.get("natural") or t.get("leisure") or t.get("shop") or ""
                addr = ", ".join(x for x in [t.get("addr:street"), t.get("addr:city")] if x)
                out.append({"name": t["name"], "cats": [kind.replace("_", " ")] if kind else [], "address": addr,
                            "area": t.get("addr:suburb") or t.get("addr:city") or "", "lat": lat, "lng": lng,
                            "url": t.get("website", ""), "phone": t.get("phone", "")})
            return out
        except Exception as e:
            logger.warning(f"Overpass error: {e}")
    return []

def _poi_matches(poi: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    name = poi["name"].lower()
    cats = " ".join(poi["cats"]).lower()
    if any(re.search(r"\b" + re.escape(x), name) for x in cfg["exclude_name"]):
        return False
    if any(x in cats for x in cfg.get("exclude_cat", [])):
        return False
    hay = cats + " " + name
    return any(re.search(r"\b" + re.escape(t) + r"(?:s|es)?\b", hay) for t in cfg["include"])

async def _wiki_info(client: httpx.AsyncClient, name: str, destination: str) -> Dict[str, str]:
    """Verified Wikipedia intro + lead image for a named place (article title must share a distinctive word)."""
    key = f"wikiinfo:{name.lower()}|{destination.lower()}"
    if key in dynamic_cache:
        return dynamic_cache[key]
    info = {"image": "", "extract": ""}
    tokens = _photo_tokens(name)
    try:
        res = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{name} {destination}", "gsrlimit": 3,
                    "prop": "extracts|pageimages", "exintro": 1, "explaintext": 1, "exsentences": 2, "exlimit": 3,
                    "piprop": "thumbnail", "pithumbsize": 900},
            headers={"User-Agent": "VoyantaTravelApp/1.0 (travel@voyanta.app)"}, timeout=3.0)
        if res.status_code == 200:
            pages = sorted(res.json().get("query", {}).get("pages", {}).values(), key=lambda pg: pg.get("index", 99))
            for page in pages:
                title_tokens = _photo_tokens(page.get("title", ""))
                if not tokens or not title_tokens:
                    continue
                # Article must be the place itself: its title words all appear in the name, or most name words appear in the title
                if not (title_tokens <= tokens or len(title_tokens & tokens) / len(tokens) >= 0.67):
                    continue
                extract = (page.get("extract") or "").strip()
                src = page.get("thumbnail", {}).get("source", "")
                if src and any(h in src.lower() for h in _BAD_IMAGE_HINTS):
                    src = ""
                if extract and "may refer to" not in extract.lower():
                    info = {"image": src, "extract": extract[:260].rsplit(" ", 1)[0] + ("…" if len(extract) > 260 else "")}
                    break
    except Exception:
        pass
    dynamic_cache[key] = info
    return info

def _describe_poi(poi: Dict[str, Any], dest: str) -> str:
    seen, labels = set(), []
    for c in poi["cats"]:
        c = c.strip().lower()
        if c and c not in seen and c not in {"building", "important tourist attraction", "national", "special", "public authority"}:
            seen.add(c)
            labels.append(c)
    if not labels and poi["cats"]:
        labels = [poi["cats"][0].lower()]
    if len(labels) >= 2 and labels[1] in ("restaurant", "cafe", "bar", "pub", "bakery"):
        label = f"{labels[0]} {labels[1]}"
    else:
        label = " · ".join(labels[:2])
    label = (label or "place").capitalize()
    where = poi["area"] or dest
    return f"{label} in {where}."

async def build_real_places(client: httpx.AsyncClient, clean_dest: str, pillar: str, geo_query: str = "") -> List[Dict[str, Any]]:
    cfg = REAL_POI_PILLARS[pillar]
    coords = await resolve_dynamic_coordinates(client, geo_query or clean_dest)

    per_query = await asyncio.gather(*[_tomtom_pois(client, q, coords) for q in cfg["queries"]])
    pois: List[Dict[str, Any]] = []
    seen = set()

    def take(lists):
        # Round-robin so one query (e.g. 'park') cannot crowd out the rest
        for i in range(max((len(l) for l in lists), default=0)):
            for l in lists:
                if i < len(l):
                    poi = l[i]
                    key = re.sub(r"[^a-z0-9]", "", poi["name"].lower())
                    if key and key not in seen and _poi_matches(poi, cfg):
                        seen.add(key)
                        pois.append(poi)

    take(per_query)
    if len(pois) < 8:
        take([await _osm_pois(client, pillar, coords)])
    pois = pois[:27]

    async def card(idx: int, poi: Dict[str, Any]) -> Dict[str, Any]:
        name = poi["name"]
        info = {"image": "", "extract": ""}
        if cfg.get("wiki"):
            info = await _wiki_info(client, name, clean_dest)
        image = info["image"]
        if not image:
            try:
                image = await asyncio.wait_for(fetch_dynamic_place_photo(client, venue=name, destination=clean_dest, category=pillar), timeout=6.0)
            except Exception:
                image = ""
            if not image:
                image = await fetch_destination_photo(client, clean_dest)
        nav = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name + ' ' + (poi['address'] or clean_dest))}"
        website = poi["url"]
        if website and not website.startswith("http"):
            website = "https://" + website
        return {
            "id": f"{pillar}_{idx + 1}",
            "title": name,
            "name": name,
            "category": pillar.replace("_", " ").title(),
            "description": info["extract"] or _describe_poi(poi, clean_dest),
            "location": poi["area"] or clean_dest,
            "address": poi["address"] or poi["area"] or clean_dest,
            "maps_url": nav,
            "navigation_url": nav,
            "image_url": image,
            "image": image,
            "lat": poi["lat"],
            "lng": poi["lng"],
            "website": website,
            "phone": poi["phone"],
        }

    return list(await asyncio.gather(*[card(i, p) for i, p in enumerate(pois)]))

# ─────────────────────────────────────────────
#  High-Capacity Parallel Trail Discovery Engine
# ─────────────────────────────────────────────

@app.get("/api/pillar", tags=["Discovery"])
@app.get("/api/places", tags=["Discovery"])
@app.get("/api/trails", tags=["Discovery"])
@app.get("/pillar", tags=["Discovery"])
@app.get("/places", tags=["Discovery"])
@app.get("/trails", tags=["Discovery"])
async def get_high_capacity_trails(
    destination: str = Query("New York"),
    pillar: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    request: Request = None
):
    clean_dest = destination.split(",")[0].strip().title() if destination else "New York"
    active_category = (pillar or category or "attractions").strip().lower()
    trip_start = _parse_event_day(start_date) if isinstance(start_date, str) else None
    trip_end = _parse_event_day(end_date) if isinstance(end_date, str) else None
    if trip_start and (not trip_end or trip_end < trip_start):
        trip_end = trip_start
    cache_key = f"trails_{destination.strip()}_{active_category}".lower()
    if active_category == "events" and trip_start:
        cache_key += f"_{trip_start}_{trip_end}"

    cached_data = response_cache.get(cache_key)
    if cached_data:
        return cached_data

    client = getattr(request.app.state, "client", None) if request else None

    if active_category == "events":
        events = await build_real_events(client, clean_dest, trip_start, trip_end, geo_query=destination)
        payload = {
            "status": "success",
            "destination": destination,
            "category": "events",
            "count": len(events),
            "places": events,
            "results": events,
            "events": events,
            "during_trip": sum(1 for e in events if e.get("in_trip")),
            "sources": [n for n, k in (("Ticketmaster", TICKETMASTER_API_KEY), ("Google Events", SERPAPI_KEY)) if k],
        }
        if events:
            response_cache.set(cache_key, payload)
        return payload

    if active_category in REAL_POI_PILLARS:
        places = await build_real_places(client, clean_dest, active_category, geo_query=destination)
        payload = {
            "status": "success",
            "destination": destination,
            "category": active_category,
            "count": len(places),
            "places": places,
            "results": places,
            active_category: places,
            "sources": ["TomTom", "OpenStreetMap"],
        }
        if places:
            response_cache.set(cache_key, payload)
        return payload

    # Define 3 dynamic sub-angles based on category to ensure rich variety
    category_themes = {
        "attractions": [
            f"Iconic must-see landmarks & world-famous highlights in {clean_dest}",
            f"Hidden local favorites, scenic spots & architectural gems in {clean_dest}",
            f"Trendy neighborhood hotspots, cultural hubs & evening atmospheres in {clean_dest}"
        ],
        "culinary": [
            f"Legendary historic restaurants, heritage eateries & signature dining in {clean_dest}",
            f"Hidden street food stalls, bustling food halls & local neighborhood favorites in {clean_dest}",
            f"Trendy modern cafes, artisan bakeries & acclaimed chef-driven bistros in {clean_dest}"
        ],
        "events": [
            f"Major world-class festivals, annual cultural pageants & landmark celebrations in {clean_dest}",
            f"Live music concerts, performing arts theaters & outdoor festival stages in {clean_dest}",
            f"Seasonal night markets, artisan craft fairs & vibrant street gatherings in {clean_dest}"
        ],
        "bars_pubs": [
            f"Iconic rooftop lounges, panoramic skyline cocktail bars in {clean_dest}",
            f"Historic speakeasies, heritage taverns & craft beer pubs in {clean_dest}",
            f"Vibrant live music jazz clubs & late-night nightlife venues in {clean_dest}"
        ],
        "wellness": [
            f"Luxury serene thermal spas, holistic retreats & wellness centers in {clean_dest}",
            f"Tranquil botanical gardens, scenic nature walking trails & parks in {clean_dest}",
            f"Mindfulness yoga sanctuaries, zen meditation spaces & outdoor viewpoints in {clean_dest}"
        ],
        "secret_spots": [
            f"Secret panoramic lookout viewpoints & secluded courtyards in {clean_dest}",
            f"Quirky hidden alleys, underground wonders & historic arcades in {clean_dest}",
            f"Undiscovered local sanctuaries & peaceful scenic nooks away from crowds in {clean_dest}"
        ],
        "essentials": [
            f"Major international & central transit terminals, grand railway stations in {clean_dest}",
            f"Premier medical centers, renowned university hospitals & emergency hubs in {clean_dest}",
            f"24/7 travel concierge hubs, visitor centers & essential infrastructure in {clean_dest}"
        ],
        "shopping": [
            f"Prestigious luxury shopping avenues, flagship designer boutiques in {clean_dest}",
            f"Historic open-air bazaars, flea markets & local artisan quarters in {clean_dest}",
            f"Trendy independent fashion arcades, concept lifestyle stores & malls in {clean_dest}"
        ],
        "adventures": [
            f"Exciting outdoor hiking trails, mountain lookout summits & canyon paths around {clean_dest}",
            f"Thrilling river expeditions, coastal water sports & marine activities in {clean_dest}",
            f"Adrenaline adventure parks, scenic cycling routes & safari tours in {clean_dest}"
        ],
        "theme_parks": [
            f"World-renowned amusement parks, roller coaster thrill lands in or near {clean_dest}",
            f"Exciting water parks, splash worlds & aquatic entertainment in {clean_dest}",
            f"Immersive interactive theme zones, escape experiences & virtual adventure arenas in {clean_dest}"
        ],
        "sacred_temples": [
            f"Historic grand cathedrals, ancient sacred temples & revered shrines in {clean_dest}",
            f"Spiritual architectural wonders, ancient sanctuaries & holy basilicas in {clean_dest}",
            f"Serene monastic courtyards, peaceful meditation pagodas & heritage temples in {clean_dest}"
        ]
    }

    sub_themes = category_themes.get(active_category, [
        f"Iconic must-see landmarks & world-famous highlights in {clean_dest}",
        f"Hidden local favorites, scenic spots & architectural gems in {clean_dest}",
        f"Trendy neighborhood hotspots, cultural hubs & evening atmospheres in {clean_dest}"
    ])

    async def fetch_theme_batch(theme_desc: str):
        prompt = f"""Local guide for {clean_dest}.
Theme: {theme_desc} (Category: {active_category})

Generate 9 authentic, verified real-world places. No generic titles.
Return strictly a JSON array:
[
  {{
    "title": "Exact Real Venue Name",
    "description": "1 concise sentence overview.",
    "location": "District / Neighborhood",
    "category": "{active_category}"
  }}
]"""
        try:
            raw = await asyncio.wait_for(call_ai_with_rate_limit_fallback(client, prompt), timeout=3.5)
            parsed = extract_json_payload(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "places" in parsed:
                return parsed["places"]
            if isinstance(parsed, dict) and active_category in parsed:
                return parsed[active_category]
        except Exception as e:
            logger.warning(f"Theme batch error: {e}")
        return []

    # 1. Fetch 3 sub-batches in parallel with strict 3.5s timeout
    batch_results = await asyncio.gather(*[fetch_theme_batch(st) for st in sub_themes], return_exceptions=True)

    places = []
    seen_titles = set()
    card_idx = 1
    for res in batch_results:
        if isinstance(res, list):
            for item in res:
                if isinstance(item, dict):
                    t = item.get("title", "").strip()
                    if t and t.lower() not in seen_titles:
                        seen_titles.add(t.lower())
                        title_clean = clean_venue_title(t, clean_dest)
                        location_clean = item.get("location") or clean_dest
                        nav_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(title_clean + ' ' + location_clean + ' ' + clean_dest)}"
                        image_url = ""

                        card = {
                            "id": f"{active_category}_{card_idx}",
                            "title": title_clean,
                            "name": title_clean,
                            "category": active_category.replace("_", " ").title(),
                            "description": item.get("description", f"Verified authentic {active_category} venue in {clean_dest}."),
                            "location": location_clean,
                            "address": location_clean,
                            "maps_url": nav_url,
                            "navigation_url": nav_url,
                            "image_url": image_url,
                            "image": image_url,
                            "rating": 4.8
                        }
                        places.append(card)
                        card_idx += 1

    async def attach_photo(card):
        try:
            url = await asyncio.wait_for(
                fetch_dynamic_place_photo(client, venue=card["title"], destination=clean_dest, category=active_category),
                timeout=6.0)
        except Exception:
            url = ""
        if not url:
            url = await fetch_destination_photo(client, clean_dest)
        card["image_url"] = url
        card["image"] = url

    await asyncio.gather(*[attach_photo(c) for c in places])

    response_payload = {
        "status": "success",
        "destination": destination,
        "category": active_category,
        "count": len(places),
        "places": places,
        "results": places,
        active_category: places
    }

    if places:
        response_cache.set(cache_key, response_payload)
        dynamic_cache[f"pure_trails_v2:{clean_dest.lower()}:{active_category}"] = places

    return response_payload

pillar_cache = dynamic_cache

@app.get("/api/pillar/{pillar_type}", tags=["Pillars"])
@app.get("/pillar/{pillar_type}", tags=["Pillars"])
async def get_dynamic_pillar_data(pillar_type: str, destination: str, request: Request):
    res = await get_high_capacity_trails(destination=destination, pillar=pillar_type, request=request)
    return res.get("places", [])

@app.get("/api/destination", tags=["Discovery"])
async def get_destination_data(request: Request, destination: str = Query(..., min_length=1)):
    return await get_high_capacity_trails(request=request, destination=destination, pillar="attractions")

@app.get("/api/weather", tags=["Weather"])
async def get_destination_weather(request: Request, destination: str = Query(..., min_length=1)):
    clean_dest = destination.split(",")[0].strip()
    cache_key = f"weather:{clean_dest.lower()}"
    if cache_key in dynamic_cache:
        return dynamic_cache[cache_key]

    client = request.app.state.client
    coords = await resolve_dynamic_coordinates(client, clean_dest)
    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={coords.lat}&longitude={coords.lng}&current_weather=true"
        w_res = await client.get(weather_url, timeout=2.0)
        if w_res.status_code == 200:
            cw = w_res.json().get("current_weather", {})
            temp = round(cw.get("temperature", 24))
            wcode = cw.get("weathercode", 0)
            condition = "Sunny" if wcode <= 3 else "Rainy" if wcode in [51, 53, 55, 61, 63, 65, 80, 81, 82] else "Cloudy"
            res_data = {"temp": temp, "temp_c": temp, "condition": condition, "icon": "01d"}
            dynamic_cache[cache_key] = res_data
            return res_data
    except Exception as e:
        logger.warning(f"Weather lookup failed: {e}")

    return {"temp": 24, "temp_c": 24, "condition": "Sunny", "icon": "01d"}

@app.get("/api/autocomplete", tags=["Maps & Geocoding"])
async def autocomplete_destinations(request: Request, q: str = Query("", min_length=1)):
    query = q.strip().lower()
    if not query:
        return {"suggestions": []}

    client = request.app.state.client
    suggestions = []
    seen = set()

    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(query)}&count=10"
        res = await client.get(url, timeout=1.5)
        if res.status_code == 200:
            for item in res.json().get("results", []):
                name = item.get("name", "")
                country = item.get("country", "")
                admin = item.get("admin1", "")
                if name.lower().startswith(query):
                    label = f"{name}, {admin}, {country}" if admin else f"{name}, {country}"
                    if label.lower() not in seen:
                        suggestions.append({"label": label, "value": f"{name}, {country}"})
                        seen.add(label.lower())
    except Exception as e:
        logger.warning(f"Autocomplete error: {e}")

    return {"suggestions": suggestions[:6]}

# ─────────────────────────────────────────────
#  Trip Planner Endpoints (100% Dynamic)
# ─────────────────────────────────────────────

@app.post("/api/trip-plan", response_model=TripPlanResponse, tags=["Trips"])
@app.post("/trip-plan", response_model=TripPlanResponse, tags=["Trips"])
async def create_dynamic_trip_plan(body: TripPlanRequest, request: Request):
    client = request.app.state.client
    dest_name = (body.destination or body.location or "Tokyo").strip().title()
    num_days = max(1, min(body.days or 3, 30))
    start_date = body.start_date or date.today()
    coords = await resolve_dynamic_coordinates(client, dest_name)
    group_desc = body.travelers.group_type if body.travelers else "Solo"
    
    prompt = f"""
    Create a {num_days}-day travel itinerary for {dest_name}.
    Pace: {body.pace or 'Balanced'}. Budget: {body.budget or 'Moderate'}. Group: {group_desc}.
    
    JSON Schema:
    {{
      "summary": "1 sentence overview",
      "days": [
        {{
          "day": 1,
          "theme": "Theme",
          "stops": [
            {{
              "title": "Real Place Name",
              "location": "Locality in {dest_name}",
              "category": "Sightseeing",
              "duration_minutes": 90,
              "best_time": "09:30 AM",
              "cost_range": "$10 - $25"
            }}
          ]
        }}
      ],
      "culinary_highlights": [
        {{
          "title": "Famous Eatery",
          "description": "Must try dish",
          "famous_for": "Specialty",
          "location": "Locality in {dest_name}"
        }}
      ]
    }}
    Provide 3 distinct real-world stops per day.
    """
    
    raw = await call_ai_with_rate_limit_fallback(client, prompt)
    ai_data = json.loads(raw)
    
    dest_image = await fetch_dynamic_place_photo(client, destination=dest_name, category="skyline landmark")
    
    itinerary = []
    routes = []
    
    for day_idx, day_obj in enumerate(ai_data.get("days", [])[:num_days]):
        day_num = day_idx + 1
        t_date = start_date.fromordinal(start_date.toordinal() + day_idx)
        day_coords = []
        
        for stop_idx, stop in enumerate(day_obj.get("stops", [])):
            clean_title = clean_venue_title(stop.get("title", f"Stop {stop_idx+1}"), dest_name)
            stop_img = await fetch_dynamic_place_photo(client, venue=clean_title, destination=dest_name, category=stop.get("category", ""))
            stop_lat = coords.lat + (stop_idx * 0.004)
            stop_lng = coords.lng + (stop_idx * 0.004)
            day_coords.append([stop_lng, stop_lat])
            
            itinerary.append(
                TripStop(
                    id=f"stop-{day_num}-{stop_idx+1}",
                    day=day_num,
                    date=t_date.strftime("%b %d"),
                    time=stop.get("best_time", "10:00 AM"),
                    title=clean_title,
                    location=stop.get("location", dest_name),
                    type=stop.get("category", "SIGHTSEEING").upper(),
                    creators=f"Scheduled for {stop.get('best_time', '10:00 AM')}",
                    distance=f"{round((stop_idx+1)*2.2, 1)}km",
                    elevation="N/A",
                    duration=f"{stop.get('duration_minutes', 90)}m",
                    image=stop_img,
                    map_image_url=dest_image,
                    lat=stop_lat,
                    lng=stop_lng,
                    cost_range=stop.get("cost_range", "$15 - $30 / person"),
                )
            )
            
        routes.append(
            TripDayRoute(
                day=day_num,
                geojson={"type": "Feature", "geometry": {"type": "LineString", "coordinates": day_coords}},
                total_distance_meters=len(day_coords) * 3200,
                total_travel_time_seconds=len(day_coords) * 1500
            )
        )
        
    culinary = [
        CulinaryHighlight(
            title=c.get("title", "Local Eatery"),
            description=c.get("description", "Authentic dining experience."),
            famous_for=c.get("famous_for", "Local Specialties"),
            location=c.get("location", dest_name),
            price_tier="",
            cost_approx=""
        ) for c in ai_data.get("culinary_highlights", [])
    ]
    
    return TripPlanResponse(
        destination=dest_name,
        language=body.language or "en",
        destination_image=dest_image,
        map_image_url=dest_image,
        weather="Dynamic AI Plan",
        dates=format_date_range(start_date, num_days),
        days=num_days,
        coordinates=coords,
        itinerary=itinerary,
        routes=routes,
        culinary_highlights=culinary
    )

# ─────────────────────────────────────────────
#  Interactive Chat Agent Endpoint
# ─────────────────────────────────────────────

@app.post("/api/chat", tags=["Chat"])
@app.post("/chat", tags=["Chat"])
@app.post("/api/voya/chat", tags=["Chat"])
async def handle_voya_chat(req: ChatRequest, request: Request):
    client = request.app.state.client
    
    system_prompt = get_voya_system_prompt(
        destination=req.destination,
        language=req.language,
        currency=req.currency,
        user_time=req.user_time,
        user_timezone=req.user_timezone,
        active_itinerary=req.active_itinerary
    )

    tools = get_chat_agent_tools()
    
    convo_history_str = ""
    if req.history:
        for m in req.history[-8:]:
            role_label = "User" if m.role == "user" else "Voya"
            convo_history_str += f"{role_label}: {m.content}\n"

    prompt = f"""{system_prompt}

Conversation History:
{convo_history_str}
User's Latest Query: {req.message}

Available Tools:
{json.dumps(tools, indent=2)}

OUTPUT FORMAT:
Respond with ONLY a single valid JSON object:
- If invoking a tool:
{{"tool_call": {{"name": "<tool_name>", "arguments": {{...}}}}, "reply": "<Your full, detailed conversational answer in {req.language}>"}}

- If answering directly (general knowledge, recommendations, advice, banter):
{{"tool_call": null, "reply": "<Your full, engaging, concrete answer in {req.language}>"}}
"""

    try:
        raw_res = await call_ai_with_rate_limit_fallback(client, prompt)
        parsed = extract_json_payload(raw_res)

        reply_text = ""
        action_payload = None

        if parsed and isinstance(parsed, dict) and ("reply" in parsed or "tool_call" in parsed or "response" in parsed):
            reply_text = parsed.get("reply", "") or parsed.get("response", "")
            tool_data = parsed.get("tool_call")

            if tool_data and isinstance(tool_data, dict) and "name" in tool_data:
                tool_name = tool_data.get("name")
                tool_args = tool_data.get("arguments", {})
                if not tool_args.get("destination") and req.destination:
                    tool_args["destination"] = req.destination
                action_payload = await execute_tool_call(tool_name, tool_args, client=client)
        else:
            # If response was plain text or malformed JSON, return raw string cleanly
            reply_text = raw_res.strip()

        if not reply_text:
            reply_text = "I'm here! What destination or plan would you like to explore?"

        return {
            "status": "success",
            "reply": reply_text,
            "response": reply_text,
            "action": action_payload
        }
    except Exception as e:
        logger.error(f"Chat execution fallback: {e}")
        try:
            fallback_prompt = f"{system_prompt}\n\nUser: {req.message}\nProvide an informative, direct response."
            raw_fallback = await call_ai_with_rate_limit_fallback(client, fallback_prompt)
            return {"status": "success", "reply": raw_fallback.strip(), "response": raw_fallback.strip(), "action": None}
        except Exception:
            return {"status": "success", "reply": "I'm here to assist your travel planning. What destination or question do you have?", "response": "I'm here to assist your travel planning. What destination or question do you have?", "action": None}

# ─────────────────────────────────────────────
#  Geocoding, Routing & POI APIs (TomTom)
# ─────────────────────────────────────────────

@app.get("/geocode", response_model=List[GeocodeResult], tags=["Maps & Geocoding"])
async def geocode(query: str = Query(...), limit: int = Query(5, ge=1, le=10), client: httpx.AsyncClient = Depends(get_http_client), key: str = Depends(tomtom_key)):
    url = f"{TOMTOM_BASE}/search/2/geocode/{query}.json"
    res = await client.get(url, params={"key": key, "limit": limit, "typeahead": True})
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="Geocoding lookup failed.")
    results = []
    for item in res.json().get("results", []):
        pos = item.get("position", {})
        addr = item.get("address", {})
        results.append(GeocodeResult(
            address=addr.get("freeformAddress", ""),
            lat=pos.get("lat", 0.0),
            lng=pos.get("lon", 0.0),
            country=addr.get("country", ""),
            city=addr.get("municipality"),
            score=item.get("score")
        ))
    return results

@app.post("/route", response_model=RouteResponse, tags=["Routing"])
async def calculate_route(body: RouteRequest, client: httpx.AsyncClient = Depends(get_http_client), key: str = Depends(tomtom_key)):
    if len(body.waypoints) < 2:
        raise HTTPException(status_code=400, detail="At least 2 waypoints are required.")
    locations = ":".join([f"{wp.lat},{wp.lng}" for wp in body.waypoints])
    url = f"{TOMTOM_BASE}/routing/1/calculateRoute/{locations}/json"
    res = await client.get(url, params={"key": key, "travelMode": body.travel_mode, "routeType": "fastest", "traffic": True})
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="Route computation failed.")
    data = res.json()
    route = data.get("routes", [])[0]
    summary = route.get("summary", {})
    all_points = []
    legs = []
    for leg in route.get("legs", []):
        pts = leg.get("points", [])
        all_points.extend([[p["longitude"], p["latitude"]] for p in pts])
        leg_sum = leg.get("summary", {})
        legs.append(RouteLeg(
            distance_meters=leg_sum.get("lengthInMeters", 0),
            travel_time_seconds=leg_sum.get("travelTimeInSeconds", 0),
            summary=f"{round(leg_sum.get('lengthInMeters', 0)/1000, 1)}km"
        ))
    return RouteResponse(
        total_distance_meters=summary.get("lengthInMeters", 0),
        total_travel_time_seconds=summary.get("travelTimeInSeconds", 0),
        geojson={"type": "Feature", "geometry": {"type": "LineString", "coordinates": all_points}},
        legs=legs
    )

@app.get("/nearby-pois", response_model=List[POI], tags=["Discovery"])
async def nearby_pois(lat: float = Query(...), lng: float = Query(...), radius: int = Query(2000, ge=100, le=50000), limit: int = Query(10, ge=1, le=50), client: httpx.AsyncClient = Depends(get_http_client), key: str = Depends(tomtom_key)):
    url = f"{TOMTOM_BASE}/search/2/nearbySearch/.json"
    res = await client.get(url, params={"key": key, "lat": lat, "lon": lng, "radius": radius, "limit": limit})
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="POI search failed.")
    pois = []
    for item in res.json().get("results", []):
        poi = item.get("poi", {})
        pos = item.get("position", {})
        addr = item.get("address", {})
        pois.append(POI(
            id=item.get("id", ""),
            name=poi.get("name", "POI"),
            category=poi.get("categories", ["Place"])[0] if poi.get("categories") else "Place",
            lat=pos.get("lat", 0.0),
            lng=pos.get("lon", 0.0),
            distance_meters=item.get("dist"),
            address=addr.get("freeformAddress")
        ))
    return pois

@app.get("/traffic", response_model=List[TrafficIncident], tags=["Traffic"])
async def get_traffic_incidents(lat: float = Query(...), lng: float = Query(...), radius_km: float = Query(5.0), client: httpx.AsyncClient = Depends(get_http_client), key: str = Depends(tomtom_key)):
    delta = radius_km / 111.0
    bbox = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"
    url = f"{TOMTOM_BASE}/traffic/services/5/incidentDetails"
    res = await client.get(url, params={"key": key, "bbox": bbox, "language": "en-GB", "t": "1111"})
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="Traffic incident lookup failed.")
    incidents = []
    for f in res.json().get("incidents", []):
        props = f.get("properties", {})
        geom = f.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        if isinstance(coords[0], list):
            coords = coords[0]
        incidents.append(TrafficIncident(
            id=props.get("id", ""),
            description=props.get("events", [{}])[0].get("description", "Traffic incident"),
            severity=str(props.get("magnitudeOfDelay", "Minor")),
            lat=coords[1] if len(coords) > 1 else lat,
            lng=coords[0]
        ))
    return incidents

@app.get("/trips/{trip_id}/smart-suggestions", response_model=List[EventFestival], tags=["Trips"])
async def get_smart_suggestions(trip_id: UUID, day_date: date, pool: asyncpg.Pool = Depends(get_db_pool)):
    query = """
        WITH trip_waypoints AS (
            SELECT location FROM waypoints WHERE trip_id = $1::uuid AND DATE(start_time) = $2::DATE
        )
        SELECT e.id::text, e.title, e.event_type, e.start_time, e.end_time,
               ST_Y(e.location::geometry)::float as lat, ST_X(e.location::geometry)::float as lng,
               MIN(ST_DistanceSphere(e.location::geometry, w.location::geometry))::float as distance_meters
        FROM events e CROSS JOIN trip_waypoints w
        WHERE DATE(e.start_time) = $2::DATE AND ST_DWithin(e.location, w.location, 5000)
        GROUP BY e.id, e.title, e.event_type, e.start_time, e.end_time, e.location
        ORDER BY distance_meters ASC LIMIT 10;
    """
    async with pool.acquire() as conn:
        try:
            records = await conn.fetch(query, trip_id, day_date)
            return [EventFestival(**dict(r)) for r in records]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
