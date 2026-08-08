"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Heart, Navigation } from "lucide-react";

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
  mapsUrl?: string;
  onLike?: () => void;
  isLiked?: boolean;
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
      mapsUrl,
      onLike,
      isLiked = false,
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
        {/* Background Image with Hover Zoom */}
        <img
          src={imageUrl}
          alt={title}
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-110"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.onerror = null;
            target.src = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=900&auto=format&fit=crop&q=80";
          }}
        />

        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/40 to-transparent" />

        {/* Action Header */}
        <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
          {mapsUrl && (
            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1.5 rounded-full bg-black/40 px-3 py-1.5 backdrop-blur-md border border-white/20 text-xs font-mono font-bold text-white transition-all hover:bg-[#39ff14] hover:text-black hover:border-[#39ff14]"
            >
              <Navigation className="h-3.5 w-3.5" />
              <span>Navigate</span>
            </a>
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
          <p className="text-xs font-mono font-semibold uppercase tracking-widest text-[#39ff14]">
            - {category} -
          </p>
          <h2 className="mt-1 text-2xl font-bold leading-tight tracking-tight text-white md:text-3xl line-clamp-2">
            {title}
          </h2>
        </div>
      </div>
    );
  }
);
DestinationCard.displayName = "DestinationCard";

export { DestinationCard };
