from dotenv import load_dotenv
import os
load_dotenv()
import json
import logging
import httpx
from uuid import UUID
from datetime import date
from contextlib import asynccontextmanager
import re
import urllib.parse
import asyncio
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncpg
from models import EventFestival
from chat_agent import get_chat_agent_tools, execute_tool_call

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Environment variables
# ─────────────────────────────────────────────

TOMTOM_API_KEY      = os.getenv("TOMTOM_API_KEY")
TOMTOM_BASE         = "https://api.tomtom.com"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "NaJtl01BUQuN6F1KxWYRAdCFHi3DTIRnxNXHYaegLg8")
PEXELS_API_KEY      = os.getenv("PEXELS_API_KEY", "rMYuM4ugKNz9f8qaj4zKDIohSR0HAHsqlodYVJk3JqRNglPRVs2AGNMF")
PEXELS_BASE         = "https://api.pexels.com/v1/search"
PEXELS_FALLBACK     = (
    "https://images.pexels.com/photos/1483769/pexels-photo-1483769.jpeg"
    "?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
)
DATABASE_URL        = os.getenv("DATABASE_URL")  # required; no localhost default
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
_raw_model          = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MODEL          = "llama-3.3-70b-versatile" if ("8192" in _raw_model or "llama3-8b" in _raw_model) else _raw_model
GROQ_BASE           = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")

if not GROQ_API_KEY and not GEMINI_API_KEY:
    logger.warning("CRITICAL WARNING: Neither GROQ_API_KEY nor GEMINI_API_KEY is set. Itinerary generation will fallback to hardcoded data.")
if not TOMTOM_API_KEY:
    logger.warning("WARNING: TOMTOM_API_KEY is not set. Map routing and POI images will fail back to defaults.")

# ─────────────────────────────────────────────
#  Pydantic response models
# ─────────────────────────────────────────────

class Coordinates(BaseModel):
    lat: float = 26.8467
    lng: float = 80.9462

CITY_COORDINATES = {
    "lucknow": Coordinates(lat=26.8467, lng=80.9462),
    "delhi": Coordinates(lat=28.6139, lng=77.2090),
    "mumbai": Coordinates(lat=19.0760, lng=72.8777),
    "paris": Coordinates(lat=48.8566, lng=2.3522),
    "dubai": Coordinates(lat=25.2048, lng=55.2708),
    "tokyo": Coordinates(lat=35.6762, lng=139.6503),
    "new york": Coordinates(lat=40.7128, lng=-74.0060)
}

def fallback_coordinates_for(destination: str) -> Coordinates:
    """Return specific lat/lng coordinates for known cities or default center."""
    if not destination:
        return Coordinates(lat=26.8467, lng=80.9462)
    dest_key = str(destination).lower().strip()
    for city, coords in CITY_COORDINATES.items():
        if city in dest_key:
            return coords
    return Coordinates(lat=26.8467, lng=80.9462)

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
    travel_mode: Optional[str] = "car"  # car | pedestrian | bicycle

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
    price_tier: str
    cost_approx: str

class PillarItem(BaseModel):
    id: str = Field(default_factory=lambda: "item-" + str(int(asyncio.get_event_loop().time() * 1000)))
    title: str = "Famous Venue"
    category: str = "Explorer Spot"
    description: str = ""
    address: str = ""
    maps_url: str = ""
    image_url: str = ""
    serving_style: str = ""
    event_time: str = ""
    price_range: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None


class GroqPillarItem(BaseModel):
    title: str
    description: Optional[str] = ""
    address: Optional[str] = "City Center"
    serving_style: Optional[str] = None
    event_time: Optional[str] = None
    price_range: Optional[str] = "$$"


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


class GroqTripStop(BaseModel):
    title: str
    location: Optional[str] = "City Center"
    category: Optional[str] = "Sightseeing"
    duration_minutes: Optional[int] = 60
    best_time: Optional[str] = "10:00 AM"
    cost_range: Optional[str] = "$10 - $25 / person"


class GroqTripDay(BaseModel):
    day: int
    theme: Optional[str] = "Exploration"
    stops: List[GroqTripStop] = []

class GroqCulinaryHighlight(BaseModel):
    title: str
    description: Optional[str] = "Authentic local culinary experience."
    famous_for: Optional[str] = "Local Specialties"
    location: Optional[str] = "City Center"
    price_tier: Optional[str] = "$$"
    cost_approx: Optional[str] = "$15 - $25 / person"

class GroqTripContent(BaseModel):
    destination: Optional[str] = None
    summary: Optional[str] = None
    days: List[GroqTripDay] = []
    culinary_highlights: List[GroqCulinaryHighlight] = []
    attractions: List[GroqPillarItem] = []
    events: List[GroqPillarItem] = []
    culinary: List[GroqPillarItem] = []
    bars_pubs: List[GroqPillarItem] = []
    wellness: List[GroqPillarItem] = []
    secret_spots: List[GroqPillarItem] = []
    essentials: List[GroqPillarItem] = []
    shopping: List[GroqPillarItem] = []
    adventures: List[GroqPillarItem] = []
    theme_parks: List[GroqPillarItem] = []
    sacred_temples: List[GroqPillarItem] = []


FALLBACK_CITY_COORDINATES = {
    "lucknow": Coordinates(lat=26.8467, lng=80.9462),
    "chennai": Coordinates(lat=13.0827, lng=80.2707),
    "reykjavik": Coordinates(lat=64.1466, lng=-21.9426),
    "kyoto": Coordinates(lat=35.0116, lng=135.7681),
    "paris": Coordinates(lat=48.8566, lng=2.3522),
    "london": Coordinates(lat=51.5072, lng=-0.1276),
    "new york": Coordinates(lat=40.7128, lng=-74.0060),
}


# ─────────────────────────────────────────────
#  App lifespan: DB pool + HTTP client
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database connection pool — only connect if DATABASE_URL is provided
    app.state.db_pool = None
    if DATABASE_URL:
        try:
            app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, timeout=10)
            logger.info("✅ Database pool connected.")
        except Exception as e:
            logger.warning(f"⚠️  Could not connect to DB on startup: {e}")
    else:
        logger.warning("⚠️  DATABASE_URL not set — DB features disabled.")

    # Shared async HTTP client
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    logger.info("✅ HTTP client initialized.")

    try:
        yield
    finally:
        if app.state.db_pool:
            await app.state.db_pool.close()
        await app.state.http_client.aclose()


app = FastAPI(
    title="Voyanta API",
    description="Intelligent travel planner powered by TomTom APIs",
    version="2.0.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────
#  CORS — read allowed origins from env var
# ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  Shared dependencies
# ─────────────────────────────────────────────

async def get_http_client() -> httpx.AsyncClient:
    return app.state.http_client

async def get_db_pool():
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database connection is unavailable.")
    yield pool

def tomtom_key():
    if not TOMTOM_API_KEY:
        raise HTTPException(status_code=500, detail="TomTom API key not configured.")
    return TOMTOM_API_KEY


def optional_tomtom_key():
    return TOMTOM_API_KEY


def format_date_range(start: date, days: int) -> str:
    end = start.fromordinal(start.toordinal() + max(days - 1, 0))
    if start.month == end.month:
        return f"{start.strftime('%b %d')} - {end.strftime('%d')}"
    return f"{start.strftime('%b %d')} - {end.strftime('%b %d')}"


def estimate_duration_minutes(distance_meters: Optional[float], index: int) -> int:
    base = 75 + (index % 3) * 30
    if not distance_meters:
        return base
    return max(45, min(240, int(distance_meters / 30)))


def build_time_label(index: int) -> str:
    schedule = ["09:00 AM", "12:30 PM", "04:00 PM", "07:30 PM"]
    return schedule[index % len(schedule)]


def clean_stop_title(title: str, destination: str = "") -> str:
    if not title:
        return "Famous Venue"
    clean = title.strip()
    if destination:
        clean = re.sub(rf"^(?:{re.escape(destination.strip())}|Lucknow|Delhi|Paris|Kyoto|Tokyo|Dubai|London|New York|Mumbai)[,\s\-]+", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"^[,\-\:\s]+", "", clean).strip()
    return clean if clean else title.strip()


def generate_maps_link(place_name: str, destination: str) -> str:
    clean_name = clean_stop_title(place_name, destination)
    query = f"{clean_name}, {destination.strip()}"
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query)}"


def build_image_url(query: str) -> str:
    return f"https://picsum.photos/seed/{query.replace(' ', '-').lower()}/1200/800"


def build_tomtom_static_map_url(
    lat: float,
    lng: float,
    zoom: int = 11,
    width: int = 1280,
    height: int = 720,
) -> str:
    return (
        f"https://api.tomtom.com/map/1/staticimage?key={TOMTOM_API_KEY}"
        f"&center={lat},{lng}&zoom={zoom}&width={width}&height={height}"
        "&format=jpg&layer=basic&style=main&view=Unified"
    )


def build_day_route_from_coordinates(day: int, coordinates: List[List[float]]) -> TripDayRoute:
    if len(coordinates) < 2:
        return TripDayRoute(day=day)

    segment_count = max(len(coordinates) - 1, 1)
    return TripDayRoute(
        day=day,
        geojson={
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
            "properties": {"source": "generated"},
        },
        total_distance_meters=segment_count * 2800,
        total_travel_time_seconds=segment_count * 1200,
    )


async def fetch_destination_image(client: httpx.AsyncClient, location: str) -> str:
    return await fetch_real_image(client, f"{location} city landmark", location)


async def fetch_real_image(
    client: httpx.AsyncClient,
    primary_query: str,
    fallback_query: Optional[str] = None,
) -> str:
    """
    Fetch a high-quality photo from the Pexels API.
    Falls back to a curated Pexels stock image if the API key is absent
    or no results are returned.
    """
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not set — using picsum fallback for '%s'", primary_query)
        return build_image_url(primary_query)

    for query in filter(None, [primary_query, fallback_query]):
        try:
            r = await client.get(
                PEXELS_BASE,
                params={
                    "query": query,
                    "per_page": 1,
                    "orientation": "landscape",
                },
                headers={"Authorization": PEXELS_API_KEY},
                timeout=8.0,
            )
            r.raise_for_status()
            photos = r.json().get("photos", [])
            if photos:
                src = photos[0].get("src", {})
                url = src.get("landscape") or src.get("large")
                if url:
                    logger.info("Pexels photo found for '%s'", query)
                    return url
        except Exception as exc:
            logger.warning("Pexels lookup failed for '%s': %s", query, exc)

    logger.info("No Pexels result for '%s' — using fallback", primary_query)
    return PEXELS_FALLBACK


async def fetch_weather_label(client: httpx.AsyncClient, lat: float, lng: float) -> str:
    if OPENWEATHER_API_KEY:
        try:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat,
                    "lon": lng,
                    "appid": OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )
            r.raise_for_status()
            main = r.json().get("main", {})
            temperature = main.get("temp")
            if temperature is not None:
                return f"{round(float(temperature))}°C"
        except Exception as exc:
            logger.warning("OpenWeather lookup failed for %s,%s: %s", lat, lng, exc)

    # Free fallback — Open-Meteo (no API key required)
    try:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "current": "temperature_2m",
            },
        )
        r.raise_for_status()
        current = r.json().get("current", {})
        temperature = current.get("temperature_2m")
        if temperature is not None:
            return f"{round(float(temperature))}°C"
    except Exception as exc:
        logger.warning("Weather lookup failed for %s,%s: %s", lat, lng, exc)

    return "Weather unavailable"


def clean_stop_title(title: str, destination: str = "") -> str:
    if not title:
        return "Famous Venue"
    clean = str(title).strip()
    if destination:
        clean = re.sub(rf"^(?:{re.escape(destination.strip())})[,\s\-]+", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"^[,\-\:\s]+", "", clean).strip()
    return clean if clean else str(title).strip()

def generate_maps_link(place_name: str, destination: str) -> str:
    clean_name = clean_stop_title(place_name, destination)
    query = f"{clean_name}, {destination.strip()}"
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query)}"


async def get_async_place_photo(client: httpx.AsyncClient, place_name: str, destination: str) -> str:
    clean_name = clean_stop_title(place_name, destination)
    query = f"{clean_name} {destination}".strip()
    encoded = urllib.parse.quote(query)

    # Tier 1: Unsplash Search API
    if UNSPLASH_ACCESS_KEY:
        try:
            url = f"https://api.unsplash.com/search/photos?page=1&query={encoded}&client_id={UNSPLASH_ACCESS_KEY}&per_page=1"
            res = await client.get(url, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("results") and len(data["results"]) > 0:
                    return data["results"][0]["urls"]["regular"]
        except Exception:
            pass

    # Tier 2: Pexels Search API
    if PEXELS_API_KEY:
        try:
            url = f"https://api.pexels.com/v1/search?query={encoded}&per_page=1"
            headers = {"Authorization": PEXELS_API_KEY}
            res = await client.get(url, headers=headers, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    return data["photos"][0]["src"]["medium"]
        except Exception:
            pass

    # Tier 3: Wikimedia Commons Search API (Free, high-res landmark search)
    try:
        wiki_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&prop=pageimages&piprop=original&gsrsearch={encoded}&format=json"
        res = await client.get(wiki_url, headers={"User-Agent": "VoyantaTravel/1.0"}, timeout=2.0)
        if res.status_code == 200:
            pages = res.json().get("query", {}).get("pages", {})
            for _, page_data in pages.items():
                if "original" in page_data and "source" in page_data["original"]:
                    return page_data["original"]["source"]
    except Exception:
        pass

    # Tier 4: Reliable Unsplash Direct Keyword Fallback
    return "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=900&auto=format&fit=crop&q=80"


# ─────────────────────────────────────────────
#  Groq AI — replaces local Ollama
# ─────────────────────────────────────────────

async def generate_trip_with_groq(
    client: httpx.AsyncClient,
    location: str,
    days: int,
    start_day: date,
    coordinates: Coordinates,
    categories: Optional[List[str]] = None,
    pace: Optional[str] = None,
    budget: Optional[str] = None,
    travelers: Optional[TravelerGroup] = None,
    language: Optional[str] = "English",
) -> Optional[TripPlanResponse]:
    """
    Generate a trip itinerary using Groq's free hosted LLM API.
    Falls back gracefully if GROQ_API_KEY is not set or the request fails.
    """
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — skipping AI trip generation for %s", location)
        return None

    stops_per_day = 3
    if pace:
        if "relaxed" in pace.lower():
            stops_per_day = 2
        elif "action" in pace.lower() or "packed" in pace.lower():
            stops_per_day = 5

    categories_str = ", ".join(categories) if categories else "Food, Culture, Nature, Shopping, Heritage, Wellness, Sightseeing"
    budget_str = budget if budget else "Moderate"

    prompt = (
        f"Create a realistic {days}-day travel itinerary for {location}. "
        f"The traveler prefers a {pace or 'Balanced'} pace ({stops_per_day} stops per day) "
        f"with a {budget_str} budget. "
        "CRITICAL REQUIREMENTS:\n"
        "- ABSOLUTELY NO REPEATING ACTIVITIES: Every single day MUST contain completely unique, non-repeating activities. Do not reuse any location, attraction, or restaurant across the entire trip.\n"
        "- DISTINCT SCHEDULES: Provide distinct morning, afternoon, and evening activities with realistic time spacing.\n"
        "- Include a dedicated 'culinary_highlights' array containing 3 to 5 'Must-Try' iconic local food suggestions and legendary eateries famous for local dishes.\n"
        "- PRICING: Provide precise cost estimates in USD ($). For stops, use 'cost_range' (e.g. '$10 - $30 / person'). For culinary, use 'price_tier' (e.g. '$$$') and 'cost_approx' (e.g. '$15 - $25 / person').\n"
        "Return ONLY a valid JSON object (no markdown, no extra text) with this exact structure:\n"
        '{"destination":"<city name>","summary":"<one sentence>","days":['
        '{"day":1,"theme":"<theme>","stops":['
        '{"title":"<famous place name>","location":"<address>","category":"<category string>","duration_minutes":<int>,"best_time":"<HH:MM AM/PM>","cost_range":"<str>"},'
        f"...{stops_per_day} stops per day]}}],"
        '"culinary_highlights":['
        '{"title":"<eatery or dish>","description":"<desc>","famous_for":"<specialty>","location":"<address>","price_tier":"$$","cost_approx":"<str>"}],'
        '"attractions":[{"title":"<real landmark>","description":"<highlights>","address":"<area>","price_range":"$10 - $20"}],'
        '"events":[{"title":"<real live event/venue>","description":"<details>","address":"<area>","event_time":"7:00 PM - 10:00 PM","price_range":"$15 - $30"}],'
        '"culinary":[{"title":"<real restaurant>","description":"<famous dishes>","address":"<area>","serving_style":"A la carte / Buffet / Street Food","price_range":"$$"}],'
        '"bars_pubs":[{"title":"<real nightlife venue>","description":"<atmosphere>","address":"<area>","price_range":"$$$"}],'
        '"wellness":[{"title":"<real spa/gym/yoga center>","description":"<facilities>","address":"<area>","price_range":"$$"}],'
        '"secret_spots":[{"title":"<real hidden gem>","description":"<local secret>","address":"<area>","price_range":"$"}],'
        '"essentials":[{"title":"<practical advice/emergency item>","description":"<numbers, hospital, transit, scam tips>","address":"<citywide>"}],'
        '"shopping":[{"title":"<real bazaar or mall>","description":"<handicrafts or brands>","address":"<area>","price_range":"$$"}],'
        '"adventures":[{"title":"<real outdoor thrill/trek>","description":"<activity details>","address":"<area>","price_range":"$$$"}],'
        '"theme_parks":[{"title":"<real amusement or water park>","description":"<attractions>","address":"<area>","price_range":"$$"}]}\n'
        f"Generate exactly {days} days with {stops_per_day} stops each, plus 3 to 5 real items for each of the 10 pillars (attractions, events, culinary, bars_pubs, wellness, secret_spots, essentials, shopping, adventures, theme_parks)."
    )

    traveler_context_str = ""
    if travelers:
        group_type = travelers.group_type or "Solo"
        seniors = travelers.seniors or 0
        infants = travelers.infants or 0
        adults = travelers.adults or 1

        guidelines = []
        if seniors > 0:
            guidelines.append("SENIOR CITIZENS PRESENT: Prefer accessible, comfortably paced venues and note low-walking options where possible, but still include iconic landmark stops with pacing notes (e.g. 'ground courtyard accessible; upper stairs optional').")
        if infants > 0:
            guidelines.append("INFANTS/CHILDREN PRESENT: Balance stroller-friendly spots or parks with essential city sights, adding gentle scheduling tips rather than omitting key attractions.")
        if group_type.lower() == "couple":
            guidelines.append("TRAVELING AS A COUPLE: Naturally lean towards atmospheric spots, scenic vistas, or cozy dining, while keeping core sightseeing balanced.")
        elif group_type.lower() == "family":
            guidelines.append("TRAVELING AS A FAMILY: Ensure a balanced mix of culture, open space, and comfortable dining options suitable for all ages.")
        elif group_type.lower() == "friends":
            guidelines.append("TRAVELING WITH FRIENDS: Include vibrant culinary hubs, iconic sights, and lively group-friendly experiences.")
        elif group_type.lower() == "business":
            guidelines.append("BUSINESS TRAVEL: Keep schedules efficient, with easy access to central landmarks and premium dining.")

        traveler_context_str = f"\n\nTRAVELER GROUP CONTEXT ({group_type}, {adults} Adults, {seniors} Seniors, {infants} Infants):\n" + "\n".join(f"- {g}" for g in guidelines) if guidelines else f"\n\nTRAVELER GROUP CONTEXT: Group Type is {group_type}."

    system_prompt = (
        "STRICT 25+ REAL VENUE PER PILLAR MANDATE (11 PILLARS TOTAL):\n"
        f"You are VOYANTA's master local curator. For the requested {location}, you MUST return AT LEAST 25 SPECIFIC REAL-WORLD VENUES for each of the 11 Explorer Pillars (275+ total venues).\n\n"
        f"TEMPLES & SACRED SHRINES REQUIREMENT FOR {location}:\n"
        f"You MUST return at least 25 specific temples, ancient shrines, sacred heritage sites, and spiritual landmarks for {location}.\n\n"
        f"SHOPPING COVERAGE MANDATE FOR {location}:\n"
        f"You MUST return at least 25 shopping spots covering luxury malls, high street shopping boulevards, local old-town bazaars, street shopping lanes, flea markets, bangle/textile alleys, and wholesale markets in {location}.\n\n"
        "STRICTLY BAN generic placeholders like 'Central Plaza', 'Grand Art Museum', 'Local Market', 'Downtown Walk', 'Signature Trail', or 'Local Temple'.\n"
        f"- STRICT LANGUAGE INSTRUCTION: You MUST generate and translate ALL titles, descriptions, and pillar items directly in {language or 'English'}. Do NOT default to English if another language is selected.\n"
        f"- NO CITY PREFIXES IN TITLES: Output ONLY the exact landmark or venue name without prefixing state/country.\n"
        f"{traveler_context_str}\n"
    )

    try:
        response = await client.post(
            GROQ_BASE,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 3000,
            },
            timeout=15.0,
        )
        if response.status_code != 200:
            logger.error("Groq API error response (%s): %s", response.status_code, response.text)
            return None
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        import re
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
        content = content.strip()

        ai_trip = GroqTripContent.model_validate_json(content)
        
        # Guardrail: Strip out banned generic terms
        banned_terms = ["gym", "fitness", "neighborhood park", "local society", "generic"]
        for day in ai_trip.days:
            day.stops = [
                stop for stop in day.stops 
                if not any(term in (stop.title.lower() + (stop.location.lower() if stop.location else "")) for term in banned_terms)
            ]
            
    except Exception as exc:
        logger.warning("Groq trip generation failed for %s: %s", location, exc)
        return None

    destination = ai_trip.destination or location.title()
    destination_image = await fetch_real_image(client, destination)
    itinerary: List[TripStop] = []
    routes: List[TripDayRoute] = []
    map_image_url = build_image_url(f"map {destination}")

    for day_index in range(days):
        day_number = day_index + 1
        trip_date = start_day.fromordinal(start_day.toordinal() + day_index)
        ai_day = next((item for item in ai_trip.days if item.day == day_number), None)
        day_coordinates: List[List[float]] = []
        day_stops = ai_day.stops[:3] if ai_day and ai_day.stops else []

        if not day_stops:
            continue

        for stop_index, stop in enumerate(day_stops):
            stop_lat = coordinates.lat
            stop_lng = coordinates.lng
            
            # Geocoding Guardrail: query "{stop.title}, {destination}" via TomTom if key available
            if TOMTOM_API_KEY:
                try:
                    geo_url = f"{TOMTOM_BASE}/search/2/geocode/{stop.title}, {destination}.json"
                    geo_res = await client.get(geo_url, params={"key": TOMTOM_API_KEY, "limit": 1})
                    if geo_res.status_code == 200:
                        geo_data = geo_res.json().get("results", [])
                        if geo_data:
                            pos = geo_data[0].get("position", {})
                            stop_lat = pos.get("lat", stop_lat)
                            stop_lng = pos.get("lon", stop_lng)
                except Exception as e:
                    logger.warning("Geocoding failed for %s, %s: %s", stop.title, destination, e)

            if stop_lat == coordinates.lat and stop_lng == coordinates.lng:
                # Small micro-offset around city center if geocoding unavailable
                stop_lat = coordinates.lat + (stop_index - 1) * 0.005 + (day_index * 0.003)
                stop_lng = coordinates.lng + (stop_index + 1) * 0.004 + (day_index * 0.003)

            cleaned_title = clean_stop_title(stop.title, destination)
            day_coordinates.append([stop_lng, stop_lat])
            stop_image = await fetch_real_image(client, cleaned_title, f"{cleaned_title} {destination}")
            itinerary.append(
                TripStop(
                    id=f"groq-{day_number}-{stop_index + 1}",
                    day=day_number,
                    date=trip_date.strftime("%b %d"),
                    time=stop.best_time or build_time_label(stop_index),
                    title=cleaned_title,
                    location=stop.location or destination,
                    type=(stop.category or "SIGHTSEEING").upper(),
                    creators=f"Starts at {stop.best_time or build_time_label(stop_index)}",
                    distance=f"{round((stop_index + 1) * 2.1 + (day_index * 0.6), 1)}km",
                    elevation="N/A",
                    duration=f"{max(45, stop.duration_minutes or 60)}m",
                    image=stop_image,
                    map_image_url=map_image_url,
                    lat=stop_lat,
                    lng=stop_lng,
                    cost_range=getattr(stop, 'cost_range', '$10 - $20 / person'),
                )
            )

        routes.append(build_day_route_from_coordinates(day_number, day_coordinates))

    if not itinerary:
        return None

    async def map_pillar_items_async(items: list, cat_label: str) -> List[PillarItem]:
        async def create_item(i: int, item: Any) -> PillarItem:
            title = clean_stop_title(getattr(item, 'title', ''), destination)
            image_url = await get_async_place_photo(client, title, destination)
            return PillarItem(
                id=f"{cat_label.lower().replace(' ', '-')}-{i+1}",
                title=title,
                category=cat_label,
                description=getattr(item, 'description', '') or '',
                address=getattr(item, 'address', '') or destination,
                maps_url=generate_maps_link(title, destination),
                image_url=image_url,
                lat=coordinates.lat,
                lng=coordinates.lng,
                serving_style=getattr(item, 'serving_style', '') or '',
                event_time=getattr(item, 'event_time', '') or '',
                price_range=getattr(item, 'price_range', '$$') or '$$',
            )

        tasks = [create_item(i, item) for i, item in enumerate(items)]
        return list(await asyncio.gather(*tasks)) if tasks else []

    (
        attractions, events, culinary, bars_pubs, wellness,
        secret_spots, essentials, shopping, adventures, theme_parks, sacred_temples
    ) = await asyncio.gather(
        map_pillar_items_async(getattr(ai_trip, 'attractions', []), "Tourist Attractions"),
        map_pillar_items_async(getattr(ai_trip, 'events', []), "Events"),
        map_pillar_items_async(getattr(ai_trip, 'culinary', []), "Culinary"),
        map_pillar_items_async(getattr(ai_trip, 'bars_pubs', []), "Bars & Pubs"),
        map_pillar_items_async(getattr(ai_trip, 'wellness', []), "Wellness & Meditation"),
        map_pillar_items_async(getattr(ai_trip, 'secret_spots', []), "Secret Spots"),
        map_pillar_items_async(getattr(ai_trip, 'essentials', []), "Travel Essentials"),
        map_pillar_items_async(getattr(ai_trip, 'shopping', []), "Shopping"),
        map_pillar_items_async(getattr(ai_trip, 'adventures', []), "Adventures"),
        map_pillar_items_async(getattr(ai_trip, 'theme_parks', []), "Theme Parks"),
        map_pillar_items_async(getattr(ai_trip, 'sacred_temples', []), "Sacred Temples & Heritage Shrines"),
    )

    weather_label = await fetch_weather_label(client, coordinates.lat, coordinates.lng)
    return TripPlanResponse(
        destination=destination,
        destination_image=destination_image,
        map_image_url=build_tomtom_static_map_url(coordinates.lat, coordinates.lng, zoom=10)
        if TOMTOM_API_KEY else build_image_url(f"map {destination}"),
        weather=weather_label if weather_label != "Weather unavailable" else "AI-planned",
        dates=format_date_range(start_day, days),
        days=days,
        coordinates=coordinates,
        itinerary=itinerary,
        routes=routes,
        culinary_highlights=[
            CulinaryHighlight(
                title=h.title,
                description=h.description,
                famous_for=h.famous_for,
                location=h.location,
                price_tier=getattr(h, 'price_tier', '$$'),
                cost_approx=getattr(h, 'cost_approx', '$15 - $25 / person'),
            ) for h in ai_trip.culinary_highlights
        ] if hasattr(ai_trip, "culinary_highlights") else [],
        attractions=attractions,
        events=events,
        culinary=culinary,
        bars_pubs=bars_pubs,
        wellness=wellness,
        secret_spots=secret_spots,
        essentials=essentials,
        shopping=shopping,
        adventures=adventures,
        theme_parks=theme_parks,
        sacred_temples=sacred_temples,
    )


CITY_REAL_VENUES = {
    "lucknow": {
        "sacred_temples": [
            "Mankameshwar Temple (Babuganj)", "Hanuman Setu Temple", "Chandrika Devi Temple (Kathwara)",
            "Sankat Mochan Hanuman Temple", "Buddha Vihar Shanti Upavan", "Aliganj Bada Hanuman Temple",
            "Sheetla Devi Temple (Mehendiganj)", "ISKCON Temple Lucknow", "Naya Hanuman Mandir (Aliganj)",
            "Khamman Pir Dargah", "Bada Imambara Mosque Complex", "Surya Temple (Gomti Riverfront)",
            "Kali Bari Mandir (Ghanshyam Nagar)", "Shiv Temple (Hazratganj)", "Sanatan Dharam Mandir",
            "Sai Baba Temple (Aliganj)", "Laxmi Narayan Mandir", "Annapurna Mandir", "Siddhi Vinayak Temple",
            "Charbagh Railway Temple Complex", "Panchmukhi Hanuman Mandir", "Durga Puri Mandir",
            "Arya Samaj Mandir Chowk", "Bhootnath Temple", "Hanuman Garhi Alambagh"
        ],
        "attractions": ["Bara Imambara & Bhool Bhulaiya", "Rumi Darwaza", "Chota Imambara", "Ambedkar Memorial Park"],
        "events": ["Lucknow Mahotsav Cultural Night", "Gomti Riverfront Light Show", "Hazratganj Live Music Evenings"],
        "culinary": ["Tunday Kababi (Aminabad)", "Dastarkhwan (Hazratganj)", "Prakash Ki Kulfi", "Sharma Tea Stall"],
        "bars_pubs": ["Sky Glasshouse", "The Flying Saucer Cafe", "Vintageland Lucknow", "Mocobos Bar"],
        "wellness": ["Gomti Riverfront Yoga Park", "Janasheen Herbal Spa", "Lohia Park Morning Walk Trail"],
        "secret_spots": ["Residency Historical Gardens", "Kudia Ghat Sunset Point", "Chattar Manzil Complex"],
        "essentials": ["Charbagh Railway Station Hub", "Chowk Medical Store", "Hazratganj Tourist Information Center"],
        "shopping": ["Hazratganj Market", "Aminabad Street Bazaar", "Chowk Chikan Embroidery Market", "Phoenix Palassio Mall"],
        "adventures": ["Kukrail Reserve Forest Trail", "Gomti River Kayaking Club", "Anandi Water Park Zip Line"],
        "theme_parks": ["Anandi Water Park", "Dream World Amusement Park", "Nilansh Theme Resort & Water Park"]
    },
    "paris": {
        "attractions": ["Eiffel Tower", "Louvre Museum", "Cathédrale Notre-Dame", "Arc de Triomphe"],
        "events": ["Seine Sunset Music Cruise", "Montmartre Art Walk", "Paris Fashion Week Showcase"],
        "culinary": ["Le Relais de l'Entrecôte", "L'As du Fallafel", "Angelina Paris", "Du Pain et des Idées"],
        "bars_pubs": ["Le Syndicat", "Café de Flore", "Little Red Door", "Harry's New York Bar"],
        "wellness": ["Spa Pont-Neuf", "Jardin du Luxembourg Yoga", "Ritz Club & Spa"],
        "secret_spots": ["Promenade Plantée", "Rue Crémieux", "Musée de l'Orangerie", "Sainte-Chapelle"],
        "essentials": ["Hôtel-Dieu Emergency Desk (112)", "RATP Metro Station Hub", "Charles de Gaulle Express Center"],
        "shopping": ["Galeries Lafayette Haussmann", "Champs-Élysées Boutiques", "Marché aux Puces de Saint-Ouen"],
        "adventures": ["Seine Kayaking Expedition", "Bois de Boulogne Bike Loop", "Catacombes Deep Exploration"],
        "theme_parks": ["Disneyland Paris", "Parc Astérix", "Jardin d'Acclimatation"]
    },
    "delhi": {
        "attractions": ["Red Fort", "Qutub Minar", "India Gate", "Humayun's Tomb"],
        "events": ["Dilli Haat Cultural Festival", "India Habitat Centre Art Showcase", "Chandni Chowk Night Food Walk"],
        "culinary": ["Karim's Chandni Chowk", "Bukhara (ITC Maurya)", "Saravana Bhavan", "Natraj Dahi Bhalle"],
        "bars_pubs": ["Sidecar GK2", "PCO Speakeasy", "The Electric Room", "Local CP"],
        "wellness": ["Lodhi Garden Sunrise Yoga", "Kairali Ayurvedic Center", "The Imperial Spa"],
        "secret_spots": ["Agrasen ki Baoli", "Hauz Khas Fort Sunset Point", "Majnu ka Tilla Secret Alley"],
        "essentials": ["AIIMS Emergency Desk (112)", "Delhi Metro Card Center", "New Delhi Railway Station Help Desk"],
        "shopping": ["Chandni Chowk Bazaar", "Khan Market Boutiques", "Dilli Haat Handicrafts", "Select CITYWALK"],
        "adventures": ["Aravalli Biodiversity Park Trail", "Yamuna Sports Complex Cycling", "Asola Bhatti Wildlife Safari"],
        "theme_parks": ["Adventure Island Rohini", "Worlds of Wonder Noida", "Fun N Food Village"]
    }
}


async def build_fallback_trip_plan(
    location: str,
    days: int = 3,
    start_day: Optional[date] = None,
    client: Optional[httpx.AsyncClient] = None
) -> TripPlanResponse:
    destination = (location or "Lucknow").strip().title()
    dest_key = destination.lower().strip()
    start_day = start_day or date.today()
    coordinates = fallback_coordinates_for(destination)
    destination_image = await get_async_place_photo(client, f"{destination} landmark", destination) if client else PEXELS_FALLBACK

    matched_venues = None
    for k, v in CITY_REAL_VENUES.items():
        if k in dest_key or dest_key in k:
            matched_venues = v
            break

    def get_fallback_venue(cat_key: str, index: int, default_pattern: str) -> str:
        if matched_venues and cat_key in matched_venues and index < len(matched_venues[cat_key]):
            return matched_venues[cat_key][index]
        return f"{destination} {default_pattern}"

    try:
        itinerary: List[TripStop] = []
        routes: List[TripDayRoute] = []

        for day_index in range(days):
            day_number = day_index + 1
            trip_date = start_day.fromordinal(start_day.toordinal() + day_index)
            day_coordinates: List[List[float]] = []

            for stop_index in range(3):
                stop_lat = coordinates.lat + (stop_index * 0.005) + (day_index * 0.01)
                stop_lng = coordinates.lng + (stop_index * 0.005) + (day_index * 0.01)
                
                venue_title = get_fallback_venue("attractions", (day_index * 3) + stop_index, f"Heritage Spot {stop_index + 1}")
                stop_image = await get_async_place_photo(client, venue_title, destination) if client else PEXELS_FALLBACK

                itinerary.append(
                    TripStop(
                        id=f"fallback-{day_number}-{stop_index + 1}",
                        day=day_number,
                        date=trip_date.strftime("%b %d"),
                        time=build_time_label(stop_index),
                        title=venue_title,
                        location=destination,
                        type="ATTRACTION",
                        creators=f"Starts at {build_time_label(stop_index)}",
                        distance=f"{round((stop_index + 1) * 1.8, 1)}km",
                        elevation="N/A",
                        duration="90m",
                        image=stop_image,
                        map_image_url=build_tomtom_static_map_url(stop_lat, stop_lng) if TOMTOM_API_KEY else build_image_url(f"map {stop_lat}"),
                        lat=stop_lat,
                        lng=stop_lng,
                        cost_range="$15 - $30 / person",
                    )
                )
                day_coordinates.append([stop_lng, stop_lat])

            route = build_day_route_from_coordinates(day_number, day_coordinates)
            route.total_distance_meters = 5400 + (day_index * 900)
            route.total_travel_time_seconds = 1800 + (day_index * 300)
            if route.geojson:
                route.geojson["properties"] = {"fallback": True}
            routes.append(route)

        async def build_pillar_list(cat_key: str, cat_label: str, defaults: List[str]) -> List[PillarItem]:
            res = []
            for i, default_pat in enumerate(defaults):
                v_title = get_fallback_venue(cat_key, i, default_pat)
                img = await get_async_place_photo(client, v_title, destination) if client else PEXELS_FALLBACK
                res.append(
                    PillarItem(
                        id=f"{cat_key}-{i+1}",
                        title=v_title,
                        category=cat_label,
                        description=f"Verified landmark experience in {destination}.",
                        address=destination,
                        maps_url=generate_maps_link(v_title, destination),
                        image_url=img,
                        lat=coordinates.lat,
                        lng=coordinates.lng,
                        price_range="$$"
                    )
                )
            return res

        (
            attractions, events, culinary, bars_pubs, wellness,
            secret_spots, essentials, shopping, adventures, theme_parks, sacred_temples
        ) = await asyncio.gather(
            build_pillar_list("attractions", "Tourist Attractions", ["Historic Landmark", "Cultural Center", "City Promenade", "Royal Monument"]),
            build_pillar_list("events", "Events", ["Cultural Evening Gala", "Live Music Session", "Heritage Art Showcase"]),
            build_pillar_list("culinary", "Culinary", ["Legendary Specialty Eatery", "Street Food Haven", "Rooftop Dining Lounge"]),
            build_pillar_list("bars_pubs", "Bars & Pubs", ["Skyline Lounge & Bar", "Craft Cocktail Taproom", "Vibrant Social Club"]),
            build_pillar_list("wellness", "Wellness & Meditation", ["Serene Herbal Spa", "Sunrise Meditation Park", "Luxury Wellness Pavilion"]),
            build_pillar_list("secret_spots", "Secret Spots", ["Hidden Courtyard Cafe", "Scenic Sunset Point", "Historic Alleyway Walk"]),
            build_pillar_list("essentials", "Travel Essentials", ["Medical & Emergency Desk", "Central Transit Station", "Tourist Information Center"]),
            build_pillar_list("shopping", "Shopping", ["Traditional Artisan Bazaar", "Bustling Street Market", "Luxury Shopping Galleria"]),
            build_pillar_list("adventures", "Adventures", ["Outdoor Nature Reserve", "Riverfront Kayaking & Trails", "Scenic Ridge Trek"]),
            build_pillar_list("theme_parks", "Theme Parks", ["Grand Water Kingdom", "Thrill Amusement World", "Family Adventure Resort"]),
            build_pillar_list("sacred_temples", "Sacred Temples & Heritage Shrines", ["Ancient Heritage Temple", "Sacred Spiritual Shrine", "Historic Royal Mosque"]),
        )

        return TripPlanResponse(
            destination=destination,
            destination_image=destination_image,
            map_image_url=build_tomtom_static_map_url(coordinates.lat, coordinates.lng, zoom=10)
            if TOMTOM_API_KEY else build_image_url(f"map {destination}"),
            weather="Offline mode",
            dates=format_date_range(start_day, days),
            days=days,
            coordinates=coordinates,
            itinerary=itinerary,
            routes=routes,
            culinary_highlights=[],
            attractions=attractions,
            events=events,
            culinary=culinary,
            bars_pubs=bars_pubs,
            wellness=wellness,
            secret_spots=secret_spots,
            essentials=essentials,
            shopping=shopping,
            adventures=adventures,
            theme_parks=theme_parks,
            sacred_temples=sacred_temples,
        )
    except Exception as exc:
        logger.error("Critical error building fallback trip plan for %s: %s", location, exc, exc_info=True)
        dest = (location or "Lucknow").title()
        c = fallback_coordinates_for(dest)
        s_date = start_day or date.today()
        d_num = days or 3
        emerg_attractions = [
            PillarItem(id="emerg-attr-1", title="Heritage Landmark", category="Tourist Attractions", description="Iconic city attraction.", address=dest, maps_url=generate_maps_link("Heritage Landmark", dest), lat=c.lat, lng=c.lng)
        ]
        return TripPlanResponse(
            destination=dest,
            destination_image=PEXELS_FALLBACK,
            map_image_url=build_image_url(f"map {dest}"),
            weather="Offline mode",
            dates=format_date_range(s_date, d_num),
            days=d_num,
            coordinates=c,
            itinerary=[
                TripStop(
                    id="emergency-1", day=1, date=s_date.strftime("%b %d"), time="09:00 AM",
                    title="Bara Imambara & Bhool Bhulaiya", location=dest, type="ATTRACTION",
                    creators="Starts at 09:00 AM", distance="1.5km", elevation="N/A", duration="90m",
                    image=PEXELS_FALLBACK, map_image_url=build_image_url("map Bara Imambara"),
                    lat=26.8689, lng=80.9128, cost_range="$10 - $20 / person",
                ),
                TripStop(
                    id="emergency-2", day=1, date=s_date.strftime("%b %d"), time="01:00 PM",
                    title="Rumi Darwaza", location=dest, type="CULTURE",
                    creators="Starts at 01:00 PM", distance="0.8km", elevation="N/A", duration="60m",
                    image=PEXELS_FALLBACK, map_image_url=build_image_url("map Rumi Darwaza"),
                    lat=26.8710, lng=80.9126, cost_range="Free",
                ),
                TripStop(
                    id="emergency-3", day=1, date=s_date.strftime("%b %d"), time="07:00 PM",
                    title="Tunday Kababi Chowk", location=dest, type="CULINARY",
                    creators="Starts at 07:00 PM", distance="2.0km", elevation="N/A", duration="90m",
                    image=PEXELS_FALLBACK, map_image_url=build_image_url("map Tunday Kababi"),
                    lat=26.8606, lng=80.9158, cost_range="$5 - $15 / person",
                )
            ],
            routes=[],
            culinary_highlights=[],
            attractions=emerg_attractions,
            events=[],
            culinary=[],
            bars_pubs=[],
            wellness=[],
            secret_spots=[],
            essentials=[],
            shopping=[],
            adventures=[],
            theme_parks=[],
        )


# ─────────────────────────────────────────────
#  Root
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "message": "Welcome to Voyanta API v2 — Powered by TomTom",
        "docs": "/docs",
        "tomtom_configured": bool(TOMTOM_API_KEY),
        "groq_configured": bool(GROQ_API_KEY),
        "db_configured": bool(DATABASE_URL),
    }


# ─────────────────────────────────────────────
#  1. GEOCODING  — convert address → coordinates
# ─────────────────────────────────────────────

@app.get("/geocode", response_model=List[GeocodeResult], tags=["Maps & Geocoding"])
async def geocode(
    query: str = Query(..., description="Address, place name, or landmark to search for"),
    limit: int = Query(5, ge=1, le=10),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    url = f"{TOMTOM_BASE}/search/2/geocode/{query}.json"
    params = {"key": key, "limit": limit, "typeahead": True}
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"TomTom geocoding error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"TomTom API unreachable: {str(e)}")

    results = []
    for item in data.get("results", []):
        pos = item.get("position", {})
        addr = item.get("address", {})
        results.append(GeocodeResult(
            address=item.get("address", {}).get("freeformAddress", ""),
            lat=pos.get("lat", 0),
            lng=pos.get("lon", 0),
            country=addr.get("country", ""),
            city=addr.get("municipality"),
            score=item.get("score")
        ))
    return results


# ─────────────────────────────────────────────
#  2. REVERSE GEOCODING — coordinates → address
# ─────────────────────────────────────────────

@app.get("/reverse-geocode", response_model=ReverseGeocodeResult, tags=["Maps & Geocoding"])
async def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    url = f"{TOMTOM_BASE}/search/2/reverseGeocode/{lat},{lng}.json"
    params = {"key": key}
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"TomTom reverse geocode error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"TomTom API unreachable: {str(e)}")

    addresses = data.get("addresses", [])
    if not addresses:
        raise HTTPException(status_code=404, detail="No address found for these coordinates.")

    addr = addresses[0].get("address", {})
    return ReverseGeocodeResult(
        address=addr.get("freeformAddress", ""),
        city=addr.get("municipality"),
        country=addr.get("country"),
        postal_code=addr.get("postalCode")
    )


# ─────────────────────────────────────────────
#  3. ROUTE CALCULATION
# ─────────────────────────────────────────────

@app.post("/route", response_model=RouteResponse, tags=["Routing"])
async def calculate_route(
    body: RouteRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    if len(body.waypoints) < 2:
        raise HTTPException(status_code=400, detail="At least 2 waypoints are required.")

    locations = ":".join([f"{wp.lat},{wp.lng}" for wp in body.waypoints])
    url = f"{TOMTOM_BASE}/routing/1/calculateRoute/{locations}/json"
    params = {
        "key": key,
        "travelMode": body.travel_mode,
        "routeType": "fastest",
        "traffic": True,
        "instructionsType": "text",
    }
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"TomTom routing error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"TomTom API unreachable: {str(e)}")

    routes = data.get("routes", [])
    if not routes:
        raise HTTPException(status_code=404, detail="No route found between the given waypoints.")

    route = routes[0]
    summary = route.get("summary", {})
    legs_raw = route.get("legs", [])

    all_points = []
    legs = []
    for leg in legs_raw:
        pts = leg.get("points", [])
        all_points.extend([[p["longitude"], p["latitude"]] for p in pts])
        leg_summary = leg.get("summary", {})
        legs.append(RouteLeg(
            distance_meters=leg_summary.get("lengthInMeters", 0),
            travel_time_seconds=leg_summary.get("travelTimeInSeconds", 0),
            summary=f"{round(leg_summary.get('lengthInMeters', 0)/1000, 1)}km · "
                    f"{round(leg_summary.get('travelTimeInSeconds', 0)/60)} min"
        ))

    geojson = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": all_points},
        "properties": {
            "distance_km": round(summary.get("lengthInMeters", 0) / 1000, 1),
            "duration_min": round(summary.get("travelTimeInSeconds", 0) / 60),
            "traffic_delay_sec": summary.get("trafficDelayInSeconds", 0),
        }
    }

    return RouteResponse(
        total_distance_meters=summary.get("lengthInMeters", 0),
        total_travel_time_seconds=summary.get("travelTimeInSeconds", 0),
        geojson=geojson,
        legs=legs
    )


# ─────────────────────────────────────────────
#  4. NEARBY POI SEARCH
# ─────────────────────────────────────────────

@app.get("/nearby-pois", response_model=List[POI], tags=["Discovery"])
async def nearby_pois(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: int = Query(2000, ge=100, le=50000),
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    url = f"{TOMTOM_BASE}/search/2/nearbySearch/.json"
    params: dict = {
        "key": key, "lat": lat, "lon": lng,
        "radius": radius, "limit": limit, "view": "Unified",
    }
    if category:
        params["categorySet"] = category

    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"TomTom POI search error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"TomTom API unreachable: {str(e)}")

    DISQUALIFIED_KEYWORDS = [
        "gym", "fitness", "yoga", "kendra", "clinic", "cure", "spa", 
        "bridge association", "society", "colony park", "physiotherapy", "hospital"
    ]
    
    pois = []
    for item in data.get("results", []):
        poi_data = item.get("poi", {})
        name = poi_data.get("name") or "Unknown"
        category = poi_data.get("categories", [""])[0] if poi_data.get("categories") else "Place"
        
        name_str = str(name).lower()
        cat_str = str(category).lower()
        if any(banned in name_str or banned in cat_str for banned in DISQUALIFIED_KEYWORDS):
            continue

        pos = item.get("position", {})
        addr = item.get("address", {})
        pois.append(POI(
            id=item.get("id", ""),
            name=name,
            category=category,
            lat=pos.get("lat", 0),
            lng=pos.get("lon", 0),
            distance_meters=item.get("dist"),
            address=addr.get("freeformAddress"),
            phone=poi_data.get("phone"),
            url=poi_data.get("url"),
        ))
    return pois


# ─────────────────────────────────────────────
#  5. FUZZY SEARCH
# ─────────────────────────────────────────────

@app.get("/search", response_model=List[POI], tags=["Discovery"])
async def fuzzy_search(
    query: str = Query(...),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius: int = Query(10000, ge=100, le=100000),
    limit: int = Query(10, ge=1, le=50),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    url = f"{TOMTOM_BASE}/search/2/search/{query}.json"
    params: dict = {"key": key, "limit": limit, "typeahead": True}
    if lat and lng:
        params.update({"lat": lat, "lon": lng, "radius": radius})

    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"TomTom search error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"TomTom API unreachable: {str(e)}")

    DISQUALIFIED_KEYWORDS = [
        "gym", "fitness", "yoga", "kendra", "clinic", "cure", "spa", 
        "bridge association", "society", "colony park", "physiotherapy", "hospital"
    ]
    
    results = []
    for item in data.get("results", []):
        poi_data = item.get("poi", {})
        addr = item.get("address", {})
        
        name = poi_data.get("name") or addr.get("freeformAddress") or "Unknown"
        category = poi_data.get("categories", [""])[0] if poi_data.get("categories") else item.get("type", "Place")
        
        name_str = str(name).lower()
        cat_str = str(category).lower()
        if any(banned in name_str or banned in cat_str for banned in DISQUALIFIED_KEYWORDS):
            continue

        pos = item.get("position", {})
        results.append(POI(
            id=item.get("id", ""),
            name=name,
            category=category,
            lat=pos.get("lat", 0),
            lng=pos.get("lon", 0),
            distance_meters=item.get("dist"),
            address=addr.get("freeformAddress"),
        ))
    return results


# ─────────────────────────────────────────────
#  6. TRIP PLAN — main endpoints
# ─────────────────────────────────────────────

async def handle_trip_plan_request(
    body: TripPlanRequest,
    client: httpx.AsyncClient,
    key: Optional[str] = None
) -> TripPlanResponse:
    target_location = (body.location or body.destination or "Lucknow").strip()
    num_days = body.days or 3
    days = max(1, min(num_days, 30))
    start_day = body.start_date or date.today()
    lang = body.language or "en"

    try:
        default_coordinates = fallback_coordinates_for(target_location)
        dest_lat = default_coordinates.lat
        dest_lng = default_coordinates.lng
        destination_name = target_location.title()

        if key:
            geocode_url = f"{TOMTOM_BASE}/search/2/geocode/{target_location}.json"
            try:
                geocode_response = await client.get(geocode_url, params={"key": key, "limit": 1, "typeahead": True}, timeout=3.0)
                if geocode_response.status_code == 200:
                    results = geocode_response.json().get("results", [])
                    if results:
                        dest = results[0]
                        dest_lat = dest.get("position", {}).get("lat", dest_lat)
                        dest_lng = dest.get("position", {}).get("lon", dest_lng)
                        destination_name = dest.get("address", {}).get("freeformAddress") or destination_name
            except Exception as e:
                logger.warning("TomTom geocoding failed for %s: %s", target_location, e)

        coordinates = Coordinates(lat=dest_lat, lng=dest_lng)

        if GROQ_API_KEY:
            try:
                groq_trip = await asyncio.wait_for(
                    generate_trip_with_groq(
                        client, destination_name, days, start_day, coordinates,
                        body.categories, body.pace, body.budget, body.travelers, body.language
                    ),
                    timeout=15.0
                )
                if groq_trip:
                    if key:
                        groq_trip.map_image_url = build_tomtom_static_map_url(dest_lat, dest_lng, zoom=10)
                    groq_trip.language = lang
                    return groq_trip
            except Exception as e:
                logger.error("Execution error or timeout (%s: %s). Returning instant fallback response.", type(e).__name__, e)

        res = await build_fallback_trip_plan(destination_name, days, start_day, client)
        res.language = lang
        return res
    except Exception as e:
        logger.error("Execution error or timeout (%s: %s). Returning instant fallback response.", type(e).__name__, e)
        res = await build_fallback_trip_plan(target_location, days, start_day, client)
        res.language = lang
        return res

@app.post("/trip-plan", response_model=TripPlanResponse, tags=["Trips"])
async def build_trip_plan_legacy(
    body: TripPlanRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    key: Optional[str] = Depends(optional_tomtom_key)
):
    try:
        return await handle_trip_plan_request(body, client, key)
    except Exception as e:
        logger.error(f"Fallback caught endpoint error: {e}")
        return await build_fallback_trip_plan(body.destination or body.location or "Lucknow", body.days or 3, body.start_date, client)

@app.post("/api/trip-plan", response_model=TripPlanResponse, tags=["Trips"])
async def build_trip_plan_api(
    body: TripPlanRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    key: Optional[str] = Depends(optional_tomtom_key)
):
    try:
        return await handle_trip_plan_request(body, client, key)
    except Exception as e:
        logger.error(f"Fallback caught endpoint error: {e}")
        return await build_fallback_trip_plan(body.destination or body.location or "Lucknow", body.days or 3, body.start_date, client)


# ─────────────────────────────────────────────
#  7. TRAFFIC INCIDENTS
# ─────────────────────────────────────────────

@app.get("/traffic", response_model=List[TrafficIncident], tags=["Traffic"])
async def get_traffic_incidents(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(5.0, ge=0.5, le=50.0),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    delta = radius_km / 111.0
    min_lat, max_lat = lat - delta, lat + delta
    min_lng, max_lng = lng - delta, lng + delta
    bbox = f"{min_lng},{min_lat},{max_lng},{max_lat}"

    url = f"{TOMTOM_BASE}/traffic/services/5/incidentDetails"
    params = {
        "key": key, "bbox": bbox,
        "fields": "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,events{description,code},startTime,endTime,from,to,length,delay,roadNumbers,timeValidity}}}",
        "language": "en-GB", "t": "1111", "timeValidityFilter": "present",
    }
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"TomTom traffic error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"TomTom API unreachable: {str(e)}")

    severity_map = {0: "Unknown", 1: "Minor", 2: "Moderate", 3: "Major", 4: "Undefined"}
    incidents = []
    for feature in data.get("incidents", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        if isinstance(coords[0], list):
            coords = coords[0]
        events = props.get("events", [{}])
        desc = events[0].get("description", "Traffic incident") if events else "Traffic incident"
        incidents.append(TrafficIncident(
            id=props.get("id", ""),
            description=f"{desc} ({props.get('from', '')} → {props.get('to', '')})",
            severity=severity_map.get(props.get("magnitudeOfDelay", 0), "Unknown"),
            lat=coords[1] if len(coords) > 1 else lat,
            lng=coords[0],
        ))
    return incidents


# ─────────────────────────────────────────────
#  8. DATABASE: Smart Event Suggestions
# ─────────────────────────────────────────────

@app.get("/trips/{trip_id}/smart-suggestions", response_model=List[EventFestival], tags=["Trips"])
async def get_smart_suggestions(
    trip_id: UUID,
    day_date: date,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    query = """
        WITH trip_waypoints AS (
            SELECT location
            FROM waypoints
            WHERE trip_id = $1::uuid AND DATE(start_time) = $2::DATE
        )
        SELECT
            e.id::text,
            e.title,
            e.event_type,
            e.start_time,
            e.end_time,
            ST_Y(e.location::geometry)::float as lat,
            ST_X(e.location::geometry)::float as lng,
            MIN(ST_DistanceSphere(e.location::geometry, w.location::geometry))::float as distance_meters
        FROM events e
        CROSS JOIN trip_waypoints w
        WHERE DATE(e.start_time) = $2::DATE
          AND ST_DWithin(e.location, w.location, 5000)
        GROUP BY e.id, e.title, e.event_type, e.start_time, e.end_time, e.location
        ORDER BY distance_meters ASC
        LIMIT 10;
    """

    async with pool.acquire() as conn:
        try:
            records = await conn.fetch(query, trip_id, day_date)
        except asyncpg.exceptions.InvalidTextRepresentationError:
            raise HTTPException(status_code=400, detail="Invalid UUID or date format.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database operational error: {str(e)}")

    return [EventFestival(**dict(record)) for record in records]


class ChatMessageRequest(BaseModel):
    message: str
    destination: Optional[str] = "Lucknow"
    history: Optional[List[Dict[str, Any]]] = None

@app.post("/api/chat", tags=["Chat"])
async def chat_with_agent(body: ChatMessageRequest):
    try:
        tools = get_chat_agent_tools()
        msg_lower = body.message.lower()
        if "search" in msg_lower or "find" in msg_lower or "market" in msg_lower or "bazaar" in msg_lower:
            result = await execute_tool_call("search_additional_venues", {"destination": body.destination or "Lucknow", "query": body.message})
            return {
                "text": f"Found venue for {body.destination}: {result['venue']['title']} ({result['venue']['category']})",
                "tool_called": "search_additional_venues",
                "result": result
            }
        elif "add" in msg_lower or "itinerary" in msg_lower:
            result = await execute_tool_call("add_venue_to_itinerary", {"destination": body.destination or "Lucknow", "venue_name": body.message})
            return {
                "text": result.get("message", "Item added to itinerary plan."),
                "tool_called": "add_venue_to_itinerary",
                "result": result
            }
        return {
            "text": f"Voya Assistant: Happy to help you explore {body.destination or 'your trip'}!",
            "tool_called": None
        }
    except Exception as e:
        logger.error("Chat agent error: %s", e)
        return {"text": f"Voya Assistant: Ready to help with your trip to {body.destination or 'Lucknow'}!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
