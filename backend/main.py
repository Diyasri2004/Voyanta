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
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")
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
    price_tier: Optional[str] = ""
    cost_approx: Optional[str] = ""

class PillarItem(BaseModel):
    id: str = Field(default_factory=lambda: "item-" + str(int(asyncio.get_event_loop().time() * 1000)))
    title: str = "Famous Venue"
    category: str = "Explorer Spot"
    specialty: str = ""
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
    specialty: Optional[str] = ""
    description: Optional[str] = ""
    address: Optional[str] = "City Center"
    serving_style: Optional[str] = None
    event_time: Optional[str] = None
    price_range: Optional[str] = ""


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
    price_tier: Optional[str] = ""
    cost_approx: Optional[str] = ""

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


# ─── Robust venue title cleaner ──────────────────────────────────────────────
# Common US state abbreviations and major destination aliases that appear
# erroneously as prefixes in AI-generated venue titles.
_STATE_ABBR = (
    r"al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn"
    r"|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt"
    r"|va|wa|wv|wi|wy|dc"
)

def clean_venue_title(title: str, destination: str = "") -> str:
    """Strip city/state prefixes and return a clean venue name.

    Handles patterns like:
      'New York, NY Historic District' -> 'Historic District'
      'Dubai, Dubai Mall'              -> 'Mall'
      'Lucknow, Lucknow Bara Imambara' -> 'Bara Imambara'
    """
    if not title:
        return "Famous Venue"
    clean = str(title).strip()

    # 1. Strip "City, ST " style prefixes (US + generic)
    clean = re.sub(
        rf"^(?:[^,]{{1,40}},\s*(?:{_STATE_ABBR})[\s,:\-]+)+",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    # 2. Strip repeated destination name (e.g. "Dubai, Dubai" or "Lucknow, Lucknow")
    if destination:
        dest_esc = re.escape(destination.strip())
        # Handle "Dest, Dest " or "Dest - " or "Dest: " repeated up to 3 times
        clean = re.sub(
            rf"^(?:{dest_esc}[\s,:\-]+){{1,3}}",
            "",
            clean,
            flags=re.IGNORECASE,
        ).strip()

    # 3. Strip leading punctuation / whitespace debris
    clean = re.sub(r"^[,\-:\s]+", "", clean).strip()

    # 4. Map any remaining generic placeholder phrases to iconic real venues
    _GENERIC_MAP = {
        "historic landmark": "Statue of Liberty & Ellis Island",
        "cultural center": "Lincoln Center for the Performing Arts",
        "city promenade": "The High Line & Hudson Yards",
        "royal monument": "Grand Central Terminal",
        "historic quarter": "Al Fahidi Historical Neighborhood",
        "downtown walk": "Dubai Fountain & Downtown Boulevard",
        "central plaza": "Times Square & Broadway District",
        "grand art museum": "The Metropolitan Museum of Art",
        "local market": "Chelsea Market & Fulton Center",
        "signature trail": "Brooklyn Bridge Promenade",
        "local temple": "Swaminarayan Akshardham Temple",
        "heritage complex": "Victoria Memorial Heritage Complex",
        "scenic viewpoint": "Top of the Rock Observation Deck",
        "royal palace": "Amber Fort & Palace Complex",
        "legendary eatery": "Peter Luger Steakhouse (Brooklyn)",
        "street food haven": "Jackson Heights Food Row, Queens",
        "rooftop dining lounge": "230 Fifth Rooftop Bar NYC",
        "skyline lounge": "Bar SixtyFive, Rainbow Room",
        "craft cocktail taproom": "Attaboy NYC (LES)",
        "vibrant social club": "Output Brooklyn",
        "serene herbal spa": "Great Jones Spa NYC",
        "sunrise meditation park": "Central Park Conservatory Garden",
        "luxury wellness pavilion": "The Spa at Mandarin Oriental NYC",
        "hidden courtyard cafe": "Caffe Reggio (Greenwich Village)",
        "scenic sunset point": "Brooklyn Promenade Sunset Overlook",
        "historic alleyway walk": "Stone Street Historic District",
        "medical emergency desk": "Bellevue Hospital NYC",
        "central transit station": "Penn Station & Grand Central",
        "tourist information center": "NYC Official Visitor Center (Midtown)",
        "traditional artisan bazaar": "Essex Market & Hester Street Fair",
        "bustling street market": "Union Square Greenmarket",
        "luxury shopping galleria": "Fifth Avenue & Rockefeller Center",
        "outdoor nature reserve": "Prospect Park & Green-Wood Cemetery",
        "riverfront kayaking": "Hudson River Park Kayak Launch",
        "scenic ridge trek": "Appalachian Trail (Bear Mountain)",
        "grand water kingdom": "Great Wolf Lodge Pocono Mountains",
        "thrill amusement world": "Six Flags Great Adventure NJ",
        "family adventure resort": "Sesame Place Philadelphia",
        "ancient heritage temple": "Ganesh Temple Flushing Queens",
        "sacred spiritual shrine": "Chinatown Buddhist Temple NYC",
        "historic royal mosque": "Islamic Cultural Center of New York",
    }
    low = clean.lower()
    for gen, real in _GENERIC_MAP.items():
        if gen in low:
            return real

    return clean if clean else str(title).strip()


# Keep legacy alias so callers of clean_stop_title still work
def clean_stop_title(title: str, destination: str = "") -> str:
    return clean_venue_title(title, destination)

def generate_google_maps_url(place_name: str, location_address: str = "", destination: str = "") -> str:
    parts = [p.strip() for p in [place_name, location_address, destination] if p and p.strip()]
    full_query = ", ".join(parts)
    encoded_query = urllib.parse.quote(full_query)
    return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

def generate_maps_link(place_name: str, destination: str) -> str:
    return generate_google_maps_url(place_name, "", destination)


CATEGORY_FALLBACK_POOL = {
    "theme_parks": [
        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1572715655204-47e297d3b6dd?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=900&auto=format&fit=crop&q=80"
    ],
    "adventures": [
        "https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1541625602330-2277a4c46182?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=900&auto=format&fit=crop&q=80"
    ],
    "sacred_temples": [
        "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1548013146-72479768bada?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1609949279531-cf48d64bed89?w=900&auto=format&fit=crop&q=80"
    ],
    "shopping": [
        "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=900&auto=format&fit=crop&q=80"
    ],
    "culinary": [
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80"
    ],
    "bars_pubs": [
        "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1572116469696-31de0f17cc34?w=900&auto=format&fit=crop&q=80"
    ],
    "wellness": [
        "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=900&auto=format&fit=crop&q=80"
    ],
    "secret_spots": [
        "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=900&auto=format&fit=crop&q=80"
    ],
    "events": [
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=900&auto=format&fit=crop&q=80"
    ],
    "essentials": [
        "https://images.unsplash.com/photo-1517649763962-0c623266010b?w=900&auto=format&fit=crop&q=80"
    ]
}

DEFAULT_FALLBACKS = [
    "https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=900&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=900&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=900&auto=format&fit=crop&q=80"
]

async def get_async_place_photo(client: httpx.AsyncClient, place_name: str, destination: str, category: str = "") -> str:
    clean_name = clean_venue_title(place_name, destination)
    
    # Step 1: Query exact venue title first to avoid generic category duplication
    exact_query = f"{clean_name} {destination}".strip()
    encoded_exact = urllib.parse.quote(exact_query)

    if UNSPLASH_ACCESS_KEY:
        try:
            url = f"https://api.unsplash.com/search/photos?page=1&query={encoded_exact}&orientation=landscape&client_id={UNSPLASH_ACCESS_KEY}&per_page=1"
            res = await client.get(url, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("results") and len(data["results"]) > 0:
                    return data["results"][0]["urls"]["regular"]
        except Exception:
            pass

    if PEXELS_API_KEY:
        try:
            url = f"https://api.pexels.com/v1/search?query={encoded_exact}&orientation=landscape&per_page=1"
            headers = {"Authorization": PEXELS_API_KEY}
            res = await client.get(url, headers=headers, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    return data["photos"][0]["src"]["large"]
        except Exception:
            pass

    # Step 2: Fallback to category + item title keyword hash to ensure unique fallback images
    cat_clean = (category or "").lower()
    pool = CATEGORY_FALLBACK_POOL.get(cat_clean, DEFAULT_FALLBACKS)
    fallback_seed = abs(hash(clean_name)) % len(pool)
    return pool[fallback_seed]


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
        "- Include a dedicated 'culinary_highlights' array containing 6 to 12 'Must-Try' iconic local food suggestions and legendary eateries famous for local dishes.\n"
        "- PRICING: Provide precise cost estimates in USD ($). For stops, use 'cost_range' (e.g. '$10 - $30 / person').\n"
        "Return ONLY a valid JSON object (no markdown, no extra text) with this exact structure:\n"
        '{"destination":"<city name>","summary":"<one sentence>","days":['
        '{"day":1,"theme":"<theme>","stops":['
        '{"title":"<famous place name>","location":"<address>","category":"<category string>","duration_minutes":<int>,"best_time":"<HH:MM AM/PM>","cost_range":"<str>"},'
        f"...{stops_per_day} stops per day]}}],"
        '"culinary_highlights":['
        '{"title":"<eatery or dish>","description":"<desc>","famous_for":"<specialty>","location":"<address>"}],'
        '"attractions":[{"title":"<real landmark>","description":"<highlights>","address":"<area>","price_range":"$10 - $20"}],'
        '"events":[{"title":"<real live event/venue>","description":"<details>","address":"<area>","event_time":"7:00 PM - 10:00 PM","price_range":"$15 - $30"}],'
        '"culinary":[{"title":"<real restaurant>","description":"<famous dishes>","address":"<area>","serving_style":"A la carte / Buffet / Street Food","price_range":"$$"}],'
        '"bars_pubs":[{"title":"<real nightlife venue>","description":"<atmosphere>","address":"<area>","price_range":"$$$"}],'
        '"wellness":[{"title":"<real spa/gym/yoga center>","description":"<facilities>","address":"<area>","price_range":"$$"}],'
        '"secret_spots":[{"title":"<real hidden gem>","description":"<local secret>","address":"<area>","price_range":"$"}],'
        '"essentials":[{"title":"<practical advice/emergency item>","description":"<numbers, hospital, transit, scam tips>","address":"<citywide>"}],'
        '"shopping":[{"title":"<real bazaar or mall>","description":"<handicrafts or brands>","address":"<area>","price_range":"$$"}],'
        '"adventures":[{"title":"<real outdoor thrill/trek>","description":"<activity details>","address":"<area>","price_range":"$$$"}],'
        '"theme_parks":[{"title":"<real amusement or water park>","description":"<attractions>","address":"<area>","price_range":"$$"}],'
        '"sacred_temples":[{"title":"<real temple, shrine, or sacred site>","description":"<spiritual heritage>","address":"<area>","price_range":"Free / Donation"}]}\n'
        "For EVERY destination requested, generate AT LEAST 25 distinct, real-world venues per pillar (275+ items total). Do NOT limit or truncate response arrays."
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
            image_url = await get_async_place_photo(client, title, destination, cat_label)
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
                specialty=getattr(item, 'specialty', '') or '',
                serving_style=getattr(item, 'serving_style', '') or '',
                event_time=getattr(item, 'event_time', '') or '',
                price_range="",
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
                title=getattr(h, 'title', '') or 'Local Eatery',
                description=getattr(h, 'description', '') or 'Authentic local culinary experience.',
                famous_for=getattr(h, 'famous_for', '') or 'Local Specialty',
                location=getattr(h, 'location', '') or destination,
                price_tier="",
                cost_approx="",
            ) for h in (getattr(ai_trip, "culinary_highlights", []) or [])
        ] or get_fallback_culinary_highlights(destination, None),
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
        "attractions": [
            "Bara Imambara & Bhool Bhulaiya", "Rumi Darwaza", "Chota Imambara", "Ambedkar Memorial Park",
            "British Residency Ruins", "Dilkusha Kothi", "Constantia House (La Martinière)", "Gomti Riverfront Promenade",
            "Chattar Manzil (Umbrella Palace)", "Shaheed Smarak Memorial", "Zoological Garden Lucknow",
            "Kukrail Picnic Spot", "Lohia Park", "Janeshwar Mishra Park", "Begum Hazrat Mahal Park",
            "Hussainabad Clock Tower", "Picture Gallery Lucknow", "State Museum Lucknow",
            "Indira Gandhi Pratishthan", "1090 Chowraha", "Tulsi Das Park", "Motijheel Park",
            "Aminabad Market Heritage Walk", "Nadan Mahal Tomb", "Saadat Ali Khan Mausoleum"
        ],
        "events": [
            "Lucknow Mahotsav Cultural Night", "Gomti Riverfront Light Show", "Hazratganj Live Music Evenings",
            "Lucknow Literary Festival", "Chikan Craft Expo", "Awadhi Food Festival", "Kite Festival at Janeshwar Park",
            "Lucknow Marathon", "Diwali Mela Aminabad", "Eid Market Chowk", "Raat Ki Raani Night Bazaar",
            "Lucknow Drama Festival", "Classical Music Baithak (Bhatkhande College)", "Vintage Car Rally",
            "Jazz in the Residency", "Heritage Walk Night Edition", "Photowalk Ganga-Jamuni Tehzeeb",
            "Filmfare Short Film Fest", "Saraswati Puja Procession", "Sufi Evening at Dargah",
            "Rang Mahal Poetry Fest", "Lakhnaupati Craft Fair", "Navratri Garba Night",
            "Republic Day Parade (Vidhan Sabha)", "Holi Mela at Eco Garden"
        ],
        "culinary": [
            "Tunday Kababi (Aminabad)", "Dastarkhwan (Hazratganj)", "Prakash Ki Kulfi", "Sharma Tea Stall",
            "Royal Cafe (Hazratganj)", "Wahid Biryani", "Idris Ki Biryani", "Moti Mahal Restaurant",
            "Naushijaan Restaurant", "Shukla Chaat Bhandar", "Bajpai Kachori Bhandar", "Radhey Lal Mithai Wale",
            "Raja Thandai Shop", "Chikan Gali Chai Corner", "Biryani Paradise", "Dum Pukht at ITC Kohinoor",
            "The Rolling Fork (Gomti Nagar)", "Oudhyana Restaurant", "Mamu Ki Dukan (Kulcha-Nihari)",
            "Lakhnaupati Lassi Centre", "Gopal Ji Sev Puri", "Chotewale Ki Lassi",
            "Aminabad Faloodewala", "Nazakat Sweets", "Rahim Chaat Corner"
        ],
        "bars_pubs": [
            "Sky Glasshouse", "The Flying Saucer Cafe", "Vintageland Lucknow", "Mocobos Bar",
            "Score Sports Bar (Lulu Mall)", "The Social (Gomti Nagar)", "Molecule Air Bar Lucknow",
            "Urban Pind Cafe", "The Beer Cafe (Hazratganj)", "Guppy by Ai", "Bada Imambara Rooftop Cafe",
            "Lord of the Drinks", "Sago Cafe", "Café Tamasha", "Kitchen Confidential",
            "The Grub Club", "Spice Route Bistro", "Olive Kitchen & Bar", "The Glass Onion Gastropub",
            "Brewed Awakenings", "Wok N Barrel", "Sunset Terrace Cafe", "Lakeview Club & Bar",
            "Azrak (Taj Hotel)", "Sheesh Mahal Lounge"
        ],
        "wellness": [
            "Gomti Riverfront Yoga Park", "Janasheen Herbal Spa", "Lohia Park Morning Walk Trail",
            "Swaraj Kund Wellness Centre", "Ayurvedagram Lucknow", "Nirogam Panchakarma Centre",
            "O2 Spa (Lulu Mall)", "Tattva Spa (Taj)", "Ananda Meditation Hall (Gomti Nagar)",
            "Sivananda Yoga Vedanta Centre", "Sri Sri Ravi Shankar Art of Living", "Zen Wellness Studio",
            "Naturoville Lucknow", "Kaya Skin Clinic (Hazratganj)", "VLCC Wellness (Hazratganj)",
            "Janeshwar Mishra Park Jogging Track", "Ekana Sports Complex Gym", "Indira Canal Riverside Walk",
            "Lotus Foot Reflexology", "Purple Orchid Salon & Spa", "Rejuve Wellness Studio",
            "Forest Healing Walk (Kukrail)", "Sunrise Meditation at Buddha Vihar",
            "Riverside Pranayam at Gomti Ghat", "District Ayurveda Clinic Charbagh"
        ],
        "secret_spots": [
            "Residency Historical Gardens", "Kudia Ghat Sunset Point", "Chattar Manzil Complex",
            "Qaiserbagh Palace Ruins", "Khursheed Manzil Rooftop View", "Dilkusha Garden Secret Corner",
            "Constantia Library (La Martinière)", "Hidden Mosque of Begum Hazrat Mahal",
            "Jhandewalan Temple Nada", "Old Gol Darwaza", "Rumi Darwaza Night View",
            "Hazratganj Colonial-Era Tunnels (DRDO Quarter)", "Naubatkhana Roof Gallery",
            "Macchi Bhawan Ruins", "Shah Najaf Imambara Gardens",
            "Silent Garden of Saadat Ali Khan Mausoleum", "Old Qaiserbagh Alley",
            "Baan Ganga Ghaat (Gomti)", "Neem Tree Courtyard (Chowk Walled City)",
            "Rooftop View from Bada Imambara", "Hidden Bazaar Lane (Nakhas)",
            "1947 Partition Street Art Wall", "Aaish Mahal Terrace",
            "Forgotten Gardens of Bibiyapur Kothi", "Old Akbari Darwaza Arch"
        ],
        "essentials": [
            "Charbagh Railway Station Hub", "Chowk Medical Store", "Hazratganj Tourist Information Center",
            "Amausi International Airport", "King George's Medical University (KGMU) Emergency",
            "Lucknow Metro (Blue Line) Central Stations", "UP Tourism Office Hazratganj",
            "Cyber City ATM Hub (Gomti Nagar)", "Lucknow Police Helpline (112) Control Room",
            "SBI Central Branch (Hazratganj)", "Thomas Cook Forex (Hazratganj)", "HDFC ATM Cluster (Mall Road)",
            "Lucknow Municipal Corporation Help Desk", "Alambagh Bus Terminal",
            "Vishnupuri Petrol Pump (24hr)", "Gomti Nagar Post Office",
            "Pharmacy Hub (Hazratganj Medical Market)", "HealthLine Diagnostic Centre (Indira Nagar)",
            "Rapido / Ola / Auto Booking Hub Charbagh", "Luggage Storage Charbagh Station",
            "Union Bank Currency Exchange", "DHL Courier (Gomti Nagar)",
            "Cybercafe & Print Hub (Aminabad)", "Government Hospital Civil Lines",
            "SIM Card Centre (Airtel, Jio — Charbagh)"
        ],
        "shopping": [
            "Hazratganj Market", "Aminabad Street Bazaar", "Chowk Chikan Embroidery Market", "Phoenix Palassio Mall",
            "Lulu Mall Lucknow", "Fun Republic Mall", "Janpath Market Lucknow",
            "Nakhas Sunday Flea Market", "Novelty Cinema Market", "Sadar Bazaar Wholesale Lane",
            "Chowk Zardozi & Ittarwali Gali", "Latouche Road Cloth Market",
            "Akbar Nagar Bangles & Jewellery Lane", "Kapoorthala Complex Market",
            "Gomti Nagar Galleria", "Wave Mall Lucknow", "Shalimar Mall",
            "Vivaan Fashion Street", "Naza Market Chowk", "Station Road Luggage Bazaar",
            "Naka Hindola Pottery Market", "Nakkhas Book Bazar",
            "Rumi Gate Antiques Lane", "Leathercraft Market (Charbagh)", "Khan Market Lucknow (Gomti Nagar)"
        ],
        "adventures": [
            "Kukrail Reserve Forest & Gharial Rehabilitation Center", "Gomti Riverfront Kayaking & Paddle Boating",
            "Janeshwar Mishra Park Cycling Track", "Lucknow Golf Club 18-Hole Green",
            "Nilansh Theme Park Zip Line & Rope Course", "Gomti Riverfront Morning Speedboat Cruise",
            "Anandi Water Park Extreme Slides", "Dilkusha Kothi Open-Air Photography Walk",
            "Nawabganj Bird Sanctuary Wildlife Trail", "Lucknow Flying Club Glider Aviation",
            "Kukrail Nature Walk & Trekking Circuit", "Gomti Riverfront Open Cycling Expedition",
            "Dream World Resort Paintball Arena", "Amrapali Water Park Wave Pool Thrills",
            "Bakhira Bird Sanctuary Eco Tour", "Sikandar Bagh Historical Heritage Trail",
            "Mahatama Gandhi Park Outdoor Exercise Zone", "Kukrail Deer Park Safari Trail",
            "PGI Open Green Jogging & Running Track", "Riverfront Night Stargazing Point",
            "Colvin Taluqdars Ground Archery Club", "Gomti Riverfront Rowing Club",
            "Gyaneshwar Mishra Park Boating Deck", "Lucknow Zoo Wilderness Walk", "Chinat Eco Resort Adventure Obstacle Course"
        ],
        "theme_parks": [
            "Anandi Water Park", "Dream World Amusement Park", "Nilansh Theme Resort & Water Park",
            "Funky Monkey Play Zone (Lulu Mall)", "Kingdom of Dreams Lucknow (EXPO Center)",
            "Funstation Amusement (Fun Republic Mall)", "VR World Lucknow",
            "Little Champs Kids Zone", "Sky Karting Track",
            "Kiddie Land Amusement (Hazratganj)", "Shooting Star Game Zone",
            "Laser Land Arcade", "Jump Zone Trampoline Park",
            "Infinity VR Gaming Lounge", "Fantasy World Park (Rae Bareli Rd)",
            "Aquamagica Day Trip", "Wet World Water Park", "Kidszone at Wave Mall",
            "Xperience Learning Park", "Mini Train Ride (Janeshwar Park)",
            "Family Arcade at Phoenix Palassio", "Roller Skate Arena",
            "Wacky World Indoor Play", "Kidzania Lucknow Experience", "Aapno Ghar Resort Park"
        ]
    },
    "dubai": {
        "sacred_temples": [
            "Jumeirah Mosque", "Grand Mosque Dubai", "Shiva Temple Dubai (Al Qusais)",
            "Guru Nanak Darbar Sikh Gurdwara", "St. Mary's Catholic Church Dubai",
            "Holy Trinity Church Dubai", "Dubai Hindu Temple (BurDubai)",
            "Al Farooq Omar Bin Al Khattab Mosque", "Iranian Mosque (Bastakiya)",
            "Sheikh Zayed Road Prayer Complex", "Bur Dubai Sikh Prayer Hall",
            "Blue Mosque (Al Khayat)", "Al Ittihad Mosque", "Deira Grand Mosque",
            "Sikh Heritage Temple (Meena Bazaar)", "National Church of Dubai",
            "St. Thomas Orthodox Church", "Al Noor Mosque Sharjah (Day Trip)",
            "Mandir Lane Bur Dubai", "Islamic Museum Dubai",
            "Zabeel Mosque", "Rashidiya Prayer Square",
            "BAPS Swaminarayan Temple (Abu Dhabi – Day Trip)",
            "Dubai Hatta Mountain Mosque", "Qusais Mosque Heritage Complex"
        ],
        "attractions": [
            "Burj Khalifa & At the Top Observation Deck", "Dubai Mall & Aquarium", "Palm Jumeirah & Atlantis",
            "Desert Safari & Dune Bashing", "Dubai Frame", "Museum of the Future",
            "Al Fahidi Historical Neighborhood", "Burj Al Arab Hotel Tour", "Dubai Fountain Show",
            "Global Village Dubai", "Dubai Creek & Abra Ride", "Gold Souk Deira",
            "Spice Souk Deira", "The Dubai Garden Glow", "Dubai Miracle Garden",
            "Ski Dubai (Mall of the Emirates)", "Aquaventure Waterpark", "Wild Wadi Water Park",
            "La Mer Beach", "JBR The Walk", "Dubai Creek Golf & Yacht Club",
            "Expo City Dubai", "Dubai Design District (d3)", "Alserkal Avenue",
            "Hatta Heritage Village"
        ],
        "events": [
            "Dubai Shopping Festival", "Dubai Food Festival", "Global Village Shows",
            "Dubai Jazz Festival", "Art Dubai Fair", "Dubai Airshow",
            "Emirates Airline Festival of Literature", "Dubai Fitness Challenge",
            "Eid Fireworks Spectacle (Creek & Burj)", "Dubai World Cup Horse Racing",
            "Dubai Expo Legacy Events", "Diwali in Dubai (GGICO)", "Dubai Rugby 7s",
            "Dubai International Film Festival", "Dubai Opera Gala Night",
            "Formula E Street Race (ad hoc)", "Sotheby's Dubai Auction",
            "Dubai Art Season", "Bastakiya Night Market", "Ramadan Night Souk",
            "Ripe Market (Al Safa Park)", "Dubai Garden Glow Opening",
            "Sunset Yoga at Jumeirah Beach", "Dubai Fitness Bootcamp", "Hatta Mountain Trail Race"
        ],
        "culinary": [
            "Al Hadheetha Restaurant (Creek)", "Logma (Boxpark JMR)", "Bu Qtair Seafood (Jumeirah)",
            "Operation Falafel", "Ravi Restaurant (Satwa)", "Zuma Dubai (DIFC)",
            "Nobu Dubai (Atlantis)", "Pierchic (Al Qasr)", "Al Dawaar Revolving Restaurant (Hyatt)",
            "Ossiano Underwater Restaurant", "COYA Dubai", "Gaucho DIFC",
            "Baker & Spice (Souk Al Bahar)", "Wild & The Moon", "Tom & Serg (Al Quoz)",
            "The Sum of Us", "BOCA Dubai", "Asil (Jumeirah Al Naseem)",
            "Al Mallah Lebanese Wrap (Satwa)", "Arabian Tea House (Al Fahidi)",
            "Dubai Creek Fish Fry", "Mama'esh (Al Serkal)", "Reform Social & Grill",
            "Eataly Dubai (Mall of the Emirates)", "Casa de Tapas"
        ],
        "bars_pubs": [
            "Siddharta Lounge (Grosvenor House)", "Vault Dubai (JW Marriott Marquis)",
            "The Rooftop (Arabian Court)", "Iris Dubai (Meydan)",
            "Lock Stock & Barrel (JBR)", "McGettigan's (JLT)",
            "Asia Asia (Dubai Marina)", "Stereo Arcade Bar",
            "White Dubai (Meydan)", "Soho Garden (Meydan)",
            "Hyde Dubai (Meydan)", "BASE Dubai (d3)",
            "Q43 Sky Bar (Media One Hotel)", "Cé La Vi (Address Sky View)",
            "Bahri Bar (One&Only The Palm)", "The Agency Wine Bar (DIFC)",
            "Neos Bar (Address Downtown)", "Barfly by Buddha Bar",
            "Level 43 Sky Lounge (Four Points)", "The Penthouse (Five Palm Jumeirah)",
            "Iris Meydan", "Mahiki Dubai (Jumeirah)",
            "The Boston Bar (Jumeirah Beach Hotel)", "Farzi Café Dubai", "Long's Bar (Towers Rotana)"
        ],
        "wellness": [
            "Talise Ottoman Spa (Jumeirah Zabeel)", "Amara Spa (Park Hyatt)",
            "One&Only Spa (The Palm)", "ESPA at Atlantis",
            "Sofitel Spa (Jumeirah Beach Residence)", "Anantara Spa Dubai",
            "Zen Yoga (JLT)", "The Hundred Wellness Centre (Jumeirah)",
            "Bodyology Medical Centre", "Fitnation Dubai Marina",
            "GymNation JLT", "Prestige Boot Camp",
            "Shuiqi Spa (Atlantis The Palm)", "Hatta Wadi Paddle SUP Sessions",
            "Morning Sunrise Yoga (JBR Beach)", "Bliss Spa (Jumeirah)",
            "Balance Wellness Studio (Business Bay)", "Elixir Spa (Sheraton)",
            "Kielo Spa", "Al Badia Golf Club Wellness & Sauna",
            "The Spa at Burj Al Arab", "Faern Spa DIFC",
            "Hammam Al Ándalus Dubai", "Raffles Spa", "Softouch Ayurveda & Spa"
        ],
        "secret_spots": [
            "Al Qudra Cycling Track & Love Lakes", "Alserkal Avenue Street Art Walk",
            "Ras Al Khor Wildlife Sanctuary (Flamingos)", "Dubai Creek Fishing Dhow at Dawn",
            "Hatta Rock Pools", "Al Fahidi Rooftop View (Wind Tower)",
            "Bastakiya Perfume Alley", "Naif Souk Hidden Tailors Lane",
            "Mushrif Park Secret Picnic Meadow", "Al Mamzar Beach Sunrise",
            "Camel Race Track (Al Marmoom)", "Jebel Ali Bird Sanctuary",
            "The Lighthouse Dubai Museum (Old)", "Zabeel Park Hidden Pond",
            "Friday Backpackers Brunch (Satwa)", "Al Manara Mosque Evening Walk",
            "Old Dubai Dhow Yard (Garhoud)", "Quoz Creative Market",
            "Tashkeel Art Studio", "Al Seef Heritage Walk at Night",
            "Meena Bazaar Old Textile Lane", "XVA Art Hotel Courtyard",
            "Deira Heritage Trail Map Walk", "Spice Souk Alleyway Wholesale",
            "Desert Stargazing at Al Qudra"
        ],
        "essentials": [
            "Dubai International Airport (DXB) — Terminal 3", "Dubai Metro Red Line Stations",
            "Al Barsha Health Centre (24hr)", "Aster Hospital (Al Qusais)",
            "Emirates NBD ATM (Ubiquitous)", "Western Union (Deira)",
            "RTA Bus Stop Network", "Dubai Taxi (Careem/Uber Hub)",
            "UAE Visa on Arrival Desk (DXB)", "Al Futtaim Exchange (DAFZA)",
            "Tom's Currency Exchange (DIFC)", "Pharmacies: Aster & Life Pharmacy",
            "Dubai Police Non-Emergency: 901", "Ambulance: 998",
            "Tourist SIM: du & Etisalat Airport Desk", "Dubai Frame Visitor Services",
            "Dubai Tourism Kiosk (Dubai Mall)", "Post Office — Karama",
            "Luggage Storage (DXB Terminal 3)", "24hr Petrol (ENOC Stations)",
            "Geant Hypermarket (Ibn Battuta)", "Al Aseel Laundry (Deira)",
            "DHL Express (Jebel Ali)", "Al Hudaiba Post Office",
            "Community Medical Centre Jumeirah"
        ],
        "shopping": [
            "Dubai Mall", "Mall of the Emirates", "Ibn Battuta Mall",
            "Gold Souk Deira", "Spice Souk Deira", "Perfume Souk (Deira)",
            "City Walk Dubai", "Boxpark JMR", "The Beach at JBR",
            "Souk Al Bahar (Downtown)", "Souk Madinat Jumeirah",
            "Mirdif City Centre", "Deira City Centre", "Al Seef Heritage Market",
            "Mercato Mall", "Karama Shopping Centre", "BurJuman Mall",
            "Silicon Central", "Dubai Outlet Mall", "Dragon Mart 2",
            "Alserkal Avenue Design Shops", "Ripe Market (Al Safa)",
            "Friday Market (Fujairah Day Trip)", "Wafi Mall", "The Pointe (Palm)"
        ],
        "adventures": [
            "Desert Safari & Quad Biking (Al Marmoom)", "Hatta Mountain Trekking",
            "Skydiving over The Palm (Skydive Dubai)", "Deep-Sea Fishing Charter (Marina)",
            "Kayaking at Hatta Wadi Hub", "Hot Air Balloon over Desert",
            "Aquaventure Waterpark Extreme Slides", "Flyboarding at JBR",
            "Parasailing Dubai Marina", "Seaplane Tour (Seawings)",
            "Dune Bashing Safari (Lahbab Desert)", "Sandboarding Al Qudra",
            "Rock Climbing Hatta", "Night Cycling Al Qudra Track",
            "Dubai Autodrome Track Day", "Indoor Ski Lessons (Ski Dubai)",
            "Camel Riding Al Marmoom", "Yacht Charter Dubai Marina",
            "Jet Ski Dubai Creek", "Sunset Horse Riding (Al Jaddaf)",
            "ATV Desert Adventure", "Wadi Bashing (4x4 Hatta)",
            "Zipline at Hatta", "Indoor Skydiving (iFly Dubai)",
            "Canopy Walk Dubai Jungle (Frame)"
        ],
        "theme_parks": [
            "IMG Worlds of Adventure", "Legoland Dubai (Dubai Parks)",
            "Motiongate Dubai", "Bollywood Parks Dubai",
            "Riverland Dubai (Theme Park Resort)", "Wild Wadi Water Park",
            "Aquaventure Waterpark (Atlantis)", "Global Village",
            "VR Park (Dubai Mall)", "KidZania Dubai (Dubai Mall)",
            "Dubai Ice Rink", "Ski Dubai (Mall of the Emirates)",
            "Hub Zero (City Walk)", "Laguna Waterpark (La Mer)",
            "Clip 'n Climb Dubai", "Bounce Trampoline Park (Dubai)",
            "iFly Indoor Skydiving", "Play DXB (Festival City)",
            "Candy Land Indoor (Ibn Battuta)", "Reel Cinemas XD",
            "Virtuocity Game Zone (Festival City)", "Toyz World Park",
            "Little Explorers (Dubai Mall)", "Fun Works (JBR)",
            "Sega Republic at Dubai Mall"
        ]
    },
    "mumbai": {
        "sacred_temples": [
            "Siddhivinayak Temple (Prabhadevi)", "Mahalakshmi Temple", "Mumba Devi Temple (Zaveri Bazaar)",
            "ISKCON Juhu Temple", "Haji Ali Dargah", "Mount Mary Basilica (Bandra)",
            "St. Thomas Cathedral (Fort)", "Afghan Church (Colaba)", "Global Vipassana Pagoda",
            "Banganga Tank & Temple Complex", "Shri Swaminarayan Mandir (Dadar)",
            "Walkeshwar Temple", "Ambaji Temple (Bhuleshwar)",
            "Kanheri Buddhist Caves (SGNP)", "Elephanta Island Caves",
            "Jama Masjid (Mohammad Ali Rd)", "Jain Temple (Malabar Hill)",
            "Shree Babulnath Mandir", "Shri Saibaba Temple (Dadar)",
            "Parsi Fire Temple (Cusrow Baug)", "Sacred Heart Church (Santacruz)",
            "Ganesh Temple Siddhivinayak Lane", "Gaondevi Mandir (Dharavi)",
            "Sri Mahalasa Narayani Temple (Vikhroli)", "Vivekananda Rock Memorial (Day Trip Shirdi)"
        ],
        "attractions": [
            "Gateway of India", "Chhatrapati Shivaji Maharaj Terminus (CST)", "Marine Drive (Queen's Necklace)",
            "Elephanta Caves (Boat Ride)", "Bandra-Worli Sea Link", "Juhu Beach",
            "Dharavi Slum Tour", "Chhatrapati Shivaji Museum", "Colaba Causeway",
            "Sanjay Gandhi National Park", "Hanging Gardens (Malabar Hill)", "Crawford Market",
            "Film City Studio Tour (Goregaon)", "Bandra Fort (Castella de Aguada)",
            "Kamala Nehru Park", "Haji Ali Dargah Marine Walk", "Sassoon Dock (Fish Market)",
            "RBI Monetary Museum (Fort)", "Nehru Science Centre", "National Gallery of Modern Art",
            "Prithvi Theatre (Juhu)", "Dhobhi Ghat", "Pherozeshah Mehta Road Heritage Walk",
            "Wankehde Stadium", "Worli Village Fishing Pier"
        ],
        "culinary": [
            "Trishna Restaurant (Fort)", "Khyber (Kala Ghoda)", "Olympia Coffee House (Colaba)",
            "Britannia & Co (Ballard Estate)", "Irani Café Kyani & Co", "Leopold Café (Colaba)",
            "Café Mondegar", "Konkan Café (Taj Vivanta)", "Mahesh Lunch Home (Fort)",
            "Sardar's Pav Bhaji (Tardeo)", "Vada Pav — Ashok Stall Dadar",
            "Lucky Restaurant (Bandra)", "Pali Bhavan (Bandra)",
            "Bademiya (Colaba)", "Shree Thaker Bhojanalaya (Dadar)",
            "Neel (Taj Lands End)", "The Table (Colaba)", "O Pedro (BKC)",
            "Bastian (Bandra)", "SodaBottleOpenerWala (Linking Road)",
            "Chowpatty Bhel Puri Stalls", "Swati Snacks (Tardeo)",
            "Rajdhani Thali (Andheri)", "Juhu Chowpatty Street Food",
            "Cream Centre (Charni Road)"
        ],
        "bars_pubs": [
            "Aer Sky Bar (Four Seasons)", "Asilo (St. Regis)",
            "Social (Colaba & Andheri)", "The Bar at The Taj Mahal Palace",
            "Harbour Bar (Taj)", "Woodside Inn (Colaba)",
            "Bar Stock Exchange (Lower Parel)", "Bonobo (Bandra)",
            "Subko (Bandra)", "Howrah Bridge (Kamala Mills)",
            "Colaba Social", "Hoppipola (Andheri)",
            "The Classique Club (Juhu)", "Todi Mill Social (Lower Parel)",
            "Lord of the Drinks (Lower Parel)", "Pisco Bar (Kala Ghoda)",
            "Khar Social", "Masala Library Bar Lounge (BKC)",
            "The Finch (Bandra)", "Over the Moon Brewpub (Thane)",
            "White Owl Brewery (Lower Parel)", "Gateway Brewing Bar (Andheri)",
            "Wild East Brewery", "Doolally Taproom", "Independence Brewing Company"
        ],
        "wellness": [
            "Spa by JW (JW Marriott Juhu)", "The Retreat (Amanjiwo)",
            "Palms Spa (The Leela Mumbai)", "Tattva Spa (Vivanta)",
            "O2 Spa (Phoenix Marketcity)", "Ananda Spa Colaba",
            "Sohum Spa (Powai)", "Atmantan Wellness (Pune Day Trip)",
            "Global Vipassana Pagoda Meditation", "Iyengar Yoga Centre (Ramamani)",
            "Marine Drive Morning Walk & Yoga", "Bandra Bandstand Sunrise Stretching",
            "Matunga Ayurvedic Clinic", "Nirogam Panchakarma Mumbai",
            "Kaya Skin Clinic (Powai)", "Naturalis Spa (Andheri)",
            "Zen Wellness (Khar)", "24/7 Fitness World (BKC)",
            "Gold's Gym (Andheri)", "Celebrity Fitness (Lower Parel)",
            "Cult.Fit (Multiple)", "FitHub (Bandra)",
            "Pilates Studio (Pali Hill)", "Muay Thai Academy (Khar)",
            "Crossfit Colaba"
        ],
        "secret_spots": [
            "Worli Koliwada Fishing Village", "Chor Bazaar Hidden Antique Lane",
            "Sassoon Dock Pre-Dawn Fish Auction", "Vasai Fort (Day Trip)",
            "Banganga Tank Sunrise", "Khau Galli (Dadar Station)",
            "Mahim Causeway Secret Bakery", "Portuguese Quarter (Bandra)",
            "Bandra Station Graffiti Wall", "Crawford Market Clock Tower",
            "Cuffe Parade Sea-Facing Bench Row", "Khotachiwadi Heritage Village (Girgaon)",
            "Mill Workers Memorial (Kamala Mills)", "Old Parsi Cemetery (Lalbaug)",
            "Street Art Alley (Dharavi Camp)", "MBPT Dockyard Viewing Pier",
            "Hidden Cafe: Prithvi Courtyard Canteen", "Bandra Reclamation Bridge Walk",
            "Kabutar Khana at CST", "Horniman Circle Garden",
            "Chor Bazaar Vintage Furniture District", "Taddeo Ghost Church Garden",
            "Colaba Back Lane Vintage Bookshops", "Mahakali Caves (Andheri)",
            "Mount Mary Steps View (Bandra)"
        ],
        "essentials": [
            "Chhatrapati Shivaji International Airport (BOM)", "CST Railway Station Hub",
            "BEST Bus Terminus Colaba", "Mumbai Metro Line 1 Stations",
            "KEM Hospital Emergency (Parel)", "Wockhardt Hospital (South Mumbai)",
            "Medical Stores: Apollo Pharmacy (Multiple)", "MRT Auto Rickshaw Hub",
            "Cab: Ola / Uber (Nationwide)", "SBI ATM (Across City)",
            "Thomas Cook Forex (Nariman Point)", "Mumbai Police Helpline: 100",
            "Fire Brigade: 101", "MMRDA Tourist Info (BKC)",
            "Maharashtra Tourism Office (Fort)", "Western Union (Zaveri Bazaar)",
            "Travellers' Lounge (T2 International)", "Post Office: General Post (Fort)",
            "Foreign Exchange (Nadir Exchange — Colaba)", "Luggage Storage (CST)",
            "Simcard: Jio / Airtel (Airport)", "24hr Petrol (HP/BPCL stations)",
            "Ambulance: 108", "Doctors on Call App (Mumbai)",
            "DHL Express (Lower Parel)"
        ],
        "shopping": [
            "Colaba Causeway Street Market", "Linking Road (Bandra)", "Hill Road Bandra",
            "Crawford Market (Mahatma Jyotiba Phule)", "Fashion Street (MG Road)",
            "Chor Bazaar Antiques", "Zaveri Bazaar Gold & Jewellery",
            "Dharavi Leather & Pottery Lane", "Phoenix Palladium (Lower Parel)",
            "High Street Phoenix", "Palladium Mall", "R City Mall (Ghatkopar)",
            "Infiniti Mall (Malad)", "Inorbit Mall (Malad)",
            "Atria Mall (Worli)", "Jio World Drive (BKC)",
            "Kurla Market", "Commercial Street (Grant Road)",
            "Dadar Flower Market", "Mangaldas Market (Lohar Chawl)",
            "Null Bazaar Wholesale Lane", "Matunga Udipi Lane",
            "Nagdevi Street Electronics", "TV Industrial Estate (Andheri)",
            "Bhuleshwar Bangles & Puja Items"
        ],
        "adventures": [
            "Elephanta Island Boat Trek", "Sanjay Gandhi National Park Panther Trail",
            "Malshej Ghat Waterfall Trek (Monsoon)", "Lonavala Bhushi Dam Walk",
            "Mumbai Harbour Sailboat Cruise", "Juhu Beach Paragliding",
            "Aksa Beach Kayaking", "Marine Drive Sunrise Cycling",
            "Bandra Fort Rock Rappelling", "Rajmachi Fort Trek (Day Trip)",
            "Karnala Fort Trek", "Matheran Heritage Walk (Train Ride)",
            "Hot Air Balloon Imagica", "Scuba Diving Tarkarli (Trip)",
            "Bandra Bandstand Frisbee & Sport", "Vasai Fort Cycling Rally",
            "Mumbai Harbour Speed Boat Ride", "Versova Sunset Fishing Ride",
            "Snorkelling at Harnai Beach (Trip)", "Running at Mahalaxmi Racecourse",
            "Laser Tag (Phoenix Palladium)", "Bowling (AMF Bowling)",
            "Rock Climbing (NSCI Worli)", "Skating at Andheri Sports Complex",
            "Mumbai Monsoon Hike Club"
        ],
        "theme_parks": [
            "Imagica Theme Park (Khopoli)", "Aquamagica Water Park (Khopoli)",
            "Essel World (Gorai)", "Water Kingdom (Gorai)",
            "Nicco Park Mumbai", "Sentosa Park Kalyan",
            "Fun Republic (Andheri)", "PVR Director's Cut (BKC)",
            "VR Gaming Zone (Phoenix Palladium)", "Smaaash Entertainment (Lower Parel)",
            "KidZee Play Zone (Powai)", "Little Planet (Thane)",
            "Play Nation (Inorbit Malad)", "Ghatkopar Kannamwar Park",
            "Mahalaxmi Racecourse Events", "Juhu Mini Water Park",
            "Snow World Mumbai (Upcoming)", "Jump Zone (Andheri)",
            "Clip 'n Climb (Powai)", "Lasertag Zone (Infinity Mall)",
            "Indoor Ski Simulator", "Bouldering Wall (Khar Gymkhana)",
            "Timezone Arcade (R City Mall)", "Castle Adventure Play (Mulund)",
            "Kidzania Mumbai (Kurla)"
        ]
    },
    "new york": {
        "sacred_temples": [
            "St. Patrick's Cathedral (Midtown)", "Riverside Church (Morningside Heights)",
            "Ganesh Temple (Flushing, Queens)", "Jain Center of America (Elmhurst)",
            "Islamic Cultural Center of New York", "Temple Emanu-El (Upper East Side)",
            "Chinatown Buddhist Temple (Mahayana)", "Cathedral of St. John the Divine",
            "Baha'i Center Manhattan", "Sri Maha Vallabha Ganapati Devasthanam (Staten Island)",
            "Zen Mountain Monastery (Catskills)", "Holy Trinity Orthodox Cathedral",
            "Sikh Cultural Society (Richmond Hill)", "Church of the Intercession (Inwood)",
            "First Presbyterian Church (West Village)", "Greater Allen Cathedral (Jamaica, Queens)",
            "Abyssinian Baptist Church (Harlem)", "Temple Israel of the City of New York",
            "St. George Ukrainian Catholic Church", "Congregation Beth Elohim (Brooklyn)",
            "Shree Swaminarayan Temple (Flushing)", "Al-Aqsa Islamic Society (Brooklyn)",
            "Church of the Holy Apostles (Chelsea)", "Eldridge Street Synagogue (Lower East Side)",
            "Corpus Christi Church (Morningside)"
        ],
        "attractions": [
            "Statue of Liberty & Ellis Island", "Central Park", "Empire State Building",
            "Brooklyn Bridge", "Times Square & Broadway", "Metropolitan Museum of Art",
            "One World Trade Center & 9/11 Memorial", "High Line Park", "The MoMA",
            "Rockefeller Center & Top of the Rock", "Brooklyn Botanic Garden",
            "American Museum of Natural History", "Whitney Museum of American Art",
            "Grand Central Terminal", "Coney Island Boardwalk", "Governors Island",
            "The Oculus (Westfield)", "Chelsea Market", "Little Italy & Chinatown Walk",
            "Washington Square Park", "Harlem Cultural District", "South Street Seaport",
            "Intrepid Sea, Air & Space Museum", "New York Botanical Garden (Bronx)",
            "Flatiron Building"
        ],
        "culinary": [
            "Peter Luger Steakhouse (Brooklyn)", "Katz's Delicatessen (LES)",
            "Di Fara Pizza (Midwood)", "Shake Shack (Madison Square Park)",
            "Le Bernardin (Midtown)", "Eleven Madison Park",
            "Balthazar (SoHo)", "Carbone (West Village)", "Via Carota",
            "Lucali Pizza (Carroll Gardens)", "Russ & Daughters (LES)",
            "Blue Ribbon Brasserie", "Smorgasburg (Williamsburg)",
            "The Halal Guys (Midtown)", "Joe's Pizza (West Village)",
            "Xi'an Famous Foods (Flushing)", "Ivan Ramen (LES)",
            "Momofuku Noodle Bar", "Roberta's Pizza (Bushwick)",
            "Dough Donuts (Flatiron)", "Eataly (Flatiron)",
            "Dirt Candy (LES)", "Gramercy Tavern",
            "The Spotted Pig (West Village)", "Dominique Ansel Bakery (SoHo)"
        ],
        "events": [
            "NYC Marathon (November)", "New York Fashion Week",
            "Tribeca Film Festival", "NYC Pride March",
            "Macy's Thanksgiving Day Parade", "New Year's Eve Ball Drop (Times Square)",
            "New York Comic Con", "Governors Ball Music Festival",
            "SummerStage in Central Park", "Smorgasburg Food Market (Saturdays)",
            "New York International Auto Show", "Brooklyn 9 Arts Festival",
            "US Open Tennis (Flushing)", "Harlem Jazz Weekend",
            "The Armory Show (Art Fair)", "New York Botanical Garden Orchid Show",
            "Coney Island Mermaid Parade", "Bryant Park Winter Village",
            "Shakespeare in the Park", "BRIC Celebrate Brooklyn! Festival",
            "Village Halloween Parade", "Brooklyn Book Festival",
            "NYC Restaurant Week", "Times Square New Year Countdown",
            "Atlantic Antic (Brooklyn Street Fair)"
        ],
        "bars_pubs": [
            "Attaboy NYC (Lower East Side)", "Death & Co (East Village)",
            "Please Don't Tell (PDT) — Speakeasy", "Employees Only (West Village)",
            "The Dead Rabbit (Financial District)", "Milk & Honey (Revisited)",
            "Bar Goto (Lower East Side)", "Amor y Amargo",
            "Dante (West Village)", "Overstory (Financial District — 64th Floor)",
            "The NoMad Bar", "Brooklyn Brewery (Williamsburg)",
            "Other Half Brewing (Carroll Gardens)", "Blind Barber (East Village)",
            "Pouring Ribbons (East Village)", "Bemelmans Bar (Carlyle Hotel)",
            "King Cole Bar (St. Regis)", "Campbell Bar (Grand Central)",
            "Jimmy's Cocktail Lounge (James Hotel)", "The Sunken Harbor Club (Brooklyn)",
            "Raines Law Room", "Nitecap (Lower East Side)",
            "BarBacon (Hell's Kitchen)", "Long Island Bar (Brooklyn)",
            "The Wayland (Alphabet City)"
        ],
        "wellness": [
            "The Spa at Mandarin Oriental NYC", "Aire Ancient Baths (TriBeCa)",
            "Great Jones Spa (NoHo)", "Shibui Spa (Greenwich Hotel)",
            "WTHN Acupuncture (Flatiron)", "YogaWorks (Multiple Locations)",
            "Barry's Bootcamp NYC", "SoulCycle (Various)",
            "Central Park Conservatory Garden Yoga", "Brooklyn Bridge Park Morning Run",
            "The Well (Midtown West)", "Equinox Spa (Multiple)",
            "Remedy Place (West Village)", "The Assemblage (Midtown)",
            "Modo Yoga NYC", "Laughing Lotus Yoga",
            "Kripalu Day Workshop (Upper West Side)", "Russian & Turkish Baths (East Village)",
            "East River Park Fitness Track", "Prospect Park Cycling & Running",
            "NYC Parks Open Air Fitness Zones", "Beach Yoga Coney Island (Summer)",
            "Exhale Spa (Financial District)", "Spa Castle Premier (Queens)",
            "Bathhouse Studios (Williamsburg)"
        ],
        "secret_spots": [
            "The Highbridge Aqueduct Walk (Bronx-Manhattan)", "Smallpox Memorial Hospital (Roosevelt Island)",
            "Whispering Gallery (Grand Central Terminal)", "53rd St Subway Mosaic Tunnel Art",
            "The Elevated Acre (FiDi)", "Greenwood Cemetery Sunset Walk (Brooklyn)",
            "Little Red Lighthouse (Fort Washington)", "Inwood Hill Park & Cave",
            "Socrates Sculpture Park (Queens)", "Dead Horse Bay (Brooklyn)",
            "Wave Hill Gardens (Riverdale, Bronx)", "Queens Night Market",
            "Staten Island Ferry Sunset Ride (Free)", "The Vessel — Hudson Yards",
            "Bohemian Hall Beer Garden (Astoria)", "Governors Island Secret Garden",
            "No. 1 Train Graffiti Wall (Dyckman)", "Ridgewood Reservoir (Queens)",
            "Rockaway Beach Surf Break", "New York Earth Room (SoHo)",
            "Panorama of the City of NY (Queens Museum)", "Untermeyer Park (Yonkers)",
            "Secret Garden (Battery Park)", "LIC Arts Open Studios",
            "The Brick Church Garden (Midtown)"
        ],
        "essentials": [
            "John F. Kennedy International Airport (JFK)", "LaGuardia Airport (LGA)",
            "Penn Station & Amtrak Hub", "Grand Central Terminal",
            "NYC MTA Subway & Bus Information", "Port Authority Bus Terminal (Midtown)",
            "NYC Official Visitor Center (Midtown)", "Bellevue Hospital Emergency (Kips Bay)",
            "Mount Sinai Emergency (Upper East Side)", "CVS Pharmacy (24hr, Multiple)",
            "Chase ATM (Citywide)", "TD Bank International Services",
            "NYC Police Non-Emergency: 311", "Emergency: 911",
            "Tourist SIM: T-Mobile Times Square", "Western Union (Midtown)",
            "US Post Office (General — 33rd St)", "DHL Express (Midtown)",
            "Luggage Storage (Stasher — Multiple)", "NYC Ferry Hub (Pier 11)",
            "MTA MetroCard Vending Machines", "24hr Pharmacies (Duane Reade)",
            "Currency Exchange (Travelex — JFK)", "Yellow Taxi & Lyft Hub",
            "NYC Health + Hospitals Urgent Care"
        ],
        "shopping": [
            "Fifth Avenue Luxury Shopping", "Rockefeller Center Shops",
            "SoHo Cast Iron District Boutiques", "Chelsea Market",
            "Union Square Greenmarket (Saturdays)", "Brookfield Place (FiDi)",
            "Westfield World Trade Center (Oculus)", "Saks Fifth Avenue",
            "Bergdorf Goodman", "Bloomingdale's (Upper East Side)",
            "Nordstrom (Columbus Circle)", "Century 21 (Reopen)",
            "Century 21 Outlet (Secaucus)", "Macy's Herald Square",
            "Essex Market (Lower East Side)", "Artists & Fleas (Williamsburg)",
            "Brooklyn Flea", "Smorgasburg Markets",
            "L Train Vintage (Williamsburg)", "Housing Works Thrift (SoHo)",
            "Strand Bookstore (Union Square)", "McNally Jackson Books (SoHo)",
            "MoMA Design Store", "ABC Carpet & Home",
            "Hester Street Fair (LES)"
        ],
        "adventures": [
            "Brooklyn Bridge Walk & Bike", "Central Park Reservoir Running Loop",
            "Hudson River Park Kayaking (Free)", "Rock Climbing — Brooklyn Boulders",
            "Surf Lessons — Rockaway Beach", "Sailing NYC Harbor",
            "Cycling the Manhattan Waterfront Greenway", "Ice Skating Wollman Rink (Winter)",
            "Top of the Rock Sky Climb", "One World Observatory Elevator Ascent",
            "Aerial Tram to Roosevelt Island", "NYC Marathon Running Route",
            "Cloisters Forest Walk (Inwood)", "Staten Island Bicycling Trails",
            "Yankee Stadium Sports Tour", "Citi Field Baseball Game",
            "Madison Square Garden Events", "East River Ferry Waterway Cruise",
            "Escape Room NYC (Various)", "Ninja NYC — Immersive Dining",
            "Archery Range (Brooklyn Archery Studio)", "Bouldering (The Cliffs)",
            "Hot Air Balloon (Hudson Valley)", "Whitewater Rafting (Letchworth Day Trip)",
            "NYC Helicopter Tour"
        ],
        "theme_parks": [
            "Coney Island Luna Park", "Six Flags Great Adventure (NJ)",
            "Sesame Place Philadelphia (Day Trip)", "Hersheypark (Day Trip)",
            "Legoland New York (Goshen)", "Adventureland (Long Island)",
            "Great Wolf Lodge (Pocono Mountains)", "Dave & Buster's (Times Square)",
            "Nickelodeon Universe (American Dream — NJ)", "Dreamworks Water Park (American Dream)",
            "Chelsea Piers Sports Complex", "VOID Hyper Reality (VR)",
            "Meow Wolf NYC (Upcoming)", "Escape Room NYC Collective",
            "Bowlero Bowling (Multiple)", "Lucky Strike Lanes (Garment District)",
            "Laser Bounce NYC", "Brooklyn Bowl (Williamsburg)",
            "Randall's Island Golf Center", "SpeedWay (Long Island)",
            "Urban Air Trampoline (Staten Island)", "Altitude Trampoline Park (NJ)",
            "Smaaash Entertainment (Times Square)", "Neuehouse Play Zone",
            "AREA15 (Las Vegas — Inspired NYC Pop-up)"
        ]
    },
    "tokyo": {
        "sacred_temples": [
            "Senso-ji Temple (Asakusa)", "Meiji Jingu Shrine (Harajuku)",
            "Zojo-ji Temple (Shiba)", "Yasukuni Shrine (Chiyoda)",
            "Nezu Shrine (Bunkyo)", "Hie Shrine (Akasaka)",
            "Gotoku-ji Temple (Setagaya)", "Sengakuji Temple (Minato)",
            "Kanda Myojin Shrine", "Nishi Arai Daishi Temple",
            "Ikegami Honmonji Temple", "Jindai-ji Temple (Chofu)",
            "Gokoku-ji Temple (Otsuka)", "Tsurugaoka Hachimangu (Kamakura Day Trip)",
            "Engaku-ji Zen Temple (Kamakura)", "Kotoku-in (Great Buddha — Kamakura)",
            "Nikko Tosho-gu (Day Trip)", "Ota-ji Temple (Yanaka)",
            "Yanaka Cemetery & Temple Row", "Asakusa Sanja Matsuri Grounds",
            "Yushima Seido Confucian Temple", "Shinjuku Hanazono Shrine",
            "Inokashira Benzaiten Shrine", "Edo-Tokyo Open Air Shrine Museum",
            "Togoshi Hachimangu Shrine"
        ],
        "attractions": [
            "Shinjuku Gyoen National Garden", "Tokyo Skytree", "Shibuya Crossing",
            "Tsukiji Outer Market", "Odaiba Waterfront", "Akihabara Electric Town",
            "teamLab Borderless Museum", "Ueno Zoo & Museum Row",
            "Harajuku Takeshita Street", "Ginza Shopping District",
            "Imperial Palace East Gardens", "Roppongi Hills & Mori Art Museum",
            "Tokyo Tower", "Asakusa & Nakamise Shopping Street",
            "Yanaka Old Town District", "Yoyogi Park (Harajuku)",
            "Koenji Vintage Shops District", "Shimokitazawa Music Village",
            "Sumo Ryogoku Kokugikan Stadium", "Edo Tokyo Museum",
            "Fuji-Q Highland (Day Trip)", "Nikko National Park (Day Trip)",
            "Mt. Takao Hiking Trail", "Kawaguchiko (Fuji Lake)", "Jimbocho Booktown"
        ],
        "culinary": [
            "Ichiran Ramen (Shinjuku)", "Sukiyabashi Jiro (Ginza)",
            "Tsukiji Sushi Zanmai", "Ramen Street (Tokyo Station B1)",
            "Tofu-ya Ukai", "Gonpachi Nishi Azabu (Kill Bill Restaurant)",
            "Narisawa (Minami-Aoyama)", "Tempura Kondo (Ginza)",
            "Afuri Ramen (Ebisu)", "Yakiniku Jumbo (Harajuku)",
            "Katsukura Tonkatsu (Shinjuku)", "Hakuun-an (Shinjuku Kaiseki)",
            "Monja Street (Tsukishima)", "Depachika Basement Food Halls (Isetan)",
            "Shibuya Scramble Egg & Brunch", "Tokyo Curry Lab (Jinbocho)",
            "Harajuku Crepe Stalls (Marion)", "Onigiri Asakusa Yadoroku",
            "Soba Restaurant Kanda Matsuya", "Matcha Sweets Nakamura Tokichi (Uji)",
            "Mazemen Bankara Ramen", "Uobei Sushi Conveyor (Shibuya)",
            "Akihabara Maid Café Dinner", "Sushi no Midori (Shibuya)",
            "Ginza Six Basement Food Hall"
        ],
        "events": [
            "Cherry Blossom Hanami (March–April)", "Sumida River Fireworks (July)",
            "Awa Odori Dance Festival", "Comiket Tokyo (Biannual)",
            "Tokyo Marathon (March)", "Shibuya Halloween Night",
            "teamLab Seasonal Exhibitions", "Tokyo International Film Festival",
            "Robot Restaurant Show (Shinjuku)", "Asakusa Sanja Matsuri",
            "Roppongi Art Night", "Harajuku Design Festa",
            "Tokyo Game Show (September)", "Winter Illumination at Roppongi Hills",
            "New Year Hatsumode at Meiji Jingu", "Sumo Tournament (Tokyo Basho)",
            "J-League Football Matches (FC Tokyo)", "Kabuki-za Traditional Theater",
            "Tokyo Auto Salon", "Anime Japan Expo",
            "Odaiba Rainbow Fireworks", "Tokyo Ramen Show (October)",
            "Nakameguro Lantern Walk", "Shinjuku Eisa Street Dancing",
            "Yoyogi Park Flea Market (Sundays)"
        ],
        "bars_pubs": [
            "Bar High Five (Ginza)", "Zoetrope Whisky Bar (Shinjuku)",
            "Tender Bar (Ginza)", "New York Bar (Park Hyatt Shinjuku)",
            "Gemstone Bar (Roppongi)", "Jicoo the Floating Bar (Odaiba)",
            "Gen Yamamoto (Azabu-Juban)", "The SG Club (Shibuya)",
            "Bespoke Bar Tokyo", "Bar Benfiddich (Shinjuku)",
            "Moonshine Tokyo (Shibuya)", "Two Rooms (Aoyama)",
            "Cé La Vi Tokyo", "Bellwood Bar (Ginza)",
            "Mixology Salon (Ginza)", "Alchemist (Roppongi)",
            "Beer Bar Popeye (Ryogoku)", "Spring Valley Brewery (Daikanyama)",
            "Baird Beer (Harajuku)", "Craft Beer Works Kamikaze (Shimokitazawa)",
            "Tachinomi Yatai Bars (Yurakucho Under-Tracks)", "Golden Gai Shinjuku Alley Bars",
            "Omoide Yokocho (Memory Lane)", "Nakameguro Riverside Craft Beer Row",
            "Shinjuku Kabukicho Bar Crawl"
        ],
        "wellness": [
            "Thermae-yu Super Sento (Shinjuku)", "Ooedo-Onsen Monogatari (Odaiba)",
            "Kudan Kaikan Onsen (Chiyoda)", "Spa LaQua (Tokyo Dome)",
            "Azabu Juban Onsen", "Daiba Sento Rooftop Bath",
            "Yoyogi Park Morning Yoga (Free)", "Imperial Hotel Spa",
            "The Spa at Four Seasons Marunouchi", "Mandarin Oriental Tokyo Spa",
            "Chidorigafuchi Moat Rowing (Seasonal)", "Shinjuku Gyoen Meditation Walk",
            "Nakameguro Canal Riverside Yoga", "Komorebi Forest Bathing (Okutama)",
            "Mount Takao Healing Trail", "Kawaguchiko Hot Spring Ryokan",
            "Anma Traditional Japanese Massage (Asakusa)", "Tokyo Athletic Club (Akasaka)",
            "Zen Meditation at Engaku-ji (Kamakura)", "Pilates Studio Shinjuku",
            "Roppongi Hills Club Gym", "Gold's Gym (Omotesando)",
            "Floating Sensory Spa (Harajuku)", "Kenko Sento (Shimokitazawa)",
            "Sodo Tokyo Yoga Loft (Shibuya)"
        ],
        "secret_spots": [
            "Golden Gai Alley (Shinjuku)", "Yanaka Ginza Old Shopping Street",
            "Koenji Kōenjisakai Passage (Vintage Alley)", "Shimokitazawa Record Shop Row",
            "Akihabara Radio Kaikan Rooftop", "Kagurazaka Cobblestone Lane",
            "Nezu Museum Secret Garden", "Inokashira Park Sunrise Paddle",
            "Mitaka No-Ji Ghibli Hidden Trail", "Hakusan Shrine Hydrangea Garden",
            "Kiyosumi Garden (East Tokyo)", "Rikugien Garden Night Illumination",
            "Tenozu Isle Art District (Shinagawa)", "Ebisu Garden Place Hidden Courtyard",
            "Meguro Parasitological Museum (Unusual)", "Jimbōchō Rare Bookshops Alley",
            "Yushima Tenjin Plum Blossom Garden", "Monzen-Nakacho Historic Bar District",
            "Kiyobashi Tsukiji Pre-Dawn Tuna Walk", "Sunamachi Ginza (East End)",
            "Nishi Ogikubo Antique Alley", "Kōenji Flea Market (Sundays)",
            "Daiba Hidden Beach Park", "Kyobashi Art District",
            "Mukojima Hyakkaen Garden"
        ],
        "essentials": [
            "Narita International Airport (NRT)", "Haneda Airport (HND)",
            "JR Pass (Shinkansen) Offices", "Tokyo Station Information Centre",
            "Yamanote Line Loop — Key Stations", "Suica / Pasmo Card Desk (Stations)",
            "NTT Docomo SIM Desk (Airports)", "Currency Exchange (Travelex)",
            "Tokyo Metropolitan Police: 110", "Fire & Ambulance: 119",
            "St. Luke's International Hospital (English-Speaking)",
            "JNTO Tourist Info (Shinjuku)", "Coin Lockers (Shibuya/Shinjuku)",
            "7-Eleven ATM (International Cards)", "Japan Post Bank ATM",
            "Lawson Convenience Stores (24hr)", "International Post (Shinjuku)",
            "IC Card Recharge Points", "Wi-Fi Rental (Yamabiko — Narita)",
            "Luggage Delivery (Yamato Transport)", "Taxi: JapanTaxi App",
            "Uber Japan (Narita Restricted)", "Pharma: Matsumoto Kiyoshi (Nationwide)",
            "FamilyMart 24hr Convenience", "Coin Laundry (Laundromat — Shibuya)"
        ],
        "shopping": [
            "Ginza Luxury Boulevard", "Harajuku Takeshita Street",
            "Omotesando Hills Shopping Complex", "Akihabara Electronics Town",
            "Shibuya Hikarie", "Tokyu Hands (DIY & Lifestyle)",
            "Isetan Department Store (Shinjuku)", "Mitsukoshi (Ginza)",
            "Yodobashi Camera (Akihabara)", "Bic Camera (Yurakucho)",
            "Nakameguro Boutique Strip", "Shimokitazawa Vintage Shops",
            "Koenji Vintage & Secondhand", "Asakusa Nakamise Souvenir Street",
            "Tokyo Skytree Solamachi Mall", "Ameyoko Market (Ueno)",
            "Shibuya 109 (Gyaru Fashion)", "Laforet Harajuku",
            "Parco Shibuya", "Roppongi Hills Shops",
            "Ikebukuro Sunshine City", "Seibu Ikebukuro",
            "Loft Store (Shibuya)", "Don Quijote (Shinjuku 24hr)",
            "Jimbocho Booktown Antique Maps"
        ],
        "adventures": [
            "Mt. Takao Hike (Day Trip)", "Fuji-Q Highland Extreme Rides",
            "Kawaguchiko Lake Kayaking", "Nikko National Park Waterfall Trek",
            "Odaiba Teamlab Digital Art Maze", "Sumida River Stand-Up Paddle",
            "Cycling Arakawa River Course", "Tokyo Bay Sailboat Charter",
            "Yokohama Seaside Cycling (Day Trip)", "Kamakura Hiking Trail",
            "Tokyo Dome City Baseball Events", "Meiji Jingu Stadium (Events)",
            "Archery at Meiji Jingu", "Sumo Stable Morning Practice Tour",
            "Tokyo Motorsport Race (Suzuka Day Trip)", "Ninja Experience Class (Asakusa)",
            "Katana Swordsmanship Class", "Pottery Class (Shibuya)",
            "Taiko Drumming Workshop", "Tokyo Bike Hire & Explore",
            "Indoor Rock Climbing (Ohsone)", "Parkour Tokyo",
            "Laser Tag Akihabara", "VR World Tokyo",
            "Flying Tokyo Canopy (SkyCircus Ikebukuro)"
        ],
        "theme_parks": [
            "Tokyo Disneyland", "Tokyo DisneySea",
            "Universal Studios Japan (Osaka — Day Trip)", "Fuji-Q Highland",
            "teamLab Planets (Toyosu)", "Joypolis SEGA (Odaiba)",
            "Tokyo Dome City Attractions", "Namjatown (Ikebukuro)",
            "KidZania Tokyo (Koto)", "Legoland Discovery Center (Odaiba)",
            "Pokemon Center Mega Tokyo", "Nintendo Store (Shibuya)",
            "VR Zone Shinjuku", "Ghibli Museum Mitaka (Ticket Required)",
            "Sanrio Puroland (Tama)", "Yomiuriland (Inagi)",
            "Toshimaen Memorial (Nearby)", "Seibuen Amusement Park",
            "Summerland (Akiru)", "Tokyo Tower Aquarium",
            "Ueno Zoo & Petting Area", "Shinagawa Aquarium",
            "Tokyo Sky Tree Floor 450 Experience", "Wonder Space (Odaiba)",
            "Bandai Namco Amusement Arcade (Akihabara)"
        ]
    },
    "paris": {
        "sacred_temples": [
            "Cathédrale Notre-Dame de Paris", "Sacré-Cœur Basilica (Montmartre)",
            "Sainte-Chapelle", "Saint-Sulpice Church",
            "La Madeleine Church", "Saint-Germain-des-Prés Church",
            "Mosque of Paris (Grande Mosquée de Paris)", "Temple Beth-El (Marais)",
            "Russian Orthodox Cathedral Saint-Alexandre-Nevsky", "Synagogue de la Victoire",
            "Saint-Eustache Church (Les Halles)", "Church of Saint-Merri",
            "Panthéon (Secular Shrine)", "Invalides Chapel & Napoleon's Tomb",
            "Temple Protestant de l'Étoile", "Buddhist Temple of the Bois de Vincennes",
            "Chapelle Expiatoire", "Saint-Louis-en-l'Île Church",
            "Notre-Dame de la Garde (Marseille Day Trip)", "Abbey of Saint-Germain (Auxerre)",
            "Basilique de Saint-Denis", "Church of the Madeleine Night Concert",
            "Notre-Dame des Victoires", "Armenian Apostolic Church (Paris)",
            "Saint-Nicolas-du-Chardonnet"
        ],
        "attractions": [
            "Eiffel Tower", "Louvre Museum", "Cathédrale Notre-Dame", "Arc de Triomphe",
            "Musée d'Orsay", "Palace of Versailles (Day Trip)",
            "Centre Pompidou", "Musée Rodin", "Sainte-Chapelle",
            "Shakespeare and Company Bookshop", "Père Lachaise Cemetery",
            "Sacré-Cœur Basilica", "Le Marais Historic Quarter",
            "Palais Royal Gardens", "Pont des Arts (Love Lock Bridge)",
            "Canal Saint-Martin", "Musée de l'Orangerie (Water Lilies)",
            "Galerie Vivienne", "Promenade Plantée (Green Walk)",
            "Buttes-Chaumont Park", "Luxembourg Gardens",
            "Île de la Cité & Île Saint-Louis Walk", "Oberkampf Street Art District",
            "La Défense Business District", "Moulin Rouge Exterior"
        ],
        "culinary": [
            "Le Relais de l'Entrecôte", "L'As du Fallafel", "Angelina Paris", "Du Pain et des Idées",
            "Breizh Café (Crepes — Marais)", "Septime (11th)",
            "Le Jules Verne (Eiffel Tower)", "Bouillon Chartier",
            "Stohrer Patisserie (Oldest in Paris)", "Maison Plisson",
            "Café de la Paix", "Laduree Champs-Elysées",
            "Pierre Hermé Macarons (Saint-Germain)", "L'Astrance (3 Michelin)",
            "Chez Janou (Marais)", "Le Grand Véfour",
            "Eric Kayser Boulangerie", "Marché d'Aligre Food Market",
            "Le Comptoir du Relais", "Frenchie (Sentier)",
            "Kitchen Galerie Bis", "David Toutain",
            "Le Chateaubriand (11th)", "Maison Lenôtre",
            "Café Procope (Oldest Café in Paris)"
        ],
        "events": [
            "Seine Sunset Music Cruise", "Montmartre Art Walk", "Paris Fashion Week Showcase",
            "Bastille Day Fireworks (July 14)", "Paris Marathon",
            "Roland Garros French Open", "Fête de la Musique (June 21)",
            "Nuit Blanche Paris (October)", "Paris Beer Week",
            "FIAC Art Fair", "Paris Photo Fair (November)",
            "Marché de Noël (Christmas Markets)", "Beaujolais Nouveau Night (November)",
            "Paris Cocktail Week", "Eiffel Tower New Year Countdown",
            "Coupe de France Football", "Tour de France (July)",
            "Palais-Royal Summer Garden Festival", "Château de Versailles Night Show",
            "Opéra National de Paris Season", "Cinéma en Plein Air (Villette)",
            "Paris Design Week", "Europride Paris",
            "Canal Saint-Martin Artisan Market", "Saint-Germain Jazz Festival"
        ],
        "shopping": [
            "Galeries Lafayette Haussmann", "Champs-Élysées Boutiques", "Marché aux Puces de Saint-Ouen",
            "Le Bon Marché (Rive Gauche)", "BHV Marais",
            "Rue de Rivoli", "Rue Montorgueil Market Street",
            "Galerie Vivienne Covered Passage", "Marché d'Aligre",
            "Rue du Faubourg Saint-Honoré (Luxury)", "Place Vendôme (Jewellery)",
            "Printemps (Grands Boulevards)", "Passage des Panoramas",
            "Shakespeare & Co Bookshop (Souvenir)", "Palais Royal Arcades",
            "Saint-Ouen Flea Market", "Belleville Artisan Market",
            "Marais Boutique District", "Oberkampf Street Shops",
            "Rue de la Roquette Vintage", "Batignolles Organic Market",
            "Abbesses Montmartre Shops", "Bercy Village Open-Air Shops",
            "Carreau du Temple", "Montmartre Art Supply Stores"
        ],
        "adventures": [
            "Seine Kayaking Expedition", "Bois de Boulogne Bike Loop", "Catacombes Deep Exploration",
            "Versailles Palace Cycling (e-bike)", "Fontainebleau Rock Climbing",
            "Paris Plages Beach Volleyball (Summer)", "Seine River Stand-Up Paddle",
            "Eiffel Tower Stair Climb Challenge", "Hot Air Balloon Paris (Parc André Citroën)",
            "Rollerblading Friday Night Fever", "Bois de Vincennes Cycling & Rowing",
            "Canal Saint-Martin Pedal Boat", "Laser Game Evolution (Paris)",
            "Squash Club Paris", "Olympic Swimming Pool La Butte-aux-Cailles",
            "Climbing Gym Minimum (Oberkampf)", "Accrobranche Forest Aventure",
            "Go-Kart Circuit Paris Est", "Tennis Roland Garros Public Courts",
            "Paris Triathlon Club Training", "Vélib' Bike Share — City Ride",
            "Escape Room Paranoia (7th)", "Laser Quest (Opera)",
            "Archery Paris (12th)", "Swim Piscine Pontoise (1930s Heritage)"
        ],
        "bars_pubs": [
            "Le Syndicat", "Café de Flore", "Little Red Door", "Harry's New York Bar",
            "Bar Hemingway (Ritz)", "Experimental Cocktail Club",
            "Glass Paris (Pigalle)", "Gossima Ping-Pong Bar",
            "Lulu White (Pigalle)", "Candelaria (Marais)",
            "Septime Cave", "Bisou Bar (11th)",
            "Combat Craft Beer Bar (19th)", "The Bombardier (English Pub)",
            "Le Tiger Bar", "Sherry Butt (Marais)",
            "Mabel (Louvre)", "Lavomatic (10th — Laundromat Bar)",
            "Bar 228 (Hotel Meurice)", "Ballroom du Bêlier",
            "Gravity Bar (Hôtel Panache)", "L'Ours Bar (Marais)",
            "Moonshiner (11th)", "Prescription Cocktail Club (Saint-Germain)",
            "Fred's Club (Oberkampf)"
        ],
        "wellness": [
            "Spa Pont-Neuf", "Jardin du Luxembourg Yoga", "Ritz Club & Spa",
            "Nuxe Spa (Palais Royal)", "My Blend Spa (Le Bristol)",
            "Cinq Mondes (Multiple)", "Institut Guerlain (Champs-Elysées)",
            "Bulgari Spa Paris", "Spa Caudalíe (Vinothérapie)",
            "Les Bains Montorgueil", "Hammam de la Mosquée de Paris",
            "Piscine Josephine Baker (Floating Pool)", "Aquaboulevard Water Park",
            "Klay Fitness (Saint-Germain)", "Keep Cool Gym (Multiple)",
            "Surya Yoga (Marais)", "The Yoga Spot Paris",
            "Pilates Lounge (9th)", "CrossFit Paris (Belleville)",
            "Centre de Yoga Iyengar Paris", "Parc des Buttes-Chaumont Morning Run",
            "Luxembourg Gardens Jogging Route", "Seine Riverside Morning Yoga",
            "Spa George V (Four Seasons)", "Institut Lanvin (8th)"
        ],
        "secret_spots": [
            "Promenade Plantée", "Rue Crémieux", "Musée de l'Orangerie", "Sainte-Chapelle",
            "Passage des Panoramas (1800s Covered Gallery)", "Galerie Vivienne Secret Corner",
            "Square du Vert-Galant (Tip of Île de la Cité)", "Petite Ceinture Abandoned Railway",
            "Hammam de la Mosquée", "Jardin de l'Hôtel de Sens",
            "Musée de Chasse et de la Nature", "Villa Montmorency (Gated Village)",
            "Cour du Commerce Saint-André", "Square des Batignolles Oasis",
            "La Géode (Mirrored Sphere)", "Musée de la Préfecture de Police",
            "Allée des Cygnes Island Walk", "Butte Bergeyre Hidden Village",
            "Jardin Atlantique (Above Train Station)", "La REcyclerie (Batignolles Station)",
            "Passage Jouffroy", "Hôtel de Lauzun (Île Saint-Louis)",
            "Villa Léandre (Montmartre)", "Parc de Bagatelle Rose Garden",
            "Le Carreau du Temple Underground"
        ],
        "essentials": [
            "Hôtel-Dieu Emergency Desk (112)", "RATP Metro Station Hub", "Charles de Gaulle Express Center",
            "Gare du Nord (Eurostar Hub)", "Gare de Lyon (TGV)",
            "Charles de Gaulle Airport CDG", "Orly Airport (ORY)",
            "Paris Visitor Centre (Hôtel de Ville)", "Bureau de Change (Marais)",
            "American Hospital of Paris (Emergency)", "Hôpital Lariboisière",
            "SNCF Railway Help Desk", "Vélib' Bike Share Stations",
            "G7 Taxi (Official)", "Uber France Hub",
            "Police (National): 17", "SAMU Medical Emergency: 15",
            "Pharmacie du Palais Royal (24hr)", "Western Union (République)",
            "La Poste (General Post)", "SIM Card: Orange & Bouygues",
            "ATM: Société Générale", "Lost & Found: BEL (Objet Trouvé, Gare de Lyon)",
            "Luggage Storage (Stasher — Paris)",
            "Paris Convention & Visitors Bureau"
        ],
        "theme_parks": [
            "Disneyland Paris", "Parc Astérix", "Jardin d'Acclimatation",
            "Aquaboulevard Water Park", "Paris Aquarium (Trocadéro)",
            "Cité des Sciences (La Villette)", "La Géode IMAX Theater",
            "Futuroscope (Poitiers Day Trip)", "Puy du Fou (Day Trip)",
            "Zoomarine (Day Trip)", "Laser Quest (Opéra)",
            "Escape Room Paranoia Paris", "Blacklight Mini Golf (Paris)",
            "Galeries de Paléontologie (Natural History)", "Palais de la Découverte",
            "Cinémathèque Française VR", "VR Room Paris (Le Marais)",
            "Stade de France Events", "Accor Arena (Concerts & Sports)",
            "Cirque d'Hiver (Seasonal)", "Magic Park (Montmartre)",
            "Bounce Paris Trampoline", "Clip 'n Climb Paris",
            "Bowling Académie de Billard (Maillot)", "iFly Indoor Skydiving (Val-de-Marne)"
        ]
    },
    "delhi": {
        "sacred_temples": [
            "Akshardham Temple", "Lotus Temple (Bahá'í House of Worship)",
            "Birla Mandir (Laxminarayan Temple)", "ISKCON New Delhi (Hare Krishna)",
            "Kalkaji Mandir", "Jama Masjid (Chandni Chowk)",
            "Gurudwara Bangla Sahib", "Gurudwara Sis Ganj Sahib (Chandni Chowk)",
            "St. James' Church (Kashmiri Gate)", "Sacred Heart Cathedral (Connaught Place)",
            "Nizamuddin Dargah", "Qutub Minar Mosque Complex",
            "Chhatarpur Mandir (South Delhi)", "Kali Mata Mandir (Karol Bagh)",
            "Hanuman Mandir (Connaught Place)", "Aadya Katyayani Shaktipeeth (Chhatarpur)",
            "Jhule Lal Mandir (Hauz Khas)", "Shiv Mandir Sector 10 Dwarka",
            "Ghalib's Dargah (Nizamuddin West)", "Fatehpuri Masjid (Chandni Chowk)",
            "Safdarjung Tomb Mosque", "Jamali Kamali Mosque (Mehrauli)",
            "Ancient Yogmaya Temple (Mehrauli)", "Tughlaqabad Fort Mosque",
            "Sri Sri Radha Parthasarathi Temple (ISKCON Dwarka)"
        ],
        "attractions": [
            "Red Fort", "Qutub Minar", "India Gate", "Humayun's Tomb",
            "Lotus Temple", "Akshardham Temple", "Rashtrapati Bhavan",
            "Purana Qila", "National Museum", "Lodi Garden",
            "Hauz Khas Village", "Mehrauli Archaeological Park",
            "Connaught Place", "Chandni Chowk Heritage Walk",
            "Dilli Haat (INA)", "Safdarjung Tomb",
            "Jama Masjid", "Jantar Mantar",
            "Garden of Five Senses", "Rail Museum Chanakyapuri",
            "Crafts Museum (Pragati Maidan)", "National Gallery of Modern Art",
            "Sunder Nursery", "Parliament Street", "Tughlaqabad Fort"
        ],
        "culinary": [
            "Karim's Chandni Chowk", "Bukhara (ITC Maurya)", "Saravana Bhavan", "Natraj Dahi Bhalle",
            "Paranthe Wali Gali (Chandni Chowk)", "Al-Jawahar (Jama Masjid)",
            "Khan Chacha (Khan Market)", "Indian Accent (Modern Indian)",
            "Varq (Taj Mahal Hotel)", "Bikkgane Biryani",
            "Roshan Di Kulfi (Karol Bagh)", "Bikaner Sweets (Bengali Market)",
            "Carnatic Cafe (Hauz Khas)", "Jamun (CMYK Complex)",
            "PCO Bar & Kitchen", "Big Chill Café (Khan Market)",
            "Soda Bottle Opener Wala (CP)", "Ode to Mughal (Agra & Delhi)",
            "Kake Da Hotel (Connaught Place)", "Street Food at Sector 29 Gurgaon",
            "Defence Colony Market Chaat", "Chhole Kulche — Nizam's",
            "Haldiram's Bikanervala", "Moti Mahal Delux (Connaught Place)",
            "Gulati Restaurant (Pandara Road)"
        ],
        "events": [
            "Dilli Haat Cultural Festival", "India Habitat Centre Art Showcase", "Chandni Chowk Night Food Walk",
            "Republic Day Parade (Rajpath)", "Delhi Half Marathon",
            "Surajkund Crafts Mela", "Auto Expo (Bharat Mandapam)",
            "World Book Fair (Pragati Maidan)", "Delhi Queer Pride Parade",
            "Dilli Diwali Mela (Dwarka)", "India International Trade Fair",
            "Aigrette Jazz Festival (IHC)", "Delhi Comedy Festival",
            "Hornbill Music Fest (South Delhi)", "Lotus Temple Music Concerts",
            "NGMA Art Exhibitions", "Jama Masjid Eid Celebration",
            "Gurudwara Baisakhi Celebration", "Dussehra — Ramlila Grounds",
            "Classical Kathak at Kamani Auditorium", "Siri Fort Culture Fest",
            "Akshardham Light & Sound Show", "Delhi Literature Festival",
            "PVR Saket Film Festival", "Delhi International Marathon"
        ],
        "bars_pubs": [
            "Sidecar GK2", "PCO Speakeasy", "The Electric Room", "Local CP",
            "Raasta (Hauz Khas)", "Kitty Su (The Lalit)",
            "My Bar (Paharganj)", "Privée (Shangri-La)",
            "Perch Wine & Coffee Bar (Khan Market)", "Harbour Bar (Taj Palace)",
            "TC (Connaught Place)", "1911 Bar (Imperial Hotel)",
            "Woodside Inn (Connaught Place)", "Unplugged Courtyard",
            "AOC Bar (GK2)", "Polo Lounge (Hyatt Regency)",
            "Bar Palladio (Jaipur — Day Trip)", "Smoke House Deli (Saket)",
            "Monkey Bar (Connaught Place)", "Q'BA (Connaught Place)",
            "Social Outpost (Hauz Khas)", "Lavaash by Saby (Mehrauli)",
            "Tamasha (Connaught Place)", "The Beer Café (Janpath)",
            "36 Bistro & Sports Bar (Noida)"
        ],
        "wellness": [
            "Lodhi Garden Sunrise Yoga", "Kairali Ayurvedic Center", "The Imperial Spa",
            "Ananda Spa (The Claridges)", "Tattva Spa (Multiple)",
            "O2 Spa (Select CITYWALK)", "Amatrra Spa (Greater Kailash)",
            "Nirvana Spa (Saket)", "Ayurmana Spa",
            "Fitness First (Multiple)", "Gold's Gym (Connaught Place)",
            "Cult.Fit (Multiple)", "Vipassana Meditation Centre (Mehrauli)",
            "Morarji Desai Yoga Institute", "Delhi Yoga Centre (Connaught Place)",
            "Ashtanga Yoga Centre (Saket)", "Art of Living Ashram",
            "National Institute of Naturopathy", "Morning Walk — India Gate Lawns",
            "Nehru Park Morning Yoga (RK Puram)", "Sunder Nursery Mindful Walk",
            "Lodi Garden Forest Bathing", "Hauz Khas Lake Run",
            "Delhi Cycling Club (Sunday Rides)", "NSIT Sports Complex (Dwarka)"
        ],
        "shopping": [
            "Chandni Chowk Bazaar", "Khan Market Boutiques", "Dilli Haat Handicrafts", "Select CITYWALK",
            "Connaught Place Inner Circle", "Karol Bagh Market",
            "Sarojini Nagar", "Janpath Market", "Palika Bazaar",
            "DLF Promenade (Vasant Kunj)", "Ambience Mall (Vasant Kunj)",
            "Pacific Mall (Subhash Nagar)", "MGF Metropolitan (Saket)",
            "DLF CyberHub (Gurgaon)", "Nehru Place Electronics Market",
            "Lajpat Nagar Central Market", "Greater Kailash Part 1 M-Block",
            "Jhandewalan Wholesale Paper Mkt", "Delhi Haat (Pitampura)",
            "Dilli Haat (Janakpuri)", "INA Market (South Delhi)",
            "Meena Bazaar Brides' Lane", "Kamla Nagar Student Market",
            "Sunder Nagar Antique Market", "Yashwant Place Antiques"
        ],
        "adventures": [
            "Aravalli Biodiversity Park Trail", "Yamuna Sports Complex Cycling", "Asola Bhatti Wildlife Safari",
            "Rappelling at Damdama Lake (Gurugram)", "Rock Climbing at Dhauj (Haryana)",
            "Horse Riding at Delhi Polo Club", "Go-Karting at Kartzone (Dwarka)",
            "Paintball at Zone (Gurugram)", "Aqua Ducks (Hauz Khas)",
            "Mehrauli Archaeological Park Heritage Run", "Cycling Delhi Ridge Forest",
            "Delhi Half Marathon Annual", "Badminton at Siri Fort Sports Complex",
            "Swimming at Delhi's 14 Olympic Pools", "Delhi Rock Gym (Lajpat Nagar)",
            "Escape Room (Connaught Place)", "Laser Tag (Airgigs)",
            "Trampoline Park (DLF)", "Rowing at INA Sports",
            "Night Cycling Rajpath", "Adventure Sports at Neemrana (Day Trip)",
            "Zip-lining Tikkar Taal (Day Trip)", "River Rafting Rishikesh (Day Trip)",
            "Trekking Nag Tibba (Weekend)", "Bungee Jumping (Mohan Chatti)"
        ],
        "secret_spots": [
            "Agrasen ki Baoli", "Hauz Khas Fort Sunset Point", "Majnu ka Tilla Secret Alley",
            "Dilli Haat at Night", "Old Sabzi Mandi Lane",
            "Mehrauli Archaeological Walk", "Chor Minar (Hauz Khas)",
            "Jahanpanah City Forest", "Bhuli Bhatiyari ka Mahal (Haunted)",
            "Khan-i-Khanan Tomb (Nizamuddin)", "Old Humayun Hamam (Behind Mosque)",
            "Hijron ka Khanqah (Gender Heritage Site)", "Begumpur Mosque",
            "Satpula (Seven-Arch Dam)", "Lado Sarai Artist Village",
            "Gulab Bagh (Rose Garden)", "Sanjay Van Forest Walk",
            "Pahari Bhojla Water Step-Well", "Quli Khan Tomb (Mehrauli)",
            "Neeli Chhatri Mosque", "Bhairon Mandir Elephant Shrine",
            "Hidden Garden Behind Safdarjung", "Khirki Village Mosque (Saket)",
            "Sufi Lane (Hauz Rani)", "Moth ki Masjid (Greater Kailash)"
        ],
        "essentials": [
            "AIIMS Emergency Desk (112)", "Delhi Metro Card Center", "New Delhi Railway Station Help Desk",
            "Indira Gandhi International Airport (DEL)", "All India Medical Institute (AIIMS)",
            "Apollo Hospital (Sarita Vihar)", "Max Hospital (Saket)",
            "NDTV Doctor on Call App", "Currency Exchange (Thomas Cook Connaught Place)",
            "State Bank ATM (Connaught Place)", "HDFC Forex (Vasant Vihar)",
            "Delhi Police Helpline: 100", "Women's Helpline: 1091",
            "Tourism India Office (Connaught Place)", "Delhi Tourism (Janpath)",
            "Rapido / Ola Cab Hub", "IGI Airport Metro Shuttle",
            "Airtel & Jio SIM (Airport Desk)", "Post Office: GPO (Sansad Marg)",
            "DMRC Metro Map (Free Download)", "Western Union (Karol Bagh)",
            "24hr Pharmacies — Apollo & MedPlus", "Lost & Found (IGI Airport)",
            "Luggage Storage (New Delhi Station)", "DHL Courier (Connaught Place)"
        ],
        "theme_parks": [
            "Adventure Island Rohini", "Worlds of Wonder Noida", "Fun N Food Village",
            "Aapno Ghar (Manesar)", "Appu Ghar (Gurugram)",
            "Kingdom of Dreams (Gurugram)", "Kingdom of Dreams Shows",
            "Smaaash Entertainment (Gurugram)", "DT Mega (Gurugram Multiplex Complex)",
            "VR World Delhi", "National Science Centre (Bhairon Road)",
            "Rail Museum Kids Gallery", "Dilli Haat Kids Craft Zone",
            "Play Nation (Select CITYWALK)", "Laser Tag Arena (Pacific Mall)",
            "Funky Monkey Play Zone (Ambience Mall)", "Bounce Delhi",
            "Jump Zone (Saket)", "Escape Room Delhi (Connaught Place)",
            "Ryze Trampoline Park (Gurugram)", "PVR Director's Cut (Vasant Kunj)",
            "Fun City (Pacific Mall)", "Kids Club (DLF CyberHub)",
            "Mini Golf (Sector 40 Gurugram)", "Go-Kart World (Dwarka)"
        ]
    }
}


PILLAR_KEYS = [
    "attractions", "events", "culinary", "bars_pubs", "wellness",
    "secret_spots", "essentials", "shopping", "adventures", "theme_parks", "sacred_temples"
]

async def call_groq_prompt(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GROQ_BASE,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 4000,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        import re
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content).strip()
        return content

async def fetch_dynamic_destination_data(destination: str) -> dict:
    clean_dest = destination.split(",")[0].strip().title()
    
    prompt = f"""
    You are an expert global travel concierge. For the destination '{clean_dest}', return a JSON object with keys: {json.dumps(PILLAR_KEYS)}.
    For EACH key, provide an array of at least 25 real, existing, verified venues/activities in {clean_dest}.
    
    Each item MUST have:
    - "id": string
    - "name": Exact real place name in {clean_dest} (e.g., "Wat Phra Kaew", "Chatuchak Market", "Maggie Choo's Bar").
    - "location": Locality/Neighborhood in {clean_dest}.
    - "description": 1 sentence description.
    
    CRITICAL RULES:
    - NEVER use generic titles or repeat the city name as the venue name (do NOT return "{clean_dest}" as name).
    - Every item MUST be a real, distinct location that exists on Google Maps.
    """

    try:
        raw_response = await call_groq_prompt(prompt)
        parsed_data = json.loads(raw_response)
        
        async with httpx.AsyncClient() as client:
            for pillar in PILLAR_KEYS:
                raw_items = parsed_data.get(pillar, [])
                items = []
                for idx, item in enumerate(raw_items):
                    v_name = item.get("name", "") if isinstance(item, dict) else str(item)
                    v_name = clean_venue_title(v_name, clean_dest)
                    if not v_name or v_name.lower() == clean_dest.lower():
                        v_name = f"{clean_dest} Local Point {idx+1}"
                    
                    v_loc = item.get("location", clean_dest) if isinstance(item, dict) else clean_dest
                    v_desc = item.get("description", f"Verified {pillar.replace('_', ' ')} venue in {clean_dest}.") if isinstance(item, dict) else f"Verified venue in {clean_dest}."
                    query_str = f"{v_name}, {v_loc}, {clean_dest}".strip()
                    
                    nav_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query_str)}"
                    img_url = await get_async_place_photo(client, v_name, clean_dest, category=pillar)
                    
                    items.append({
                        "id": f"{pillar}_{idx+1}",
                        "title": v_name,
                        "name": v_name,
                        "category": pillar.replace("_", " ").title(),
                        "description": v_desc,
                        "address": v_loc,
                        "location": v_loc,
                        "maps_url": nav_url,
                        "navigation_url": nav_url,
                        "image_url": img_url,
                    })
                parsed_data[pillar] = items
                
        return parsed_data

    except Exception as e:
        logger.error(f"Free dynamic generation fallback triggered for {clean_dest}: {e}")
        return generate_structural_dynamic_fallback(clean_dest)

def generate_structural_dynamic_fallback(destination: str) -> dict:
    """Guaranteed free fallback generator—never repeats raw city name."""
    clean_dest = destination.split(",")[0].strip().title()
    fallback = {}
    
    pillar_descriptors = {
        "attractions": ["Central Monument", "Royal Heritage Site", "Historic Square", "National Museum", "Riverfront Promenade"],
        "events": ["Cultural Heritage Fair", "Night Street Market", "Live Music Session", "Artisan Expo"],
        "culinary": ["Traditional Noodle House", "Heritage Eatery", "Local Street Food Hub", "Famous Sweet Corner"],
        "bars_pubs": ["Rooftop Sunset Lounge", "Speakeasy Cocktail Bar", "Craft Taproom", "Live Jazz Pub"],
        "wellness": ["Traditional Herbal Spa", "Zen Yoga Sanctuary", "Healing Retreat Center"],
        "secret_spots": ["Hidden Courtyard Cafe", "Old Town Viewpoint", "Secluded Alleyway Market"],
        "essentials": ["Central Railway Terminal", "Main Tourist Info Center", "Central Pharmacy"],
        "shopping": ["Central Grand Bazaar", "Crafts & Silk Market", "Luxury Shopping Galleria"],
        "adventures": ["River Kayaking Deck", "Heritage Bicycle Trail", "Forest Reserve Nature Walk"],
        "theme_parks": ["Ocean World Aquarium", "Extreme Water Slide Park", "Digital Gaming Zone"],
        "sacred_temples": ["Grand Cathedral", "Historic Sacred Temple", "Central Peace Pagoda"]
    }
    
    for pillar in PILLAR_KEYS:
        items = []
        templates = pillar_descriptors.get(pillar, ["Landmark Spot"])
        for idx in range(25):
            base_desc = templates[idx % len(templates)]
            venue_title = f"{clean_dest} {base_desc} {idx+1}"
            nav_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(venue_title + ' ' + clean_dest)}"
            items.append({
                "id": f"{pillar}_{idx+1}",
                "title": venue_title,
                "name": venue_title,
                "category": pillar.replace("_", " ").title(),
                "address": f"{clean_dest} Zone {idx%5 + 1}",
                "location": f"{clean_dest} Zone {idx%5 + 1}",
                "description": f"Popular {pillar.replace('_', ' ')} location situated in {clean_dest}.",
                "maps_url": nav_url,
                "navigation_url": nav_url,
                "image_url": "https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=900&auto=format&fit=crop&q=80"
            })
        fallback[pillar] = items
        
    return fallback


async def build_fallback_trip_plan(
    location: str,
    days: int = 3,
    start_day: Optional[date] = None,
    client: Optional[httpx.AsyncClient] = None
) -> TripPlanResponse:
    destination = (location or "Lucknow").strip().title()
    start_day = start_day or date.today()
    coordinates = fallback_coordinates_for(destination)
    destination_image = await get_async_place_photo(client, f"{destination} landmark", destination) if client else PEXELS_FALLBACK

    dynamic_data = await fetch_dynamic_destination_data(destination)

    def convert_items(pillar_key: str, default_category: str) -> List[PillarItem]:
        raw_list = dynamic_data.get(pillar_key, [])
        res = []
        for idx, item in enumerate(raw_list):
            if isinstance(item, dict):
                v_title = item.get("name") or item.get("title") or f"{destination} Point {idx+1}"
                v_loc = item.get("location") or item.get("address") or destination
                v_desc = item.get("description") or f"Verified {default_category} spot in {destination}."
                nav_url = item.get("navigation_url") or item.get("maps_url") or generate_google_maps_url(v_title, v_loc, destination)
                img_url = item.get("image_url") or PEXELS_FALLBACK
            else:
                v_title = str(item)
                v_loc = destination
                v_desc = f"Verified {default_category} spot in {destination}."
                nav_url = generate_google_maps_url(v_title, v_loc, destination)
                img_url = PEXELS_FALLBACK

            res.append(
                PillarItem(
                    id=f"{pillar_key}-{idx+1}",
                    title=v_title,
                    category=default_category,
                    description=v_desc,
                    address=v_loc,
                    maps_url=nav_url,
                    image_url=img_url,
                    lat=coordinates.lat,
                    lng=coordinates.lng,
                    price_range=""
                )
            )
        return res

    attractions = convert_items("attractions", "Tourist Attractions")
    events = convert_items("events", "Events")
    culinary = convert_items("culinary", "Culinary")
    bars_pubs = convert_items("bars_pubs", "Bars & Pubs")
    wellness = convert_items("wellness", "Wellness & Meditation")
    secret_spots = convert_items("secret_spots", "Secret Spots")
    essentials = convert_items("essentials", "Travel Essentials")
    shopping = convert_items("shopping", "Shopping")
    adventures = convert_items("adventures", "Adventures")
    theme_parks = convert_items("theme_parks", "Theme Parks")
    sacred_temples = convert_items("sacred_temples", "Temples & Shrines")

    itinerary: List[TripStop] = []
    routes: List[TripDayRoute] = []

    attr_names = [a.title for a in attractions] or [f"{destination} Central Landmark"]
    for day_index in range(days):
        day_number = day_index + 1
        trip_date = start_day.fromordinal(start_day.toordinal() + day_index)
        day_coordinates: List[List[float]] = []

        for stop_index in range(3):
            stop_lat = coordinates.lat + (stop_index * 0.005) + (day_index * 0.01)
            stop_lng = coordinates.lng + (stop_index * 0.005) + (day_index * 0.01)
            
            v_idx = ((day_index * 3) + stop_index) % len(attr_names)
            venue_title = attr_names[v_idx]
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

    culinary_highlights = [
        CulinaryHighlight(
            title=c.title,
            description=c.description,
            famous_for=f"Specialty Dish at {c.title}",
            location=c.address,
            price_tier="",
            cost_approx=""
        ) for c in culinary[:8]
    ]

    try:
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
            culinary_highlights=culinary_highlights,
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
            sacred_temples=[],
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
#  6b. LIVE WEATHER ENDPOINT
# ─────────────────────────────────────────────

WMO_CODE_MAP = {
    0: ("Clear Sky", "☀️"), 1: ("Mainly Clear", "🌤️"), 2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"), 45: ("Foggy", "🌫️"), 48: ("Icy Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy Drizzle", "🌧️"),
    61: ("Light Rain", "🌧️"), 63: ("Rain", "🌧️"), 65: ("Heavy Rain", "🌧️"),
    71: ("Light Snow", "🌨️"), 73: ("Snow", "❄️"), 75: ("Heavy Snow", "❄️"),
    80: ("Rain Showers", "🌦️"), 81: ("Showers", "🌦️"), 82: ("Violent Showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm + Hail", "⛈️"), 99: ("Severe Thunderstorm", "⛈️"),
}

@app.get("/api/weather")
async def get_destination_weather(destination: str = "Lucknow", start_date: str = "", end_date: str = ""):
    try:
        coords = fallback_coordinates_for(destination)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords.lat}&longitude={coords.lng}&current_weather=true"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=3.0)
            if res.status_code == 200:
                cw = res.json().get("current_weather", {})
                temp = round(cw.get("temperature", 28))
                return {
                    "temp_c": temp,
                    "condition": "Partly Cloudy" if temp > 20 else "Clear",
                    "description": "Pleasant Weather",
                    "icon": "02d"
                }
    except Exception as e:
        logger.warning(f"Weather lookup failed: {e}")

    return {"temp_c": 28, "condition": "Sunny", "description": "Clear Sky", "icon": "01d"}


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
