"use client";

import { useMemo, useState, useEffect } from "react";
import dynamic from "next/dynamic";
import CyberDashboard from "@/components/dashboard/CyberDashboard";
import VoyAI from "@/components/ai/Voya";
import CityHeroImage from "@/components/CityHeroImage";
import { TravelerWaitIndicator } from "@/components/ui/traveler-wait-indicator";
import { AnimatePresence, motion } from "framer-motion";
import { DestinationInput } from "@/components/search/DestinationInput";
import { useCurrency } from "@/context/CurrencyContext";
import {
  Calendar,
  Loader2,
  MapPin,
  Search,
  Snowflake,
  LayoutGrid,
  Map as MapIcon,
  Navigation,
  PlaneTakeoff,
  PlaneLanding,
  Home,
  Users,
  ChevronDown,
  Plus,
  Minus,
} from "lucide-react";

import { getTranslation, LanguageName } from "@/lib/i18n";

const VoyantaMap = dynamic(() => import("@/components/VoyantaMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[520px] bg-[#0A0D14] rounded-[2rem] border border-white/[0.08] flex items-center justify-center text-[#94A3B8]">
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
      className="group overflow-hidden rounded-[2rem] bg-[#0A0D14]/85 border border-white/[0.08] shadow-2xl cursor-pointer transition-all hover:border-blue-500/40 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]"
    >
      <div className="relative h-64 overflow-hidden">
        <img
          src={stop.image}
          alt={stop.title}
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#07090E] via-[#07090E]/30 to-transparent" />
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
    <div className="relative flex flex-col justify-between p-6 rounded-2xl bg-zinc-900/80 border border-zinc-800 hover:border-pink-500/30 transition-all duration-300 min-h-[220px]">
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
          className="px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium hover:bg-cyan-500/20 transition-all"
        >
          Navigate
        </a>
      </div>
    </div>
  );
}

/** Today as YYYY-MM-DD for the date input min attribute */
function todayIso() {
  return new Date().toISOString().split("T")[0];
}

/** Add `n` days to a YYYY-MM-DD string, return YYYY-MM-DD */
function addDays(iso: string, n: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + n);
  return d.toISOString().split("T")[0];
}

function diffDays(start: string, end: string): number {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  return Math.max(1, Math.round(ms / 86400000));
}

export default function Page() {
  const { currency, setCurrency } = useCurrency();
  const [locationInput, setLocationInput] = useState("");
  const [startDate, setStartDate] = useState(todayIso());
  const [returnDate, setReturnDate] = useState(() => addDays(todayIso(), 3));
  const [trip, setTrip] = useState<TripPlan | null>(null);
  const [activeDay, setActiveDay] = useState(1);
  const [viewMode, setViewMode] = useState<ViewMode>("split");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [travelers, setTravelers] = useState<TravelersState>({
    group_type: "Couple",
    adults: 2,
    seniors: 0,
    infants: 0,
  });
  const [isTravelersOpen, setIsTravelersOpen] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageName>("English");

  const t = getTranslation(selectedLanguage);

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
    }, 50);

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

      setTrip(payload);
      setActiveDay(1);
      if (typeof window !== "undefined") {
        window.history.pushState({ step: "dashboard" }, "");
      }
    } catch (err) {
      setTrip(null);
      setError(err instanceof Error ? err.message : "Something went wrong.");
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

  return (
    <>
      <style
        dangerouslySetInnerHTML={{
          __html: `
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Syne:wght@400;600;700;800&display=swap');
            body {
              background: #05070A;
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

      <div className="relative min-h-screen h-screen max-h-screen overflow-hidden bg-[#05070A] font-manrope text-white selection:bg-[#ff007f] selection:text-white flex flex-col justify-between">
        <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_top,rgba(148,163,184,0.14),transparent_42%),linear-gradient(180deg,#05070A_0%,#04060A_100%)]" />
        <div className="fixed inset-0 pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.16] mix-blend-overlay" />

        <header className="sticky top-0 z-40 border-b border-white/[0.05] bg-[#05070A]/85 backdrop-blur-2xl shrink-0">
          <div className="mx-auto flex max-w-[1600px] flex-col md:flex-row md:items-center gap-4 px-6 py-3.5 md:px-10">
            <button
              type="button"
              onClick={() => setTrip(null)}
              className="flex items-center gap-3 transition-opacity hover:opacity-80"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white shadow-[0_0_28px_rgba(255,255,255,0.18)]">
                <Snowflake className="h-5 w-5 text-black" />
              </div>
              <span className="text-xl font-syne font-bold tracking-tight">VOYANTA</span>
            </button>

            {trip ? (
              <form
                onSubmit={handleSubmit}
                className="ml-auto flex w-full max-w-5xl flex-col gap-3 md:flex-row"
              >
                <div className="relative flex-1">
                  <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]" />
                  <input
                    value={locationInput}
                    onChange={(e) => setLocationInput(e.target.value)}
                    placeholder={t.searchPlaceholder}
                    className="w-full rounded-full border border-white/[0.10] bg-white/[0.03] py-3 pl-11 pr-4 text-sm text-white outline-none transition focus:border-[#00f0ff]/50 focus:shadow-[0_0_15px_rgba(0,240,255,0.2)]"
                  />
                </div>
                {/* Departure date */}
                <div className="relative">
                  <PlaneTakeoff className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]" />
                  <input
                    id="start-date-header"
                    type="date"
                    value={startDate}
                    min={todayIso()}
                    onChange={(e) => handleStartDate(e.target.value)}
                    className="w-full rounded-full border border-white/[0.10] bg-white/[0.03] py-3 pl-11 pr-4 text-sm text-white outline-none transition focus:border-blue-500/50 focus:shadow-[0_0_0_2px_rgba(59,130,246,0.15)] md:w-44"
                    style={{ colorScheme: "dark" }}
                  />
                </div>
                {/* Return date */}
                <div className="relative">
                  <PlaneLanding className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]" />
                  <input
                    id="return-date-header"
                    type="date"
                    value={returnDate}
                    min={addDays(startDate, 1)}
                    max={addDays(startDate, 30)}
                    onChange={(e) => handleReturnDate(e.target.value)}
                    className="w-full rounded-full border border-white/[0.10] bg-white/[0.03] py-3 pl-11 pr-4 text-sm text-white outline-none transition focus:border-[#00f0ff]/50 focus:shadow-[0_0_15px_rgba(0,240,255,0.2)] md:w-44"
                    style={{ colorScheme: "dark" }}
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || !locationInput.trim()}
                  className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-bold text-[#05070A] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t.planTrip}
                </button>
              </form>
            ) : (
              <div className="ml-auto" />
            )}

            <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
              {/* Language Selector */}
              <div className="flex items-center gap-1.5 rounded-full border border-[#00f0ff]/40 bg-[#03050a]/80 px-3 py-1.5 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
                <span className="text-xs font-bold text-[#00f0ff]">🌐</span>
                <select 
                  value={selectedLanguage} 
                  onChange={e => setSelectedLanguage(e.target.value as LanguageName)}
                  className="bg-transparent text-white text-xs font-bold outline-none cursor-pointer"
                >
                  {LANGUAGES.map(lang => (
                    <option key={lang.code} value={lang.name} className="bg-[#03050a] text-white">
                      {lang.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Currency Selector */}
              <div className="flex items-center gap-1.5 rounded-full border border-[#00f0ff]/40 bg-[#03050a]/80 px-3 py-1.5 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
                <span className="text-xs font-bold text-[#00f0ff]">💲</span>
                <select 
                  value={currency} 
                  onChange={e => setCurrency(e.target.value)}
                  className="bg-transparent text-white text-xs font-bold outline-none cursor-pointer"
                >
                  <option value="USD" className="bg-[#03050a] text-white">USD ($)</option>
                  <option value="EUR" className="bg-[#03050a] text-white">EUR (€)</option>
                  <option value="GBP" className="bg-[#03050a] text-white">GBP (£)</option>
                  <option value="INR" className="bg-[#03050a] text-white">INR (₹)</option>
                  <option value="JPY" className="bg-[#03050a] text-white">JPY (¥)</option>
                  <option value="AUD" className="bg-[#03050a] text-white">AUD (A$)</option>
                  <option value="CAD" className="bg-[#03050a] text-white">CAD (C$)</option>
                  <option value="AED" className="bg-[#03050a] text-white">AED (د.إ)</option>
                  <option value="SGD" className="bg-[#03050a] text-white">SGD (S$)</option>
                </select>
              </div>

              {trip && (
                <button
                  onClick={() => setTrip(null)}
                  className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-4 py-2.5 text-xs font-bold text-white transition hover:bg-white/[0.08]"
                >
                  <Home className="h-3.5 w-3.5" />
                  {t.newTrip}
                </button>
              )}
            </div>
          </div>
        </header>

        <main className="relative z-10 mx-auto w-full max-w-[1600px] px-6 py-4 md:px-10 flex-1 flex flex-col justify-center overflow-y-auto">
          {error ? (
            <div className="mx-auto my-auto max-w-2xl rounded-3xl border border-[#00f0ff]/40 bg-[#03050a]/90 p-8 text-center backdrop-blur-md shadow-[0_0_40px_rgba(0,240,255,0.15)]">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#111827] border border-[#ff007f]/40 shadow-[0_0_20px_rgba(255,0,127,0.2)]">
                <Navigation className="h-6 w-6 text-[#ff007f]" strokeWidth={2} />
              </div>
              <h3 className="mb-2 font-syne text-xl font-bold text-white">{t.connectionInterrupted}</h3>
              <p className="mb-6 text-sm text-[#94A3B8]">{error}</p>
              <button
                onClick={() => handleSubmit()}
                className="rounded-full bg-[#00f0ff]/10 px-6 py-2.5 text-sm font-bold text-[#00f0ff] transition-all hover:bg-[#00f0ff]/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.3)] border border-[#00f0ff]/30"
              >
                {t.retryGeneration}
              </button>
            </div>
          ) : null}

          {trip ? (
            <div className="flex flex-col w-full h-full">
              <CyberDashboard trip={trip} setTrip={setTrip} selectedLanguage={selectedLanguage} />
            </div>
          ) : null}

          {loading && !trip ? (
            <TravelerWaitIndicator destination={locationInput} />
          ) : null}

          {!loading && !trip && !error ? (
            <div className="flex my-auto items-center justify-center px-4 py-2">
              <div className="w-full max-w-[780px] rounded-[2rem] border border-white/[0.07] bg-[#0B0F18]/80 px-6 py-6 md:px-10 md:py-8 text-center backdrop-blur-2xl shadow-[0_0_80px_rgba(0,0,0,0.6)]">

                {/* Icon */}
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#111827] border border-blue-500/20 shadow-[0_0_28px_rgba(59,130,246,0.25)]">
                  <Navigation className="h-5 w-5 text-blue-400" strokeWidth={1.8} />
                </div>

                {/* Title */}
                <h1 className="font-syne text-2xl md:text-[2.2rem] font-extrabold leading-tight tracking-tight text-white">
                  {t.heroTitle}
                </h1>

                {/* Subtitle */}
                <p className="mx-auto mt-3 max-w-lg text-[0.9rem] leading-relaxed text-[#64748B]">
                  {t.heroSubtitle}
                </p>

                <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-[10px]">

                  {/* ── Row 1 : Destination search ── */}
                  <DestinationInput
                    value={locationInput}
                    onChange={setLocationInput}
                    placeholder={t.searchPlaceholder}
                  />

                  {/* Suggestion Chips */}
                  <div className="flex flex-wrap gap-2 mt-1 mb-2">
                    {['Kyoto', 'Lucknow', 'Dubai', 'Paris', 'New York', 'Tokyo', 'Delhi', 'London'].map(city => (
                      <button
                        key={city}
                        type="button"
                        onClick={() => {
                          setLocationInput(city);
                          setIsAutocompleteOpen(false);
                        }}
                        className="bg-[#00f0ff]/10 border border-[#00f0ff]/30 text-[#00f0ff] text-[10px] px-3 py-1 rounded-full font-bold tracking-widest hover:bg-[#00f0ff] hover:text-black transition-colors"
                      >
                        {city}
                      </button>
                    ))}
                  </div>

                  {/* ── Row 2 : Departure | Return | Travelers | Plan trip ── */}
                  <div className="flex flex-col md:flex-row items-stretch md:items-center gap-[10px]">

                    {/* Departure date */}
                    <div className="relative flex-1">
                      <PlaneTakeoff className="pointer-events-none absolute left-[18px] top-1/2 h-[16px] w-[16px] -translate-y-1/2 text-[#475569]" />
                      <input
                        id="start-date-main"
                        type="date"
                        value={startDate}
                        min={todayIso()}
                        onChange={(e) => handleStartDate(e.target.value)}
                        className="w-full rounded-full border border-white/[0.09] bg-[#111827]/60 py-[14px] pl-12 pr-4 text-[0.95rem] text-white outline-none transition-all focus:border-blue-500/40 focus:bg-[#111827]/90 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.12)]"
                        style={{ colorScheme: "dark" }}
                      />
                    </div>

                    {/* Return date */}
                    <div className="relative flex-1">
                      <PlaneLanding className="pointer-events-none absolute left-[18px] top-1/2 h-[16px] w-[16px] -translate-y-1/2 text-[#475569]" />
                      <input
                        id="return-date-main"
                        type="date"
                        value={returnDate}
                        min={addDays(startDate, 1)}
                        max={addDays(startDate, 30)}
                        onChange={(e) => handleReturnDate(e.target.value)}
                        className="w-full rounded-full border border-white/[0.09] bg-[#111827]/60 py-[14px] pl-12 pr-4 text-[0.95rem] text-white outline-none transition-all focus:border-blue-500/40 focus:bg-[#111827]/90 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.12)]"
                        style={{ colorScheme: "dark" }}
                      />
                    </div>

                    {/* Travelers Popover */}
                    <div className="relative flex-1">
                      <button
                        type="button"
                        onClick={() => setIsTravelersOpen(!isTravelersOpen)}
                        className="w-full flex items-center justify-between gap-2 rounded-full border border-[#00f0ff]/40 bg-[#111827]/80 py-[14px] px-5 text-[0.85rem] font-bold text-white outline-none transition-all hover:border-[#00f0ff] focus:border-[#00f0ff] focus:shadow-[0_0_15px_rgba(0,240,255,0.3)] cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <Users className="h-4 w-4 text-[#00f0ff] shrink-0" />
                          <span className="truncate">
                            {getGroupTypeLabel(travelers.group_type)} ({travelers.adults + travelers.seniors + travelers.infants})
                          </span>
                        </div>
                        <ChevronDown className="h-4 w-4 text-[#64748B] shrink-0" />
                      </button>

                      {isTravelersOpen && (
                        <div className="absolute top-full mt-2 right-0 w-80 bg-[#03050a]/95 backdrop-blur-2xl border border-[#00f0ff]/40 rounded-3xl p-5 z-50 shadow-[0_10px_40px_rgba(0,240,255,0.25)] text-left">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-[#00f0ff] mb-3">{t.groupType}</p>
                          <div className="flex flex-wrap gap-2 mb-5">
                            {(['Solo', 'Couple', 'Family', 'Friends', 'Business'] as const).map((type) => (
                              <button
                                key={type}
                                type="button"
                                onClick={() => setTravelers((prev) => ({ ...prev, group_type: type }))}
                                className={cn(
                                  "px-3 py-1.5 rounded-full text-xs font-bold transition-all border",
                                  travelers.group_type === type
                                    ? "bg-[#00f0ff]/20 border-[#00f0ff] text-white shadow-[0_0_12px_rgba(0,240,255,0.3)]"
                                    : "bg-white/5 border-white/10 text-[#94A3B8] hover:bg-white/10 hover:text-white"
                                )}
                              >
                                {getGroupTypeLabel(type)}
                              </button>
                            ))}
                          </div>

                          <p className="text-[11px] font-bold uppercase tracking-wider text-[#00f0ff] mb-3">{t.travelerCounts}</p>
                          <div className="flex flex-col gap-3.5">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm font-semibold text-white">{t.adults}</p>
                                <p className="text-[11px] text-[#64748B]">{t.adultsDesc}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <button
                                  type="button"
                                  onClick={() => setTravelers((prev) => ({ ...prev, adults: Math.max(1, prev.adults - 1) }))}
                                  className="h-7 w-7 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white hover:bg-white/20 transition"
                                >
                                  <Minus className="h-3.5 w-3.5" />
                                </button>
                                <span className="text-sm font-bold text-white w-4 text-center">{travelers.adults}</span>
                                <button
                                  type="button"
                                  onClick={() => setTravelers((prev) => ({ ...prev, adults: prev.adults + 1 }))}
                                  className="h-7 w-7 rounded-full bg-[#00f0ff]/20 border border-[#00f0ff]/40 flex items-center justify-center text-[#00f0ff] hover:bg-[#00f0ff]/30 transition"
                                >
                                  <Plus className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>

                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm font-semibold text-white">{t.seniors}</p>
                                <p className="text-[11px] text-[#64748B]">{t.seniorsDesc}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <button
                                  type="button"
                                  onClick={() => setTravelers((prev) => ({ ...prev, seniors: Math.max(0, prev.seniors - 1) }))}
                                  className="h-7 w-7 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white hover:bg-white/20 transition"
                                >
                                  <Minus className="h-3.5 w-3.5" />
                                </button>
                                <span className="text-sm font-bold text-white w-4 text-center">{travelers.seniors}</span>
                                <button
                                  type="button"
                                  onClick={() => setTravelers((prev) => ({ ...prev, seniors: prev.seniors + 1 }))}
                                  className="h-7 w-7 rounded-full bg-[#00f0ff]/20 border border-[#00f0ff]/40 flex items-center justify-center text-[#00f0ff] hover:bg-[#00f0ff]/30 transition"
                                >
                                  <Plus className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>

                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm font-semibold text-white">{t.infants}</p>
                                <p className="text-[11px] text-[#64748B]">{t.infantsDesc}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <button
                                  type="button"
                                  onClick={() => setTravelers((prev) => ({ ...prev, infants: Math.max(0, prev.infants - 1) }))}
                                  className="h-7 w-7 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white hover:bg-white/20 transition"
                                >
                                  <Minus className="h-3.5 w-3.5" />
                                </button>
                                <span className="text-sm font-bold text-white w-4 text-center">{travelers.infants}</span>
                                <button
                                  type="button"
                                  onClick={() => setTravelers((prev) => ({ ...prev, infants: prev.infants + 1 }))}
                                  className="h-7 w-7 rounded-full bg-[#00f0ff]/20 border border-[#00f0ff]/40 flex items-center justify-center text-[#00f0ff] hover:bg-[#00f0ff]/30 transition"
                                >
                                  <Plus className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => setIsTravelersOpen(false)}
                            className="w-full mt-5 py-2.5 rounded-full bg-[#00f0ff]/15 border border-[#00f0ff]/40 text-[#00f0ff] text-xs font-bold hover:bg-[#00f0ff]/30 transition"
                          >
                            {t.applySelection}
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Plan trip button */}
                    <button
                      id="plan-trip-btn"
                      type="submit"
                      disabled={loading || !locationInput.trim()}
                      className="w-full sm:w-auto shrink-0 rounded-full bg-white px-7 py-[14px] text-[0.95rem] font-bold text-[#05070A] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t.planTrip}
                    </button>
                  </div>

                  {/* Days pill — live count */}
                  <div className="flex justify-center pt-1">
                    <span className="rounded-full border border-blue-500/25 bg-blue-500/8 px-3 py-1 text-[11px] font-semibold text-blue-400 tracking-wide">
                      {diffDays(startDate, returnDate)}&nbsp;{diffDays(startDate, returnDate) > 1 ? t.days : t.day}
                    </span>
                  </div>
                </form>

                <p className="mt-5 text-[0.8rem] text-[#334155]">
                  When you open the map, clicking any marker will open navigation for that place.
                </p>
              </div>
            </div>
          ) : null}
        </main>
      </div>

      {/* FLOATING VOYA DRAWER */}
      <VoyAI trip={trip} />
    </>
  );
}
