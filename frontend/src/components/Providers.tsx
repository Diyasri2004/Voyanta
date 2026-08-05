"use client";

import { CurrencyProvider } from "@/context/CurrencyContext";

export default function Providers({ children }: { children: React.ReactNode }) {
  return <CurrencyProvider>{children}</CurrencyProvider>;
}
