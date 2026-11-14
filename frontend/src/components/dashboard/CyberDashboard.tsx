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
    <div className="relative w-full max-w-7xl mx-auto px-4 py-6 flex flex-col min-h-[calc(100vh-100px)] glass text-white font-plus-jakarta mt-6 rounded-3xl shadow-[0_0_60px_rgba(94,234,212,0.08)]">
      <div className="w-full flex-1 flex flex-col bg-[#04060d]/35 z-10 rounded-2xl">
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
