"use client";

import { MapPin } from "lucide-react";

export interface CulinaryItemProps {
  id?: string;
  name?: string;
  title?: string;
  specialty?: string;
  famous_for?: string;
  category?: string;
  description?: string;
  location?: string;
  address?: string;
  maps_url?: string;
}

export function CulinaryCard({
  item,
  destination,
  onAddToPlan,
}: {
  item: CulinaryItemProps;
  destination: string;
  onAddToPlan?: (item: any) => void;
}) {
  const name = item.name || item.title || "Specialty Eatery";
  const specialty = item.specialty || item.famous_for || (item.category !== "Culinary" ? item.category : "") || "";
  const description = item.description || "Verified authentic dining spot & specialty cuisine.";
  const location = item.location || item.address || destination;
  const mapsUrl =
    item.maps_url ||
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      `${name}, ${destination}`
    )}`;

  return (
    <div className="relative flex flex-col justify-between p-5 rounded-2xl bg-zinc-900/90 border border-zinc-800 hover:border-pink-500/30 transition-all duration-300 min-h-[220px]">
      <div className="space-y-2">
        <h3 className="text-lg font-bold text-white tracking-wide">{name}</h3>
        {specialty && (
          <span className="inline-block px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[11px] font-semibold tracking-wider uppercase">
            {specialty}
          </span>
        )}
        <p className="text-xs text-zinc-400 leading-relaxed pt-1 line-clamp-2">{description}</p>
      </div>

      <div className="pt-3 mt-3 border-t border-zinc-800/80 flex items-center justify-between gap-2 w-full">
        <div className="flex items-center gap-1 text-xs text-zinc-400 min-w-0 flex-1">
          <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          <span className="truncate text-[11px] text-zinc-400">
            {location || `${destination} Area`}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {onAddToPlan && (
            <button
              onClick={() => onAddToPlan(item)}
              className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-all shrink-0"
            >
              + Plan
            </button>
          )}
          <a
            href={mapsUrl}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium hover:bg-cyan-500/20 transition-all flex items-center gap-1"
          >
            <span>Navigate</span>
          </a>
        </div>
      </div>
    </div>
  );
}

export default CulinaryCard;
