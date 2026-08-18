"use client";

import { CurrencyProvider } from "@/context/CurrencyContext";
import { ItineraryProvider } from "@/context/ItineraryContext";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <CurrencyProvider>
      <ItineraryProvider>{children}</ItineraryProvider>
    </CurrencyProvider>
  );
}
