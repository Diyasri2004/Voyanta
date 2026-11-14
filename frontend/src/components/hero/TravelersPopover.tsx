"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Minus, Plus, Users } from "lucide-react";
import type { TranslationDictionary } from "@/lib/i18n";
import type { TravelersState } from "@/app/page";

const GROUPS = ["Solo", "Couple", "Family", "Friends", "Business"] as const;

function Stepper({
  label,
  hint,
  value,
  min,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  min: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="text-[11px] text-white/45">{hint}</p>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label={`Fewer ${label}`}
          onClick={() => onChange(Math.max(min, value - 1))}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-white/5 text-white transition hover:bg-white/15"
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <span className="w-4 text-center text-sm font-bold text-white tabular-nums">{value}</span>
        <button
          type="button"
          aria-label={`More ${label}`}
          onClick={() => onChange(value + 1)}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-[#ffc36b]/40 bg-[#ffc36b]/15 text-[#ffc36b] transition hover:bg-[#ffc36b]/25"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export default function TravelersPopover({
  t,
  travelers,
  setTravelers,
  groupLabel,
}: {
  t: TranslationDictionary;
  travelers: TravelersState;
  setTravelers: React.Dispatch<React.SetStateAction<TravelersState>>;
  groupLabel: (type: string) => string;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const total = travelers.adults + travelers.seniors + travelers.infants;

  // close on outside click / Escape
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex h-full min-h-[3.4rem] w-full items-center justify-between gap-2 rounded-2xl border border-white/10 bg-white/[0.045] px-4 text-sm font-semibold text-white outline-none transition hover:border-white/25 focus-visible:border-[#ffc36b]/60"
      >
        <span className="flex items-center gap-2.5">
          <Users className="h-4 w-4 shrink-0 text-[#ffc36b]" />
          <span className="truncate">
            {groupLabel(travelers.group_type)} ({total})
          </span>
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-white/50 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute bottom-full right-0 z-50 mb-3 w-[min(20rem,calc(100vw-2rem))] rounded-3xl border border-white/12 bg-[#080d19]/95 p-5 text-left shadow-[0_24px_70px_-10px_rgba(0,0,0,0.9)] backdrop-blur-2xl">
          <p className="mb-3 text-xs font-semibold text-[#ffc36b]">{t.groupType}</p>
          <div className="mb-5 flex flex-wrap gap-2">
            {GROUPS.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setTravelers((p) => ({ ...p, group_type: type }))}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                  travelers.group_type === type
                    ? "border-[#ffc36b] bg-[#ffc36b]/15 text-white"
                    : "border-white/10 bg-white/5 text-white/60 hover:bg-white/10 hover:text-white"
                }`}
              >
                {groupLabel(type)}
              </button>
            ))}
          </div>

          <p className="mb-3 text-xs font-semibold text-[#ffc36b]">{t.travelerCounts}</p>
          <div className="flex flex-col gap-4">
            <Stepper label={t.adults} hint={t.adultsDesc} value={travelers.adults} min={1} onChange={(v) => setTravelers((p) => ({ ...p, adults: v }))} />
            <Stepper label={t.seniors} hint={t.seniorsDesc} value={travelers.seniors} min={0} onChange={(v) => setTravelers((p) => ({ ...p, seniors: v }))} />
            <Stepper label={t.infants} hint={t.infantsDesc} value={travelers.infants} min={0} onChange={(v) => setTravelers((p) => ({ ...p, infants: v }))} />
          </div>

          <button
            type="button"
            onClick={() => setOpen(false)}
            className="mt-5 w-full rounded-full border border-[#ffc36b]/40 bg-[#ffc36b]/12 py-2.5 text-xs font-bold text-[#ffc36b] transition hover:bg-[#ffc36b]/22"
          >
            {t.applySelection}
          </button>
        </div>
      )}
    </div>
  );
}
