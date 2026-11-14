"use client";

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

export function TravelersButton({
  travelers,
  open,
  onToggle,
}: {
  travelers: TravelersState;
  open: boolean;
  onToggle: () => void;
}) {
  const total = travelers.adults + travelers.seniors + travelers.infants;
  return (
    <button
      type="button"
      aria-expanded={open}
      onClick={onToggle}
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
  );
}

/** Opens below the controls as part of the card, so it never covers the search box or the destination chips. */
export function TravelersPanel({
  t,
  travelers,
  setTravelers,
  onClose,
}: {
  t: TranslationDictionary;
  travelers: TravelersState;
  setTravelers: React.Dispatch<React.SetStateAction<TravelersState>>;
  onClose: () => void;
}) {
  const update = (patch: Partial<Pick<TravelersState, "adults" | "seniors" | "infants">>) =>
    setTravelers((p) => {
      const next = { ...p, ...patch };
      return { ...next, group_type: inferGroup(next.adults, next.seniors, next.infants) };
    });

  return (
    <div className="mt-3 w-full rounded-2xl border border-white/12 bg-[#080d19]/80 p-5 text-left lg:ml-auto lg:max-w-sm">
      <p className="mb-3 text-xs font-semibold text-[#ffc36b]">{t.travelerCounts}</p>
      <div className="flex flex-col gap-4">
        <Stepper label={t.adults} hint={t.adultsDesc} value={travelers.adults} min={1} onChange={(v) => update({ adults: v })} />
        <Stepper label={t.seniors} hint={t.seniorsDesc} value={travelers.seniors} min={0} onChange={(v) => update({ seniors: v })} />
        <Stepper label={t.infants} hint={t.infantsDesc} value={travelers.infants} min={0} onChange={(v) => update({ infants: v })} />
      </div>
      <button
        type="button"
        onClick={onClose}
        className="mt-5 w-full rounded-full border border-[#ffc36b]/40 bg-[#ffc36b]/12 py-2.5 text-xs font-bold text-[#ffc36b] transition hover:bg-[#ffc36b]/22"
      >
        {t.applySelection}
      </button>
    </div>
  );
}
