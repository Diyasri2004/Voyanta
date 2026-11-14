"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Minus, Plus, Users } from "lucide-react";
import type { TranslationDictionary } from "@/lib/i18n";
import type { TravelersState } from "@/app/page";

/** The trip type is no longer chosen by hand; it is worked out from who is travelling. */
function inferGroup(adults: number, seniors: number, infants: number): TravelersState["group_type"] {
  const total = adults + seniors + infants;
  if (total <= 1) return "Solo";
  if (infants > 0 || seniors > 0) return "Family";
  if (total === 2) return "Couple";
  return "Friends";
}

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
  groupLabel: _groupLabel,
}: {
  t: TranslationDictionary;
  travelers: TravelersState;
  setTravelers: React.Dispatch<React.SetStateAction<TravelersState>>;
  groupLabel: (type: string) => string;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const total = travelers.adults + travelers.seniors + travelers.infants;
  const [place, setPlace] = useState<{ up: boolean; max: number }>({ up: true, max: 480 });

  const update = (patch: Partial<Pick<TravelersState, "adults" | "seniors" | "infants">>) =>
    setTravelers((p) => {
      const next = { ...p, ...patch };
      return { ...next, group_type: inferGroup(next.adults, next.seniors, next.infants) };
    });

  // Open towards whichever side of the button has more room, so it is never cut off by the header or the screen edge.
  const toggle = () => {
    if (!open && root.current) {
      const r = root.current.getBoundingClientRect();
      const above = r.top - 84;
      const below = window.innerHeight - r.bottom - 16;
      const up = above >= 330 || above >= below;
      setPlace({ up, max: Math.max(220, Math.floor(up ? above : below) - 12) });
    }
    setOpen((o) => !o);
  };

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
        onClick={toggle}
        className="flex h-full min-h-[3.4rem] w-full items-center justify-between gap-2 rounded-2xl border border-white/10 bg-white/[0.045] px-4 text-sm font-semibold text-white outline-none transition hover:border-white/25 focus-visible:border-[#ffc36b]/60"
      >
        <span className="flex items-center gap-2.5">
          <Users className="h-4 w-4 shrink-0 text-[#ffc36b]" />
          <span className="truncate">
            {total} {total === 1 ? "traveler" : "travelers"}
          </span>
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-white/50 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          style={{ maxHeight: place.max }}
          className={`absolute right-0 z-50 w-[min(20rem,calc(100vw-2rem))] overflow-y-auto overscroll-contain ${place.up ? "bottom-full mb-3" : "top-full mt-3"} rounded-3xl border border-white/12 bg-[#080d19]/95 p-5 text-left shadow-[0_24px_70px_-10px_rgba(0,0,0,0.9)] backdrop-blur-2xl`}
        >
          <p className="mb-3 text-xs font-semibold text-[#ffc36b]">{t.travelerCounts}</p>
          <div className="flex flex-col gap-4">
            <Stepper label={t.adults} hint={t.adultsDesc} value={travelers.adults} min={1} onChange={(v) => update({ adults: v })} />
            <Stepper label={t.seniors} hint={t.seniorsDesc} value={travelers.seniors} min={0} onChange={(v) => update({ seniors: v })} />
            <Stepper label={t.infants} hint={t.infantsDesc} value={travelers.infants} min={0} onChange={(v) => update({ infants: v })} />
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
