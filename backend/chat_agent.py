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
    active_itinerary: Optional[List[Dict[str, Any]]] = None
) -> str:
    itinerary_summary = "None currently loaded"
    if active_itinerary:
        itinerary_summary = ", ".join([
            f"Day {s.get('day', 1)}: {s.get('title', '')} ({s.get('time', 'Slot')})"
            for s in active_itinerary[:8]
        ])

    return f"""
You are **Voya**, an elite AI travel intelligence engine and concierge.
Current Trip State:
- Primary Destination & Region: {destination or 'Awaiting user input'}
- Preferred Currency: {currency}
- Primary Interaction Language: {language}
- Active Itinerary Context: {itinerary_summary}

YOUR OPERATIONAL MANDATE:
1. **Multilingual Auto-Detection:** Seamlessly respond in the language the user writes in (Hindi, Spanish, French, Japanese, German, etc.) while preserving all structured markdown, dynamic booking URLs, and action tags.
2. **Authentic Accommodations:** When recommending stays, call `find_accommodations` to produce real deep links for Skyscanner, Booking.com, Airbnb, and Agoda.
3. **Attraction & Tour Bookings:** When suggesting activities, day trips, museum entries, or theme parks, call `find_activity_tickets` to provide direct search links for Klook, Headout, GetYourGuide, and Viator.
4. **Hyper-Local Live Events & Nightlife:** When suggesting live concerts, theater, club nights, cultural festivals, or sports, call `find_live_events`. It supports city and district/neighborhood scoping across Eventbrite, Ticketmaster, BookMyShow, Paytm Insider, Resident Advisor, and DICE.
5. **Interactive Itinerary Execution:** When the user asks to add, remove, or modify spots, call `add_venue_to_itinerary` so the frontend canvas updates in real time.
6. **Zero Generic Fluff:** Provide specific venue names, dish recommendations, transport lines, and local cost estimates formatted in {currency}.
"""

def get_chat_agent_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "find_accommodations",
            "description": "Generate dynamic booking deep-links for stays, hotels, luxury resorts, boutique villas, or hostels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City or region name"},
                    "district_or_area": {"type": "string", "description": "Specific district, neighborhood, or borough"},
                    "stay_type": {"type": "string", "description": "Hotels, Boutique, Hostels, Resorts, or Villas"},
                    "checkin": {"type": "string", "description": "Check-in date (YYYY-MM-DD)"},
                    "checkout": {"type": "string", "description": "Check-out date (YYYY-MM-DD)"}
                },
                "required": ["destination"]
            }
        },
        {
            "name": "find_activity_tickets",
            "description": "Generate authentic tour, museum, adventure, and attraction ticket booking links (Klook, Headout, GetYourGuide, Viator).",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Target city, landmark, or island"},
                    "query": {"type": "string", "description": "Specific activity or venue (e.g. Scuba Diving, Museum Ticket, Desert Safari)"},
                    "category": {"type": "string", "description": "Tours, Theme Parks, Water Sports, Museums, Day Trips"}
                },
                "required": ["destination", "query"]
            }
        },
        {
            "name": "find_live_events",
            "description": "Find live concerts, cultural festivals, sports, comedy shows, and club events with direct district-aware ticketing links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City or metropolitan area"},
                    "district_or_neighborhood": {"type": "string", "description": "Specific district, zone, or locality"},
                    "event_type": {"type": "string", "description": "Music, Festival, Nightlife, Cultural, Comedy, Sports"}
                },
                "required": ["destination"]
            }
        },
        {
            "name": "search_additional_venues",
            "description": "Locate off-pillar hidden gems, viewpoints, specialty dining, or transit stops.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City name"},
                    "district": {"type": "string", "description": "Neighborhood or district"},
                    "category": {"type": "string", "description": "Category (e.g. Secret Spots, Street Food, Night View)"},
                    "query": {"type": "string", "description": "Specific place or experience search term"}
                },
                "required": ["destination", "query"]
            }
        },
        {
            "name": "add_venue_to_itinerary",
            "description": "Directly inject a verified place or activity into the active user itinerary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {"type": "string", "description": "Official name of the venue"},
                    "destination": {"type": "string", "description": "City or locality name"},
                    "day": {"type": "integer", "description": "Day index (1, 2, 3...)"},
                    "time_slot": {"type": "string", "description": "Target time or period (e.g. 10:00 AM, Afternoon, Sunset)"}
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
    district = args.get("district_or_area") or args.get("district_or_neighborhood") or args.get("district", "")
    full_loc = f"{district} {dest}".strip() if district else dest
    loc_encoded = urllib.parse.quote(full_loc)
    dest_encoded = urllib.parse.quote(dest)

    # 1. ACCOMMODATIONS ENGINE
    if tool_name == "find_accommodations":
        stay_type = args.get("stay_type", "Hotels")
        checkin = args.get("checkin", "")
        checkout = args.get("checkout", "")

        loc_encoded = urllib.parse.quote(full_loc)
        loc_slug = re.sub(r'[^a-zA-Z0-9]+', '-', full_loc.lower()).strip('-')

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

    # 2. ACTIVITY & TOUR TICKETING (KLOOK, HEADOUT, GETYOURGUIDE, VIATOR)
    elif tool_name == "find_activity_tickets":
        query = args.get("query", "").strip()
        search_target = f"{query} {dest}".strip()
        target_encoded = urllib.parse.quote(search_target)

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

    # 3. LIVE EVENTS & DISTRICT-AWARE TICKETING
    elif tool_name == "find_live_events":
        event_type = args.get("event_type", "Events")
        event_encoded = urllib.parse.quote(f"{event_type} {full_loc}".strip())

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

    # 4. EXTRA VENUE & LOCAL DISCOVERY
    elif tool_name == "search_additional_venues":
        query = args.get("query", "")
        category = args.get("category", "General")
        venue_query = f"{query} {full_loc}".strip()
        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(venue_query)}"

        return {
            "status": "success",
            "venue": {
                "title": query.title(),
                "category": category,
                "location": full_loc,
                "maps_url": maps_url
            }
        }

    # 5. DYNAMIC ITINERARY MANIPULATION
    elif tool_name == "add_venue_to_itinerary":
        venue_name = args.get("venue_name", "")
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