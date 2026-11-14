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


def test_html_to_text_keeps_list_items_and_drops_scripts():
    html = "<html><script>var x=1</script><nav>menu</nav><h2>Best cafes</h2><ul><li>Sutra Cafe</li><li>Cafe Neon</li></ul></html>"
    text = hp._html_to_text(html)
    assert "Sutra Cafe" in text and "Cafe Neon" in text and "var x" not in text and "menu" not in text


def test_wrapped_object_reply_is_accepted():
    out = hp._clean({"places": [{"name": "Sutra Cafe", "area": "Gomti Nagar", "why": "Relaxed"}]})
    assert out and out[0]["name"] == "Sutra Cafe"


def test_gemini_follows_replacement_model_named_in_404(monkeypatch):
    calls = []

    class R:
        def __init__(self, code, body, js=None):
            self.status_code, self.text, self._js = code, body, js
        def json(self):
            return self._js

    class C:
        async def get(self, url, **kw):
            return R(200, "", {"models": [{"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]}]})
        async def post(self, url, **kw):
            m = url.split("models/")[1].split(":")[0]
            calls.append(m)
            if m == "gemini-2.5-flash":
                return R(404, '{"error":{"message":"This model is no longer available. Please update your code to use models/gemini-9.9-flash."}}')
            return R(200, "", {"candidates": [{"content": {"parts": [{"text": '[{"name":"Cafe Neon","area":"X","why":"Nice"}]'}]}}]})

    hp._model_cache.update(at=0.0, models=[])
    out = asyncio.run(hp.gemini_hot(C(), "KEY", "Lucknow", "cafes", extract))
    assert calls == ["gemini-2.5-flash", "gemini-9.9-flash"] and out[0]["name"] == "Cafe Neon"
