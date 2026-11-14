"use client";

import { useState, useEffect, useRef } from "react";
import WeatherBadge from "./WeatherBadge";
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
  Flame,
} from "lucide-react";
import { motion } from "framer-motion";
import { getTranslation, LanguageName } from "@/lib/i18n";

export const PILLARS = [
  { id: "trending", label: "Trending Now" },
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
  const [pillarCache, setPillarCache] = useState<Record<string, PillarItemData[]>>({});
  const [loadingPillars, setLoadingPillars] = useState<Record<string, boolean>>({});
  const fetchedRef = useRef(new Set<string>());
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const ALL_PILLARS = [
    "trending", "attractions", "events", "culinary", "bars_pubs", "wellness",
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
    { id: "trending", icon: Flame, label: "Trending Now" },
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
  const tripStart: string = trip?.start_date || "";
  const tripEnd: string = trip?.end_date || "";
  const cacheKeyFor = (p: string) =>
    p === "events" ? `voyanta_${destination}_events_${tripStart}_${tripEnd}` : `voyanta_${destination}_${p}`;

  const fetchPillarData = async (pillarName: string) => {
    if (!destination || destination === "Destination") return;
    if (fetchedRef.current.has(pillarName)) return;
    fetchedRef.current.add(pillarName);

    setLoadingPillars((prev) => ({ ...prev, [pillarName]: true }));
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    try {
      const dateParams = pillarName === "events" && tripStart ? `&start_date=${tripStart}&end_date=${tripEnd}` : "";
      const res = await fetch(`/api/pillar?destination=${encodeURIComponent(destination)}&pillar=${encodeURIComponent(pillarName)}${dateParams}`, {
        signal: controller.signal
      });
      if (res.ok) {
        const data = await res.json();
        const items = data.places || data.results || data[pillarName] || [];
        if (Array.isArray(items) && items.length > 0) {
          setPillarCache((prev) => {
            const updated = { ...prev, [pillarName]: items };
            try {
              sessionStorage.setItem(cacheKeyFor(pillarName), JSON.stringify(items));
            } catch (_) {}
            return updated;
          });
        }
      }
    } catch (err) {
      console.error(`Error fetching pillar ${pillarName}:`, err);
      fetchedRef.current.delete(pillarName);
    } finally {
      clearTimeout(timeoutId);
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
        const saved = sessionStorage.getItem(cacheKeyFor(p));
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
  }, [destination, tripStart, tripEnd]);

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
    // Toggle: tap Add again to remove. The drawer stays closed so the person
    // can keep browsing and adding; a small toast offers a way to open it.
    const exists = savedPlanItems.some((p) => p.title === item.title);
    setSavedPlanItems((prev) =>
      prev.some((p) => p.title === item.title)
        ? prev.filter((p) => p.title !== item.title)
        : [...prev, item]
    );
    const added = !exists;
    setToast(added ? `Added "${item.title}"` : `Removed "${item.title}"`);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3200);
  };

  const handleRemovePlanItem = (idx: number) => {
    setSavedPlanItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleClearAllPlanItems = () => {
    setSavedPlanItems([]);
  };

  const planItems = savedPlanItems;
  const addedTitles = savedPlanItems.map((p) => p.title);

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
      {/* Masthead: the destination, set like the landing page */}
      <div className="flex shrink-0 flex-wrap items-end justify-between gap-4 px-2 pb-5 pt-3 md:px-4">
        <div className="min-w-0">
          <p className="mb-1 text-xs font-medium tracking-wide text-[#ffc36b]/80">
            {t.commandCenter}
            {tripStart && tripEnd ? `  ·  ${tripStart} → ${tripEnd}` : ""}
          </p>
          <h2 className="font-display truncate text-4xl leading-[0.95] text-[#f6efe2] md:text-6xl">
            {destination.split(",")[0]}
          </h2>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[#aab3c5]">
            {destination.includes(",") && <span>{destination.split(",").slice(1).join(",").trim()}</span>}
            <WeatherBadge destination={destination} startDate={tripStart} endDate={tripEnd} />
          </div>
        </div>
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="btn-glow flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold"
        >
          <span>Itinerary plan</span>
          <span className="rounded-full bg-[#1b1206] px-2 py-0.5 text-[11px] font-bold text-[#ffc36b]">
            {planItems.length}
          </span>
        </button>
      </div>

      {/* Tab dock */}
      <div className="no-scrollbar mx-2 mb-2 flex shrink-0 items-center gap-1 overflow-x-auto rounded-2xl border border-white/[0.07] bg-white/[0.03] p-1.5 backdrop-blur-xl md:mx-4">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = currentTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`relative flex items-center gap-2 whitespace-nowrap rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-colors ${
                isActive ? "text-[#1b1206]" : "text-[#9aa5bb] hover:text-white"
              }`}
            >
              {isActive && (
                <motion.span
                  layoutId="tab-pill"
                  className="absolute inset-0 rounded-xl bg-[linear-gradient(115deg,#ffe2ae,#ffc36b_55%,#ff9d5c)] shadow-[0_8px_28px_-8px_rgba(255,176,80,0.7)]"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                />
              )}
              <Icon className="relative h-4 w-4" />
              <span className="relative">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-2 md:p-4 hide-scrollbar relative">
        <motion.div
          key={currentTab}
          initial={{ opacity: 0, y: 14, rotateX: -6 }}
          animate={{ opacity: 1, y: 0, rotateX: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
        <PillarTab
          items={getPillarItems(currentTab)}
          destination={destination}
          selectedLanguage={selectedLanguage}
          onAddToPlan={handleAddToPlan}
          addedTitles={addedTitles}
          isLoading={loadingPillars[currentTab] && (!getPillarItems(currentTab) || getPillarItems(currentTab).length === 0)}
          emptyMessage={
            fetchedRef.current.has(currentTab) && !loadingPillars[currentTab]
              ? currentTab === "events"
                ? `No upcoming events found in ${destination} right now. Try again later or check other dates.`
                : `No results found for ${destination} right now. Please try again shortly.`
              : undefined
          }
        />
        </motion.div>
      </div>

      {/* Add / remove confirmation */}
      {toast && (
        <div className="pointer-events-none fixed inset-x-0 bottom-24 z-40 flex justify-center px-4">
          <div className="pointer-events-auto flex max-w-md items-center gap-3 rounded-full border border-white/10 bg-[#0b1020]/95 py-2 pl-4 pr-2 text-sm text-[#f6efe2] shadow-2xl backdrop-blur-xl">
            <span className="truncate">{toast}</span>
            <button
              type="button"
              onClick={() => { setIsDrawerOpen(true); setToast(null); }}
              className="shrink-0 rounded-full bg-[#ffc36b] px-3 py-1.5 text-xs font-bold text-[#1b1206]"
            >
              View itinerary ({planItems.length})
            </button>
          </div>
        </div>
      )}

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
