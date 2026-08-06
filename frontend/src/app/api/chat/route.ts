import { GoogleGenAI } from '@google/genai';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
    const body = await req.json();

    const message = body.message || (Array.isArray(body.messages) ? body.messages[body.messages.length - 1]?.content : '');
    const history = body.history || (Array.isArray(body.messages) 
      ? body.messages.slice(0, -1).map((m: any) => ({ role: m.role === 'assistant' ? 'model' : 'user', text: m.content })) 
      : []);
    const tripContext = body.tripContext || body.context || {};

    const systemInstruction = `
      You are "Voya", an energetic, highly knowledgeable, and polite AI Travel Concierge for the web app VOYANTA.
      
      YOUR CORE RESPONSIBILITIES:
      1. Provide accurate, realistic, and authentic recommendations for travel destinations worldwide.
      2. When asked about costs, ticket fees, or approximate expenditures, give realistic price ranges converted to the traveler's active currency (${tripContext?.currency || 'USD'}).
      3. Help travelers customize, swap, or refine their active itinerary based on their vibe, pace, or budget preferences.
      4. Never suggest fake or generic places like "Local Park" or "Generic Gym". Always name real-world, iconic spots, legendary food outlets, or hidden gems.

      ACTIVE TRIP CONTEXT:
      - Destination: ${tripContext?.destination || 'Not selected'}
      - Dates/Duration: ${tripContext?.dates || 'Flexible'}
      - Selected Currency: ${tripContext?.currency || 'USD'}
      - Active Itinerary Summary: ${JSON.stringify(tripContext?.itinerary || {})}

      TONE & STYLE:
      - Keep responses concise, well-structured (use bullet points), enthusiastic, and practical.
      - Keep travel disclaimers light (e.g., "≈ Prices are approximate and subject to seasonal changes").
    `;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: [
        ...history.map((h: { role: string; text: string }) => ({
          role: h.role === 'assistant' ? 'model' : h.role,
          parts: [{ text: h.text }],
        })),
        { role: 'user', parts: [{ text: message }] },
      ],
      config: {
        systemInstruction: systemInstruction,
      },
    });

    return NextResponse.json({ text: response.text, reply: response.text });
  } catch (error) {
    console.error('Voya Chat API Error:', error);
    return NextResponse.json({ error: 'Failed to fetch response from Voya.' }, { status: 500 });
  }
}
