"use client";

import { MapPin } from "lucide-react";

export interface CulinaryHighlightProps {
  title?: string;
  name?: string;
  famous_for?: string;
  specialty?: string;
  description?: string;
  location?: string;
  price_tier?: string;
  cost_approx?: string;
}

export default function CulinaryCard({
  highlight,
  destination,
}: {
  highlight: CulinaryHighlightProps;
  destination: string;
}) {
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
