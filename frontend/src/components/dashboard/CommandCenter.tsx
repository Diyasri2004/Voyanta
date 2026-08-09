"use client";

import { useState, useEffect } from "react";
import CulinaryPillarTab from "./CulinaryPillarTab";
import PillarTab, { PillarItemData } from "./PillarTab";
import PlanBuilderDrawer, { SavedPlanItem } from "./PlanBuilderDrawer";
import {
  Compass,
  Ticket,
  Utensils,
  Wine,
  Sparkles,
  Eye,
  ShieldCheck,
  ShoppingBag,
  Mountain,
  Palmtree,
  Landmark,
} from "lucide-react";
import { getTranslation, LanguageName } from "@/lib/i18n";

export const PILLARS = [
  { id: "attractions", label: "Tourist Attractions" },
  { id: "events", label: "Events" },
  { id: "culinary", label: "Culinary" },
  { id: "bars_pubs", label: "Bars & Pubs" },
  { id: "wellness", label: "Wellness & Meditation" },
  { id: "secret_spots", label: "Secret Spots" },
  { id: "essentials", label: "Travel Essentials" },
  { id: "shopping", label: "Shopping" },
  { id: "adventures", label: "Adventures" },
  { id: "theme_parks", label: "Theme Parks" },
  { id: "sacred_temples", label: "Temples & Shrines" }
];

export default function CommandCenter({
  trip,
  setTrip,
  activeTab = "attractions",
  setActiveTab,
  selectedLanguage = "English",
}: {
  trip: any;
  setTrip?: any;
  activeTab?: string;
  setActiveTab?: (v: string) => void;
  selectedLanguage?: LanguageName;
}) {
  const t = getTranslation(selectedLanguage);
  const [internalTab, setInternalTab] = useState(activeTab);
  const [savedPlanItems, setSavedPlanItems] = useState<SavedPlanItem[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [weather, setWeather] = useState<{ temp_c: number; condition: string } | null>(null);

  const currentTab = setActiveTab ? activeTab : internalTab;
  const handleTabChange = (tabId: string) => {
    if (setActiveTab) {
      setActiveTab(tabId);
    } else {
      setInternalTab(tabId);
    }
  };

  const tabs = [
    { id: "attractions", icon: Compass, label: t.attractions },
    { id: "events", icon: Ticket, label: t.events },
    { id: "culinary", icon: Utensils, label: t.culinaryPillar },
    { id: "bars_pubs", icon: Wine, label: t.barsPubs },
    { id: "wellness", icon: Sparkles, label: t.wellnessPillar },
    { id: "secret_spots", icon: Eye, label: t.secretSpots },
    { id: "essentials", icon: ShieldCheck, label: t.essentialsPillar },
    { id: "shopping", icon: ShoppingBag, label: t.shoppingPillar },
    { id: "adventures", icon: Mountain, label: t.adventuresPillar },
    { id: "theme_parks", icon: Palmtree, label: t.themeParksPillar },
    { id: "sacred_temples", icon: Landmark, label: t.sacredTemples },
  ];

  const destination = trip?.destination || "Destination";

  useEffect(() => {
    if (destination && destination !== "Destination") {
      fetch(`/api/weather?destination=${encodeURIComponent(destination)}`)
        .then((res) => res.json())
        .then((data) => setWeather(data))
        .catch(() => setWeather({ temp_c: 28, condition: "Sunny" }));
    }
  }, [destination]);

  const handleAddToPlan = (item: PillarItemData) => {
    setSavedPlanItems((prev) => {
      if (prev.some((p) => p.title === item.title)) return prev;
      return [...prev, item];
    });
    setIsDrawerOpen(true);
  };

  const handleRemovePlanItem = (idx: number) => {
    setSavedPlanItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleClearAllPlanItems = () => {
    setSavedPlanItems([]);
  };

  const planItems = savedPlanItems;

  const combinedCulinaryItems = (() => {
    const rawCulinary = trip?.culinary || [];
    const highlights = trip?.culinary_highlights || [];
    
    const highlightAsItems = highlights.map((h: any, idx: number) => ({
      id: `highlight-${idx}`,
      name: h.title || h.name || "Specialty Eatery",
      title: h.title || h.name || "Specialty Eatery",
      specialty: h.famous_for || h.specialty || "LOCAL SPECIALTY",
      category: "Culinary Highlight",
      description: h.description || "Authentic local culinary experience.",
      address: h.location || destination,
      location: h.location || destination,
      maps_url: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${h.title || h.name} ${destination}`)}`
    }));

    const existingTitles = new Set(highlightAsItems.map((i: any) => i.title.toLowerCase().trim()));
    const filteredPillarItems = rawCulinary
      .filter((item: any) => !existingTitles.has((item.title || "").toLowerCase().trim()))
      .map((item: any, idx: number) => ({
        id: item.id || `culinary-item-${idx}`,
        name: item.title || item.name || "Dining Spot",
        title: item.title || item.name || "Dining Spot",
        specialty: item.specialty || (item.category !== "Culinary" ? item.category : "") || "LOCAL FAVORITE",
        category: item.category || "Culinary",
        description: item.description || `Verified authentic dining spot in ${destination}.`,
        address: item.address || destination,
        location: item.address || destination,
        maps_url: item.maps_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${item.title} ${destination}`)}`
      }));

    return [...highlightAsItems, ...filteredPillarItems];
  })();

  return (
    <div className="flex flex-col h-full relative">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 shrink-0">
        <h2 className="font-syne font-bold text-lg text-white">{t.commandCenter}</h2>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
            <span>🌤️ {weather?.temp_c ?? 28}°C</span>
            <span className="text-gray-500">|</span>
            <span className="text-gray-300">{weather?.condition ?? "Sunny"}</span>
          </div>

          <button
            onClick={() => setIsDrawerOpen(true)}
            className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-medium hover:bg-emerald-500/30 transition-all"
          >
            <span>📋 Itinerary Plan</span>
            <span className="px-1.5 py-0.5 rounded-full bg-emerald-500 text-black text-[10px] font-bold">
              {planItems.length}
            </span>
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-white/10 p-2 hide-scrollbar shrink-0">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = currentTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
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
        {currentTab === "attractions" && (
          <PillarTab
            items={trip?.attractions || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "events" && (
          <PillarTab
            items={trip?.events || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "culinary" && (
          <CulinaryPillarTab
            items={combinedCulinaryItems}
            destination={destination}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "bars_pubs" && (
          <PillarTab
            items={trip?.bars_pubs || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "wellness" && (
          <PillarTab
            items={trip?.wellness || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "secret_spots" && (
          <PillarTab
            items={trip?.secret_spots || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "essentials" && (
          <PillarTab
            items={trip?.essentials || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "shopping" && (
          <PillarTab
            items={trip?.shopping || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "adventures" && (
          <PillarTab
            items={trip?.adventures || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "theme_parks" && (
          <PillarTab
            items={trip?.theme_parks || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
        {currentTab === "sacred_temples" && (
          <PillarTab
            items={trip?.sacred_temples || []}
            destination={destination}
            selectedLanguage={selectedLanguage}
            onAddToPlan={handleAddToPlan}
          />
        )}
      </div>

      {/* Plan Builder Drawer Slide-over */}
      <PlanBuilderDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        items={savedPlanItems}
        onRemoveItem={handleRemovePlanItem}
        onClearAll={handleClearAllPlanItems}
        destination={destination}
      />
    </div>
  );
}
