import asyncio
import httpx
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv("backend/.env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"

async def test_groq():
    print("API KEY:", GROQ_API_KEY[:5] + "..." if GROQ_API_KEY else None)
    prompt = (
        f"Create a realistic 2-day travel itinerary for Paris. "
        "Return ONLY a valid JSON object (no markdown, no extra text) with this exact structure:\n"
        '{"destination":"<city name>","summary":"<one sentence>","days":['
        '{"day":1,"theme":"<theme>","stops":['
        '{"title":"<place>","location":"<address>","category":"<Food|Culture|Nature|Shopping|Heritage|Beach|Wellness>","duration_minutes":<int>,"best_time":"<HH:MM AM/PM>"},'
        "...3 stops per day]}]}\n"
        f"Generate exactly 2 days with 3 stops each. Use real landmarks."
    )
    
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a travel planner. Return only valid JSON, no markdown.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 3000,
            },
            timeout=30.0,
        )
        print("Status:", r.status_code)
        try:
            content = r.json()["choices"][0]["message"]["content"]
            print("Content:", content[:200] + "...")
        except Exception as e:
            print("Error parsing response:", e)
            print("Response:", r.text)

if __name__ == "__main__":
    asyncio.run(test_groq())
