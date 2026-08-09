"use client";

import { DestinationCard } from "@/components/ui/destination-card";

export interface DestinationGridProps {
  items: Array<{
    id?: string;
    title: string;
    category: string;
    description?: string;
    address?: string;
    maps_url?: string;
    image?: string;
    image_url?: string;
    serving_style?: string;
    event_time?: string;
    price_range?: string;
  }>;
  destination: string;
  onAddToPlan?: (item: any) => void;
  likedIds?: Record<string, boolean>;
  onToggleLike?: (id: string) => void;
}

export function DestinationGrid({
  items,
  destination,
  onAddToPlan,
  likedIds = {},
  onToggleLike,
}: DestinationGridProps) {
  const UNSPLASH_FALLBACK = "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=900&auto=format&fit=crop&q=80";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-4">
      {items.map((item, idx) => {
        const itemId = item.id || `grid-card-${idx}`;
        const address = item.address || "";
        const mapsUrl =
          item.maps_url ||
          `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
            [item.title, address, destination].filter(Boolean).join(", ")
          )}`;
        const imageUrl = item.image_url || item.image || UNSPLASH_FALLBACK;

        const locationText = (item as any).location || item.address || destination;

        return (
          <DestinationCard
            key={itemId}
            title={item.title}
            category={item.category}
            imageUrl={imageUrl}
            location={locationText}
            destination={destination}
            mapsUrl={mapsUrl}
            isLiked={!!likedIds[itemId]}
            onLike={onToggleLike ? () => onToggleLike(itemId) : undefined}
            onAddToPlan={onAddToPlan ? () => onAddToPlan(item) : undefined}
          />
        );
      })}
    </div>
  );
}

export default DestinationGrid;
