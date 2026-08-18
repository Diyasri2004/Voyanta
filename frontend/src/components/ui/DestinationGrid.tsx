"use client";

import { DestinationCard } from "@/components/dashboard/DestinationCard";

export interface DestinationGridProps {
  items: Array<any>;
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
  const itemsToRender = items; // DO NOT use .slice()

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-4">
      {itemsToRender.map((item, idx) => {
        const itemId = item.id || `grid-card-${idx}`;
        return (
          <DestinationCard
            key={itemId}
            item={item}
            destination={destination}
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
