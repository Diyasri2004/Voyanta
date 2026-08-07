"use client";

import AgendaTab from "./AgendaTab";
import BudgetTab from "./BudgetTab";
import PackingTab from "./PackingTab";
import StoryTab from "./StoryTab";
import RadarTab from "./RadarTab";
import { LayoutList, Wallet, Backpack, PenTool, Radar } from "lucide-react";
import { getTranslation, LanguageName } from "@/lib/i18n";

export default function TabController({
  trip,
  setTrip,
  activeTab,
  setActiveTab,
  selectedLanguage = "English",
}: {
  trip: any;
  setTrip: any;
  activeTab: string;
  setActiveTab: (v: string) => void;
  selectedLanguage?: LanguageName;
}) {
  const t = getTranslation(selectedLanguage);

  const tabs = [
    { id: "agenda", icon: LayoutList, label: t.agenda },
    { id: "radar", icon: Radar, label: t.liveHits },
    { id: "budget", icon: Wallet, label: t.damage },
    { id: "packing", icon: Backpack, label: t.fitsGear },
    { id: "story", icon: PenTool, label: t.storyFlex },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 shrink-0">
        <h2 className="font-syne font-bold text-lg text-white">{t.commandCenter}</h2>
      </div>
      
      {/* Tab Navigation */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-white/10 p-2 hide-scrollbar shrink-0">
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex flex-col items-center gap-1 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
                isActive 
                  ? "bg-[#ff007f]/20 text-[#ff007f] border border-[#ff007f]/50 shadow-[0_0_15px_rgba(255,0,127,0.3)]" 
                  : "text-[#94A3B8] hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 hide-scrollbar relative">
        {activeTab === "agenda" && <AgendaTab trip={trip} setTrip={setTrip} />}
        {activeTab === "radar" && <RadarTab trip={trip} setTrip={setTrip} />}
        {activeTab === "budget" && <BudgetTab trip={trip} />}
        {activeTab === "packing" && <PackingTab trip={trip} />}
        {activeTab === "story" && <StoryTab trip={trip} />}
      </div>
    </div>
  );
}
