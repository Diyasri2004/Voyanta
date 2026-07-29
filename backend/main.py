from dotenv import load_dotenv
import os
import logging
import httpx
from uuid import UUID
from datetime import date
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg
from models import EventFestival

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
TOMTOM_BASE = "https://api.tomtom.com"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PEXELS_BASE = "https://api.pexels.com/v1/search"
PEXELS_FALLBACK = "https://images.pexels.com/photos/1483769/pexels-photo-1483769.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"

# ─────────────────────────────────────────────
#  Pydantic response models
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


class TripPlanRequest(BaseModel):
    location: str
    days: int = 3
    start_date: Optional[date] = None


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
    elevation: str
    duration: str
    image: str
    map_image_url: str
    lat: float
    lng: float


class TripDayRoute(BaseModel):
    day: int
    geojson: Optional[dict] = None
    total_distance_meters: float = 0
    total_travel_time_seconds: float = 0


class TripPlanResponse(BaseModel):
    destination: str
    destination_image: str
    map_image_url: str
    weather: str
    dates: str
    days: int
    coordinates: Coordinates
    itinerary: List[TripStop]
    routes: List[TripDayRoute]


class OllamaTripStop(BaseModel):
    title: str
    location: str
    category: str
    duration_minutes: int
    best_time: str


class OllamaTripDay(BaseModel):
    day: int
    theme: str
    stops: List[OllamaTripStop]


class OllamaTripContent(BaseModel):
    destination: str
    summary: str
    days: List[OllamaTripDay]


FALLBACK_CITY_COORDINATES = {
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
    # Database connection pool
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/voyanta")
    app.state.db_pool = None
    try:
        app.state.db_pool = await asyncpg.create_pool(db_url, timeout=10)
        logger.info("✅ Database pool connected.")
    except Exception as e:
        logger.warning(f"⚠️  Could not connect to DB on startup: {e}")

    # Shared async HTTP client for TomTom API calls
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
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
            encoded = query.replace(' ', '%20')
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


async def generate_trip_with_ollama(
    client: httpx.AsyncClient,
    location: str,
    days: int,
    start_day: date,
    coordinates: Coordinates,
) -> Optional[TripPlanResponse]:
    model_name = OLLAMA_MODEL
    try:
        tags_response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10.0)
        tags_response.raise_for_status()
        available_models = tags_response.json().get("models", [])
        available_names = [model.get("name") for model in available_models if model.get("name")]
        if available_names and model_name not in available_names:
            model_name = available_names[0]
    except Exception as exc:
        logger.warning("Ollama model discovery failed: %s", exc)

    schema = OllamaTripContent.model_json_schema()
    prompt = (
        f"Create a realistic {days}-day travel itinerary for {location}. "
        "Return only data matching the provided JSON schema. "
        "Use real-sounding landmarks, neighborhoods, food spots, and cultural activities for the destination. "
        "Give exactly 3 stops per day. Keep best_time short like '09:00 AM'. "
        "Make category labels concise like Food, Culture, Beach, Nature, Shopping, Wellness, Heritage."
    )

    try:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model_name,
                "stream": False,
                "format": schema,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a travel planner. Produce concise, realistic city itineraries as valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "options": {"temperature": 0.2},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content")
        if not content:
            return None
        ai_trip = OllamaTripContent.model_validate_json(content)
    except Exception as exc:
        logger.warning("Ollama trip generation failed for %s: %s", location, exc)
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
            lat_offset = (stop_index - 1) * 0.022 + (day_index * 0.008)
            lng_offset = (stop_index + 1) * 0.018 + (day_index * 0.008)
            stop_lat = coordinates.lat + lat_offset
            stop_lng = coordinates.lng + lng_offset
            day_coordinates.append([stop_lng, stop_lat])
            stop_image = await fetch_real_image(client, stop.title, f"{stop.title} {destination}")
            itinerary.append(
                TripStop(
                    id=f"ollama-{day_number}-{stop_index + 1}",
                    day=day_number,
                    date=trip_date.strftime("%b %d"),
                    time=stop.best_time or build_time_label(stop_index),
                    title=stop.title,
                    location=stop.location,
                    type=stop.category.upper(),
                    creators=f"Starts at {stop.best_time or build_time_label(stop_index)}",
                    distance=f"{round((stop_index + 1) * 2.1 + (day_index * 0.6), 1)}km",
                    elevation="N/A",
                    duration=f"{max(45, stop.duration_minutes)}m",
                    image=stop_image,
                    map_image_url=map_image_url,
                    lat=stop_lat,
                    lng=stop_lng,
                )
            )

        routes.append(build_day_route_from_coordinates(day_number, day_coordinates))

    if not itinerary:
        return None

    weather_label = await fetch_weather_label(client, coordinates.lat, coordinates.lng)
    return TripPlanResponse(
        destination=destination,
        destination_image=destination_image,
        map_image_url=build_tomtom_static_map_url(coordinates.lat, coordinates.lng, zoom=10),
        weather=weather_label if weather_label != "Weather unavailable" else "AI-planned",
        dates=format_date_range(start_day, days),
        days=days,
        coordinates=coordinates,
        itinerary=itinerary,
        routes=routes,
    )


def fallback_coordinates_for(location: str) -> Coordinates:
    location_lower = location.lower()
    for city_name, coordinates in FALLBACK_CITY_COORDINATES.items():
        if city_name in location_lower:
            return coordinates
    return Coordinates(lat=20.5937, lng=78.9629)


def build_fallback_trip_plan(location: str, days: int, start_day: date) -> TripPlanResponse:
    coordinates = fallback_coordinates_for(location)
    destination = location.title()
    destination_image = build_image_url(destination)
    routes: List[TripDayRoute] = []
    itinerary: List[TripStop] = []
    stop_templates = [
        ("Arrival and local check-in", "Arrival", 0.00, 0.00),
        ("Signature food trail", "Culinary", 0.03, 0.04),
        ("Landmark walk", "Sightseeing", -0.02, 0.05),
    ]

    for day_index in range(days):
        day_number = day_index + 1
        trip_date = start_day.fromordinal(start_day.toordinal() + day_index)
        day_coordinates: List[List[float]] = []

        for stop_index, (title, category, lat_offset, lng_offset) in enumerate(stop_templates):
            stop_lat = coordinates.lat + lat_offset + (day_index * 0.01)
            stop_lng = coordinates.lng + lng_offset + (day_index * 0.01)
            itinerary.append(
                TripStop(
                    id=f"fallback-{day_number}-{stop_index + 1}",
                    day=day_number,
                    date=trip_date.strftime("%b %d"),
                    time=build_time_label(stop_index),
                    title=f"{destination} {title}",
                    location=destination,
                    type=category.upper(),
                    creators=f"Starts at {build_time_label(stop_index)}",
                    distance=f"{round((stop_index + 1) * 1.8, 1)}km",
                    elevation="N/A",
                    duration=f"{90 + (stop_index * 30)}m",
                    image=destination_image,
                    map_image_url=build_image_url(f"map {destination}"),
                    lat=stop_lat,
                    lng=stop_lng,
                )
            )
            day_coordinates.append([stop_lng, stop_lat])

        route = build_day_route_from_coordinates(day_number, day_coordinates)
        route.total_distance_meters = 5400 + (day_index * 900)
        route.total_travel_time_seconds = 1800 + (day_index * 300)
        if route.geojson:
            route.geojson["properties"] = {"fallback": True}
        routes.append(route)

    return TripPlanResponse(
        destination=destination,
        destination_image=destination_image,
        map_image_url=build_tomtom_static_map_url(coordinates.lat, coordinates.lng, zoom=10),
        weather="Offline mode",
        dates=format_date_range(start_day, days),
        days=days,
        coordinates=coordinates,
        itinerary=itinerary,
        routes=routes,
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
    """
    Convert a free-text address or place name into geographic coordinates
    using TomTom's Fuzzy Search API.
    """
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
    """
    Convert geographic coordinates into a human-readable address using TomTom Reverse Geocoding.
    """
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
#  3. ROUTE CALCULATION — multi-stop itinerary routing
# ─────────────────────────────────────────────

@app.post("/route", response_model=RouteResponse, tags=["Routing"])
async def calculate_route(
    body: RouteRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    """
    Calculate an optimized multi-stop route across all itinerary waypoints.
    Returns total distance, travel time, and a GeoJSON LineString for the map.
    Supports car, pedestrian, and bicycle travel modes.
    """
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

    # Build GeoJSON LineString from all leg points
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
        "geometry": {
            "type": "LineString",
            "coordinates": all_points
        },
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
#  4. NEARBY POI SEARCH — discover local spots
# ─────────────────────────────────────────────

@app.get("/nearby-pois", response_model=List[POI], tags=["Discovery"])
async def nearby_pois(
    lat: float = Query(..., description="Center latitude"),
    lng: float = Query(..., description="Center longitude"),
    radius: int = Query(2000, ge=100, le=50000, description="Search radius in meters"),
    category: Optional[str] = Query(None, description="TomTom category filter (e.g. 'restaurant', 'museum', 'hotel')"),
    limit: int = Query(10, ge=1, le=50),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    """
    Discover nearby Points of Interest around a waypoint using TomTom's Nearby Search.
    Perfect for the Voyanta 'Smart Radar' feature — surfaces restaurants, museums, 
    landmarks, and events near any itinerary stop.
    """
    url = f"{TOMTOM_BASE}/search/2/nearbySearch/.json"
    params: dict = {
        "key": key,
        "lat": lat,
        "lon": lng,
        "radius": radius,
        "limit": limit,
        "view": "Unified",
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

    pois = []
    for item in data.get("results", []):
        pos = item.get("position", {})
        poi_data = item.get("poi", {})
        addr = item.get("address", {})
        categories = poi_data.get("categories", [""])
        pois.append(POI(
            id=item.get("id", ""),
            name=poi_data.get("name", "Unknown"),
            category=categories[0] if categories else "Place",
            lat=pos.get("lat", 0),
            lng=pos.get("lon", 0),
            distance_meters=item.get("dist"),
            address=addr.get("freeformAddress"),
            phone=poi_data.get("phone"),
            url=poi_data.get("url"),
        ))
    return pois


# ─────────────────────────────────────────────
#  5. FUZZY SEARCH — smart place search bar
# ─────────────────────────────────────────────

@app.get("/search", response_model=List[POI], tags=["Discovery"])
async def fuzzy_search(
    query: str = Query(..., description="Free text search (e.g. 'coffee shops in Reykjavik')"),
    lat: Optional[float] = Query(None, description="Bias results near this latitude"),
    lng: Optional[float] = Query(None, description="Bias results near this longitude"),
    radius: int = Query(10000, ge=100, le=100000),
    limit: int = Query(10, ge=1, le=50),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    """
    Full-text fuzzy search for places, addresses, and landmarks.
    Powers the Voyanta search bar to find any destination worldwide.
    """
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

    results = []
    for item in data.get("results", []):
        pos = item.get("position", {})
        poi_data = item.get("poi", {})
        addr = item.get("address", {})
        categories = poi_data.get("categories", [""])
        results.append(POI(
            id=item.get("id", ""),
            name=poi_data.get("name") or addr.get("freeformAddress", "Unknown"),
            category=categories[0] if categories else item.get("type", "Place"),
            lat=pos.get("lat", 0),
            lng=pos.get("lon", 0),
            distance_meters=item.get("dist"),
            address=addr.get("freeformAddress"),
        ))
    return results


@app.post("/trip-plan", response_model=TripPlanResponse, tags=["Trips"])
async def build_trip_plan(
    body: TripPlanRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    key: Optional[str] = Depends(optional_tomtom_key)
):
    """
    Build a trip dashboard payload from a user-entered destination and trip length.
    The destination is geocoded with TomTom, nearby POIs are fetched, and each day
    receives a small set of itinerary stops plus route geometry when available.
    """
    days = max(1, min(body.days, 30))
    start_day = body.start_date or date.today()
    default_coordinates = fallback_coordinates_for(body.location)
    if not key:
        logger.warning("TomTom API key missing. Trying Ollama trip plan for %s", body.location)
        ollama_trip = await generate_trip_with_ollama(
            client,
            body.location,
            days,
            start_day,
            default_coordinates,
        )
        return ollama_trip or build_fallback_trip_plan(body.location, days, start_day)

    geocode_url = f"{TOMTOM_BASE}/search/2/geocode/{body.location}.json"
    geocode_params = {"key": key, "limit": 1, "typeahead": True}
    try:
        geocode_response = await client.get(geocode_url, params=geocode_params)
        geocode_response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.warning("TomTom geocoding HTTP error for %s: %s", body.location, e)
        ollama_trip = await generate_trip_with_ollama(
            client,
            body.location,
            days,
            start_day,
            default_coordinates,
        )
        return ollama_trip or build_fallback_trip_plan(body.location, days, start_day)
    except httpx.RequestError as e:
        logger.warning("TomTom geocoding unreachable for %s: %s", body.location, e)
        ollama_trip = await generate_trip_with_ollama(
            client,
            body.location,
            days,
            start_day,
            default_coordinates,
        )
        return ollama_trip or build_fallback_trip_plan(body.location, days, start_day)

    geocode_results = geocode_response.json().get("results", [])
    if not geocode_results:
        ollama_trip = await generate_trip_with_ollama(
            client,
            body.location,
            days,
            start_day,
            default_coordinates,
        )
        return ollama_trip or build_fallback_trip_plan(body.location, days, start_day)

    destination = geocode_results[0]
    destination_position = destination.get("position", {})
    destination_address = destination.get("address", {})
    destination_name = destination_address.get("freeformAddress") or body.location
    dest_lat = destination_position.get("lat")
    dest_lng = destination_position.get("lon")

    if dest_lat is None or dest_lng is None:
        raise HTTPException(status_code=502, detail="Destination coordinates were missing from geocoding response.")

    poi_url = f"{TOMTOM_BASE}/search/2/nearbySearch/.json"
    poi_params = {
        "key": key,
        "lat": dest_lat,
        "lon": dest_lng,
        "radius": 12000,
        "limit": max(days * 4, 8),
        "view": "Unified",
    }
    try:
        poi_response = await client.get(poi_url, params=poi_params)
        poi_response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.warning("TomTom POI search HTTP error for %s: %s", body.location, e)
        ollama_trip = await generate_trip_with_ollama(
            client,
            destination_name,
            days,
            start_day,
            Coordinates(lat=dest_lat, lng=dest_lng),
        )
        return ollama_trip or build_fallback_trip_plan(body.location, days, start_day)
    except httpx.RequestError as e:
        logger.warning("TomTom POI search unreachable for %s: %s", body.location, e)
        ollama_trip = await generate_trip_with_ollama(
            client,
            destination_name,
            days,
            start_day,
            Coordinates(lat=dest_lat, lng=dest_lng),
        )
        return ollama_trip or build_fallback_trip_plan(body.location, days, start_day)

    raw_pois = poi_response.json().get("results", [])
    if not raw_pois:
        logger.warning("No POIs found for %s. Trying Ollama trip plan.", body.location)
        ollama_trip = await generate_trip_with_ollama(
            client,
            destination_name,
            days,
            start_day,
            Coordinates(lat=dest_lat, lng=dest_lng),
        )
        return ollama_trip or build_fallback_trip_plan(body.location, days, start_day)

    destination_image = await fetch_destination_image(client, destination_name)
    weather_label = await fetch_weather_label(client, dest_lat, dest_lng)
    itinerary: List[TripStop] = []
    routes: List[TripDayRoute] = []
    stops_per_day = 3
    fallback_map_image = build_image_url(f"map {destination_name}")

    for day_index in range(days):
        day_number = day_index + 1
        trip_date = start_day.fromordinal(start_day.toordinal() + day_index)
        start_idx = day_index * stops_per_day
        day_pois = raw_pois[start_idx:start_idx + stops_per_day]
        if not day_pois:
            day_pois = raw_pois[: min(stops_per_day, len(raw_pois))]

        day_waypoints = []
        for stop_index, poi in enumerate(day_pois):
            pos = poi.get("position", {})
            address = poi.get("address", {})
            poi_data = poi.get("poi", {})
            categories = poi_data.get("categories", []) or [poi.get("type", "Place")]
            title = poi_data.get("name") or address.get("freeformAddress") or f"Stop {stop_index + 1}"
            stop_lat = pos.get("lat", dest_lat)
            stop_lng = pos.get("lon", dest_lng)
            distance_meters = poi.get("dist") or 0
            stop_location = address.get("freeformAddress") or destination_name
            stop_image = await fetch_real_image(client, title, f"{title} {destination_name}")
            itinerary.append(
                TripStop(
                    id=f"{day_number}-{stop_index + 1}-{poi.get('id', title)}",
                    day=day_number,
                    date=trip_date.strftime("%b %d"),
                    time=build_time_label(stop_index),
                    title=title,
                    location=stop_location,
                    type=(categories[0] or "Place").upper().replace("_", " "),
                    creators=f"Starts at {build_time_label(stop_index)}",
                    distance=f"{round(distance_meters / 1000, 1)}km" if distance_meters else "Local",
                    elevation="N/A",
                    duration=f"{estimate_duration_minutes(distance_meters, stop_index)}m",
                    image=stop_image,
                    map_image_url=fallback_map_image,
                    lat=stop_lat,
                    lng=stop_lng,
                )
            )
            day_waypoints.append(RouteWaypoint(lat=stop_lat, lng=stop_lng))

        if len(day_waypoints) < 2:
            routes.append(TripDayRoute(day=day_number))
            continue

        locations = ":".join([f"{wp.lat},{wp.lng}" for wp in day_waypoints])
        route_url = f"{TOMTOM_BASE}/routing/1/calculateRoute/{locations}/json"
        route_params = {
            "key": key,
            "travelMode": "car",
            "routeType": "fastest",
            "traffic": True,
        }
        try:
            route_response = await client.get(route_url, params=route_params)
            route_response.raise_for_status()
            route_data = route_response.json().get("routes", [])
        except Exception as exc:
            logger.warning("Route generation failed for day %s: %s", day_number, exc)
            route_data = []

        if not route_data:
            routes.append(TripDayRoute(day=day_number))
            continue

        route = route_data[0]
        summary = route.get("summary", {})
        coords = []
        for leg in route.get("legs", []):
            for point in leg.get("points", []):
                coords.append([point.get("longitude"), point.get("latitude")])

        routes.append(
            TripDayRoute(
                day=day_number,
                geojson={
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords,
                    },
                    "properties": {},
                },
                total_distance_meters=summary.get("lengthInMeters", 0),
                total_travel_time_seconds=summary.get("travelTimeInSeconds", 0),
            )
        )

    return TripPlanResponse(
        destination=destination_name,
        destination_image=destination_image,
        weather=weather_label,
        dates=format_date_range(start_day, days),
        days=days,
        coordinates=Coordinates(lat=dest_lat, lng=dest_lng),
        itinerary=itinerary,
        routes=routes,
    )


# ─────────────────────────────────────────────
#  6. TRAFFIC INCIDENTS — live traffic alerts
# ─────────────────────────────────────────────

@app.get("/traffic", response_model=List[TrafficIncident], tags=["Traffic"])
async def get_traffic_incidents(
    lat: float = Query(..., description="Bounding box center latitude"),
    lng: float = Query(..., description="Bounding box center longitude"),
    radius_km: float = Query(5.0, ge=0.5, le=50.0, description="Radius in km"),
    client: httpx.AsyncClient = Depends(get_http_client),
    key: str = Depends(tomtom_key)
):
    """
    Fetch live traffic incidents (accidents, roadworks, closures) near a location.
    Used by Voyanta to warn travelers about disruptions along their route.
    """
    # Build a rough bounding box from center + radius
    delta = radius_km / 111.0
    min_lat, max_lat = lat - delta, lat + delta
    min_lng, max_lng = lng - delta, lng + delta
    bbox = f"{min_lng},{min_lat},{max_lng},{max_lat}"

    url = f"{TOMTOM_BASE}/traffic/services/5/incidentDetails"
    params = {
        "key": key,
        "bbox": bbox,
        "fields": "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,events{description,code},startTime,endTime,from,to,length,delay,roadNumbers,timeValidity}}}",
        "language": "en-GB",
        "t": "1111",
        "timeValidityFilter": "present",
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
            coords = coords[0]  # take first point of a line

        events = props.get("events", [{}])
        desc = events[0].get("description", "Traffic incident") if events else "Traffic incident"
        mag = props.get("magnitudeOfDelay", 0)

        incidents.append(TrafficIncident(
            id=props.get("id", ""),
            description=f"{desc} ({props.get('from', '')} → {props.get('to', '')})",
            severity=severity_map.get(mag, "Unknown"),
            lat=coords[1] if len(coords) > 1 else lat,
            lng=coords[0],
        ))
    return incidents


# ─────────────────────────────────────────────
#  7. DATABASE: Smart Event Suggestions (existing)
# ─────────────────────────────────────────────

@app.get("/trips/{trip_id}/smart-suggestions", response_model=List[EventFestival], tags=["Trips"])
async def get_smart_suggestions(
    trip_id: UUID,
    day_date: date,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Finds events happening within a 5km radius of any scheduled itinerary waypoint
    for that specific calendar day using PostGIS ST_DWithin.
    """
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
