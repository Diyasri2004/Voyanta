"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Layers } from "lucide-react";
import { getTranslation, LanguageName } from "@/lib/i18n";

const LeafletMap = dynamic(() => import("./LeafletMap"), { ssr: false });
const ThreeMap = dynamic(() => import("./ThreeMap"), { ssr: false });

export default function MapContainer({ trip, selectedLanguage = "English" }: { trip: any; selectedLanguage?: LanguageName }) {
  const [viewMode, setViewMode] = useState<"2d" | "3d">("2d");
  const t = getTranslation(selectedLanguage);

  return (
    <div className="relative w-full h-full bg-[#0E1525]">
      {viewMode === "2d" ? (
        <LeafletMap trip={trip} />
      ) : (
        <ThreeMap trip={trip} />
      )}

      {/* View Switcher */}
      <div className="absolute top-6 right-6 z-[1000]">
        <div className="bg-[#03050a]/80 backdrop-blur-md border border-[#00f0ff]/30 p-1 rounded-xl flex gap-1 shadow-[0_0_20px_rgba(0,240,255,0.2)]">
          <button 
            onClick={() => setViewMode("2d")}
            className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition-all ${
              viewMode === "2d" ? "bg-[#00f0ff] text-black shadow-[0_0_10px_rgba(0,240,255,0.5)]" : "text-white hover:bg-white/10"
            }`}
          >
            <Layers className="h-4 w-4" /> {t.cyberMap2D}
          </button>
          <button 
            onClick={() => setViewMode("3d")}
            className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition-all ${
              viewMode === "3d" ? "bg-[#ff007f] text-white shadow-[0_0_10px_rgba(255,0,127,0.5)]" : "text-white hover:bg-white/10"
            }`}
          >
            <Layers className="h-4 w-4" /> {t.holoGlobe3D}
          </button>
        </div>
      </div>
    </div>
  );
}
