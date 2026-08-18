"use client";

import React from "react";
import { MapPin, Navigation, Heart, Plus } from "lucide-react";

export interface DestinationCardProps {
  item?: {
    id?: string;
    title?: string;
    name?: string;
    category?: string;
    description?: string;
    location?: string;
    address?: string;
    navigation_url?: string;
    maps_url?: string;
    image_url?: string;
    image?: string;
  };
  destination?: string;
  onLike?: () => void;
  isLiked?: boolean;
  onAddToPlan?: (item?: any) => void;
}

export function DestinationCard({
  item = {},
  destination = "",
  onLike,
  isLiked = false,
  onAddToPlan,
}: DestinationCardProps) {
  const name = item.name || item.title || "Landmark";
  const locationText = item.location || item.address || (destination ? `${destination} Area` : "Local Area");
  const categoryText = item.category || "ATTRACTION";
  const imageUrl =
    item.image_url ||
    item.image ||
    "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=900&auto=format&fit=crop&q=80";

  const navUrl =
    item.navigation_url ||
    item.maps_url ||
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      `${name}, ${locationText || ""}, ${destination}`
    )}`;

  return (
    <div className="relative grid h-full w-full transform-gpu overflow-hidden rounded-2xl border border-white/10 shadow-lg transition-all duration-300 ease-in-out group hover:shadow-2xl hover:border-[#39ff14]/40 min-h-[420px]">
      {/* Background Image with Hover Zoom */}
      <img
        src={imageUrl}
        alt={name}
        className="absolute inset-0 h-full w-full object-cover object-[center_25%] transition-transform duration-500 ease-out group-hover:scale-105"
        onError={(e) => {
          const target = e.target as HTMLImageElement;
          target.onerror = null;
          target.src =
            "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=900&auto=format&fit=crop&q=80";
        }}
      />

      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent" />

      {/* Action Header */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
        {onAddToPlan && (
          <button
            type="button"
            aria-label="Add to Itinerary Plan"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onAddToPlan(item);
            }}
            className="flex items-center justify-center w-8 h-8 rounded-full bg-black/60 backdrop-blur-md border border-white/20 text-white hover:bg-emerald-500 hover:text-black hover:border-emerald-500 transition-all active:scale-95 shadow-md"
            title="Add to Itinerary Plan"
          >
            <Plus className="w-4 h-4" />
          </button>
        )}

        {onLike && (
          <button
            type="button"
            aria-label={isLiked ? "Unlike place" : "Like place"}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onLike();
            }}
            className="rounded-full bg-black/40 p-2 backdrop-blur-md border border-white/20 transition-all hover:bg-white/30 active:scale-95"
          >
            <Heart
              className={`h-5 w-5 text-white transition-all ${
                isLiked ? "fill-red-500 text-red-500 border-none" : ""
              }`}
            />
          </button>
        )}
      </div>

      {/* Text Content */}
      <div className="relative z-10 flex h-full flex-col justify-end p-6 text-white transition-transform duration-500 ease-in-out group-hover:-translate-y-1">
        <p className="text-[11px] uppercase tracking-wider text-[#39ff14] font-semibold mb-1">
          {categoryText}
        </p>
        <h2 className="text-xl font-bold leading-tight tracking-tight text-white md:text-2xl line-clamp-2 drop-shadow-md mb-3">
          {name}
        </h2>

        {/* Footer Container */}
        <div className="pt-3 mt-3 border-t border-zinc-800/80 flex items-center justify-between gap-2 w-full">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 min-w-0 flex-1">
            <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <span className="truncate text-[11px] text-zinc-400 block">
              {locationText}
            </span>
          </div>

          <a
            href={navUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="shrink-0 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium hover:bg-cyan-500/20 transition-all flex items-center gap-1"
          >
            <Navigation className="w-3 h-3 shrink-0" />
            <span>Navigate</span>
          </a>
        </div>
      </div>
    </div>
  );
}

export default DestinationCard;
