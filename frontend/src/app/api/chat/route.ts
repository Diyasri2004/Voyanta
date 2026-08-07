import { GoogleGenAI } from '@google/genai';
import { NextResponse } from 'next/server';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export async function POST(req: Request) {
  try {
    const { message, history, tripContext } = await req.json();

    const systemInstruction = `
      You are "Voya", an energetic, highly knowledgeable, and polite AI Travel Concierge for VOYANTA.
      
      YOUR CORE RESPONSIBILITIES:
      1. Provide accurate, realistic recommendations for travel destinations worldwide.
      2. When asked about costs, ticket fees, or expenditures, give realistic price ranges in the active currency (${tripContext?.currency || 'INR'}).
      3. Help travelers customize, swap, or refine their active itinerary dynamically.
      4. Never suggest generic places. Always name real-world iconic spots, legendary food outlets, or hidden gems.

      ACTIVE TRIP CONTEXT:
      - Destination: ${tripContext?.destination || 'Not selected'}
      - Dates: ${tripContext?.dates || 'Flexible'}
      - Selected Currency: ${tripContext?.currency || 'INR'}
      - Itinerary Summary: ${JSON.stringify(tripContext?.itinerary || {})}

      TONE & STYLE: Keep responses well-structured (bullet points), concise, and practical.
    `;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: [
        ...(history || []).map((h: { role: string; text: string }) => ({
          role: h.role,
          parts: [{ text: h.text }],
        })),
        { role: 'user', parts: [{ text: message }] },
      ],
      config: { systemInstruction },
    });

    return NextResponse.json({ text: response.text, reply: response.text });
  } catch (error) {
    console.error('Voya Chat API Error:', error);
    return NextResponse.json({ error: 'Failed to fetch response from Voya.' }, { status: 500 });
  }
}
