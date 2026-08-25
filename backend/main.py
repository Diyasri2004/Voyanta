import os
import json
import logging
import httpx
import re
import urllib.parse
import asyncio
from datetime import date
from uuid import UUID
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncpg
from cachetools import TTLCache

from models import EventFestival
from chat_agent import get_voya_system_prompt, get_chat_agent_tools, execute_tool_call

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voyanta")

# 24-hour dynamic in-memory cache
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

    clean = destination.split(",")[0].strip()
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean)}&count=1"
        res = await client.get(geo_url, timeout=2.0)
        if res.status_code == 200 and res.json().get("results"):
            item = res.json()["results"][0]
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

async def fetch_dynamic_place_photo(client: httpx.AsyncClient, venue: str = "", destination: str = "", category: str = "") -> str:
    # 1. Clean dynamic inputs at runtime
    v_clean = re.sub(r'[\(\)\[\],|]', ' ', venue or "").strip()
    d_clean = destination.split(",")[0].strip() if destination else ""
    c_clean = re.sub(r'[\(\)\[\],|]', ' ', category or "").strip().lower()

    # 2. Derive dynamic contextual keyword based on category
    context_suffix = ""
    if any(k in c_clean for k in ["culinary", "food", "restaurant", "cafe", "dining", "bakery", "dhaba"]):
        context_suffix = "food dish"
    elif any(k in c_clean for k in ["wellness", "spa", "meditation", "massage", "yoga", "retreat"]):
        context_suffix = "spa wellness resort"
    elif any(k in c_clean for k in ["bar", "pub", "nightlife", "cocktail", "lounge"]):
        context_suffix = "cocktail bar lounge"
    elif any(k in c_clean for k in ["theme", "park", "water", "amusement"]):
        context_suffix = "theme park rides"
    elif any(k in c_clean for k in ["temple", "shrine", "church", "mosque", "monastery"]):
        context_suffix = "temple shrine architecture"
    elif any(k in c_clean for k in ["adventure", "trekking", "hiking", "safari"]):
        context_suffix = "outdoor adventure nature"
    elif any(k in c_clean for k in ["shopping", "market", "bazaar", "mall"]):
        context_suffix = "shopping street market"
    elif any(k in c_clean for k in ["secret", "hidden", "viewpoint"]):
        context_suffix = "scenic view landscape"
    elif any(k in c_clean for k in ["event", "festival", "concert"]):
        context_suffix = "festival celebration event"
    else:
        context_suffix = "travel landmark scenery"

    # 3. Build cascading dynamic search queries
    search_queries = []
    if v_clean and d_clean:
        search_queries.append(f"{v_clean} {context_suffix}".strip())
        search_queries.append(f"{v_clean} {d_clean}".strip())
        search_queries.append(f"{d_clean} {context_suffix}".strip())
    elif v_clean:
        search_queries.append(f"{v_clean} {context_suffix}".strip())
        search_queries.append(v_clean)
    elif d_clean:
        search_queries.append(f"{d_clean} {context_suffix}".strip())

    # 4. Search Pexels API
    if PEXELS_API_KEY:
        for q in search_queries:
            encoded = urllib.parse.quote(q)
            try:
                p_url = f"https://api.pexels.com/v1/search?query={encoded}&orientation=landscape&per_page=1"
                res = await client.get(p_url, headers={"Authorization": PEXELS_API_KEY}, timeout=2.5)
                if res.status_code == 200:
                    photos = res.json().get("photos", [])
                    if photos and len(photos) > 0:
                        return photos[0]["src"]["large2x"]
            except Exception:
                pass

    # 5. Search Unsplash API
    if UNSPLASH_ACCESS_KEY:
        for q in search_queries:
            encoded = urllib.parse.quote(q)
            try:
                u_url = f"https://api.unsplash.com/search/photos?query={encoded}&orientation=landscape&per_page=1&client_id={UNSPLASH_ACCESS_KEY}"
                res = await client.get(u_url, timeout=2.5)
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    if results and len(results) > 0:
                        return results[0]["urls"]["regular"]
            except Exception:
                pass

    # 6. Search Wikipedia Thumbnail API (Filter SVG/PNG maps and icons)
    wiki_headers = {"User-Agent": "VoyantaTravelApp/1.0 (travel@voyanta.app)"}
    if v_clean:
        try:
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&pithumbsize=1000&generator=search&gsrsearch={urllib.parse.quote(v_clean)}&gsrlimit=1"
            res = await client.get(wiki_url, headers=wiki_headers, timeout=2.0)
            if res.status_code == 200:
                pages = res.json().get("query", {}).get("pages", {})
                for _, page in pages.items():
                    src = page.get("thumbnail", {}).get("source", "")
                    if src and not any(ext in src.lower() for ext in [".svg", "flag", "locator_map", "_map", "location_in"]):
                        return src
        except Exception:
            pass

    return ""

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
    # ── TIER 1: GROQ ────────────────────────────────────────────────────────
    if GROQ_API_KEY:
        groq_models = [GROQ_MODEL, "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]
        seen_g = set()
        groq_models = [m for m in groq_models if not (m in seen_g or seen_g.add(m))]
        for g_model in groq_models:
            try:
                g_payload = {
                    "model": g_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Voyanta's AI concierge. Return clean output without conversational fluff or invalid markdown syntax unless requested."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                res = await client.post("https://api.groq.com/openai/v1/chat/completions", json=g_payload, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    raw = res.json()["choices"][0]["message"]["content"]
                    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                    logger.info(f"⚡ Instant AI generation succeeded via Groq ({g_model})")
                    return cleaned
                else:
                    logger.warning(f"Groq {g_model} status {res.status_code}: {res.text[:120]}")
            except Exception as e:
                logger.warning(f"Groq {g_model} connection error: {e}")

    # ── TIER 2: DIRECT OPENROUTER ───────────────────────────────────────────
    if OPENROUTER_API_KEY:
        or_models = [
            "openrouter/auto",
            "meta-llama/llama-3.3-70b-instruct:free",
            "deepseek/deepseek-r1:free"
        ]
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://voyanta-xi.vercel.app",
            "X-Title": "Voyanta AI",
            "Content-Type": "application/json"
        }
        for model in or_models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Voyanta's travel intelligence engine. Return strictly a valid JSON object matching the requested schema."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                res = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=12.0)
                if res.status_code == 200:
                    raw = res.json()["choices"][0]["message"]["content"]
                    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                    logger.info(f"⚡ Instant AI generation succeeded via OpenRouter ({model})")
                    return cleaned
                else:
                    logger.warning(f"OpenRouter {model} status {res.status_code}: {res.text[:120]}")
            except Exception as e:
                logger.warning(f"OpenRouter {model} connection error: {e}")

    # ── TIER 3: GEMINI FALLBACK ──────────────────────────────────────────────
    if GEMINI_API_KEY:
        try:
            g_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
            g_payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
            res = await client.post(g_url, json=g_payload, timeout=10.0)
            if res.status_code == 200:
                raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                logger.info("⚡ Fallback AI generation succeeded via Gemini")
                return cleaned
        except Exception as e:
            logger.warning(f"Gemini fallback connection error: {e}")

    raise HTTPException(status_code=503, detail="AI generation engine unavailable. Please verify API status.")

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

def get_default_attractions_for_destination(destination: str, category: str = "attractions") -> List[Dict[str, Any]]:
    dest = destination.strip().title()
    cat_title = category.replace("_", " ").title()
    return [
        {
            "id": f"{category}_1",
            "title": f"Iconic {dest} City Center",
            "name": f"Iconic {dest} City Center",
            "category": cat_title,
            "description": f"Must-visit central landmark and vibrant cultural hub in {dest}.",
            "location": f"Central {dest}",
            "address": f"Central {dest}",
            "rating": 4.8,
            "image_url": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80",
            "image": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80",
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(dest + ' city center')}",
            "navigation_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(dest + ' city center')}"
        },
        {
            "id": f"{category}_2",
            "title": f"{dest} Historic Cultural District",
            "name": f"{dest} Historic Cultural District",
            "category": cat_title,
            "description": f"Historic quarter featuring traditional architecture, local markets, and heritage sites in {dest}.",
            "location": f"Old Quarter, {dest}",
            "address": f"Old Quarter, {dest}",
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
            "image": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(dest + ' historic district')}",
            "navigation_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(dest + ' historic district')}"
        },
        {
            "id": f"{category}_3",
            "title": f"{dest} Grand Promenade & Park",
            "name": f"{dest} Grand Promenade & Park",
            "category": cat_title,
            "description": f"Scenic open green space and pedestrian walkway offering stunning panoramic views of {dest}.",
            "location": f"Waterfront, {dest}",
            "address": f"Waterfront, {dest}",
            "rating": 4.9,
            "image_url": "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?auto=format&fit=crop&w=800&q=80",
            "image": "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?auto=format&fit=crop&w=800&q=80",
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(dest + ' promenade')}",
            "navigation_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(dest + ' promenade')}"
        }
    ]

@app.get("/api/places", tags=["Discovery"])
@app.get("/places", tags=["Discovery"])
async def get_places_for_destination(request: Request, destination: str = Query("Tokyo"), category: str = Query("attractions")):
    client = request.app.state.client
    dest_clean = destination.strip().title()
    cat_clean = category.strip().lower()
    cache_key = f"places:{dest_clean.lower()}:{cat_clean}"

    if cache_key in dynamic_cache:
        return {"status": "success", "places": dynamic_cache[cache_key], "results": dynamic_cache[cache_key]}

    desc = PILLAR_DESCRIPTIONS.get(cat_clean, "attractions and spots")
    prompt = f'Return JSON: {{"places": [{{"name": "Place Name", "location": "Neighborhood", "description": "Engaging 1-sentence description"}}]}} for 8 top real {desc} in {dest_clean}.'
    
    try:
        raw = await asyncio.wait_for(call_ai_with_rate_limit_fallback(client, prompt), timeout=6.0)
        data = json.loads(raw)
        raw_places = data.get("places", [])
    except Exception as e:
        logger.warning(f"AI places fetching error/timeout: {e}; returning fallback places")
        fallback_places = get_default_attractions_for_destination(dest_clean, cat_clean)
        return {"status": "success", "places": fallback_places, "results": fallback_places}

    async def build_place_card(idx: int, item: dict) -> dict:
        p_name = clean_venue_title(item.get("name", f"Spot {idx+1}"), dest_clean)
        p_loc = item.get("location", dest_clean)
        query_str = f"{p_name}, {p_loc}, {dest_clean}".strip()
        nav_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query_str)}"
        try:
            img_url = await asyncio.wait_for(
                fetch_dynamic_place_photo(client, venue=p_name, destination=dest_clean, category=cat_clean),
                timeout=3.0
            )
        except Exception:
            img_url = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80"
        return {
            "id": f"place_{cat_clean}_{idx+1}",
            "title": p_name,
            "name": p_name,
            "category": cat_clean.replace("_", " ").title(),
            "description": item.get("description", f"Famous point of interest in {dest_clean}."),
            "address": p_loc,
            "location": p_loc,
            "maps_url": nav_url,
            "navigation_url": nav_url,
            "image_url": img_url,
            "image": img_url,
            "rating": 4.8
        }

    tasks = [build_place_card(idx, item) for idx, item in enumerate(raw_places[:10]) if item.get("name")]
    if not tasks:
        fallback_places = get_default_attractions_for_destination(dest_clean, cat_clean)
        return {"status": "success", "places": fallback_places, "results": fallback_places}

    resolved = await asyncio.gather(*tasks)
    dynamic_cache[cache_key] = resolved
    return {"status": "success", "places": resolved, "results": resolved}

@app.get("/api/pillar", tags=["Discovery"])
async def get_single_pillar_data(request: Request, destination: str = Query(..., min_length=1), pillar: str = Query("attractions")):
    clean_dest = destination.split(",")[0].strip().title()
    pillar_clean = pillar.strip().lower()
    cache_key = f"{clean_dest}:{pillar_clean}"

    if cache_key in dynamic_cache:
        return {pillar_clean: dynamic_cache[cache_key]}

    client = request.app.state.client

    if pillar_clean in ["theme_parks", "themeparks"]:
        coords = await resolve_dynamic_coordinates(client, clean_dest)
        resolved = await build_dynamic_themeparks_pillar(client, clean_dest, coords)
        dynamic_cache[cache_key] = resolved
        return {pillar_clean: resolved}

    if pillar_clean == "events":
        coords = await resolve_dynamic_coordinates(client, clean_dest)
        resolved = await build_dynamic_events_pillar(client, clean_dest, coords)
        dynamic_cache[cache_key] = resolved
        return {pillar_clean: resolved}

    desc = PILLAR_DESCRIPTIONS.get(pillar_clean, "landmarks and venues")
    prompt = f'Return JSON: {{"{pillar_clean}": [{{"name": "Place", "location": "Area", "description": "1 short sentence"}}]}} for 15-20 real iconic {desc} in {clean_dest}.'
    try:
        raw = await asyncio.wait_for(call_ai_with_rate_limit_fallback(client, prompt), timeout=6.0)
        data = json.loads(raw)
        items = data.get(pillar_clean, [])

        async def process_item(idx: int, item: dict) -> dict:
            v_name = clean_venue_title(item.get("name", ""), clean_dest)
            v_loc = item.get("location", clean_dest)
            query_str = f"{v_name}, {v_loc}, {clean_dest}".strip()
            nav_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query_str)}"
            try:
                img_url = await asyncio.wait_for(fetch_dynamic_place_photo(client, venue=v_name, destination=clean_dest, category=pillar_clean), timeout=3.5)
            except Exception:
                img_url = ""
            return {
                "id": f"{pillar_clean}_{idx+1}",
                "title": v_name,
                "name": v_name,
                "category": pillar_clean.replace("_", " ").title(),
                "description": item.get("description", f"Verified venue in {clean_dest}."),
                "address": v_loc,
                "location": v_loc,
                "maps_url": nav_url,
                "navigation_url": nav_url,
                "image_url": img_url,
                "image": img_url,
            }

        tasks = [process_item(idx, item) for idx, item in enumerate(items) if item.get("name")]
        if not tasks:
            fallback_cards = get_default_attractions_for_destination(clean_dest, pillar_clean)
            dynamic_cache[cache_key] = fallback_cards
            return {pillar_clean: fallback_cards}

        resolved = await asyncio.gather(*tasks)
        dynamic_cache[cache_key] = resolved
        return {pillar_clean: resolved}
    except Exception as e:
        logger.error(f"Pillar generation error / timeout: {e}; returning fallback cards")
        fallback_cards = get_default_attractions_for_destination(clean_dest, pillar_clean)
        dynamic_cache[cache_key] = fallback_cards
        return {pillar_clean: fallback_cards}

pillar_cache = dynamic_cache

@app.get("/api/pillar/{pillar_type}", tags=["Pillars"])
@app.get("/pillar/{pillar_type}", tags=["Pillars"])
async def get_dynamic_pillar_data(pillar_type: str, destination: str, request: Request):
    client = request.app.state.client
    dest_clean = destination.strip().title()
    pillar_key = f"{dest_clean.lower()}:{pillar_type.lower()}"

    # Instant sub-millisecond memory hit
    if pillar_key in pillar_cache:
        return pillar_cache[pillar_key]

    coords_task = resolve_dynamic_coordinates(client, dest_clean)
    
    prompt = f"""
    Provide 8 to 10 diverse, verified real-world recommendations for '{pillar_type}' in {dest_clean}.
    JSON Schema:
    {{
      "items": [
        {{
          "title": "Exact Official Venue / Attraction Name",
          "category": "{pillar_type.title()}",
          "description": "Engaging description with genuine local context",
          "location": "Locality or neighborhood in {dest_clean}",
          "rating": 4.7
        }}
      ]
    }}
    STRICT: Return strictly valid JSON containing all items.
    """
    
    ai_task = call_ai_with_rate_limit_fallback(client, prompt)
    
    # Run AI generation and geocoding in parallel
    raw_ai, coords = await asyncio.gather(ai_task, coords_task)
    data = json.loads(raw_ai)
    raw_items = data.get("items", [])

    # Parallelize photo lookups concurrently across all cards
    async def fetch_photo_safe(item_title: str):
        try:
            return await asyncio.wait_for(
                fetch_dynamic_place_photo(client, venue=item_title, destination=dest_clean, category=pillar_type),
                timeout=3.0
            )
        except Exception:
            return ""

    photos = await asyncio.gather(*[fetch_photo_safe(it.get("title", "")) for it in raw_items])

    results = []
    for idx, (item, photo) in enumerate(zip(raw_items, photos)):
        results.append({
            "id": f"{pillar_type}-{idx+1}",
            "title": item.get("title", f"Spot {idx+1}"),
            "category": item.get("category", pillar_type.title()),
            "description": item.get("description", ""),
            "location": item.get("location", dest_clean),
            "image": photo,
            "rating": item.get("rating", 4.6),
            "lat": coords.lat + (idx * 0.002),
            "lng": coords.lng + (idx * 0.002)
        })

    pillar_cache[pillar_key] = results
    return results

@app.get("/api/destination", tags=["Discovery"])
async def get_destination_data(request: Request, destination: str = Query(..., min_length=1)):
    return await get_single_pillar_data(request=request, destination=destination, pillar="attractions")

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

def extract_json_payload(text: str) -> Optional[Dict[str, Any]]:
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

    # Extract JSON object regex pattern safely
    try:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return None

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
