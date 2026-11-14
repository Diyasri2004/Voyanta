import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import cache_store


def test_memory_fallback_roundtrip_and_miss():
    async def go():
        assert await cache_store.cache_get("nope") is None
        await cache_store.cache_set("k", {"a": [1, 2]}, ttl=60)
        return await cache_store.cache_get("k")
    assert asyncio.run(go()) == {"a": [1, 2]}


def test_expired_entries_are_not_returned():
    async def go():
        await cache_store.cache_set("old", {"x": 1}, ttl=0)
        await asyncio.sleep(0.01)
        return await cache_store.cache_get("old")
    assert asyncio.run(go()) is None
