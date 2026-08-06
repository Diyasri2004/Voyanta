import { GoogleGenAI } from '@google/genai';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
    const { messages, context } = await req.json();

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: 'Invalid messages array' }, { status: 400 });
    }

    const { destination, budget, currency, itinerary } = context || {};

    const serializedItinerary = Array.isArray(itinerary)
      ? itinerary.map((stop: any) => `• Day ${stop.day}: ${stop.title} (${stop.location || 'Local'}) | Type: ${stop.type || 'Attraction'} | Approx Cost: ${stop.cost_range || 'N/A'}`).join("\n")
      : (itinerary ? JSON.stringify(itinerary).substring(0, 3000) : 'None');

    const systemInstruction = `You are Voya, an energetic AI travel concierge with full visibility into the user's active itinerary, selected city, dates, and currency.
You are helping the traveler with their trip to ${destination || 'an unknown destination'}.
Preferred currency: ${currency || 'USD'}.

ACTIVE ITINERARY DETAILS & COST DATA:
${serializedItinerary}

INSTRUCTIONS FOR VOYA:
- If a traveler wants custom tweaks (e.g. 'more chill pace', 'budget street food', 'hidden gems', 'family friendly spots', 'swap an activity'), suggest specific, real-world venues and help refine their schedule interactively.
- When asked about costs, entry fees, or approximate expenditures for any venue or overall trip, provide accurate price range estimates converted into their active currency (${currency || 'USD'}) along with helpful context like ticket prices, food costs, or transportation.
- Respond warmly and in character. Keep answers concise, helpful, and visually engaging using emojis.`;

    // Convert messages to Gemini format (user vs model)
    const formattedMessages = messages.map((m: any) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }]
    }));

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: formattedMessages,
      config: {
        systemInstruction,
        temperature: 0.7,
      }
    });

    return NextResponse.json({ reply: response.text });
  } catch (error: any) {
    console.error('Chat API Error:', error);
    return NextResponse.json(
      { error: 'Failed to communicate with Voya.' },
      { status: 500 }
    );
  }
}
