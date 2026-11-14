"use client";

import { useState, useEffect } from "react";
import { Plane } from "lucide-react";

const TRAVEL_TIPS = [
  "💡 Tip: Local markets are best visited early in the morning for fresh finds and peaceful walks.",
  "✈️ Checking real live events, concerts, and cultural showcases for your travel dates...",
  "🍽️ Sourcing authentic local food hubs, legendary street stalls, and fine dining spots...",
  "📍 Geocoding landmarks to generate direct turn-by-turn Google Maps navigation links...",
  "🛡️ Gathering local safety advice, hospital contacts, and emergency assistance numbers...",
  "✨ Preparing 7 Explorer Pillars customized specifically for your traveler group...",
];

export function TravelerWaitIndicator({ destination }: { destination?: string }) {
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % TRAVEL_TIPS.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="my-auto flex flex-col items-center justify-center p-8 text-center md:p-12">
      {/* CSS-3D globe with two orbiting planes */}
      <div className="relative mb-10 h-44 w-44 perspective-1200">
        <div
          className="absolute inset-[22%] rounded-full"
          style={{
            background:
              "radial-gradient(circle at 32% 28%, #a5f3fc 0%, #5eead4 18%, #0e3b53 55%, #050914 100%)",
            boxShadow: "0 0 60px rgba(94,234,212,0.45), inset -14px -14px 30px rgba(0,0,0,0.6)",
          }}
        />

        <div className="preserve-3d absolute inset-0" style={{ animation: "orbit 5.5s linear infinite" }}>
          <div className="absolute inset-0 rounded-full border border-[#5eead4]/40" />
          <div
            className="absolute left-1/2 top-0 -ml-3 -mt-3"
            style={{ animation: "orbit-counter 5.5s linear infinite" }}
          >
            <Plane className="h-6 w-6 rotate-45 text-[#fcd34d] drop-shadow-[0_0_10px_rgba(252,211,77,0.9)]" />
          </div>
        </div>

        <div
          className="preserve-3d absolute -inset-4"
          style={{ animation: "orbit 9s linear infinite reverse" }}
        >
          <div className="absolute inset-0 rounded-full border border-[#ff8a5c]/30" />
          <div
            className="absolute bottom-0 left-1/2 -ml-2 -mb-2"
            style={{ animation: "orbit-counter 9s linear infinite reverse" }}
          >
            <Plane className="h-4 w-4 rotate-45 text-[#ff8a5c] drop-shadow-[0_0_8px_rgba(255,138,92,0.9)]" />
          </div>
        </div>
      </div>

      <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#5eead4]/40 bg-[#5eead4]/10 px-4 py-1.5 text-xs font-bold text-[#5eead4] shadow-[0_0_20px_rgba(94,234,212,0.2)] md:text-sm">
        <span>✈ Curating verified spots in {destination || "your destination"}... Please give us a few moments.</span>
      </div>

      <div className="flex h-12 max-w-md items-center justify-center">
        <p className="glass rounded-xl px-4 py-2 text-xs font-medium text-[#CBD5E1] transition-all duration-500 ease-in-out md:text-sm">
          {TRAVEL_TIPS[tipIndex]}
        </p>
      </div>
    </div>
  );
}
