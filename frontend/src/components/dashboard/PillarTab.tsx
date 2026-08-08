"use client";

import { useState } from "react";
import { Navigation } from "lucide-react";
import { getTranslation, LanguageName } from "@/lib/i18n";
import { DestinationCard } from "@/components/ui/destination-card";
import { TravelerWaitIndicator } from "@/components/ui/traveler-wait-indicator";

export interface PillarItemData {
  id?: string;
  title: string;
  category: string;
  description: string;
  address?: string;
  maps_url?: string;
  image?: string;
  image_url?: string;
  serving_style?: string;
  event_time?: string;
  price_range?: string;
}

export default function PillarTab({
  items,
  destination,
  selectedLanguage = "English",
  onAddToPlan,
}: {
  items: PillarItemData[];
  destination: string;
  selectedLanguage?: LanguageName;
  onAddToPlan?: (item: PillarItemData) => void;
}) {
  const t = getTranslation(selectedLanguage);
  const [likedIds, setLikedIds] = useState<Record<string, boolean>>({});

  const toggleLike = (id: string) => {
    setLikedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (!items || items.length === 0) {
    return <TravelerWaitIndicator destination={destination} />;
  }

  const UNSPLASH_FALLBACK = "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=900&auto=format&fit=crop&q=80";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-4">
      {items.map((item, idx) => {
        const itemId = item.id || `pillar-card-${idx}`;
        const mapsUrl =
          item.maps_url ||
          `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
            `${item.title}, ${destination}`
          )}`;
        const imageUrl = item.image_url || item.image || UNSPLASH_FALLBACK;

        return (
          <DestinationCard
            key={itemId}
            title={item.title}
            category={item.category}
            imageUrl={imageUrl}
            mapsUrl={mapsUrl}
            isLiked={!!likedIds[itemId]}
            onLike={() => toggleLike(itemId)}
            onAddToPlan={onAddToPlan ? () => onAddToPlan(item) : undefined}
          />
        );
      })}
    </div>
  );
}
