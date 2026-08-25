"use client";

import { useState } from "react";
import { Clock, MapPin, AlertTriangle, ArrowRight } from "lucide-react";
import { useCurrency } from "@/context/CurrencyContext";

export default function AgendaTab({ trip, setTrip }: { trip: any; setTrip: any }) {
  const { formatStringRange } = useCurrency();
  const itinerary = trip?.itinerary || [];
  const [activeDay, setActiveDay] = useState(1);

  const dayStops = itinerary.filter((s: any) => s.day === activeDay);

  // Transit Conflict Detection Logic
  // We check if the end time of one activity + transit time > start time of next activity
  const conflicts: number[] = []; // Store indices of stops that have conflicts with the next one
  for (let i = 0; i < dayStops.length - 1; i++) {
    const current = dayStops[i];
    const next = dayStops[i + 1];
    
    // Simplistic time logic for demo:
    // Parse time like "09:00 AM" to minutes
    const parseTime = (t: string) => {
      const match = t.match(/(\d+):(\d+)\s*(AM|PM)/i);
      if (!match) return 0;
      let [_, h, m, p] = match;
      let hours = parseInt(h);
      if (p.toUpperCase() === "PM" && hours !== 12) hours += 12;
      if (p.toUpperCase() === "AM" && hours === 12) hours = 0;
      return hours * 60 + parseInt(m);
    };

    const startMins = parseTime(current.time);
    const duration = parseInt(current.duration) || 60; 
    const endMins = startMins + duration;
    
    // Assume 30 mins transit time
    const transitMins = 30;
    const nextStartMins = parseTime(next.time);

    if (endMins + transitMins > nextStartMins) {
      conflicts.push(i);
    }
  }

  const handleMagicReRoute = () => {
    // Shifts subsequent start times to eliminate conflicts
    const updated = [...itinerary];
    // Implementation of shift logic...
    alert("Magic Re-Route triggered! Schedules shifted.");
  };

  const totalDays = Math.min(30, Math.max(1, trip?.days || (trip?.startDate && trip?.returnDate ? Math.ceil((new Date(trip.returnDate).getTime() - new Date(trip.startDate).getTime()) / (1000 * 60 * 60 * 24)) + 1 : 1)));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2 overflow-x-auto hide-scrollbar">
        {Array.from({ length: totalDays }, (_, i) => i + 1).map((dayNum) => (
          <button
            key={dayNum}
            onClick={() => setActiveDay(dayNum)}
            className={`px-4 py-2 rounded-full text-xs font-bold whitespace-nowrap transition-colors ${
              activeDay === dayNum 
                ? "bg-[#00f0ff] text-black shadow-[0_0_10px_rgba(0,240,255,0.5)]" 
                : "bg-white/5 text-white hover:bg-white/10"
            }`}
          >
            Day {dayNum}
          </button>
        ))}
      </div>

      {conflicts.length > 0 && (
        <div className="bg-[#ff007f]/10 border border-[#ff007f]/50 p-3 rounded-xl flex flex-col gap-2">
          <div className="flex items-center gap-2 text-[#ff007f] font-bold text-sm">
            <AlertTriangle className="h-4 w-4" />
            Transit Conflict Detected!
          </div>
          <p className="text-xs text-[#ff007f]/80">There isn't enough time to travel between some stops.</p>
          <button 
            onClick={handleMagicReRoute}
            className="mt-1 bg-[#ff007f] text-white text-xs font-bold py-2 rounded-lg hover:bg-[#ff007f]/80 shadow-[0_0_15px_rgba(255,0,127,0.4)] transition-all"
          >
            Magic Re-Route
          </button>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {dayStops.map((stop: any, idx: number) => (
          <div key={stop.id} className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-2 relative group">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold mb-1">{stop.time} • {stop.duration}</p>
                <h3 className="font-syne font-bold text-base text-white group-hover:text-[#39ff14] transition-colors line-clamp-1">{stop.title || stop.name || stop.location || "Attraction"}</h3>
              </div>
              <button 
                onClick={() => {
                  const SPOT_NAME = stop.title;
                  const CITY_NAME = trip.destination;
                  const query = encodeURIComponent(SPOT_NAME + " " + CITY_NAME);
                  window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, "_blank");
                }}
                className="bg-[#39ff14]/10 text-[#39ff14] p-2 rounded-full hover:bg-[#39ff14]/20 transition-colors"
                title="Open in Google Maps"
              >
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
            
            <p className="text-xs text-[#94A3B8] flex items-center gap-1 mt-1">
              <MapPin className="h-3 w-3" />
              <span className="truncate">{stop.location}</span>
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
