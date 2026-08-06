"use client";

import { useState } from "react";
import TabController from "./TabController";
import MapContainer from "../maps/MapContainer";
import VoyAI from "../ai/Voya";

export default function CyberDashboard({ trip, setTrip }: { trip: any; setTrip: any }) {
  const [activeTab, setActiveTab] = useState("agenda");
  
  return (
    <div className="relative flex flex-col lg:flex-row min-h-[800px] h-auto lg:h-[calc(100vh-100px)] w-full overflow-hidden bg-[#03050a] text-white font-plus-jakarta mt-6 rounded-3xl border border-white/10 shadow-[0_0_50px_rgba(255,0,127,0.1)]">
      {/* LEFT COLUMN: 5-TAB PANEL */}
      <div className="w-full lg:w-[450px] shrink-0 border-b lg:border-r lg:border-b-0 border-[#ff007f]/20 bg-[#03050a]/90 backdrop-blur-md flex flex-col h-[50vh] lg:h-full z-10">
        <TabController trip={trip} setTrip={setTrip} activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>

      {/* RIGHT COLUMN: DUAL VIEWPORT MAPS */}
      <div className="flex-1 relative min-h-[400px] lg:min-h-0 lg:h-full bg-[#0E1525]">
        <MapContainer trip={trip} />
      </div>

      {/* FLOATING VOYA DRAWER */}
      <VoyAI trip={trip} />
    </div>
  );
}
