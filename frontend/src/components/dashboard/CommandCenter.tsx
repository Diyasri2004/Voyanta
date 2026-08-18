"use client";

import { useState, useEffect, useRef } from "react";
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
  const [pillarCache, setPillarCache] = useState<Record<string, PillarItemData[]>>({});
  const [loadingPillars, setLoadingPillars] = useState<Record<string, boolean>>({});
  const fetchedRef = useRef(new Set<string>());

  const ALL_PILLARS = [
    "attractions", "events", "culinary", "bars_pubs", "wellness",
    "secret_spots", "essentials", "shopping", "adventures", "theme_parks", "sacred_temples"
  ];

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

  const fetchPillarData = async (pillarName: string) => {
    if (!destination || destination === "Destination") return;
    if (fetchedRef.current.has(pillarName)) return;
    fetchedRef.current.add(pillarName);

    setLoadingPillars((prev) => ({ ...prev, [pillarName]: true }));
    try {
      const res = await fetch(`/api/pillar?destination=${encodeURIComponent(destination)}&pillar=${encodeURIComponent(pillarName)}`);
      if (res.ok) {
        const data = await res.json();
        if (data && data[pillarName] && Array.isArray(data[pillarName])) {
          setPillarCache((prev) => {
            const updated = { ...prev, [pillarName]: data[pillarName] };
            try {
              sessionStorage.setItem(`voyanta_${destination}_${pillarName}`, JSON.stringify(data[pillarName]));
            } catch (_) {}
            return updated;
          });
        }
      }
    } catch (err) {
      console.error(`Error fetching pillar ${pillarName}:`, err);
      fetchedRef.current.delete(pillarName);
    } finally {
      setLoadingPillars((prev) => ({ ...prev, [pillarName]: false }));
    }
  };

  // 1. Fetch active pillar & restore sessionStorage on mount or destination change
  useEffect(() => {
    if (!destination || destination === "Destination") return;
    fetchedRef.current.clear();
    setPillarCache({});

    ALL_PILLARS.forEach((p) => {
      try {
        const saved = sessionStorage.getItem(`voyanta_${destination}_${p}`);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setPillarCache((prev) => ({ ...prev, [p]: parsed }));
            fetchedRef.current.add(p);
          }
        }
      } catch (_) {}
    });

    fetchPillarData(currentTab);
  }, [destination]);

  // 2. Fetch active pillar on tab change if not already loaded
  useEffect(() => {
    if (!destination || destination === "Destination") return;
    if (!pillarCache[currentTab] && !fetchedRef.current.has(currentTab)) {
      fetchPillarData(currentTab);
    }
  }, [currentTab, destination]);

  // 3. Background prefetch adjacent tabs
  useEffect(() => {
    if (!destination || destination === "Destination") return;
    if (pillarCache[currentTab] && pillarCache[currentTab].length > 0) {
      const currentIndex = ALL_PILLARS.indexOf(currentTab);
      const nextPillars = [
        ALL_PILLARS[(currentIndex + 1) % ALL_PILLARS.length],
        ALL_PILLARS[(currentIndex + 2) % ALL_PILLARS.length]
      ];
      nextPillars.forEach((p) => {
        if (!pillarCache[p] && !fetchedRef.current.has(p)) {
          fetchPillarData(p);
        }
      });
    }
  }, [currentTab, pillarCache, destination]);

  const getPillarItems = (key: string) => {
    if (pillarCache[key] && pillarCache[key].length > 0) {
      return pillarCache[key];
    }
    if (trip && trip[key] && Array.isArray(trip[key])) {
      return trip[key];
    }
    return [];
  };

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
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 w-full border-b border-white/10 shrink-0">
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
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-2 w-full border-b border-white/10 p-2 shrink-0">
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
        <PillarTab
          items={getPillarItems(currentTab)}
          destination={destination}
          selectedLanguage={selectedLanguage}
          onAddToPlan={handleAddToPlan}
          isLoading={loadingPillars[currentTab] && (!getPillarItems(currentTab) || getPillarItems(currentTab).length === 0)}
        />
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
