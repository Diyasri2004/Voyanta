"use client";

import { DestinationCard } from "./DestinationCard";

export interface CulinaryHighlightProps {
  id?: string;
  title?: string;
  name?: string;
  famous_for?: string;
  specialty?: string;
  description?: string;
  location?: string;
  address?: string;
  price_tier?: string;
  cost_approx?: string;
  navigation_url?: string;
  maps_url?: string;
  image_url?: string;
  image?: string;
}

export default function CulinaryCard({
  highlight,
  destination,
}: {
  highlight: CulinaryHighlightProps;
  destination: string;
}) {
  const item = {
    ...highlight,
    category: "Culinary Highlight",
    name: highlight.name || highlight.title || "Specialty Eatery",
    title: highlight.title || highlight.name || "Specialty Eatery",
    location: highlight.location || highlight.address || destination,
    image_url:
      highlight.image_url ||
      highlight.image ||
      "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&auto=format&fit=crop&q=80",
  };

  return <DestinationCard item={item} destination={destination} />;
}
