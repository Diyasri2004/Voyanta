"use client";

import { useState } from "react";
import { DestinationGrid } from "@/components/ui/DestinationGrid";
import { TravelerWaitIndicator } from "@/components/ui/traveler-wait-indicator";

export interface CulinaryPillarTabProps {
  items: Array<any>;
  destination: string;
  onAddToPlan?: (item: any) => void;
}

export default function CulinaryPillarTab({
  items,
  destination,
  onAddToPlan,
}: CulinaryPillarTabProps) {
  const [likedIds, setLikedIds] = useState<Record<string, boolean>>({});

  const toggleLike = (id: string) => {
    setLikedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (!items || items.length === 0) {
    return <TravelerWaitIndicator destination={destination} />;
  }

  const formattedItems = items.map((item, idx) => ({
    id: item.id || `culinary_${idx+1}`,
    title: item.title || item.name || "Specialty Eatery",
    name: item.name || item.title || "Specialty Eatery",
    category: item.category || "Culinary",
    description: item.description || "Verified authentic dining spot & specialty cuisine.",
    location: item.location || item.address || destination,
    address: item.address || item.location || destination,
    maps_url: item.maps_url || item.navigation_url,
    navigation_url: item.navigation_url || item.maps_url,
    image_url: item.image_url || item.image || "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80",
    image: item.image || item.image_url || "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80"
  }));

  return (
    <DestinationGrid
      items={formattedItems}
      destination={destination}
      onAddToPlan={onAddToPlan}
      likedIds={likedIds}
      onToggleLike={toggleLike}
    />
  );
}
