"""Offline tests for the Voya chat engine (fake model + fake data, no network)."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from voya_engine import Deps, RateLimiter, run_chat, clamp_request, MAX_MESSAGE_CHARS


def extract(text):
    try:
        return json.loads(text)
    except Exception:
        return None


class FakeModel:
    """Scripted replies; records every prompt it was given."""
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    async def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def make_deps(model, events=None, pois=None, weather=None):
    async def build_events(d, s, e):
        return events if events is not None else []

    async def poi_search(q, d):
        return pois if pois is not None else []

    async def get_weather(d, s, e):
        return weather

    return Deps(call_ai=model, extract_json=extract, build_events=build_events, poi_search=poi_search,
                weather=get_weather, parse_day=lambda s: None, client=None)


def run(coro):
    return asyncio.run(coro)


REQ = {"message": "hi", "destination": "Lisbon", "language": "en", "currency": "EUR", "history": [],
       "trip_start": "2026-12-01", "trip_end": "2026-12-04", "shown_places": ["Belem Tower"]}


def test_small_talk_uses_one_model_call():
    m = FakeModel('{"tools": [], "reply": "Hello! Where to?"}')
    out = run(run_chat({**REQ, "message": "hey"}, make_deps(m)))
    assert out["reply"] == "Hello! Where to?" and out["action"] is None
    assert len(m.prompts) == 1


def test_events_use_real_data_and_booking_links():
    ev = [{"title": "Fado Night", "when": "Sat, Dec 02, 2026", "venue": "Clube de Fado", "url": "https://tickets.example/fado",
           "source": "Ticketmaster", "note": "Happening during your trip", "price": "EUR 25"}]
    m = FakeModel('{"tools": [{"name": "search_events", "arguments": {"destination": "Lisbon"}}], "reply": ""}',
                  "There is **Fado Night** on Dec 2: [Book](https://tickets.example/fado)")
    out = run(run_chat({**REQ, "message": "any events?"}, make_deps(m, events=ev)))
    assert len(m.prompts) == 2
    assert "Fado Night" in m.prompts[1] and "tickets.example" in m.prompts[1]   # tool data reached the answer prompt
    assert out["action"]["events"][0]["book_url"] == "https://tickets.example/fado"
    assert "ticketmaster" in out["action"]["event_platforms"]
    assert "bookmyshow" not in out["action"]["event_platforms"]                 # not offered outside India


def test_india_gets_regional_booking_sites():
    m = FakeModel('{"tools": [{"name": "search_events", "arguments": {}}], "reply": ""}', "ok")
    out = run(run_chat({**REQ, "destination": "Jaipur"}, make_deps(m, events=[]), in_india=True))
    assert "bookmyshow" in out["action"]["event_platforms"]
    assert "No live listings" in m.prompts[1]


def test_no_events_still_returns_real_booking_sites():
    m = FakeModel('{"tools": [{"name": "search_events", "arguments": {}}], "reply": ""}', "Nothing listed, try these.")
    out = run(run_chat(REQ, make_deps(m, events=[])))
    assert "events" not in out["action"] and out["action"]["event_platforms"]


def test_offbeat_places_skip_cards_already_shown():
    pois = [{"name": f"Famous {i}", "area": "Centre", "address": "x", "url": ""} for i in range(6)] + \
           [{"name": "Belem Tower", "area": "Belem", "address": "x", "url": ""},
            {"name": "Secret Garden", "area": "Alfama", "address": "Rua A", "url": "garden.example"}] + \
           [{"name": f"Filler {i}", "area": "z", "address": "z", "url": ""} for i in range(8)]
    m = FakeModel('{"tools": [{"name": "discover_places", "arguments": {"query": "garden", "vibe": "offbeat"}}], "reply": ""}', "Try Secret Garden.")
    out = run(run_chat({**REQ, "message": "offbeat gardens"}, make_deps(m, pois=pois)))
    names = [p["name"] for p in out["action"]["places"]]
    assert "Belem Tower" not in names                       # already a card
    assert "Famous 0" not in names                          # most prominent hits skipped for 'offbeat'
    assert "Secret Garden" in names
    assert out["action"]["places"][0]["maps_url"].startswith("https://www.google.com/maps")


def test_weather_tool_result_reaches_answer():
    w = {"temp_c": 14, "condition": "Light rain", "daily": [{"date": "2026-12-01", "max_c": 15, "min_c": 9, "condition": "Rain"}], "forecast_available": True}
    m = FakeModel('{"tools": [{"name": "get_weather", "arguments": {}}], "reply": ""}', "Pack a raincoat.")
    run(run_chat({**REQ, "message": "weather?"}, make_deps(m, weather=w)))
    assert "Light rain" in m.prompts[1]


def test_tool_failure_does_not_break_chat():
    async def boom(d, s, e):
        raise RuntimeError("down")
    m = FakeModel('{"tools": [{"name": "search_events", "arguments": {}}], "reply": ""}', "Sorry, events are unavailable.")
    deps = make_deps(m); deps.build_events = boom
    out = run(run_chat(REQ, deps))
    assert out["reply"]


def test_garbage_plan_falls_back_gracefully():
    m = FakeModel("Sure! Lisbon is lovely in winter.")
    out = run(run_chat(REQ, make_deps(m)))
    assert "Lisbon" in out["reply"]


def test_unknown_tool_is_ignored_and_urls_are_sanitised():
    ev = [{"title": "X", "url": "javascript:alert(1)", "when": "", "venue": ""}]
    m = FakeModel('{"tools": [{"name": "rm_rf", "arguments": {}}, {"name": "search_events", "arguments": {}}], "reply": ""}', "ok")
    out = run(run_chat(REQ, make_deps(m, events=ev)))
    assert out["action"]["events"][0]["book_url"] == ""


def test_context_and_guardrails_in_prompt():
    m = FakeModel('{"tools": [], "reply": "ok"}')
    run(run_chat({**REQ, "language": "hi"}, make_deps(m)))
    p = m.prompts[0]
    assert "Lisbon" in p and "2026-12-01" in p and "Belem Tower" in p and "Never invent" in p and "hi" in p


def test_input_is_clamped():
    msg, hist = clamp_request("x" * 5000, [{"role": "user", "content": "y" * 9000}] * 30)
    assert len(msg) == MAX_MESSAGE_CHARS and len(hist) == 10 and len(hist[0]["content"]) == 1500


def test_rate_limiter():
    rl = RateLimiter(per_minute=3, per_hour=10)
    assert all(rl.allow("a", now=100 + i) for i in range(3))
    assert not rl.allow("a", now=110)
    assert rl.allow("b", now=110)
    assert rl.allow("a", now=200)


def test_locate_place_returns_real_address_and_pinned_map_link():
    pois = [{"name": "Summit Building", "address": "Kapoorthala, Aliganj, Lucknow 226024", "area": "Aliganj", "lat": 26.8883, "lng": 80.9391, "url": ""}]
    m = FakeModel('{"tools": [{"name": "locate_place", "arguments": {"name": "Summit Building", "destination": "Lucknow"}}], "reply": ""}',
                  "Summit Building is at Kapoorthala. [Open in Maps](x)")
    out = run(run_chat({**REQ, "message": "where is summit building", "destination": "Lucknow"}, make_deps(m, pois=pois)))
    assert "Kapoorthala" in m.prompts[1] and "26.8883,80.9391" in m.prompts[1]
    place = out["action"]["places"][0]
    assert place["name"] == "Summit Building" and "26.8883,80.9391" in place["maps_url"]
    assert place["directions_url"].endswith("26.8883,80.9391")


def test_locate_place_never_guesses_when_unmatched():
    pois = [{"name": "Totally Different Cafe", "address": "x", "lat": 1.0, "lng": 2.0}]
    m = FakeModel('{"tools": [{"name": "locate_place", "arguments": {"name": "Summit Building"}}], "reply": ""}',
                  "I could not confirm it. [Search](https://www.google.com/maps/search/?api=1&query=x)")
    out = run(run_chat({**REQ, "message": "where is summit building"}, make_deps(m, pois=pois)))
    assert '"matched": false' in m.prompts[1].lower() and out["action"] is None


def test_locate_place_falls_back_to_geocoder():
    async def geo(name, dest):
        return [{"name": "Summit Building", "address": "Aliganj, Lucknow", "lat": 26.9, "lng": 80.9, "url": ""}]
    m = FakeModel('{"tools": [{"name": "locate_place", "arguments": {"name": "Summit Building"}}], "reply": ""}', "ok")
    deps = make_deps(m, pois=[])
    deps.geocode = geo
    out = run(run_chat({**REQ, "message": "where is summit building"}, deps))
    assert out["action"]["places"][0]["name"] == "Summit Building"


def test_vague_offbeat_request_fans_out_to_real_categories():
    seen = []
    async def poi(q, d):
        seen.append(q)
        return [{"name": f"{q.title()} One", "address": "a", "area": "x", "lat": 1.0, "lng": 2.0}] if q != "museum" else []
    m = FakeModel('{"tools": [{"name": "discover_places", "arguments": {"query": "offbeat locations", "vibe": "offbeat"}}], "reply": ""}', "ok")
    deps = make_deps(m)
    deps.poi_search = poi
    out = run(run_chat({**REQ, "message": "give me off beat locations"}, deps))
    assert len(seen) >= 4 and "offbeat locations" not in seen
    assert len(out["action"]["places"]) >= 4


def test_genz_request_uses_live_trending_names_verified_on_map():
    async def trending(dest, focus):
        return [{"name": "Cafe Neon", "area": "Gomti Nagar", "why": "Packed with college crowds for its late-night waffles"}]
    async def poi(q, d):
        if q == "Cafe Neon":
            return [{"name": "Cafe Neon", "address": "Vibhuti Khand, Gomti Nagar, Lucknow", "area": "Gomti Nagar", "lat": 26.85, "lng": 81.0, "url": ""}]
        return []
    m = FakeModel('{"tools": [{"name": "discover_places", "arguments": {"query": "fun spots for gen z", "vibe": "genz"}}], "reply": ""}', "ok")
    deps = make_deps(m)
    deps.poi_search, deps.trending = poi, trending
    out = run(run_chat({**REQ, "destination": "Lucknow", "message": "where do gen z hang out"}, deps))
    top = out["action"]["places"][0]
    assert top["name"] == "Cafe Neon" and "26.85,81.0" in top["maps_url"] and "waffles" in top["about"]


def test_card_descriptions_are_vibes_not_addresses():
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    os.environ.setdefault("TOMTOM_API_KEY", "x")
    import main
    poi = {"name": "Cafe Coffee Day", "cats": ["cafe/pub"], "area": "Hazratganj", "address": "31/82 Vidhan Sabha Marg"}
    line = main._vibe_template(poi, "trending")
    assert "Hazratganj" not in line and "31/82" not in line and len(line) > 20
    assert main._vibe_kind({"name": "The Lockdown Escape Room", "cats": []}, "trending") == "play"
