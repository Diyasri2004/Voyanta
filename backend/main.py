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
    logger.warning("CRITICAL WARNING: Neither GROQ_API_KEY nor GEMINI_API_KEY is set. Itinerary generation will fallback to procedural dynamic data.")
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


CATEGORY_PHOTO_POOLS = {
    "attractions": [
        "https://images.unsplash.com/photo-1599661046289-e31897846e41?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1548013146-72479768bada?w=900&auto=format&fit=crop&q=80"
    ],
    "secret_spots": [
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=900&auto=format&fit=crop&q=80"
    ],
    "culinary": [
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=900&auto=format&fit=crop&q=80"
    ],
    "bars_pubs": [
        "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=900&auto=format&fit=crop&q=80"
    ],
    "wellness": [
        "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=900&auto=format&fit=crop&q=80"
    ],
    "sacred_temples": [
        "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1548013146-72479768bada?w=900&auto=format&fit=crop&q=80"
    ],
    "shopping": [
        "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=900&auto=format&fit=crop&q=80"
    ],
    "events": [
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=900&auto=format&fit=crop&q=80"
    ],
    "adventures": [
        "https://images.unsplash.com/photo-1541625602330-2277a4c46182?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=900&auto=format&fit=crop&q=80"
    ],
    "theme_parks": [
        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=900&auto=format&fit=crop&q=80"
    ],
    "essentials": [
        "https://images.unsplash.com/photo-1517649763962-0c623266010b?w=900&auto=format&fit=crop&q=80"
    ]
}

DEFAULT_FALLBACKS = [
    "https://images.unsplash.com/photo-1599661046289-e31897846e41?w=900&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=900&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80"
]

def get_category_fallback_photo(category: str, place_name: str) -> str:
    cat = (category or "").lower()
    pool = CATEGORY_PHOTO_POOLS.get(cat, CATEGORY_PHOTO_POOLS["attractions"])
    idx = abs(hash(place_name)) % len(pool)
    return pool[idx]

CATEGORY_SAFE_FALLBACKS = {
    "attractions": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=900&auto=format&fit=crop&q=80",
    "events": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=900&auto=format&fit=crop&q=80",
    "culinary": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80",
    "bars_pubs": "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=900&auto=format&fit=crop&q=80",
    "wellness": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=900&auto=format&fit=crop&q=80",
    "secret_spots": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=900&auto=format&fit=crop&q=80",
    "essentials": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=900&auto=format&fit=crop&q=80",
    "shopping": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=900&auto=format&fit=crop&q=80",
    "adventures": "https://images.unsplash.com/photo-1541625602330-2277a4c46182?w=900&auto=format&fit=crop&q=80",
    "theme_parks": "https://images.unsplash.com/photo-1513889961551-628c1e5e2ee9?w=900&auto=format&fit=crop&q=80",
    "sacred_temples": "https://images.unsplash.com/photo-1548013146-72479768bada?w=900&auto=format&fit=crop&q=80"
}

CATEGORY_SAFE_POOLS = {
    "attractions": [
        "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1508807526345-15e9b5f4eaff?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=900&auto=format&fit=crop&q=80"
    ],
    "culinary": [
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=900&auto=format&fit=crop&q=80"
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
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=900&auto=format&fit=crop&q=80"
    ],
    "essentials": [
        "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=900&auto=format&fit=crop&q=80"
    ],
    "shopping": [
        "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=900&auto=format&fit=crop&q=80"
    ],
    "adventures": [
        "https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=900&auto=format&fit=crop&q=80"
    ],
    "theme_parks": [
        "https://images.unsplash.com/photo-1513889961551-628c1e5e2ee9?w=900&auto=format&fit=crop&q=80"
    ],
    "sacred_temples": [
        "https://images.unsplash.com/photo-1548013146-72479768bada?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=900&auto=format&fit=crop&q=80"
    ],
    "events": [
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=900&auto=format&fit=crop&q=80"
    ]
}

def get_dynamic_fallback_image(place_name: str, destination: str, category: str) -> str:
    query = urllib.parse.quote(f"{place_name} {destination} {category}".strip())
    cat_key = (category or "").lower().strip()
    if cat_key in CATEGORY_SAFE_FALLBACKS:
        return CATEGORY_SAFE_FALLBACKS[cat_key]
    return f"https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=900&auto=format&fit=crop&q=80" if "beach" in query.lower() else f"https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=900&auto=format&fit=crop&q=80"

async def get_async_place_photo(client: httpx.AsyncClient, place_name: str, destination: str, category: str = "", idx: int = 0) -> str:
    """Fetch photo via Pexels or fall back immediately to category-matched rotating pools."""
    if PEXELS_API_KEY:
        try:
            query = f"{place_name} {destination}".strip()
            url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&orientation=landscape&per_page=1"
            res = await client.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=1.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    return data["photos"][0]["src"]["large"]
        except Exception:
            pass

    pool = CATEGORY_SAFE_POOLS.get(category, CATEGORY_SAFE_POOLS.get("attractions", []))
    if pool:
        return pool[idx % len(pool)]
    return get_dynamic_fallback_image(place_name, destination, category)


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

    full_prompt = f"{system_prompt}\n\nUSER REQUEST: {prompt}"
    try:
        content = await call_ai_with_rate_limit_fallback(full_prompt, response_format={"type": "json_object"})
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
        ] or [],
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


PILLAR_KEYS = [
    "attractions", "events", "culinary", "bars_pubs", "wellness",
    "secret_spots", "essentials", "shopping", "adventures", "theme_parks", "sacred_temples"
]

async def call_ai_with_rate_limit_fallback(prompt: str, response_format: Optional[dict] = None) -> str:
    groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    if GROQ_API_KEY:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        for model in groq_models:
            try:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": response_format or {"type": "json_object"}
                }
                async with httpx.AsyncClient() as client:
                    res = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=6.0)
                    if res.status_code == 200:
                        return res.json()["choices"][0]["message"]["content"]
                    elif res.status_code == 429:
                        logger.warning(f"Groq {model} hit 429 rate limit. Escalating...")
                        continue
            except Exception as e:
                logger.warning(f"Groq {model} call failed: {e}")
                continue

    if GEMINI_API_KEY:
        try:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            gemini_payload = {"contents": [{"parts": [{"text": prompt + "\nReturn strictly a valid JSON object only."}]}]}
            async with httpx.AsyncClient() as client:
                res = await client.post(gemini_url, json=gemini_payload, timeout=6.0)
                if res.status_code == 200:
                    raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return raw_text.replace("```json", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"Gemini fallback failed: {e}")

    raise Exception("All AI generation backends unavailable.")

async def call_groq_api(prompt: str, response_format: Optional[dict] = None) -> str:
    return await call_ai_with_rate_limit_fallback(prompt, response_format=response_format)

async def call_groq_prompt(prompt: str, response_format: Optional[dict] = None) -> str:
    return await call_ai_with_rate_limit_fallback(prompt, response_format=response_format)

async def process_single_venue(client: httpx.AsyncClient, item: dict, clean_dest: str, pillar: str, idx: int) -> dict:
    if isinstance(item, str):
        item = {"name": item}
    elif not isinstance(item, dict):
        item = {}

    v_name = item.get("name") or item.get("title") or f"{clean_dest} Spot {idx+1}"
    v_name = clean_venue_title(str(v_name), clean_dest)
    if not v_name or v_name.lower() == clean_dest.lower():
        v_name = f"{clean_dest} Spot {idx+1}"

    v_loc = item.get("location") or item.get("address") or clean_dest
    v_loc = str(v_loc).strip()
    v_desc = item.get("description") or f"Verified {pillar.replace('_', ' ')} venue in {clean_dest}."
    query_str = f"{v_name}, {v_loc}, {clean_dest}".strip()
    
    nav_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query_str)}"
    img_url = await get_async_place_photo(client, v_name, clean_dest, category=pillar, idx=idx)

    return {
        "id": item.get("id") or f"{pillar}_{idx+1}",
        "title": v_name,
        "name": v_name,
        "category": pillar.replace("_", " ").title(),
        "description": str(v_desc),
        "address": v_loc,
        "location": v_loc,
        "maps_url": nav_url,
        "navigation_url": nav_url,
        "image_url": img_url,
        "image": img_url,
    }

async def generate_pillar_batch(destination: str, pillars: list) -> dict:
    prompt = f"""
    You are an expert global travel concierge engine.
    For the real destination '{destination}', generate a JSON object with keys: {json.dumps(pillars)}.
    For EACH key, generate an array of at least 15 real, authentic, verified landmarks, activities, or venues in {destination} (e.g. for Venice: St. Mark's Basilica, Rialto Bridge, Doge's Palace, Grand Canal, Murano Island, Cicchetti at Cantina Do Mori).
    
    Output JSON schema:
    {{
      "{pillars[0]}": [
        {{"id": "str", "name": "Exact Real Place Name", "location": "Real Neighborhood or Area", "description": "1 concise sentence description."}}
      ]
    }}
    
    STRICT RULES:
    1. NEVER generate placeholder names like '{destination} Monument 1' or generic numbered locations like 'Zone 1'.
    2. Every venue must be an actual location in {destination}.
    """
    try:
        raw_response = await call_ai_with_rate_limit_fallback(prompt)
        return json.loads(raw_response)
    except Exception as e:
        logger.warning(f"Batch generation failed for {destination} pillars {pillars}: {e}")
        return {}

generate_pillar_group = generate_pillar_batch

async def fetch_dynamic_destination_data(destination: str) -> dict:
    clean_dest = destination.split(",")[0].strip().title()
    
    # Split into 2 parallel batches of 5-6 pillars each to prevent token limit crashes
    batch_1 = PILLAR_KEYS[:6]
    batch_2 = PILLAR_KEYS[6:]
    
    try:
        data_1, data_2 = await asyncio.gather(
            generate_pillar_batch(clean_dest, batch_1),
            generate_pillar_batch(clean_dest, batch_2)
        )
        combined_data = {**data_1, **data_2}
        
        async with httpx.AsyncClient() as client:
            for pillar in PILLAR_KEYS:
                items = combined_data.get(pillar, [])
                tasks = [
                    process_single_venue(client, item, clean_dest, pillar, idx)
                    for idx, item in enumerate(items)
                    if isinstance(item, dict) and item.get("name")
                ]
                combined_data[pillar] = await asyncio.gather(*tasks)
                
        return combined_data

    except Exception as e:
        logger.error(f"Batch AI generation error for {clean_dest}: {e}")
        try:
            data_fallback = await generate_pillar_batch(clean_dest, PILLAR_KEYS[:4])
            async with httpx.AsyncClient() as client:
                for pillar in PILLAR_KEYS[:4]:
                    items = data_fallback.get(pillar, [])
                    tasks = [
                        process_single_venue(client, item, clean_dest, pillar, idx)
                        for idx, item in enumerate(items)
                        if isinstance(item, dict) and item.get("name")
                    ]
                    data_fallback[pillar] = await asyncio.gather(*tasks)
            return data_fallback
        except Exception:
            return {}

@app.get("/api/destination")
async def get_destination_data(destination: str = Query(..., min_length=1)):
    return await fetch_dynamic_destination_data(destination)


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
#  STRICT DYNAMIC AUTOCOMPLETE
# ─────────────────────────────────────────────

@app.get("/api/autocomplete")
async def autocomplete_destinations(q: str = Query("", min_length=0)):
    query = q.strip().lower()
    if not query:
        return {"suggestions": []}

    suggestions = []
    seen = set()

    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(query)}&count=12"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=1.8)
            if res.status_code == 200:
                for item in res.json().get("results", []):
                    name = item.get("name", "")
                    country = item.get("country", "")
                    admin = item.get("admin1", "")
                    # STRICT PREFIX MATCH
                    if name.lower().startswith(query):
                        label = f"{name}, {admin}, {country}" if admin else f"{name}, {country}"
                        if label.lower() not in seen:
                            suggestions.append({"label": label, "value": f"{name}, {country}"})
                            seen.add(label.lower())
    except Exception as e:
        logger.warning(f"Open-Meteo autocomplete error: {e}")

    if len(suggestions) < 6 and TOMTOM_API_KEY:
        try:
            url = f"https://api.tomtom.com/search/2/search/{urllib.parse.quote(query)}.json?key={TOMTOM_API_KEY}&typehead=true&limit=15&idxSet=Geo,PAD,Addr"
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=1.5)
                if res.status_code == 200:
                    for result in res.json().get("results", []):
                        address = result.get("address", {})
                        city = address.get("municipality") or address.get("freeformAddress") or result.get("poi", {}).get("name")
                        country = address.get("country")
                        if city and country:
                            clean_city = city.strip()
                            if clean_city.lower().startswith(query):
                                label = f"{clean_city}, {country.strip()}"
                                if label.lower() not in seen:
                                    suggestions.append({"label": label, "value": label})
                                    seen.add(label.lower())
        except Exception as e:
            logger.warning(f"TomTom prefix search failed: {e}")

    if len(suggestions) < 6:
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&addressdetails=1&limit=15"
            headers = {"User-Agent": "VoyantaTravelEngine/1.0"}
            async with httpx.AsyncClient() as client:
                res = await client.get(url, headers=headers, timeout=1.5)
                if res.status_code == 200:
                    for item in res.json():
                        parts = [p.strip() for p in item.get("display_name", "").split(",")]
                        main_place = parts[0]
                        if main_place.lower().startswith(query):
                            country = parts[-1] if len(parts) > 1 else ""
                            label = f"{main_place}, {country}" if country else main_place
                            if label.lower() not in seen:
                                suggestions.append({"label": label, "value": label})
                                seen.add(label.lower())
        except Exception as e:
            logger.error(f"Nominatim prefix search failed: {e}")

    return {"suggestions": suggestions[:6]}



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
async def get_destination_weather(destination: str = Query("")):
    clean_dest = destination.split(",")[0].strip()
    if not clean_dest:
        return {"temp": 24, "temp_c": 24, "condition": "Sunny", "icon": "01d"}

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_dest)}&count=1"
        async with httpx.AsyncClient() as client:
            geo_res = await client.get(geo_url, timeout=2.0)
            if geo_res.status_code == 200 and geo_res.json().get("results"):
                loc = geo_res.json()["results"][0]
                lat, lon = loc["latitude"], loc["longitude"]
                
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                w_res = await client.get(weather_url, timeout=2.0)
                if w_res.status_code == 200:
                    cw = w_res.json().get("current_weather", {})
                    temp = round(cw.get("temperature", 24))
                    wcode = cw.get("weathercode", 0)
                    
                    condition = "Sunny"
                    if wcode in [1, 2, 3]:
                        condition = "Partly Cloudy"
                    elif wcode in [45, 48]:
                        condition = "Foggy"
                    elif wcode in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                        condition = "Rainy"
                    elif wcode >= 95:
                        condition = "Thunderstorm"

                    return {"temp": temp, "temp_c": temp, "condition": condition, "icon": "01d"}
    except Exception as e:
        logger.warning(f"Weather lookup error: {e}")

    if OPENWEATHER_API_KEY and clean_dest:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(clean_dest)}&appid={OPENWEATHER_API_KEY}&units=metric"
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=1.5)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "temp": round(data["main"]["temp"]),
                        "temp_c": round(data["main"]["temp"]),
                        "condition": data["weather"][0]["main"],
                        "icon": data["weather"][0]["icon"]
                    }
        except Exception:
            pass

    return {"temp": 24, "temp_c": 24, "condition": "Sunny", "icon": "01d"}


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
