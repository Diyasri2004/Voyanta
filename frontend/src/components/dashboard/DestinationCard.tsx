"use client";

import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Navigation, Plus, Check, MapPin } from "lucide-react";
import TiltCard from "@/components/ui/TiltCard";

export interface DestinationCardProps {
  item?: {
    id?: string;
    title?: string;
    name?: string;
    category?: string;
    description?: string;
    location?: string;
    address?: string;
    lat?: number | string | null;
    lng?: number | string | null;
    navigation_url?: string;
    maps_url?: string;
    image_url?: string;
    image?: string;
    event_date?: string;
    in_trip?: boolean;
    event_note?: string;
    url?: string;
    source?: string;
    price_range?: string;
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
  const reduce = useReducedMotion();
  const title = item.title || item.name || "Landmark";
  // The label and the Map button must always describe the SAME place.
  // Real coordinates (from TomTom/OSM) are the only fully reliable source, so:
  //  - with coordinates: show the real street/area and open the map pinned there
  //  - events: show the real venue and open that venue
  //  - anything else (AI-written cards): never show a guessed neighbourhood;
  //    show the destination and search "<place>, <destination>".
  const lat = Number(item.lat);
  const lng = Number(item.lng);
  const hasCoords = item.lat != null && item.lng != null && Number.isFinite(lat) && Number.isFinite(lng) && !(lat === 0 && lng === 0);
  const isEvent = (item.category || "").toLowerCase() === "event";
  const locationText = hasCoords || isEvent
    ? item.address || item.location || destination || "Local Area"
    : destination || "Local Area";
  const categoryText = item.category || "ATTRACTION";
  const imageUrl = item.image || item.image_url || "";
  const [imageBroken, setImageBroken] = React.useState(false);

  const navUrl = hasCoords
    ? `https://www.google.com/maps/search/${encodeURIComponent(title)}/@${lat},${lng},17z`
    : isEvent && (item.navigation_url || item.maps_url)
      ? (item.navigation_url || item.maps_url)!
      : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${title}, ${destination}`)}`;

  const z = (px: number) => ({ transform: `translateZ(${px}px)` });

  return (
    <TiltCard max={9} lift={18} className="rounded-3xl">
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 36, rotateX: -16, scale: 0.96 }}
        whileInView={{ opacity: 1, y: 0, rotateX: 0, scale: 1 }}
        viewport={{ once: true, margin: "0px 0px -8% 0px" }}
        transition={{ duration: 0.7, delay: Math.min(index % 4, 3) * 0.08, ease: [0.16, 1, 0.3, 1] }}
        whileTap={{ scale: 0.985 }}
        className="group relative flex min-h-[400px] flex-col rounded-3xl [transform-style:preserve-3d]"
      >
        {/* ambient glow plate behind the card */}
        <div
          aria-hidden
          style={z(-20)}
          className="pointer-events-none absolute inset-3 rounded-3xl bg-[#ffc36b]/0 blur-2xl transition-colors duration-500 group-hover:bg-[#ffc36b]/25"
        />

        {/* card plate: photo + body surface */}
        <div className="absolute inset-0 overflow-hidden rounded-3xl border border-white/10 bg-[#0a1020]/90 shadow-[0_20px_50px_-20px_rgba(0,0,0,0.9)] transition-colors duration-500 group-hover:border-[#ffc36b]/40">
          <div className="relative h-52 w-full overflow-hidden bg-[#0f172a]">
            {imageUrl && !imageBroken ? (
              <img
                src={imageUrl}
                alt={title}
                loading="lazy"
                decoding="async"
                className="h-full w-full scale-110 object-cover transition-transform duration-[900ms] ease-out group-hover:scale-125"
                onError={() => setImageBroken(true)}
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-[radial-gradient(circle_at_50%_40%,#1a2442,#0a1020_70%)]">
                <MapPin className="h-10 w-10 text-[#ffc36b]/50" />
              </div>
            )}
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#0a1020] via-[#0a1020]/20 to-transparent" />
          </div>
        </div>

        {/* floating layers (these sit in front of the plate in 3D) */}
        <div className="relative h-52 shrink-0 [transform-style:preserve-3d]">
          <span
            style={z(28)}
            className="absolute left-4 top-4 rounded-full border border-white/15 bg-black/55 px-3 py-1 text-[11px] font-semibold tracking-wide text-[#ffd89a] backdrop-blur-md"
          >
            {categoryText}
          </span>
        </div>

        <div className="relative flex flex-1 flex-col justify-between p-5 pt-3 [transform-style:preserve-3d]">
          <div style={z(18)}>
            {item.event_date && <p className="mb-1 text-[11px] font-semibold text-[#7fd6ff] line-clamp-1">{item.event_date}</p>}
            {item.event_note && (
              <p className={`mb-1 text-[11px] font-semibold line-clamp-1 ${item.in_trip ? "text-emerald-300" : "text-[#ffc36b]"}`}>
                {item.event_note}
              </p>
            )}
            <h4 className="font-display text-[1.45rem] leading-[1.05] text-[#f6efe2] line-clamp-2 transition-colors group-hover:text-[#ffd89a]">
              {title}
            </h4>
            <p className="mt-2 line-clamp-2 text-[13px] leading-relaxed text-[#9aa5bb]">
              {item.description || `Verified authentic ${categoryText.toLowerCase()} spot in ${destination}.`}
            </p>
          </div>

          <div style={z(22)} className="mt-4 flex items-center gap-2 border-t border-white/[0.08] pt-3 text-xs text-[#8b95ab]">
            <div className="flex w-full items-center gap-2">
              <a
                href={navUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex h-10 flex-1 items-center justify-center gap-1.5 rounded-full border border-white/10 bg-white/[0.05] px-3 font-semibold text-[#cbd3e3] transition hover:bg-white/15"
                title="View on Maps"
              >
                <Navigation className="h-3.5 w-3.5" />
                Map
              </a>
              {isEvent && item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex h-9 items-center rounded-full border border-[#7fd6ff]/30 bg-[#7fd6ff]/10 px-3 font-semibold text-[#7fd6ff] transition hover:bg-[#7fd6ff]/20"
                  title={item.source ? `Source: ${item.source}` : "Event details"}
                >
                  Details
                </a>
              )}
              {onAddToPlan && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onAddToPlan(item);
                  }}
                  className={`flex h-10 flex-1 items-center justify-center gap-1.5 rounded-full px-3.5 font-bold transition ${
                    isAdded
                      ? "bg-[#ffc36b] text-[#1b1206]"
                      : "bg-[linear-gradient(115deg,#ffe2ae,#ffc36b_55%,#ff9d5c)] text-[#1b1206] hover:brightness-105"
                  }`}
                >
                  {isAdded ? (
                    <>
                      <Check className="h-3.5 w-3.5" /> Added
                    </>
                  ) : (
                    <>
                      <Plus className="h-3.5 w-3.5" /> Add
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </TiltCard>
  );
};

export default DestinationCard;
