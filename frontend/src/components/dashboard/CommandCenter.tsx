"use client";

import TabController from "./TabController";

export const PILLARS = [
  { id: "attractions", label: "Tourist Attractions" },
  { id: "events", label: "Events" },
  { id: "culinary", label: "Culinary" },
  { id: "bars_pubs", label: "Bars & Pubs" },
  { id: "wellness", label: "Wellness & Meditation" },
  { id: "secret_spots", label: "Secret Spots" },
  { id: "essentials", label: "Travel Essentials" },
  { id: "shopping", label: "Shopping" },
  { id: "adventures", label: "Adventures" },
  { id: "theme_parks", label: "Theme Parks" },
  { id: "sacred_temples", label: "Temples & Shrines" }
];

export default function CommandCenter(props: any) {
  return <TabController {...props} />;
}
