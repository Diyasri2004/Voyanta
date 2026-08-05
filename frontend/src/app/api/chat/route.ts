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

    const systemInstruction = `You are Voya - an energetic, knowledgeable, and cyber-aesthetic AI Travel Concierge.
You are helping the user with their trip to ${destination || 'an unknown destination'}.
Current budget level: ${budget || 'unknown'}.
Preferred currency: ${currency || 'USD'}.
Current itinerary snippet: ${itinerary ? JSON.stringify(itinerary).substring(0, 1000) : 'none'}.

Respond in character. Keep answers concise, helpful, and visually engaging (use emojis). If they ask about real places, recommend top-rated authentic spots.`;

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
