import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import hot_places as hp


def extract(t):
    try:
        return json.loads(t)
    except Exception:
        return None


def test_falls_back_to_web_search_and_drops_invented_names(monkeypatch):
    monkeypatch.setattr(hp, "_ddg_text", lambda q, n: [{"title": "Best cafes in Lucknow", "body": "Try Sutra Cafe in Gomti Nagar and Chatori Gali near Aminabad."}])

    async def ai(prompt):
        return json.dumps([{"name": "Sutra Cafe", "area": "Gomti Nagar", "why": "A relaxed hangout"},
                           {"name": "Totally Invented Place", "area": "", "why": "x"}])
    out = asyncio.run(hp.hot_places(None, "Lucknow", "trending", "", ai, extract))
    assert [o["name"] for o in out] == ["Sutra Cafe"]


def test_numbers_are_stripped_from_reasons():
    out = hp._clean([{"name": "X Cafe", "area": "A", "why": "Rated 4.8 with 2000 reviews"}])
    assert not any(c.isdigit() for c in out[0]["why"])


def test_every_tab_has_a_focus():
    for p in ["trending", "attractions", "culinary", "bars_pubs", "secret_spots", "shopping", "adventures", "wellness"]:
        assert p in hp.HOT_FOCUS
