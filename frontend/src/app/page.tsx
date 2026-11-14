"use client";

import { useMemo, useState, useEffect } from "react";
import dynamic from "next/dynamic";
import CyberDashboard from "@/components/dashboard/CyberDashboard";
import WeatherBadge from "@/components/dashboard/WeatherBadge";
import VoyAI from "@/components/ai/Voya";
import CityHeroImage from "@/components/CityHeroImage";
import { TravelerWaitIndicator } from "@/components/ui/traveler-wait-indicator";
import TravelBackdrop from "@/components/3d/TravelBackdrop";
import HeaderMenu from "@/components/ui/HeaderMenu";
import Landing from "@/components/landing/Landing";
import { sceneStore } from "@/lib/sceneStore";
import { findDestination } from "@/lib/destinations";
import { AnimatePresence, motion } from "framer-motion";
import { DestinationInput } from "@/components/search/DestinationInput";
import { useCurrency } from "@/context/CurrencyContext";
import {
  Calendar,
  Loader2,
  MapPin,
  Search,
  Plane,
  LayoutGrid,
  Map as MapIcon,
  Navigation,
  PlaneTakeoff,
  PlaneLanding,
  Home,
  Pencil,
  Users,
  ChevronDown,
  Plus,
  Minus,
} from "lucide-react";

import { getTranslation, LanguageName } from "@/lib/i18n";

const VoyantaMap = dynamic(() => import("@/components/VoyantaMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[520px] bg-[#090e1a] rounded-[2rem] border border-white/[0.08] flex items-center justify-center text-[#94A3B8]">
      Loading map...
    </div>
  ),
});

type ViewMode = "grid" | "split";

interface TripStop {
  id: string;
  day: number;
  date: string;
  time: string;
  title: string;
  location: string;
  type: string;
  creators: string;
  distance: string;
  elevation: string;
  duration: string;
  image: string;
  map_image_url: string;
  lat: number;
  lng: number;
}

interface RouteGeoJson {
  type: "Feature";
  geometry: {
    type: "LineString";
    coordinates: number[][];
  };
  properties?: Record<string, unknown>;
}

interface TripRoute {
  day: number;
  geojson?: RouteGeoJson;
  total_distance_meters: number;
  total_travel_time_seconds: number;
}

interface CulinaryHighlight {
  title: string;
  description: string;
  famous_for: string;
  location: string;
}

export interface TravelersState {
  group_type: 'Solo' | 'Couple' | 'Family' | 'Friends' | 'Business';
  adults: number;
  seniors: number;
  infants: number;
}

const LANGUAGES = [
  { code: "EN", name: "English" as LanguageName, label: "🇬🇧 EN" },
  { code: "HI", name: "Hindi" as LanguageName, label: "🇮🇳 HI (हिंदी)" },
  { code: "ES", name: "Spanish" as LanguageName, label: "🇪🇸 ES (Español)" },
  { code: "FR", name: "French" as LanguageName, label: "🇫🇷 FR (Français)" },
  { code: "DE", name: "German" as LanguageName, label: "🇩🇪 DE (Deutsch)" },
  { code: "AR", name: "Arabic" as LanguageName, label: "🇦🇪 AR (العربية)" },
  { code: "ZH", name: "Chinese" as LanguageName, label: "🇨🇳 ZH (中文)" },
  { code: "JA", name: "Japanese" as LanguageName, label: "🇯🇵 JA (日本語)" },
];

const CURRENCIES = [
  { code: "USD", sym: "$" }, { code: "EUR", sym: "€" }, { code: "GBP", sym: "£" },
  { code: "INR", sym: "₹" }, { code: "JPY", sym: "¥" }, { code: "AUD", sym: "A$" },
  { code: "CAD", sym: "C$" }, { code: "AED", sym: "د.إ" }, { code: "SGD", sym: "S$" },
];

interface TripPlan {
  destination: string;
  destination_image: string;
  map_image_url: string;
  weather: string;
  dates: string;
  days: number;
  itinerary: TripStop[];
  routes: TripRoute[];
  culinary_highlights: CulinaryHighlight[];
  start_date?: string;
  end_date?: string;
}

const cn = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

function formatRouteSummary(route?: TripRoute) {
  if (!route || !route.total_distance_meters) {
    return "Route will appear once multiple stops are available.";
  }

  const km = (route.total_distance_meters / 1000).toFixed(1);
  const minutes = Math.round(route.total_travel_time_seconds / 60);
  return `${km} km planned route • ${minutes} min drive time`;
}

function StopCard({ stop, destination }: { stop: TripStop; destination: string }) {
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(stop.title + ' ' + destination)}`;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      onClick={() => window.open(mapUrl, "_blank")}
      className="group overflow-hidden rounded-[2rem] bg-[#090e1a]/85 border border-white/[0.08] shadow-2xl cursor-pointer transition-all hover:border-blue-500/40 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]"
    >
      <div className="relative h-64 overflow-hidden">
        <img
          src={stop.image}
          alt={stop.title}
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#060913] via-[#060913]/30 to-transparent" />
        <div className="absolute left-0 right-0 bottom-0 p-6">
          <span className="inline-flex rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold tracking-[0.22em] text-white">
            {stop.type}
          </span>
          <h3 className="mt-3 text-2xl font-syne font-bold tracking-tight text-white group-hover:text-blue-400 transition-colors">
            {stop.title}
          </h3>
          <p className="mt-2 flex items-center gap-2 text-sm text-[#CBD5E1]">
            <MapPin className="h-4 w-4" />
            {stop.location}
          </p>
        </div>
      </div>

      <div className="p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.24em] text-[#64748B]">
              Schedule
            </p>
            <p className="mt-1 text-lg font-semibold text-white">{stop.time}</p>
          </div>
          <div className="overflow-hidden rounded-xl border border-white/10 bg-white/5">
            <img
              src={stop.map_image_url}
              alt={`${stop.title} preview`}
              className="h-12 w-16 object-cover"
            />
          </div>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-3 border-t border-white/[0.06] pt-5">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-[#64748B]">
              Distance
            </p>
            <p className="mt-1 text-sm font-semibold text-white">{stop.distance}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-[#64748B]">
              Elevation
            </p>
            <p className="mt-1 text-sm font-semibold text-white">{stop.elevation}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-[#64748B]">
              Duration
            </p>
            <p className="mt-1 text-sm font-semibold text-white">{stop.duration}</p>
          </div>
        </div>
      </div>
    </motion.article>
  );
}

function CulinaryCard({ highlight, destination }: { highlight: any; destination: string }) {
  const title = highlight.title || highlight.name || "Specialty Eatery";
  const specialty = highlight.famous_for || highlight.specialty || "LOCAL SPECIALTY";
  const description = highlight.description || "Authentic local culinary experience.";
  const locationName = highlight.location || destination;
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${title} ${destination}`)}`;

  return (
    <div className="relative flex flex-col justify-between p-6 rounded-2xl bg-zinc-900/80 border border-zinc-800 hover:border-amber-500/30 transition-all duration-300 min-h-[220px]">
      <div className="space-y-2">
        <h3 className="text-xl font-bold text-white tracking-wide">{title}</h3>
        <p className="text-xs font-semibold tracking-wider text-emerald-400 uppercase">{specialty}</p>
        <p className="text-sm text-zinc-400 leading-relaxed pt-1 line-clamp-2">{description}</p>
      </div>

      <div className="pt-4 mt-4 border-t border-zinc-800/80 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-zinc-400">
          <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          <span className="truncate max-w-[180px]">{locationName}</span>
        </div>
        <a
          href={mapUrl}
          target="_blank"
          rel="noreferrer"
          className="px-4 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 text-xs font-medium hover:bg-sky-500/20 transition-all"
        >
          Navigate
        </a>
      </div>
    </div>
  );
}

const getLocalDateString = (offsetDays = 0): string => {
  const now = new Date();
  now.setDate(now.getDate() + offsetDays);
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

function todayIso() {
  return getLocalDateString(0);
}

function addDays(iso: string, n: number): string {
  const parts = iso.split('-');
  if (parts.length === 3) {
    const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
    d.setDate(d.getDate() + n);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  return getLocalDateString(n);
}

function fmtShort(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function diffDays(start: string, end: string): number {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  return Math.max(1, Math.round(ms / 86400000));
}

export default function Page() {
  const { currency, setCurrency } = useCurrency();
  const [locationInput, setLocationInput] = useState("");
  const [startDate, setStartDate] = useState<string>(() => getLocalDateString(0));
  const [returnDate, setReturnDate] = useState<string>(() => getLocalDateString(3));
  const [trip, setTrip] = useState<TripPlan | null>(null);
  const [activeDay, setActiveDay] = useState(1);
  const [viewMode, setViewMode] = useState<ViewMode>("split");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editTrip, setEditTrip] = useState(false);

  const [travelers, setTravelers] = useState<TravelersState>({
    group_type: "Couple",
    adults: 2,
    seniors: 0,
    infants: 0,
  });
  const [isTravelersOpen, setIsTravelersOpen] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageName>("English");

  const t = getTranslation(selectedLanguage);

  interface TrendingDest {
    name: string;
    country?: string;
  }

  const [trending, setTrending] = useState<TrendingDest[]>([]);
  const [loadingTrending, setLoadingTrending] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const fetchTrending = async () => {
      try {
        const res = await fetch("/api/trending");
        if (res.ok) {
          const data = await res.json();
          if (isMounted && Array.isArray(data.trending) && data.trending.length > 0) {
            setTrending(data.trending);
          }
        }
      } catch (err) {
        console.error("Dynamic trending fetch failed:", err);
      } finally {
        if (isMounted) setLoadingTrending(false);
      }
    };

    fetchTrending();
    return () => { isMounted = false; };
  }, []);

  const getGroupTypeLabel = (type: string) => {
    switch (type) {
      case "Solo": return t.solo;
      case "Couple": return t.couple;
      case "Family": return t.family;
      case "Friends": return t.friends;
      case "Business": return t.business;
      default: return type;
    }
  };

  const [isAutocompleteOpen, setIsAutocompleteOpen] = useState(false);
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<Array<{ label: string; value: string }>>([]);

  useEffect(() => {
    const query = locationInput.trim();
    if (!query) {
      setAutocompleteSuggestions([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`, { signal: controller.signal })
        .then((res) => res.json())
        .then((data) => {
          if (data && Array.isArray(data.suggestions)) {
            setAutocompleteSuggestions(data.suggestions);
          }
        })
        .catch(() => {});
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [locationInput]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.history.replaceState({ step: "setup" }, "");
    }
  }, []);

  useEffect(() => {
    const handlePopState = (event: PopStateEvent) => {
      if (event.state?.modal === "voya") return;

      if (trip) {
        setTrip(null);
        return;
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [trip]);

  async function loadTripPlan(
    location: string, 
    days: number, 
    date: string
  ) {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/trip-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location, days, start_date: date, categories: [], pace: "", budget: "", travelers, language: selectedLanguage }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail ?? "Unable to build trip plan.");
      }

      setTrip({ ...payload, start_date: date, end_date: addDays(date, Math.max(days - 1, 0)) });
      setActiveDay(1);
      if (typeof window !== "undefined") {
        window.history.pushState({ step: "dashboard" }, "");
      }
    } catch (err) {
      setTrip(null);
      const msg = err instanceof Error ? err.message : "";
      setError(!msg || msg.trimStart().startsWith("<") ? "The Voyanta server is unavailable right now. Please try again shortly." : msg);
    } finally {
      setLoading(false);
    }
  }

  const filteredItinerary = useMemo(
    () => trip?.itinerary.filter((item) => item.day === activeDay) ?? [],
    [trip, activeDay]
  );

  const activeRoute = useMemo(
    () => trip?.routes.find((route) => route.day === activeDay),
    [trip, activeDay]
  );

  /** When departure changes, keep return ≥ departure+1 */
  function handleStartDate(val: string) {
    setStartDate(val);
    if (val >= returnDate) setReturnDate(addDays(val, 1));
  }

  /** When return changes, clamp to max 30 days from departure */
  function handleReturnDate(val: string) {
    const max = addDays(startDate, 30);
    setReturnDate(val > max ? max : val);
  }

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmedLocation = locationInput.trim();
    if (!trimmedLocation) {
      setError("Enter a destination before planning the trip.");
      return;
    }

    const days = Math.min(30, Math.max(1, diffDays(startDate, returnDate)));
    void loadTripPlan(trimmedLocation, days, startDate);
  }

  // The dashboard (and its loader) own the viewport; otherwise the full landing scrolls.
  const showDashboard = Boolean(trip) || loading;

  // Steer the 3D world: dive toward the destination while planning, recede behind the dashboard.
  useEffect(() => {
    sceneStore.warp = loading ? 1 : 0;
    if (loading) {
      const d = findDestination(locationInput);
      if (d) sceneStore.focus = { lat: d.lat, lng: d.lng };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading]);

  useEffect(() => {
    if (trip && typeof window !== "undefined") window.scrollTo({ top: 0 });
  }, [trip]);

  return (
    <>
      <style
        dangerouslySetInnerHTML={{
          __html: `
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Syne:wght@400;600;700;800&display=swap');
            html, body { max-width: 100%; overflow-x: hidden; }
            input[type="date"] { min-width: 0; -webkit-appearance: none; appearance: none; }
            body {
              background: #04060d;
              margin: 0;
              -webkit-font-smoothing: antialiased;
              -moz-osx-font-smoothing: grayscale;
            }
            .font-manrope { font-family: 'Manrope', sans-serif; }
            .font-syne { font-family: 'Syne', sans-serif; }
            .hide-scrollbar::-webkit-scrollbar { display: none; }
            .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

            @keyframes shake {
              0%, 100% { transform: translateX(0); }
              20%, 60% { transform: translateX(-8px); }
              40%, 80% { transform: translateX(8px); }
            }
            .animate-shake {
              animation: shake 0.4s ease-in-out;
            }
            @keyframes glowPulse {
              0%, 100% { opacity: 0.7; }
              50%       { opacity: 1; }
            }

            /* Date input dark styling */
            input[type="date"]::-webkit-calendar-picker-indicator {
              filter: invert(1) brightness(0.6);
              cursor: pointer;
            }
          `,
        }}
      />

      <div className={`relative min-h-screen font-manrope text-white selection:bg-[#ffc36b] selection:text-[#050912] flex flex-col ${showDashboard ? "md:h-screen md:max-h-screen md:overflow-hidden justify-between" : ""}`}>
        <TravelBackdrop recede={Boolean(trip)} dive={loading && !trip} />

        <header
          className={`${showDashboard ? "relative md:sticky" : "fixed inset-x-0"} top-0 z-40 shrink-0 border-b border-white/[0.06] bg-[#050912]/60 backdrop-blur-xl`}
          style={{ paddingTop: "env(safe-area-inset-top)" }}
        >
          <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-3 gap-y-2.5 px-4 py-3 sm:px-6 lg:flex-nowrap lg:gap-4 lg:px-10">
            <button
              type="button"
              onClick={() => setTrip(null)}
              aria-label="Voyanta home"
              className="flex items-center gap-2 transition-opacity hover:opacity-80 sm:gap-2.5"
            >
              <div className="relative flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-[#7fd6ff] via-[#38bdf8] to-[#818cf8] shadow-[0_0_28px_rgba(127,214,255,0.4)] sm:h-11 sm:w-11">
                <Plane className="h-5 w-5 -rotate-45 text-[#04060d]" strokeWidth={2.4} />
              </div>
              <span className="font-syne text-[0.95rem] font-extrabold tracking-[0.08em] sm:text-xl sm:tracking-[0.18em]">VOYANTA</span>
            </button>

            {/* Trip capsule: destination + dates at a glance, tap to edit */}
            {trip ? (
              <button
                type="button"
                onClick={() => setEditTrip((v) => !v)}
                aria-expanded={editTrip}
                className={`glass order-3 flex h-12 w-full min-w-0 items-center gap-3 rounded-full pl-4 pr-2 text-left transition hover:border-[#ffc36b]/40 lg:order-none lg:mx-auto lg:w-auto lg:min-w-[26rem] lg:max-w-xl lg:flex-1 ${
                  editTrip ? "border-[#ffc36b]/50" : ""
                }`}
              >
                <MapPin className="h-4 w-4 shrink-0 text-[#ffc36b]" />
                <span className="font-display truncate text-xl leading-none text-[#f6efe2]">
                  {(trip.destination || locationInput).split(",")[0]}
                </span>
                <span className="hidden h-5 w-px bg-white/15 sm:block" />
                <span className="hidden truncate text-xs font-medium text-[#aab3c5] sm:block">
                  {fmtShort(startDate)} → {fmtShort(returnDate)}
                </span>
                <span className="ml-auto flex shrink-0 items-center gap-1.5 rounded-full bg-white/[0.07] px-3 py-1.5 text-xs font-semibold text-[#e8edf7]">
                  {diffDays(startDate, returnDate)}d
                  <Pencil className="h-3 w-3 text-[#ffc36b]" />
                </span>
              </button>
            ) : (
              <div className="ml-auto" />
            )}

            <div className={`flex items-center gap-1.5 sm:gap-3 ${trip ? "ml-auto lg:ml-0" : ""}`}>
              <HeaderMenu
                icon="globe"
                ariaLabel="Language"
                value={selectedLanguage}
                display={LANGUAGES.find((l) => l.name === selectedLanguage)?.code ?? "EN"}
                onChange={(v) => setSelectedLanguage(v as LanguageName)}
                options={LANGUAGES.map((l) => ({ value: l.name, label: l.name, hint: l.code }))}
              />
              <HeaderMenu
                icon="coins"
                ariaLabel="Currency"
                value={currency}
                display={currency}
                onChange={setCurrency}
                options={CURRENCIES.map((c) => ({ value: c.code, label: c.code, hint: c.sym }))}
              />
              {trip && (
                <WeatherBadge destination={trip.destination} startDate={trip.start_date} endDate={trip.end_date} />
              )}

              {trip && (
                <button
                  type="button"
                  onClick={() => {
                    setEditTrip(false);
                    setTrip(null);
                  }}
                  aria-label={t.newTrip}
                  className="flex h-10 items-center gap-2 whitespace-nowrap rounded-full border border-[#ffc36b]/45 bg-[#ffc36b]/10 px-3.5 text-xs font-bold text-[#ffd89a] transition hover:bg-[#ffc36b]/20 sm:px-4"
                >
                  <Plus className="h-4 w-4" strokeWidth={2.4} />
                  <span className="hidden sm:inline">{t.newTrip}</span>
                </button>
              )}
            </div>
          </div>

          <AnimatePresence initial={false}>
            {trip && editTrip && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                className="overflow-hidden"
              >
                <form
                  onSubmit={(e) => {
                    setEditTrip(false);
                    handleSubmit(e);
                  }}
                  className="mx-auto flex max-w-[1600px] flex-col gap-3 px-4 pb-4 sm:px-6 md:flex-row md:px-10"
                >
                  <div className="relative flex-1">
                    <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]" />
                    <input
                      value={locationInput}
                      onChange={(e) => setLocationInput(e.target.value)}
                      placeholder={t.searchPlaceholder}
                      className="h-12 w-full rounded-full border border-white/[0.10] bg-white/[0.04] pl-11 pr-4 text-base text-white outline-none transition focus:border-[#ffc36b]/50 focus:shadow-[0_0_15px_rgba(255,195,107,0.2)] md:text-sm"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3 md:flex">
                    <div className="relative">
                      <PlaneTakeoff className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]" />
                      <input
                        id="start-date-header"
                        type="date"
                        value={startDate}
                        min={todayIso()}
                        onChange={(e) => handleStartDate(e.target.value)}
                        className="h-12 w-full rounded-full border border-white/[0.10] bg-white/[0.04] pl-11 pr-3 text-base text-white outline-none transition focus:border-[#ffc36b]/50 md:w-44 md:text-sm"
                        style={{ colorScheme: "dark" }}
                      />
                    </div>
                    <div className="relative">
                      <PlaneLanding className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]" />
                      <input
                        id="return-date-header"
                        type="date"
                        value={returnDate}
                        min={addDays(startDate, 1)}
                        max={addDays(startDate, 30)}
                        onChange={(e) => handleReturnDate(e.target.value)}
                        className="h-12 w-full rounded-full border border-white/[0.10] bg-white/[0.04] pl-11 pr-3 text-base text-white outline-none transition focus:border-[#ffc36b]/50 md:w-44 md:text-sm"
                        style={{ colorScheme: "dark" }}
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={loading || !locationInput.trim()}
                    className="btn-glow inline-flex h-12 items-center justify-center rounded-full px-7 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t.planTrip}
                  </button>
                </form>
              </motion.div>
            )}
          </AnimatePresence>
        </header>

        {showDashboard ? (
          <main className="relative z-10 mx-auto w-full max-w-[1600px] px-4 sm:px-6 py-4 md:px-10 flex-1 flex flex-col justify-center md:overflow-y-auto">
            {trip ? (
              <div className="flex flex-col w-full h-full">
                <CyberDashboard trip={trip} setTrip={setTrip} selectedLanguage={selectedLanguage} />
              </div>
            ) : null}

            {loading && !trip ? <TravelerWaitIndicator destination={locationInput} /> : null}
          </main>
        ) : (
          <Landing
            t={t}
            language={selectedLanguage}
            locationInput={locationInput}
            setLocationInput={setLocationInput}
            startDate={startDate}
            returnDate={returnDate}
            minStart={todayIso()}
            minReturn={addDays(startDate, 1)}
            maxReturn={addDays(startDate, 30)}
            onStartDate={handleStartDate}
            onReturnDate={handleReturnDate}
            daysCount={diffDays(startDate, returnDate)}
            travelers={travelers}
            setTravelers={setTravelers}
            groupLabel={getGroupTypeLabel}
            trending={trending}
            loadingTrending={loadingTrending}
            loading={loading}
            error={error}
            onSubmit={handleSubmit}
          />
        )}
      </div>

      {/* FLOATING VOYA DRAWER */}
      <VoyAI trip={trip} />
    </>
  );
}
