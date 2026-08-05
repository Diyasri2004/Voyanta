"use client";

import { useState } from "react";
import { Radar as RadarIcon, Plus, MapPin } from "lucide-react";

export default function RadarTab({ trip, setTrip }: { trip: any; setTrip: any }) {
  const [radarHits] = useState([
    { id: "r1", title: "Secret Underground Club", location: "Downtown", type: "NIGHTLIFE", lat: 0, lng: 0 },
    { id: "r2", title: "Cyberpunk Ramen Stand", location: "Neon Alley", type: "FOOD", lat: 0, lng: 0 },
  ]);

  const addWaypoint = (hit: any) => {
    if (!trip) return;
    const newStop = {
      id: hit.id + "-" + Date.now(),
      day: 1, // default to day 1 for now
      date: trip.dates?.split(" - ")[0] || "Unknown",
      time: "TBD",
      title: hit.title,
      location: hit.location,
      type: hit.type,
      creators: "Live Radar",
      duration: "60m",
      distance: "1km",
      elevation: "N/A",
      image: "",
      map_image_url: "",
      lat: hit.lat || trip.coordinates?.lat || 0,
      lng: hit.lng || trip.coordinates?.lng || 0,
    };
    
    setTrip({
      ...trip,
      itinerary: [...(trip.itinerary || []), newStop]
    });
    alert(`Added ${hit.title} to Agenda!`);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-[#00f0ff]/10 border border-[#00f0ff]/30 p-4 rounded-xl flex items-center justify-between">
        <div>
          <h3 className="text-[#00f0ff] font-syne font-bold text-lg flex items-center gap-2">
            <RadarIcon className="h-5 w-5 animate-pulse" />
            Live Radar Active
          </h3>
          <p className="text-xs text-[#00f0ff]/80 mt-1">Scanning for hidden spots nearby...</p>
        </div>
        <div className="w-8 h-8 rounded-full border border-[#00f0ff] flex items-center justify-center relative">
          <div className="w-2 h-2 bg-[#00f0ff] rounded-full"></div>
          <div className="absolute inset-0 border border-[#00f0ff] rounded-full animate-ping"></div>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <h4 className="text-xs font-bold text-[#94A3B8] uppercase tracking-widest">Detected Hits</h4>
        {radarHits.map(hit => (
          <div key={hit.id} className="bg-white/5 border border-white/10 p-4 rounded-xl flex items-center justify-between group hover:border-[#00f0ff]/50 transition-colors">
            <div>
              <p className="text-[10px] text-[#00f0ff] font-bold uppercase">{hit.type}</p>
              <h4 className="font-bold text-white text-sm">{hit.title}</h4>
              <p className="text-xs text-white/50 flex items-center gap-1 mt-1">
                <MapPin className="h-3 w-3" /> {hit.location}
              </p>
            </div>
            <button 
              onClick={() => addWaypoint(hit)}
              className="bg-[#00f0ff]/20 text-[#00f0ff] p-2 rounded-full hover:bg-[#00f0ff] hover:text-black transition-colors"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
