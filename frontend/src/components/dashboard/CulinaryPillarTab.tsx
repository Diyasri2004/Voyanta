"use client";

import CulinaryCard from "@/components/ui/CulinaryCard";
import { TravelerWaitIndicator } from "@/components/ui/traveler-wait-indicator";

export interface CulinaryPillarTabProps {
  items: Array<{
    id?: string;
    name?: string;
    title?: string;
    specialty?: string;
    famous_for?: string;
    category?: string;
    description?: string;
    location?: string;
    address?: string;
    maps_url?: string;
  }>;
  destination: string;
  onAddToPlan?: (item: any) => void;
}

export default function CulinaryPillarTab({
  items,
  destination,
  onAddToPlan,
}: CulinaryPillarTabProps) {
  if (!items || items.length === 0) {
    return <TravelerWaitIndicator destination={destination} />;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-4">
      {items.map((item, idx) => {
        const itemId = item.id || `culinary-card-${idx}`;
        return (
          <CulinaryCard
            key={itemId}
            item={item}
            destination={destination}
            onAddToPlan={onAddToPlan}
          />
        );
      })}
    </div>
  );
}
