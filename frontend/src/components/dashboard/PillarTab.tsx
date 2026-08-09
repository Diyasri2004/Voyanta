"use client";

import { useState } from "react";
import { getTranslation, LanguageName } from "@/lib/i18n";
import { TravelerWaitIndicator } from "@/components/ui/traveler-wait-indicator";
import { DestinationGrid } from "@/components/ui/DestinationGrid";

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
  const [likedIds, setLikedIds] = useState<Record<string, boolean>>({});

  const toggleLike = (id: string) => {
    setLikedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (!items || items.length === 0) {
    return <TravelerWaitIndicator destination={destination} />;
  }

  return (
    <DestinationGrid
      items={items}
      destination={destination}
      onAddToPlan={onAddToPlan}
      likedIds={likedIds}
      onToggleLike={toggleLike}
    />
  );
}
