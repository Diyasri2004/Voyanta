"use client";

import { useState, useEffect } from "react";
import FlapBoard from "@/components/hero/FlapBoard";

const TRAVEL_TIPS = [
  "💡 Tip: Local markets are best visited early in the morning for fresh finds and peaceful walks.",
  "✈️ Checking real live events, concerts, and cultural showcases for your travel dates...",
  "🍽️ Sourcing authentic local food hubs, legendary street stalls, and fine dining spots...",
  "📍 Geocoding landmarks to generate direct turn-by-turn Google Maps navigation links...",
  "🛡️ Gathering local safety advice, hospital contacts, and emergency assistance numbers...",
  "✨ Preparing 7 Explorer Pillars customized specifically for your traveler group...",
];

/** While the trip is built, the globe dives toward the destination behind this. */
export function TravelerWaitIndicator({ destination }: { destination?: string }) {
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % TRAVEL_TIPS.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="mt-auto flex flex-col items-center gap-7 px-4 pb-14 pt-10 text-center md:pb-20">
      <FlapBoard text={destination?.split(",")[0] || "Voyanta"} />

      <div className="inline-flex max-w-[92vw] items-center gap-2 rounded-full border border-[#ffc36b]/35 bg-[#ffc36b]/10 px-5 py-2 text-xs font-semibold text-[#ffd89a] md:text-sm">
        Curating verified spots in {destination || "your destination"}. This takes a few moments.
      </div>

      <div className="flex h-14 max-w-md items-center justify-center">
        <p className="glass rounded-xl px-4 py-2.5 text-xs font-medium text-[#d6dbe6] transition-all duration-500 ease-in-out md:text-sm">
          {TRAVEL_TIPS[tipIndex]}
        </p>
      </div>
    </div>
  );
}
