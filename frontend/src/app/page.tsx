"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import CityHeroImage from "@/components/CityHeroImage";
import { AnimatePresence, motion } from "framer-motion";
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
  Settings2,
  ChevronDown,
  ChevronUp,
  Home,
} from "lucide-react";

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

function CulinaryCard({ highlight, destination }: { highlight: CulinaryHighlight; destination: string }) {
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(highlight.title + ' ' + destination)}`;

  return (
    <article className="flex flex-col gap-4 rounded-3xl border border-white/[0.06] bg-white/[0.01] p-6 hover:bg-white/[0.03] transition-colors">
      <div>
        <h3 className="font-syne text-lg font-bold text-white">{highlight.title}</h3>
        <p className="mt-1 text-[0.8rem] font-medium text-orange-400">{highlight.famous_for}</p>
      </div>
      <p className="text-[0.85rem] leading-relaxed text-[#94A3B8] flex-1">
        {highlight.description}
      </p>
      <div className="mt-2 flex items-center justify-between border-t border-white/[0.05] pt-4">
        <span className="text-[0.75rem] text-[#64748B] flex items-center gap-1.5 line-clamp-1 max-w-[60%]">
          <MapPin className="h-3 w-3 shrink-0" />
          {highlight.location}
        </span>
        <a
          href={mapUrl}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 rounded-full bg-blue-500/10 px-3 py-1.5 text-[11px] font-bold text-blue-400 transition-colors hover:bg-blue-500/20"
        >
          Navigate
        </a>
      </div>
    </article>
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

const ACTIVITY_CATEGORIES = [
  "🏛️ Culture & History", "🍕 Foodie & Culinary", "⛰️ Outdoor & Adventure",
  "🛍️ Shopping & Local Markets", "🎨 Art & Entertainment", "🌙 Nightlife & Social",
  "🧘 Wellness & Relaxation", "🎢 Family & Theme Parks"
];

const TRAVEL_PACES = [
  { id: "Relaxed", label: "☕ Relaxed", desc: "1-2 stops/day" },
  { id: "Balanced", label: "🚶 Balanced", desc: "3-4 stops/day" },
  { id: "Action-Packed", label: "⚡ Action-Packed", desc: "5+ stops/day" },
];

const BUDGET_LEVELS = [
  { id: "Budget-Friendly", label: "💰 Budget-Friendly" },
  { id: "Moderate", label: "💳 Moderate" },
  { id: "Luxury", label: "✨ Luxury" },
];

export default function Page() {
  const [locationInput, setLocationInput] = useState("");
  const [startDate, setStartDate] = useState(todayIso());
  const [returnDate, setReturnDate] = useState(() => addDays(todayIso(), 3));
  const [trip, setTrip] = useState<TripPlan | null>(null);
  const [activeDay, setActiveDay] = useState(1);
  const [viewMode, setViewMode] = useState<ViewMode>("split");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [pace, setPace] = useState<string>("Balanced");
  const [budget, setBudget] = useState<string>("Moderate");
  const [showAdvanced, setShowAdvanced] = useState(false);

  async function loadTripPlan(
    location: string, 
    days: number, 
    date: string,
    categories: string[],
    pace: string,
    budget: string
  ) {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/trip-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location, days, start_date: date, categories, pace, budget }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail ?? "Unable to build trip plan.");
      }

      setTrip(payload);
      setActiveDay(1);
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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedLocation = locationInput.trim();
    if (!trimmedLocation) {
      setError("Enter a destination before planning the trip.");
      return;
    }
    const days = Math.min(30, Math.max(1, diffDays(startDate, returnDate)));
    void loadTripPlan(trimmedLocation, days, startDate, selectedCategories, pace, budget);
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

            /* Blue edge glow */
            .blue-glow-left {
              position: fixed;
              left: 0; top: 0; bottom: 0;
              width: 6px;
              background: linear-gradient(180deg, transparent 0%, #2563EB 30%, #3B82F6 50%, #2563EB 70%, transparent 100%);
              box-shadow: 0 0 32px 10px rgba(59,130,246,0.55), 0 0 80px 24px rgba(37,99,235,0.28);
              pointer-events: none;
              z-index: 9999;
              animation: glowPulse 3s ease-in-out infinite;
            }
            .blue-glow-right {
              position: fixed;
              right: 0; top: 0; bottom: 0;
              width: 6px;
              background: linear-gradient(180deg, transparent 0%, #2563EB 30%, #3B82F6 50%, #2563EB 70%, transparent 100%);
              box-shadow: 0 0 32px 10px rgba(59,130,246,0.55), 0 0 80px 24px rgba(37,99,235,0.28);
              pointer-events: none;
              z-index: 9999;
              animation: glowPulse 3s ease-in-out infinite;
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

      {/* Blue edge glows */}
      <div className="blue-glow-left" aria-hidden="true" />
      <div className="blue-glow-right" aria-hidden="true" />

      <div className="min-h-screen bg-[#05070A] text-white font-manrope selection:bg-white selection:text-black">
        <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_top,rgba(148,163,184,0.14),transparent_42%),linear-gradient(180deg,#05070A_0%,#04060A_100%)]" />
        <div className="fixed inset-0 pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.16] mix-blend-overlay" />

        <header className="sticky top-0 z-40 border-b border-white/[0.05] bg-[#05070A]/85 backdrop-blur-2xl">
          <div className="mx-auto flex max-w-[1600px] items-center gap-4 px-6 py-5 md:px-10">
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
                    placeholder="Search a destination..."
                    className="w-full rounded-full border border-white/[0.10] bg-white/[0.03] py-3 pl-11 pr-4 text-sm text-white outline-none transition focus:border-blue-500/50 focus:shadow-[0_0_0_2px_rgba(59,130,246,0.15)]"
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
                    className="w-full rounded-full border border-white/[0.10] bg-white/[0.03] py-3 pl-11 pr-4 text-sm text-white outline-none transition focus:border-blue-500/50 focus:shadow-[0_0_0_2px_rgba(59,130,246,0.15)] md:w-44"
                    style={{ colorScheme: "dark" }}
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || !locationInput.trim()}
                  className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-bold text-[#05070A] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Plan trip"}
                </button>
              </form>
            ) : (
              <div className="ml-auto" />
            )}

            <div className="hidden items-center gap-3 md:flex">
              {trip && (
                <button
                  onClick={() => setTrip(null)}
                  className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-4 py-2.5 text-xs font-bold text-white transition hover:bg-white/[0.08]"
                >
                  <Home className="h-3.5 w-3.5" />
                  New Trip
                </button>
              )}
              
              <div className="flex items-center rounded-full border border-white/[0.08] bg-white/[0.03] p-1">
              <button
                onClick={() => setViewMode("grid")}
                className={cn(
                  "flex items-center gap-2 rounded-full px-3 py-2 text-xs font-bold transition",
                  viewMode === "grid" ? "bg-white text-[#05070A]" : "text-[#94A3B8]"
                )}
              >
                <LayoutGrid className="h-3.5 w-3.5" />
                Grid
              </button>
              <button
                onClick={() => setViewMode("split")}
                className={cn(
                  "flex items-center gap-2 rounded-full px-3 py-2 text-xs font-bold transition",
                  viewMode === "split" ? "bg-white text-[#05070A]" : "text-[#94A3B8]"
                )}
              >
                <MapIcon className="h-3.5 w-3.5" />
                3D Map
              </button>
            </div>
            </div>
          </div>
        </header>

        <main className="relative z-10 mx-auto max-w-[1600px] px-6 py-8 md:px-10">
          {error ? (
            <div className="rounded-[2rem] border border-red-400/20 bg-red-400/10 p-6 text-red-100">
              {error}
            </div>
          ) : null}

          {trip ? (
            <>
              <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-[2.5rem] border border-white/[0.08] bg-white/[0.02] p-8 backdrop-blur-xl">
                  <p className="text-[11px] uppercase tracking-[0.3em] text-[#64748B]">
                    Live destination
                  </p>
                  <h1 className="mt-4 text-4xl font-syne font-bold tracking-tight md:text-6xl">
                    {trip.destination}
                  </h1>

                  <div className="mt-5 flex flex-wrap items-center gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-blue-300">
                      <Calendar className="h-3.5 w-3.5" />
                      {trip.dates}
                    </span>
                    <span className="rounded-full border border-white/[0.1] bg-white/[0.04] px-4 py-2 text-xs font-bold uppercase tracking-[0.18em]">
                      {trip.weather}
                    </span>
                    <span className="rounded-full border border-white/[0.1] bg-white/[0.04] px-4 py-2 text-xs font-bold uppercase tracking-[0.18em]">
                      {trip.days} days
                    </span>
                  </div>

                  <p className="mt-8 max-w-2xl text-sm leading-7 text-[#94A3B8]">
                    Search any destination and choose how many days you want for the trip.
                    The backend geocodes the place, finds nearby stops, builds day plans,
                    and sends route data back to this dashboard.
                  </p>
                </div>

                <div className="overflow-hidden rounded-[2.5rem] border border-white/[0.08] bg-white/[0.02]">
                  <CityHeroImage
                    city={trip.destination}
                    className="h-full min-h-[280px] w-full"
                  />
                </div>
              </section>

              <section className="mt-10 flex gap-4 overflow-x-auto border-b border-white/[0.05] pb-8 hide-scrollbar">
                {Array.from({ length: trip.days }, (_, index) => {
                  const day = index + 1;
                  const dayStops = trip.itinerary.filter((item) => item.day === day);
                  const dateLabel = dayStops[0]?.date ?? `Day ${day}`;
                  return (
                    <button
                      key={day}
                      onClick={() => setActiveDay(day)}
                      className={cn(
                        "min-w-[180px] shrink-0 rounded-[2rem] px-6 py-5 text-left transition",
                        activeDay === day
                          ? "bg-white text-[#05070A]"
                          : "border border-white/[0.08] bg-white/[0.02] text-[#94A3B8]"
                      )}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-[11px] font-bold uppercase tracking-[0.24em]">
                          Day {day}
                        </span>
                        <span className="rounded-full bg-black/10 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.16em]">
                          {dayStops.length} stops
                        </span>
                      </div>
                      <p className="mt-3 text-2xl font-syne font-bold">{dateLabel}</p>
                    </button>
                  );
                })}
              </section>

              <section className="mt-10">
                <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.28em] text-[#64748B]">
                      Day overview
                    </p>
                    <h2 className="mt-2 text-3xl font-syne font-bold tracking-tight">
                      Day {activeDay} itinerary
                    </h2>
                  </div>
                  <p className="text-sm text-[#94A3B8]">{formatRouteSummary(activeRoute)}</p>
                </div>

                {viewMode === "grid" ? (
                  <div className="grid gap-8 sm:grid-cols-2 xl:grid-cols-3">
                    <AnimatePresence mode="popLayout">
                      {filteredItinerary.map((stop) => (
                        <StopCard key={stop.id} stop={stop} destination={trip.destination} />
                      ))}
                    </AnimatePresence>
                  </div>
                ) : (
                  <div className="grid gap-8 xl:grid-cols-[0.95fr_1.05fr]">
                    <div className="grid gap-8 sm:grid-cols-2 xl:grid-cols-1">
                      <AnimatePresence mode="popLayout">
                        {filteredItinerary.map((stop) => (
                          <StopCard key={stop.id} stop={stop} destination={trip.destination} />
                        ))}
                      </AnimatePresence>
                    </div>
                    <div className="min-h-[620px] overflow-hidden rounded-[2rem] border border-white/[0.08]">
                      <VoyantaMap
                        waypoints={filteredItinerary.map((stop) => ({
                          id: stop.id,
                          lat: stop.lat,
                          lng: stop.lng,
                          title: stop.title,
                          location: stop.location,
                        }))}
                        mapImageUrl={trip.map_image_url}
                      />
                    </div>
                  </div>
                )}
              </section>

              {/* Culinary Highlights Section */}
              {trip.culinary_highlights && trip.culinary_highlights.length > 0 && (
                <section className="mt-16 border-t border-white/[0.08] pt-12">
                  <div className="mb-8">
                    <p className="text-[11px] uppercase tracking-[0.28em] text-[#64748B]">
                      Local Flavour
                    </p>
                    <h2 className="mt-2 text-3xl font-syne font-bold tracking-tight">
                      Must-Try Culinary Highlights
                    </h2>
                  </div>
                  <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {trip.culinary_highlights.map((highlight, idx) => (
                      <CulinaryCard key={idx} highlight={highlight} destination={trip.destination} />
                    ))}
                  </div>
                </section>
              )}
            </>
          ) : null}

          {loading && !trip ? (
            <div className="flex min-h-[50vh] items-center justify-center">
              <div className="flex items-center gap-3 rounded-full border border-blue-500/20 bg-blue-500/5 px-5 py-3 text-sm text-[#CBD5E1] shadow-[0_0_24px_rgba(59,130,246,0.12)]">
                <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                Building your trip dashboard...
              </div>
            </div>
          ) : null}

          {!loading && !trip && !error ? (
            <div className="flex min-h-[55vh] items-center justify-center px-4">
              <div className="w-full max-w-[780px] rounded-[2rem] border border-white/[0.07] bg-[#0B0F18]/80 px-10 py-12 text-center backdrop-blur-2xl shadow-[0_0_80px_rgba(0,0,0,0.6)]">

                {/* Icon */}
                <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-[#111827] border border-blue-500/20 shadow-[0_0_28px_rgba(59,130,246,0.25)]">
                  <Navigation className="h-6 w-6 text-blue-400" strokeWidth={1.8} />
                </div>

                {/* Title */}
                <h1 className="font-syne text-[2.6rem] font-extrabold leading-tight tracking-tight text-white">
                  Start with a real destination
                </h1>

                {/* Subtitle */}
                <p className="mx-auto mt-4 max-w-lg text-[0.95rem] leading-relaxed text-[#64748B]">
                  Search for a city or place, pick your travel dates, choose the number of trip days (up to 30), and Voyanta will build the dashboard only after you ask for it.
                </p>

                <form onSubmit={handleSubmit} className="mt-9 flex flex-col gap-[10px]">

                  {/* ── Row 1 : Destination search ── */}
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-[18px] top-1/2 h-[17px] w-[17px] -translate-y-1/2 text-[#475569]" />
                    <input
                      id="destination-input"
                      value={locationInput}
                      onChange={(e) => setLocationInput(e.target.value)}
                      placeholder="Search a destination..."
                      autoComplete="off"
                      className="w-full rounded-full border border-white/[0.09] bg-[#111827]/60 py-[14px] pl-12 pr-5 text-[0.95rem] text-white placeholder-[#475569] outline-none transition-all focus:border-blue-500/40 focus:bg-[#111827]/90 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.12)]"
                    />
                  </div>

                  {/* ── Row 2 : Departure | Return | Plan trip ── */}
                  <div className="flex items-center gap-[10px]">

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

                    {/* Plan trip button */}
                    <button
                      id="plan-trip-btn"
                      type="submit"
                      disabled={loading || !locationInput.trim()}
                      className="shrink-0 rounded-full bg-white px-7 py-[14px] text-[0.95rem] font-bold text-[#05070A] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Plan trip"}
                    </button>
                  </div>

                  {/* Days pill — live count */}
                  <div className="flex justify-center pt-1">
                    <span className="rounded-full border border-blue-500/25 bg-blue-500/8 px-3 py-1 text-[11px] font-semibold text-blue-400 tracking-wide">
                      {diffDays(startDate, returnDate)}&nbsp;day{diffDays(startDate, returnDate) !== 1 ? "s" : ""}
                    </span>
                  </div>

                  {/* Advanced Options Toggle */}
                  <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="mx-auto mt-2 flex items-center gap-2 text-[0.85rem] text-[#64748B] hover:text-white transition-colors"
                  >
                    <Settings2 className="h-4 w-4" />
                    Advanced preferences
                    {showAdvanced ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>

                  {/* Advanced Options Panel */}
                  <AnimatePresence>
                    {showAdvanced && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="mt-4 flex flex-col gap-6 rounded-2xl border border-white/[0.05] bg-white/[0.02] p-6 text-left">
                          
                          {/* Categories */}
                          <div>
                            <p className="mb-3 text-[0.85rem] font-semibold text-white">Activity Interests</p>
                            <div className="flex flex-wrap gap-2">
                              {ACTIVITY_CATEGORIES.map(cat => {
                                const isSelected = selectedCategories.includes(cat);
                                return (
                                  <button
                                    key={cat}
                                    type="button"
                                    onClick={() => setSelectedCategories(prev => 
                                      isSelected ? prev.filter(c => c !== cat) : [...prev, cat]
                                    )}
                                    className={cn(
                                      "rounded-full px-4 py-2 text-[0.8rem] transition-colors border",
                                      isSelected 
                                        ? "bg-blue-500/20 border-blue-500/50 text-blue-100" 
                                        : "bg-white/[0.03] border-white/[0.08] text-[#94A3B8] hover:bg-white/[0.08]"
                                    )}
                                  >
                                    {cat}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          <div className="grid gap-6 md:grid-cols-2">
                            {/* Pace */}
                            <div>
                              <p className="mb-3 text-[0.85rem] font-semibold text-white">Travel Pace</p>
                              <div className="flex flex-col gap-2">
                                {TRAVEL_PACES.map(p => (
                                  <label key={p.id} className="flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.05] bg-white/[0.02] p-3 hover:bg-white/[0.05] transition-colors">
                                    <input
                                      type="radio"
                                      name="pace"
                                      value={p.id}
                                      checked={pace === p.id}
                                      onChange={() => setPace(p.id)}
                                      className="h-4 w-4 accent-blue-500"
                                    />
                                    <div className="flex flex-col">
                                      <span className="text-[0.85rem] text-white">{p.label}</span>
                                      <span className="text-[0.75rem] text-[#64748B]">{p.desc}</span>
                                    </div>
                                  </label>
                                ))}
                              </div>
                            </div>

                            {/* Budget */}
                            <div>
                              <p className="mb-3 text-[0.85rem] font-semibold text-white">Budget Level</p>
                              <div className="flex flex-col gap-2">
                                {BUDGET_LEVELS.map(b => (
                                  <label key={b.id} className="flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.05] bg-white/[0.02] p-3 hover:bg-white/[0.05] transition-colors">
                                    <input
                                      type="radio"
                                      name="budget"
                                      value={b.id}
                                      checked={budget === b.id}
                                      onChange={() => setBudget(b.id)}
                                      className="h-4 w-4 accent-blue-500"
                                    />
                                    <span className="text-[0.85rem] text-white">{b.label}</span>
                                  </label>
                                ))}
                              </div>
                            </div>
                          </div>

                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </form>

                <p className="mt-5 text-[0.8rem] text-[#334155]">
                  When you open the map, clicking any marker will open navigation for that place.
                </p>
              </div>
            </div>
          ) : null}
        </main>
      </div>
    </>
  );
}
