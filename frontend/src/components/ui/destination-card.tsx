"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Heart, MapPin, Navigation, Plus } from "lucide-react";

const cardVariants = cva(
  "relative grid h-full w-full transform-gpu overflow-hidden rounded-2xl border border-white/10 shadow-lg transition-all duration-300 ease-in-out group hover:shadow-2xl hover:border-[#39ff14]/40 min-h-[420px]",
  {
    variants: {},
    defaultVariants: {},
  }
);

export interface DestinationCardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  imageUrl: string;
  category: string;
  title: string;
  location?: string;
  mapsUrl?: string;
  destination?: string;
  onLike?: () => void;
  isLiked?: boolean;
  onAddToPlan?: () => void;
}

const DestinationCard = React.forwardRef<
  HTMLDivElement,
  DestinationCardProps
>(
  (
    {
      className,
      imageUrl,
      category,
      title,
      location,
      mapsUrl,
      destination = "",
      onLike,
      isLiked = false,
      onAddToPlan,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(cardVariants({ className }))}
        {...props}
      >
        {/* Background Image with Hover Zoom & Top Focus */}
        <img
          src={imageUrl}
          alt={title}
          className="absolute inset-0 h-full w-full object-cover object-[center_25%] transition-transform duration-500 ease-out group-hover:scale-105"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.onerror = null;
            target.src = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=900&auto=format&fit=crop&q=80";
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
                onAddToPlan();
              }}
              className="flex items-center justify-center w-8 h-8 rounded-full bg-black/60 backdrop-blur-md border border-white/20 text-white hover:bg-emerald-500 hover:text-black hover:border-emerald-500 transition-all active:scale-95 shadow-md"
              title="Add to Itinerary Plan"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}

          {onLike && (
            <button
              aria-label={isLiked ? "Unlike place" : "Like place"}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onLike();
              }}
              className="rounded-full bg-black/40 p-2 backdrop-blur-md border border-white/20 transition-all hover:bg-white/30 active:scale-95"
            >
              <Heart
                className={cn(
                  "h-5 w-5 text-white transition-all",
                  isLiked && "fill-red-500 text-red-500 border-none"
                )}
              />
            </button>
          )}
        </div>

        {/* Text Content */}
        <div className="relative z-10 flex h-full flex-col justify-end p-6 text-white transition-transform duration-500 ease-in-out group-hover:-translate-y-1">
          <p className="text-[11px] uppercase tracking-wider text-[#39ff14] font-semibold mb-1">
            {category}
          </p>
          <h2 className="text-xl font-bold leading-tight tracking-tight text-white md:text-2xl line-clamp-2 drop-shadow-md mb-3">
            {title}
          </h2>

          {/* Footer Container */}
          <div className="pt-3 border-t border-white/15 flex items-center justify-between gap-2 w-full">
            <div className="flex items-center gap-1 text-xs text-zinc-300 min-w-0 flex-1">
              <MapPin className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
              <span className="truncate text-[11px] text-zinc-300">
                {location || (destination ? `${destination} Area` : "Local Area")}
              </span>
            </div>

            <a
              href={mapsUrl || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${title}, ${location || ''}, ${destination}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="shrink-0 px-3 py-1.5 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-semibold hover:bg-cyan-500/40 transition-all flex items-center gap-1.5 backdrop-blur-md shadow-sm"
            >
              <Navigation className="w-3 h-3" />
              <span>Navigate</span>
            </a>
          </div>
        </div>
      </div>
    );
  }
);
DestinationCard.displayName = "DestinationCard";

export { DestinationCard };
