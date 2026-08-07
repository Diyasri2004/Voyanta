"use client";

import { useState } from "react";
import TabController from "./TabController";
import { LanguageName } from "@/lib/i18n";

export default function CyberDashboard({
  trip,
  setTrip,
  selectedLanguage = "English",
}: {
  trip: any;
  setTrip: any;
  selectedLanguage?: LanguageName;
}) {
  const [activeTab, setActiveTab] = useState("attractions");

  return (
    <div className="relative w-full max-w-7xl mx-auto px-4 py-6 flex flex-col min-h-[calc(100vh-100px)] bg-[#03050a] text-white font-plus-jakarta mt-6 rounded-3xl border border-white/10 shadow-[0_0_50px_rgba(255,0,127,0.1)]">
      <div className="w-full flex-1 flex flex-col bg-[#03050a]/90 backdrop-blur-md z-10 rounded-2xl">
        <TabController
          trip={trip}
          setTrip={setTrip}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          selectedLanguage={selectedLanguage}
        />
      </div>
    </div>
  );
}
