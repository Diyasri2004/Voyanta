"use client";

import { useState } from "react";
import { LanguageName } from "@/lib/i18n";
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

function SkeletonCardGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-4">
      {Array.from({ length: 8 }).map((_, idx) => (
        <div
          key={idx}
          className="relative grid h-full w-full overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/60 min-h-[420px] animate-pulse p-6 flex flex-col justify-end"
        >
          <div className="h-4 w-24 bg-zinc-800 rounded mb-3" />
          <div className="h-6 w-3/4 bg-zinc-800 rounded mb-2" />
          <div className="h-4 w-1/2 bg-zinc-800 rounded mb-6" />
          <div className="pt-3 border-t border-zinc-800 flex items-center justify-between gap-2">
            <div className="h-4 w-28 bg-zinc-800 rounded" />
            <div className="h-7 w-20 bg-zinc-800 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function PillarTab({
  items,
  destination,
  selectedLanguage = "English",
  onAddToPlan,
  isLoading = false,
}: {
  items: PillarItemData[];
  destination: string;
  selectedLanguage?: LanguageName;
  onAddToPlan?: (item: PillarItemData) => void;
  isLoading?: boolean;
}) {
  const [likedIds, setLikedIds] = useState<Record<string, boolean>>({});

  const toggleLike = (id: string) => {
    setLikedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (isLoading || !items || items.length === 0) {
    return <SkeletonCardGrid />;
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
