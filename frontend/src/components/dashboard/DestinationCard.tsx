"use client";

import React from "react";
import { MapPin, Navigation, Plus, Heart } from "lucide-react";

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
  isAdded?: boolean;
}

export const DestinationCard = ({
  item = {},
  destination = "",
  onAddToPlan,
  isLiked = false,
  onLike,
  isAdded = false,
}: DestinationCardProps) => {
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
    <div className="group relative bg-zinc-900/90 border border-zinc-800/80 hover:border-cyan-500/40 rounded-2xl overflow-hidden flex flex-col h-[380px] min-h-[380px] transition-all duration-300 hover:shadow-xl hover:shadow-cyan-500/10">
      {/* Background Image Container */}
      <div className="relative h-48 w-full overflow-hidden">
        <img
          src={imageUrl}
          alt={name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.onerror = null;
            target.src =
              "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=900&auto=format&fit=crop&q=80";
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/30 to-transparent" />

        {/* Top Badges */}
        <div className="absolute top-3 right-3 flex items-center gap-1.5 z-10">
          {onAddToPlan && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onAddToPlan(item);
              }}
              className={`p-1.5 rounded-full backdrop-blur-md transition-all active:scale-95 shadow-md ${
                isAdded ? "bg-cyan-500 text-white" : "bg-black/40 text-zinc-300 hover:bg-black/70"
              }`}
              title="Add to Itinerary Plan"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}

          {onLike && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onLike();
              }}
              className="p-1.5 rounded-full bg-black/40 text-zinc-300 hover:bg-white/30 backdrop-blur-md transition-all active:scale-95 shadow-md"
            >
              <Heart
                className={`w-4 h-4 transition-all ${
                  isLiked ? "fill-red-500 text-red-500" : "text-white"
                }`}
              />
            </button>
          )}
        </div>
      </div>

      {/* Card Content & Footer */}
      <div className="p-4 flex flex-col justify-between flex-1">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-cyan-400 font-semibold mb-1">
            {categoryText}
          </p>
          <h3 className="font-semibold text-base text-zinc-100 line-clamp-1 group-hover:text-cyan-400 transition-colors">
            {name}
          </h3>
          <p className="text-xs text-zinc-400 mt-1 line-clamp-2 leading-relaxed">
            {item.description || `Verified ${categoryText.toLowerCase()} venue in ${destination}.`}
          </p>
        </div>

        {/* Footer Container */}
        <div className="pt-3 mt-2 border-t border-zinc-800/80 flex items-center justify-between gap-2 w-full">
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
};

export default DestinationCard;
