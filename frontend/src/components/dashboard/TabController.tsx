"use client";

import AgendaTab from "./AgendaTab";
import PillarTab from "./PillarTab";
import {
  Compass,
  Ticket,
  Utensils,
  Wine,
  Sparkles,
  Eye,
  ShieldCheck,
  LayoutList,
} from "lucide-react";
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
    { id: "attractions", icon: Compass, label: t.attractions },
    { id: "events", icon: Ticket, label: t.events },
    { id: "culinary", icon: Utensils, label: t.culinaryPillar },
    { id: "bars_pubs", icon: Wine, label: t.barsPubs },
    { id: "wellness", icon: Sparkles, label: t.wellnessPillar },
    { id: "secret_spots", icon: Eye, label: t.secretSpots },
    { id: "essentials", icon: ShieldCheck, label: t.essentialsPillar },
    { id: "agenda", icon: LayoutList, label: t.agenda },
  ];

  const destination = trip?.destination || "Destination";

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 shrink-0">
        <h2 className="font-syne font-bold text-lg text-white">{t.commandCenter}</h2>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-white/10 p-2 hide-scrollbar shrink-0">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center gap-1 rounded-xl px-3 py-2 text-[11px] font-bold whitespace-nowrap transition-all ${
                isActive
                  ? "bg-[#ff007f]/20 text-[#ff007f] border border-[#ff007f]/50 shadow-[0_0_15px_rgba(255,0,127,0.3)]"
                  : "text-[#94A3B8] hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 hide-scrollbar relative">
        {activeTab === "attractions" && (
          <PillarTab
            items={trip?.attractions || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
          />
        )}
        {activeTab === "events" && (
          <PillarTab
            items={trip?.events || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
          />
        )}
        {activeTab === "culinary" && (
          <PillarTab
            items={trip?.culinary || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
          />
        )}
        {activeTab === "bars_pubs" && (
          <PillarTab
            items={trip?.bars_pubs || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
          />
        )}
        {activeTab === "wellness" && (
          <PillarTab
            items={trip?.wellness || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
          />
        )}
        {activeTab === "secret_spots" && (
          <PillarTab
            items={trip?.secret_spots || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
          />
        )}
        {activeTab === "essentials" && (
          <PillarTab
            items={trip?.essentials || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
          />
        )}
        {activeTab === "agenda" && <AgendaTab trip={trip} setTrip={setTrip} />}
      </div>
    </div>
  );
}
