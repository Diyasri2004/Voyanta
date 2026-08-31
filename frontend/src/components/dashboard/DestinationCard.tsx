"use client";

import React from "react";
import { Navigation, Plus, Heart, Check } from "lucide-react";

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
  index?: number;
  destination?: string;
  onLike?: () => void;
  isLiked?: boolean;
  onAddToPlan?: (item?: any) => void;
  isAdded?: boolean;
}

export const DestinationCard = ({
  item = {},
  index = 0,
  destination = "",
  onAddToPlan,
  isLiked = false,
  onLike,
  isAdded = false,
}: DestinationCardProps) => {
  const title = item.title || item.name || "Landmark";
  const locationText = item.location || item.address || (destination ? `${destination} Area` : "Local Area");
  const categoryText = item.category || "ATTRACTION";
  const imageUrl = item.image || item.image_url || "/fallback-travel.jpg";

  const navUrl =
    item.navigation_url ||
    item.maps_url ||
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      `${title}, ${locationText || ""}, ${destination}`
    )}`;

  return (
    <div
      style={{
        animation: "fadeInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        animationDelay: `${Math.min(index * 0.04, 0.6)}s`,
        opacity: 0,
      }}
      className="group relative flex flex-col rounded-2xl bg-neutral-900/80 border border-white/10 overflow-hidden shadow-lg transition-transform duration-300 hover:-translate-y-1 hover:border-pink-500/40 min-h-[380px]"
    >
      {/* Background Image Container */}
      <div className="relative h-48 w-full overflow-hidden bg-neutral-800 shrink-0">
        <img
          src={imageUrl}
          alt={title}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.onerror = null;
            target.src = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80";
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-neutral-950/80 via-transparent to-transparent pointer-events-none" />

        {/* Category Badge */}
        <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold bg-black/60 backdrop-blur-md text-pink-400 border border-white/10 uppercase tracking-wider">
          {categoryText}
        </span>

        {/* Action icons top-right */}
        <div className="absolute top-3 right-3 flex items-center gap-1.5 z-10">
          {onLike && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onLike();
              }}
              className="p-1.5 rounded-full bg-black/50 text-zinc-300 hover:bg-black/80 backdrop-blur-md transition-all active:scale-95 border border-white/10"
              title="Like venue"
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

      {/* Card Content */}
      <div className="p-4 flex flex-col flex-1 justify-between">
        <div>
          <h4 className="text-base font-bold text-white line-clamp-1 group-hover:text-pink-400 transition-colors">
            {title}
          </h4>
          <p className="mt-1.5 text-xs text-neutral-400 line-clamp-2 leading-relaxed">
            {item.description || `Verified authentic ${categoryText.toLowerCase()} spot in ${destination}.`}
          </p>
        </div>

        {/* Footer with Location & Buttons */}
        <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-neutral-400 gap-2">
          <span className="truncate max-w-[130px] flex items-center gap-1 text-neutral-400" title={locationText}>
            📍 {locationText}
          </span>
          <div className="flex items-center gap-1.5 shrink-0">
            <a
              href={navUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/15 text-neutral-300 transition-colors font-medium text-xs flex items-center gap-1 border border-white/10"
              title="View on Maps"
            >
              <Navigation className="w-3 h-3" />
              <span>Map</span>
            </a>
            {onAddToPlan && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onAddToPlan(item);
                }}
                className={`px-3 py-1 rounded-lg transition-colors font-medium text-xs flex items-center gap-1 ${
                  isAdded
                    ? "bg-pink-600 text-white"
                    : "bg-white/10 hover:bg-pink-600 hover:text-white text-gray-200"
                }`}
              >
                {isAdded ? (
                  <>
                    <Check className="w-3 h-3" /> Added
                  </>
                ) : (
                  <>
                    <Plus className="w-3 h-3" /> Add
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DestinationCard;
