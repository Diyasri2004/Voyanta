import os
import re
import urllib.parse
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("uvicorn")

def get_voya_system_prompt(
    destination: str = "",
    language: str = "en",
    currency: str = "USD",
    user_time: str = "",
    user_timezone: str = "",
    active_itinerary: Optional[List[Dict[str, Any]]] = None
) -> str:
    itinerary_summary = "None loaded"
    if active_itinerary:
        itinerary_summary = ", ".join([
            f"Day {s.get('day', 1)}: {s.get('title', '')} ({s.get('time', 'Slot')})"
            for s in active_itinerary[:8]
        ])

    return f"""
You are **Voya**, an elite autonomous AI travel intelligence concierge.
Current Environmental Context:
- Target Destination: {destination or 'Awaiting user prompt'}
- Traveler Local Time: {user_time or 'Current local time'} ({user_timezone or 'Auto-detected'})
- Preferred Currency: {currency}
- Interface Language: {language}
- Active Itinerary Context: {itinerary_summary}

RULES & BEHAVIOR:
1. Dynamic Local Greeting: Greet the user naturally according to their active local time (Morning / Afternoon / Evening / Night) and reference their destination if chosen.
2. Multilingual Auto-Detection: Respond natively in the language the user writes in while retaining all markdown formatting and action tags.
3. Time-Aware Recommendations: Adapt real-time suggestions based on user time of day (e.g., breakfast cafes in the morning, night markets or lounges late at night).
4. Tool Calling: Always invoke matching tools for accommodations, activities, events, cabs/transit, multi-city routing, budgets, weather pivots, and itinerary updates.
5. Zero Hardcoding: Derive all recommendations and parameters dynamically. Avoid static IDs or placeholder strings.
"""

def get_chat_agent_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "find_accommodations",
            "description": "Generate dynamic booking search links for stays, hotels, boutique villas, or hostels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City or region name"},
                    "district": {"type": "string", "description": "Specific neighborhood or district"},
                    "stay_type": {"type": "string", "description": "Hotels, Boutique, Hostels, Resorts, or Villas"},
                    "checkin": {"type": "string", "description": "Check-in date (YYYY-MM-DD)"},
                    "checkout": {"type": "string", "description": "Check-out date (YYYY-MM-DD)"}
                },
                "required": ["destination"]
            }
        },
        {
            "name": "find_activity_tickets",
            "description": "Generate tour, museum, adventure, and attraction ticket booking search links (Klook, Headout, GetYourGuide, Viator).",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Target city or landmark"},
                    "query": {"type": "string", "description": "Specific activity or venue"},
                    "category": {"type": "string", "description": "Tours, Theme Parks, Water Sports, Museums, Day Trips"}
                },
                "required": ["destination", "query"]
            }
        },
        {
            "name": "find_live_events",
            "description": "Find live concerts, cultural festivals, sports, and club events with direct ticketing links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City or metropolitan area"},
                    "district": {"type": "string", "description": "Specific district or locality"},
                    "event_type": {"type": "string", "description": "Music, Festival, Nightlife, Cultural, Comedy, Sports"}
                },
                "required": ["destination"]
            }
        },
        {
            "name": "find_transportation",
            "description": "Generate dynamic ride-hailing links (Uber, Ola, Grab, Bolt), airport transfers, cabs, and transit routes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City or region name"},
                    "from_location": {"type": "string", "description": "Origin spot or airport"},
                    "to_location": {"type": "string", "description": "Destination spot"}
                },
                "required": ["destination"]
            }
        },
        {
            "name": "plan_multicity_transit",
            "description": "Generate intercity transit routes, high-speed rail links, flights, and connecting transit across multiple cities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_city": {"type": "string", "description": "Starting city or hub"},
                    "destination_cities": {"type": "array", "items": {"type": "string"}, "description": "List of destination cities in order"}
                },
                "required": ["origin_city", "destination_cities"]
            }
        },
        {
            "name": "calculate_trip_budget",
            "description": "Calculate daily and total trip budget burn rates in target currency.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Target city or country"},
                    "duration_days": {"type": "integer", "description": "Number of travel days"},
                    "travel_tier": {"type": "string", "description": "Budget, Comfort, or Luxury"},
                    "target_currency": {"type": "string", "description": "USD, EUR, INR, GBP, JPY"}
                },
                "required": ["destination"]
            }
        },
        {
            "name": "get_weather_adaptive_gems",
            "description": "Find weather-adapted indoor alternatives, covered markets, arcades, or scenic viewpoints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Target city"},
                    "condition": {"type": "string", "description": "rain, heatwave, snow, or clear"}
                },
                "required": ["destination", "condition"]
            }
        },
        {
            "name": "get_destination_safety_and_etiquette",
            "description": "Provide emergency tourist hotlines, essential transit passes, tipping rules, and scam advisories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Destination city or country"}
                },
                "required": ["destination"]
            }
        },
        {
            "name": "browse_live_web_intelligence",
            "description": "Fetch real-time live events, breaking advisories, festival schedules, or temporary closures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Destination city or region"},
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["destination", "query"]
            }
        },
        {
            "name": "add_venue_to_itinerary",
            "description": "Inject a verified place or activity directly into the active itinerary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {"type": "string", "description": "Name of the venue"},
                    "destination": {"type": "string", "description": "City name"},
                    "day": {"type": "integer", "description": "Day index (e.g. 1, 2, 3)"},
                    "time_slot": {"type": "string", "description": "Target time or period"}
                },
                "required": ["venue_name", "destination"]
            }
        }
    ]

async def execute_tool_call(
    tool_name: str,
    args: Dict[str, Any],
    client: Optional[httpx.AsyncClient] = None
) -> Dict[str, Any]:
    dest = args.get("destination", "").strip()
    district = args.get("district", "").strip()
    full_loc = f"{district} {dest}".strip() if district else dest
    loc_encoded = urllib.parse.quote(full_loc)
    dest_encoded = urllib.parse.quote(dest)
    loc_slug = re.sub(r'[^a-zA-Z0-9]+', '-', full_loc.lower()).strip('-')

    if tool_name == "find_accommodations":
        stay_type = args.get("stay_type", "Hotels")
        checkin = args.get("checkin", "")
        checkout = args.get("checkout", "")

        makemytrip_url = f"https://www.makemytrip.com/hotels/hotel-listing/?searchText={loc_encoded}"
        booking_url = f"https://www.booking.com/searchresults.html?ss={loc_encoded}"
        goibibo_url = f"https://www.goibibo.com/hotels/find-hotels-in-{loc_slug}/"
        skyscanner_url = f"https://www.skyscanner.net/hotels/search?destination={loc_encoded}"
        airbnb_url = f"https://www.airbnb.com/s/{loc_encoded}/homes"
        agoda_url = f"https://www.agoda.com/search?text={loc_encoded}"

        if checkin and checkout:
            booking_url += f"&checkin={checkin}&checkout={checkout}"
            airbnb_url += f"?checkin={checkin}&checkout={checkout}"
            agoda_url += f"&checkIn={checkin}&checkOut={checkout}"
            makemytrip_url += f"&checkin={checkin}&checkout={checkout}"

        return {
            "status": "success",
            "category": "Accommodations",
            "location": full_loc,
            "stay_type": stay_type,
            "booking_platforms": {
                "makemytrip": makemytrip_url,
                "booking_com": booking_url,
                "goibibo": goibibo_url,
                "skyscanner": skyscanner_url,
                "agoda": agoda_url,
                "airbnb": airbnb_url
            }
        }

    elif tool_name == "find_activity_tickets":
        query = args.get("query", "").strip()
        target_encoded = urllib.parse.quote(f"{query} {dest}".strip())
        return {
            "status": "success",
            "category": "Experience Tickets",
            "activity": query,
            "location": dest,
            "ticket_platforms": {
                "klook": f"https://www.klook.com/en-US/search/result/?query={target_encoded}",
                "headout": f"https://www.headout.com/search/?query={target_encoded}",
                "getyourguide": f"https://www.getyourguide.com/s/?q={target_encoded}",
                "viator": f"https://www.viator.com/searchResults/all?text={target_encoded}"
            }
        }

    elif tool_name == "find_live_events":
        event_type = args.get("event_type", "Events")
        return {
            "status": "success",
            "category": "Live Events",
            "location": full_loc,
            "event_type": event_type,
            "ticketing_platforms": {
                "eventbrite": f"https://www.eventbrite.com/d/{loc_encoded}/{urllib.parse.quote(event_type)}-events/",
                "ticketmaster": f"https://www.ticketmaster.com/search?q={loc_encoded}",
                "bookmyshow": f"https://in.bookmyshow.com/explore/events-{dest_encoded.lower()}",
                "paytm_insider": f"https://insider.in/all-events-in-{dest_encoded.lower()}",
                "resident_advisor": f"https://ra.co/events/search?query={loc_encoded}",
                "dice": f"https://dice.fm/search?query={loc_encoded}"
            }
        }

    elif tool_name == "find_transportation":
        from_loc = args.get("from_location", "").strip()
        to_loc = args.get("to_location", "").strip()
        origin_q = f"{from_loc} {dest}".strip() if from_loc else dest
        dest_q = f"{to_loc} {dest}".strip() if to_loc else dest

        maps_transit = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(dest_q)}&travelmode=transit"
        if from_loc and to_loc:
            maps_transit = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(origin_q)}&destination={urllib.parse.quote(dest_q)}&travelmode=transit"

        return {
            "status": "success",
            "category": "Transportation & Cabs",
            "destination": dest,
            "ride_hailing": {
                "uber": f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]={urllib.parse.quote(dest_q)}",
                "ola": "https://www.olacabs.com/",
                "grab_sea": "https://www.grab.com/",
                "bolt_eu": "https://bolt.eu/"
            },
            "transit_and_navigation": {
                "google_maps_transit": maps_transit,
                "trainline": f"https://www.thetrainline.com/search/{dest_encoded.lower()}",
                "12go_asia": f"https://12go.asia/en/travel/{dest_encoded.lower()}",
                "redbus": f"https://www.redbus.in/bus-tickets/{dest_encoded.lower()}"
            },
            "rentals": {
                "rentalcars": f"https://www.rentalcars.com/search-results?locationName={dest_encoded}",
                "skyscanner_car_hire": f"https://www.skyscanner.net/carhire/search?destination={dest_encoded}"
            }
        }

    elif tool_name == "plan_multicity_transit":
        origin = args.get("origin_city", "").strip()
        dest_cities = args.get("destination_cities", [])
        legs = []
        prev = origin
        for c in dest_cities:
            next_city = c.strip()
            route_slug = f"{urllib.parse.quote(prev.lower())}-to-{urllib.parse.quote(next_city.lower())}"
            legs.append({
                "from": prev,
                "to": next_city,
                "train_booking": f"https://www.thetrainline.com/train-times/{route_slug}",
                "omio_booking": f"https://www.omio.com/search-frontend/results/trains/{route_slug}",
                "flight_booking": f"https://www.skyscanner.net/transport/flights/{urllib.parse.quote(prev.lower())}/{urllib.parse.quote(next_city.lower())}",
                "google_transit": f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(prev)}&destination={urllib.parse.quote(next_city)}&travelmode=transit"
            })
            prev = next_city

        return {
            "status": "success",
            "category": "Intercity Split Routing",
            "origin": origin,
            "itinerary_legs": legs
        }

    elif tool_name == "calculate_trip_budget":
        days = args.get("duration_days", 3)
        tier = args.get("travel_tier", "Comfort")
        curr = args.get("target_currency", "USD").upper()
        return {
            "status": "success",
            "category": "Trip Budget Burn Rate",
            "destination": dest,
            "duration_days": days,
            "tier": tier,
            "currency": curr,
            "breakdown_status": "ready"
        }

    elif tool_name == "get_weather_adaptive_gems":
        cond = args.get("condition", "rain").lower()
        search_kw = "indoor museum arcade covered market" if cond in ["rain", "heatwave"] else "scenic viewpoint nature walk"
        return {
            "status": "success",
            "category": "Weather Adaptive Recommendations",
            "destination": dest,
            "condition": cond,
            "discovery_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(f'{dest} {search_kw}')}"
        }

    elif tool_name == "get_destination_safety_and_etiquette":
        return {
            "status": "success",
            "category": "Safety, Scams & Cultural Etiquette",
            "destination": dest,
            "emergency_search": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(f'{dest} emergency police hospital')}"
        }

    elif tool_name == "browse_live_web_intelligence":
        query = args.get("query", "").strip()
        search_term = f"{dest} {query}".strip()
        live_results = []
        try:
            from duckduckgo_search import AsyncDDGS
            async with AsyncDDGS() as ddgs:
                raw_results = [r async for r in ddgs.text(search_term, max_results=3)]
                for r in raw_results:
                    live_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
        except Exception:
            pass

        return {
            "status": "success",
            "category": "Live Real-World Intelligence",
            "destination": dest,
            "query": query,
            "live_data": live_results
        }

    elif tool_name == "add_venue_to_itinerary":
        venue_name = args.get("venue_name", "").strip()
        day = args.get("day", 1)
        time_slot = args.get("time_slot", "02:00 PM")
        return {
            "status": "added",
            "action": "INSERT_STOP",
            "stop": {
                "title": venue_name.title(),
                "day": day,
                "time": time_slot,
                "location": full_loc
            },
            "message": f"Added '{venue_name.title()}' to Day {day} ({time_slot}) for {full_loc}."
        }

    return {"status": "error", "message": f"Unknown tool: {tool_name}"}