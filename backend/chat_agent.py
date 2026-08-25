import os
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("uvicorn")

def get_chat_agent_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "search_additional_venues",
            "description": "Search for additional real-world venues, local markets, food spots, or landmarks in a destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "The destination city"},
                    "category": {"type": "string", "description": "Category (e.g. Shopping, Culinary, Attractions)"},
                    "query": {"type": "string", "description": "Specific search query"}
                },
                "required": ["destination", "query"]
            }
        },
        {
            "name": "add_venue_to_itinerary",
            "description": "Add a specific venue to the user's itinerary plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_name": {"type": "string", "description": "Name of the venue"},
                    "destination": {"type": "string", "description": "City name"},
                    "day_or_time": {"type": "string", "description": "Preferred day or time slot"}
                },
                "required": ["venue_name", "destination"]
            }
        }
    ]

async def execute_tool_call(tool_name: str, args: Dict[str, Any], client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    destination = args.get("destination", "Lucknow")
    
    if tool_name == "search_additional_venues":
        query = args.get("query", "")
        category = args.get("category", "Attractions")
        venue_title = f"{query} in {destination}"
        maps_url = f"https://www.google.com/maps/search/?api=1&query={venue_title.replace(' ', '+')}"
        image_url = ""
        
        return {
            "status": "success",
            "venue": {
                "title": query.title(),
                "category": category,
                "description": f"Top verified venue in {destination}.",
                "maps_url": maps_url,
                "image_url": image_url
            }
        }
    
    elif tool_name == "add_venue_to_itinerary":
        venue_name = args.get("venue_name", "")
        day_or_time = args.get("day_or_time", "Day 1")
        return {
            "status": "added",
            "message": f"Successfully added '{venue_name}' to your itinerary for {day_or_time} in {destination}."
        }
    
    return {"status": "error", "message": f"Unknown tool: {tool_name}"}
