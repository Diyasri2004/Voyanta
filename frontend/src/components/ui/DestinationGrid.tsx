"use client";

import { DestinationCard } from "@/components/dashboard/DestinationCard";

export interface DestinationGridProps {
  items: Array<any>;
  destination: string;
  onAddToPlan?: (item: any) => void;
  likedIds?: Record<string, boolean>;
  onToggleLike?: (id: string) => void;
  addedTitles?: string[];
}

export function DestinationGrid({
  items,
  destination,
  onAddToPlan,
  likedIds = {},
  onToggleLike,
  addedTitles = [],
}: DestinationGridProps) {
  const itemsToRender = items || [];

  return (
    <div className="grid grid-cols-1 gap-5 p-2 sm:grid-cols-2 sm:gap-6 md:p-4 lg:grid-cols-3 xl:grid-cols-4">
      {itemsToRender.map((place, idx) => {
        const itemId = place.id || `grid-card-${idx}`;
        return (
          <DestinationCard
            key={itemId}
            item={place}
            index={idx}
            destination={destination}
            isAdded={addedTitles.includes(place.title)}
            isLiked={!!likedIds[itemId]}
            onLike={onToggleLike ? () => onToggleLike(itemId) : undefined}
            onAddToPlan={onAddToPlan ? () => onAddToPlan(place) : undefined}
          />
        );
      })}
    </div>
  );
}

export default DestinationGrid;
