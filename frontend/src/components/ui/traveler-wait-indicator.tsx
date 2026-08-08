"use client";

import { useState, useEffect } from "react";
import { Sparkles } from "lucide-react";

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
    <div className="flex flex-col items-center justify-center p-8 md:p-12 text-center my-auto">
      {/* Animated Radar Pulse Spinner */}
      <div className="relative mb-6 flex items-center justify-center">
        <div className="absolute h-24 w-24 rounded-full bg-[#00f0ff]/10 animate-ping" />
        <div className="absolute h-16 w-16 rounded-full border-2 border-[#00f0ff]/40 shadow-[0_0_30px_rgba(0,240,255,0.4)] animate-spin" />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-full bg-[#03050a] border border-[#00f0ff]/60 shadow-[0_0_20px_rgba(0,240,255,0.5)]">
          <Sparkles className="h-6 w-6 text-[#00f0ff] animate-pulse" />
        </div>
      </div>

      {/* Status Badge */}
      <div className="inline-flex items-center gap-2 rounded-full border border-[#00f0ff]/40 bg-[#00f0ff]/10 px-4 py-1.5 text-xs md:text-sm font-bold text-[#00f0ff] shadow-[0_0_20px_rgba(0,240,255,0.2)] mb-4">
        <span>⚡ Curating verified spots in {destination || "your destination"}... Please give us a few moments.</span>
      </div>

      {/* Rotating Travel Tip */}
      <div className="max-w-md h-12 flex items-center justify-center">
        <p className="text-xs md:text-sm text-[#CBD5E1] font-medium transition-all duration-500 ease-in-out px-4 py-2 rounded-xl bg-white/5 border border-white/10">
          {TRAVEL_TIPS[tipIndex]}
        </p>
      </div>
    </div>
  );
}
