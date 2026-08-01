import httpx
import asyncio

async def test():
    url = "https://voyanta-backend.onrender.com/trip-plan"
    payload = {
        "location": "Paris",
        "days": 2
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, timeout=60.0)
            print("Status:", r.status_code)
            data = r.json()
            itinerary = data.get("itinerary", [])
            for stop in itinerary:
                print(f"Stop: {stop.get('title')} | Type: {stop.get('type')}")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test())
