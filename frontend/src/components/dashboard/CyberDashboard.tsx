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
  const [activeTab, setActiveTab] = useState("trending");

  return (
    <div className="relative w-full max-w-7xl mx-auto px-4 py-6 flex flex-col min-h-[calc(100vh-100px)] text-white font-plus-jakarta mt-2">
      <div className="w-full flex-1 flex flex-col z-10">
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
