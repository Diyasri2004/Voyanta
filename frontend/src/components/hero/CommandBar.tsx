"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, PlaneLanding, PlaneTakeoff, TriangleAlert } from "lucide-react";
import { DestinationInput } from "@/components/search/DestinationInput";
import MagneticButton from "@/components/ui/MagneticButton";
import { TravelersButton, TravelersPanel } from "./TravelersPopover";
import type { LandingProps } from "./types";

const dateField =
  "w-full min-h-[3.4rem] rounded-2xl border border-white/10 bg-white/[0.045] pl-11 pr-3 text-sm font-medium text-white outline-none transition hover:border-white/25 focus:border-[#ffc36b]/60";

export default function CommandBar(p: LandingProps) {
  const { t } = p;
  const [travOpen, setTravOpen] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  // close on outside click / Escape
  useEffect(() => {
    if (!travOpen) return;
    const onDown = (e: MouseEvent) => {
      if (formRef.current && !formRef.current.contains(e.target as Node)) setTravOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setTravOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [travOpen]);

  return (
    <form
      ref={formRef}
      onSubmit={p.onSubmit}
      className="glass relative w-full rounded-[1.6rem] p-3 sm:p-4"
      aria-label="Plan a trip"
    >
      <DestinationInput value={p.locationInput} onChange={p.setLocationInput} placeholder={t.searchPlaceholder} />

      <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-[1fr_1fr_1fr_auto]">
        <label className="relative block">
          <span className="sr-only">Departure date</span>
          <PlaneTakeoff className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#ffc36b]" />
          <input
            id="start-date-main"
            type="date"
            value={p.startDate}
            min={p.minStart}
            onChange={(e) => p.onStartDate(e.target.value)}
            className={dateField}
            style={{ colorScheme: "dark" }}
          />
        </label>

        <label className="relative block">
          <span className="sr-only">Return date</span>
          <PlaneLanding className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#ffc36b]" />
          <input
            id="return-date-main"
            type="date"
            value={p.returnDate}
            min={p.minReturn}
            max={p.maxReturn}
            onChange={(e) => p.onReturnDate(e.target.value)}
            className={dateField}
            style={{ colorScheme: "dark" }}
          />
        </label>

        <div className="col-span-2 lg:col-span-1">
          <TravelersButton travelers={p.travelers} open={travOpen} onToggle={() => setTravOpen((o) => !o)} />
        </div>

        <div className="col-span-2 lg:col-span-1">
          <MagneticButton className="w-full">
            <button
              id="plan-trip-btn"
              type="submit"
              disabled={p.loading || !p.locationInput.trim()}
              className="btn-glow flex min-h-[3.4rem] w-full items-center justify-center gap-2 rounded-2xl px-8 text-[0.95rem] font-bold disabled:cursor-not-allowed disabled:opacity-50"
            >
              {p.loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t.planTrip}
            </button>
          </MagneticButton>
        </div>
      </div>

      {travOpen && <TravelersPanel t={t} travelers={p.travelers} setTravelers={p.setTravelers} onClose={() => setTravOpen(false)} />}

      <p className="mt-3 px-1 text-xs text-white/45">
        {p.daysCount} {p.daysCount > 1 ? t.days : t.day}
      </p>

      {p.error && (
        <div role="alert" className="mt-3 flex items-start gap-2.5 rounded-xl border border-[#ff8a5c]/30 bg-[#ff8a5c]/10 px-4 py-3 text-sm text-[#ffd3c0]">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-[#ff8a5c]" />
          <span className="break-words">{p.error}</span>
        </div>
      )}
    </form>
  );
}
