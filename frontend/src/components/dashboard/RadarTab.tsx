"use client";

import { useState, useEffect } from "react";
import { Radar as RadarIcon, Plus, MapPin, RefreshCw, ExternalLink, Check } from "lucide-react";
import { useCurrency } from "@/context/CurrencyContext";

const DESTINATION_HITS_DATABASE: Record<string, Array<{ title: string; location: string; type: string; cost: string; latOffset: number; lngOffset: number }>> = {
  lucknow: [
    { title: "Rooftop Lounge over Rumi Darwaza", location: "Old City, Lucknow", type: "VIEWPOINT", cost: "$15 - $25", latOffset: 0.005, lngOffset: 0.003 },
    { title: "Secret Tunday Kebab Night Trail", location: "Chowk, Lucknow", type: "CULINARY", cost: "$8 - $15", latOffset: -0.004, lngOffset: 0.006 },
    { title: "Chikankari Heritage Artisan Alley", location: "Aminabad, Lucknow", type: "CULTURE", cost: "$20 - $50", latOffset: 0.008, lngOffset: -0.002 },
    { title: "Gomti Riverfront Speakeasy", location: "Riverfront Park", type: "NIGHTLIFE", cost: "$12 - $30", latOffset: -0.007, lngOffset: -0.005 }
  ],
  kyoto: [
    { title: "Gion Night Bamboo Lantern Walk", location: "Gion District", type: "NIGHTLIFE", cost: "$10 - $20", latOffset: 0.003, lngOffset: 0.004 },
    { title: "Hidden Teahouse behind Yasaka Shrine", location: "Higashiyama", type: "CULTURE", cost: "$15 - $25", latOffset: -0.002, lngOffset: 0.005 },
    { title: "Rooftop Craft Sake Bar", location: "Pontocho Alley", type: "FOOD & DRINK", cost: "$20 - $40", latOffset: 0.006, lngOffset: -0.003 }
  ],
  tokyo: [
    { title: "Cyberpunk Underground Arcade & Bar", location: "Shinjuku", type: "ENTERTAINMENT", cost: "$15 - $35", latOffset: 0.004, lngOffset: -0.004 },
    { title: "Omoide Yokocho Midnight Ramen Stand", location: "Memory Lane", type: "CULINARY", cost: "$10 - $18", latOffset: -0.003, lngOffset: 0.002 },
    { title: "Akihabara Vintage Retro Tech Lounge", location: "Akihabara", type: "SHOPPING", cost: "$25 - $60", latOffset: 0.007, lngOffset: 0.005 }
  ],
  paris: [
    { title: "Montmartre Hidden Rooftop Sunset Point", location: "Montmartre", type: "VIEWPOINT", cost: "Free", latOffset: 0.006, lngOffset: -0.002 },
    { title: "Le Marais Secret Jazz Cellar", location: "Le Marais", type: "NIGHTLIFE", cost: "$20 - $40", latOffset: -0.004, lngOffset: 0.004 },
    { title: "Canal Saint-Martin Artisan Bakery", location: "10th Arrondissement", type: "CULINARY", cost: "$5 - $15", latOffset: 0.002, lngOffset: -0.006 }
  ],
  dubai: [
    { title: "Old Dubai Creek Sunset Abra Lounge", location: "Al Fahidi", type: "HERITAGE", cost: "$10 - $25", latOffset: 0.008, lngOffset: 0.003 },
    { title: "Secret Palm Jumeirah Sky Observation Deck", location: "The Palm", type: "VIEWPOINT", cost: "$30 - $70", latOffset: -0.006, lngOffset: -0.005 },
    { title: "Desert Stargazing Pop-up Cafe", location: "Al Marmoom", type: "NIGHTLIFE", cost: "$25 - $50", latOffset: 0.012, lngOffset: 0.009 }
  ]
};

export default function RadarTab({ trip, setTrip }: { trip: any; setTrip: any }) {
  const { formatStringRange } = useCurrency();
  const [isScanning, setIsScanning] = useState(false);
  const [addedIds, setAddedIds] = useState<Record<string, boolean>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const destination = trip?.destination?.toLowerCase() || "";
  const cityKey = Object.keys(DESTINATION_HITS_DATABASE).find(k => destination.includes(k)) || "";

  const baseHits = DESTINATION_HITS_DATABASE[cityKey] || [
    { title: `Secret ${trip?.destination || "City"} Viewpoint`, location: "Historic Center", type: "VIEWPOINT", cost: "$10 - $20", latOffset: 0.004, lngOffset: 0.003 },
    { title: `Hidden ${trip?.destination || "Local"} Culinary Alley`, location: "Old Town", type: "CULINARY", cost: "$12 - $25", latOffset: -0.003, lngOffset: 0.005 },
    { title: `Pop-up Artisan Night Market`, location: "Downtown Promenade", type: "SHOPPING", cost: "$15 - $35", latOffset: 0.006, lngOffset: -0.004 },
    { title: `Rooftop Sunset Sound Lounge`, location: "Financial District", type: "NIGHTLIFE", cost: "$20 - $45", latOffset: -0.005, lngOffset: -0.002 }
  ];

  const [radarHits, setRadarHits] = useState(baseHits);

  useEffect(() => {
    setRadarHits(baseHits);
  }, [trip?.destination]);

  const handleRescan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      setToastMessage("Radar scan complete! Live hits updated for " + (trip?.destination || "your destination") + ".");
      setTimeout(() => setToastMessage(null), 3000);
    }, 1200);
  };

  const addWaypoint = (hit: any, index: number) => {
    if (!trip) return;
    const hitId = `hit-${index}-${hit.title}`;

    const newStop = {
      id: "radar-" + Date.now() + "-" + index,
      day: 1,
      date: trip.dates?.split(" - ")[0] || "Day 1",
      time: "08:00 PM",
      title: hit.title,
      location: hit.location,
      type: hit.type,
      creators: "Live Cyber Radar",
      duration: "60m",
      distance: "1.2km",
      elevation: "N/A",
      image: "",
      map_image_url: "",
      lat: (trip.coordinates?.lat || 20) + hit.latOffset,
      lng: (trip.coordinates?.lng || 78) + hit.lngOffset,
      cost_range: hit.cost
    };
    
    setTrip({
      ...trip,
      itinerary: [...(trip.itinerary || []), newStop]
    });

    setAddedIds(prev => ({ ...prev, [hitId]: true }));
    setToastMessage(`✨ Added "${hit.title}" to Day 1 Agenda!`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Toast alert */}
      {toastMessage && (
        <div className="bg-[#00f0ff]/20 border border-[#00f0ff] text-[#00f0ff] text-xs font-bold p-3 rounded-xl shadow-[0_0_15px_rgba(0,240,255,0.4)] animate-pulse">
          {toastMessage}
        </div>
      )}

      {/* Radar Status Header */}
      <div className="bg-[#00f0ff]/10 border border-[#00f0ff]/30 p-4 rounded-xl flex items-center justify-between">
        <div>
          <h3 className="text-[#00f0ff] font-syne font-bold text-lg flex items-center gap-2">
            <RadarIcon className={`h-5 w-5 ${isScanning ? "animate-spin text-[#39ff14]" : "animate-pulse"}`} />
            Live Radar: {trip?.destination || "Active City"}
          </h3>
          <p className="text-xs text-[#00f0ff]/80 mt-1">
            {isScanning ? "Scanning frequencies for local pop-ups..." : "Active - Detecting hidden gems & real-time spots"}
          </p>
        </div>
        <button
          onClick={handleRescan}
          disabled={isScanning}
          className="flex items-center gap-1.5 bg-[#00f0ff]/20 hover:bg-[#00f0ff]/40 text-[#00f0ff] text-xs font-bold px-3 py-2 rounded-xl transition-all border border-[#00f0ff]/40 cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isScanning ? "animate-spin" : ""}`} />
          {isScanning ? "Scanning..." : "Rescan"}
        </button>
      </div>

      {/* List of Detected Hits */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-[#94A3B8] uppercase tracking-widest">
            Detected Hits ({radarHits.length})
          </h4>
          <span className="text-[10px] text-[#39ff14] font-mono">● LIVE GPS FEED</span>
        </div>

        {radarHits.map((hit, idx) => {
          const hitId = `hit-${idx}-${hit.title}`;
          const isAdded = addedIds[hitId];
          const mapQuery = encodeURIComponent(`${hit.title} ${trip?.destination || ""}`);

          return (
            <div key={idx} className="bg-white/5 border border-white/10 p-4 rounded-xl flex items-center justify-between group hover:border-[#00f0ff]/50 transition-colors">
              <div className="flex-1 pr-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] bg-[#00f0ff]/20 text-[#00f0ff] px-2 py-0.5 rounded-full font-bold uppercase">{hit.type}</span>
                </div>
                <h4 className="font-bold text-white text-sm group-hover:text-[#00f0ff] transition-colors">{hit.title}</h4>
                <p className="text-xs text-white/50 flex items-center gap-1 mt-1">
                  <MapPin className="h-3 w-3 text-[#94A3B8]" /> {hit.location}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${mapQuery}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-white/5 hover:bg-white/10 text-white/70 hover:text-white p-2 rounded-full transition-colors"
                  title="Open in Maps"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>

                <button 
                  onClick={() => addWaypoint(hit, idx)}
                  disabled={isAdded}
                  className={`p-2 rounded-full transition-colors flex items-center justify-center ${
                    isAdded 
                      ? "bg-[#39ff14]/20 text-[#39ff14] border border-[#39ff14]/40" 
                      : "bg-[#00f0ff]/20 text-[#00f0ff] hover:bg-[#00f0ff] hover:text-black cursor-pointer"
                  }`}
                  title={isAdded ? "Added to Agenda" : "Add to Agenda"}
                >
                  {isAdded ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
